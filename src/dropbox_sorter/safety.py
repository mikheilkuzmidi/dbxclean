"""
The rules that make this tool safe to run.

The web API this repository already contains deletes for real: local storage
calls os.remove and Dropbox storage calls files_delete_v2, both immediately and
irreversibly, and nothing in that path checks whether the file being removed is
the last surviving copy of its contents. Given a duplicate group, deleting
every path in it was entirely possible.

Everything here exists to make that impossible:

  * Nothing is destructive unless the caller explicitly opts in.
  * A duplicate group always keeps one member, chosen deterministically.
  * Removal means moving into a quarantine directory, not unlinking.
  * Every action is appended to a log that can be read back and reversed.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

QUARANTINE_DIRNAME = ".dropbox-sorter-quarantine"
OPLOG_NAME = "operations.jsonl"


def content_hash(path: Path, chunk: int = 1 << 20) -> str:
    """
    SHA-256 of the file's bytes.

    Duplicate detection has to be by content. Matching on name and size alone
    calls two different files identical whenever they happen to agree, and the
    consequence of that mistake here is a deleted file.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


@dataclass
class DuplicateGroup:
    """Files that share byte-identical contents."""

    digest: str
    paths: list[Path] = field(default_factory=list)
    _keeper: Path | None = field(default=None, repr=False)
    _sizes: dict[Path, int] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        # Sizes are read once, while every path still exists. Reading them
        # later would fail as soon as the first file has been moved.
        for path in self.paths:
            try:
                self._sizes[path] = path.stat().st_size
            except OSError:
                self._sizes[path] = 0

    @property
    def keeper(self) -> Path:
        """
        The copy that is never touched.

        Decided once and remembered. It used to be recomputed on every access
        from a stat() of all members, which raised FileNotFoundError the moment
        the first sibling was moved, part way through the very operation that
        depends on knowing which file to keep.

        Deterministic on purpose: shallowest path, then oldest, then
        alphabetical. A second run makes the same choice.
        """
        if self._keeper is None:
            self._keeper = sorted(
                self.paths,
                key=lambda p: (
                    len(p.parts),
                    p.stat().st_mtime if p.exists() else 0,
                    str(p),
                ),
            )[0]
        return self._keeper

    @property
    def removable(self) -> list[Path]:
        keeper = self.keeper
        return [p for p in self.paths if p != keeper]

    @property
    def reclaimable_bytes(self) -> int:
        return sum(self._sizes.get(p, 0) for p in self.removable)


class Quarantine:
    """
    Where removed files go instead of being deleted.

    Nothing leaves the filesystem. The original path is recorded alongside each
    move, so restore is a rename back, and the whole operation can be undone
    without a backup.
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.dir = self.root / QUARANTINE_DIRNAME
        self.oplog = self.dir / OPLOG_NAME

    def _record(self, entry: dict) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        with self.oplog.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")

    def hold(self, path: Path, *, digest: str, keeper: Path) -> Path:
        """Move one file into quarantine and record how to put it back."""
        relative = path.relative_to(self.root)
        target = self.dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)

        # Never overwrite something already quarantined under the same name.
        if target.exists():
            stem, suffix = target.stem, target.suffix
            counter = 2
            while target.exists():
                target = target.with_name(f"{stem}.{counter}{suffix}")
                counter += 1

        shutil.move(str(path), str(target))
        self._record(
            {
                "at": datetime.now(timezone.utc).isoformat(),
                "action": "quarantine",
                "from": str(path),
                "to": str(target),
                "digest": digest,
                "kept": str(keeper),
            }
        )
        return target

    def restore_all(self) -> list[tuple[Path, Path]]:
        """Put every quarantined file back where it came from."""
        if not self.oplog.exists():
            return []
        restored: list[tuple[Path, Path]] = []
        for line in self.oplog.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("action") != "quarantine":
                continue
            src, dst = Path(entry["to"]), Path(entry["from"])
            if src.exists() and not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                restored.append((src, dst))
        if restored:
            self._record(
                {
                    "at": datetime.now(timezone.utc).isoformat(),
                    "action": "restore",
                    "count": len(restored),
                }
            )
        return restored


def find_duplicates(root: Path, *, skip_hidden: bool = True) -> list[DuplicateGroup]:
    """
    Group files under root by content.

    Size is compared first because it is free, and only files that agree on size
    are hashed. The quarantine directory is skipped so a second run does not
    rediscover what the first one set aside.
    """
    by_size: dict[int, list[Path]] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        if QUARANTINE_DIRNAME in Path(dirpath).parts:
            continue
        if skip_hidden:
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for name in filenames:
            if skip_hidden and name.startswith("."):
                continue
            path = Path(dirpath) / name
            try:
                if path.is_symlink() or not path.is_file():
                    continue
                by_size.setdefault(path.stat().st_size, []).append(path)
            except OSError:
                continue

    groups: list[DuplicateGroup] = []
    for size, candidates in by_size.items():
        if size == 0 or len(candidates) < 2:
            continue
        by_digest: dict[str, list[Path]] = {}
        for path in candidates:
            try:
                by_digest.setdefault(content_hash(path), []).append(path)
            except OSError:
                continue
        for digest, paths in by_digest.items():
            if len(paths) > 1:
                groups.append(DuplicateGroup(digest=digest, paths=sorted(paths)))

    groups.sort(key=lambda g: g.reclaimable_bytes, reverse=True)
    return groups
