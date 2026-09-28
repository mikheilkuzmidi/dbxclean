"""Local duplicate grouping and reversible CLI quarantine operations."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

QUARANTINE_DIRNAME = ".dbxclean-quarantine"
OPLOG_NAME = "operations.jsonl"


def move_without_replace(source: Path, target: Path) -> None:
    """Move a file on one filesystem without ever replacing the target."""
    os.link(source, target)
    try:
        source.unlink()
    except OSError:
        target.unlink()
        raise


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
        self.root = Path(root).resolve()
        self.dir = self.root / QUARANTINE_DIRNAME
        if self.dir.is_symlink():
            raise ValueError("Quarantine directory cannot be a symlink")
        self.oplog = self.dir / OPLOG_NAME

    def _record(self, entry: dict) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        with self.oplog.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")

    def hold(self, path: Path, *, digest: str, keeper: Path) -> Path:
        """Move one file into quarantine and record how to put it back."""
        relative = path.relative_to(self.root)
        if self.dir.is_symlink():
            raise ValueError("Quarantine directory cannot be a symlink")
        target = self.dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.parent.resolve().is_relative_to(self.dir.resolve()):
            raise ValueError("Quarantine path escaped its root")

        # Never overwrite something already quarantined under the same name.
        if target.exists():
            stem, suffix = target.stem, target.suffix
            counter = 2
            while target.exists():
                target = target.with_name(f"{stem}.{counter}{suffix}")
                counter += 1

        move_without_replace(path, target)
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
            result = self.restore_one(Path(entry["to"]), record=False)
            if result is not None:
                restored.append(result)
        if restored:
            self._record(
                {
                    "at": datetime.now(timezone.utc).isoformat(),
                    "action": "restore",
                    "count": len(restored),
                }
            )
        return restored

    def restore_one(self, target: Path, *, record: bool = True) -> tuple[Path, Path] | None:
        """Restore one logged file without replacing an existing destination."""
        if not self.oplog.exists():
            return None
        if Path(target).is_symlink():
            raise ValueError("Recovery path cannot be a symlink")
        target = Path(target).resolve()
        if not target.is_relative_to(self.dir.resolve()):
            raise ValueError("Recovery path is outside quarantine")
        entries = [json.loads(line) for line in self.oplog.read_text(encoding="utf-8").splitlines() if line.strip()]
        matching = [entry for entry in entries if entry.get("action") == "quarantine" and Path(entry["to"]).resolve() == target]
        if not matching:
            raise ValueError("Recovery path was not logged")
        original = Path(matching[-1]["from"])
        if not original.resolve().is_relative_to(self.root.resolve()):
            raise ValueError("Original path is outside scan root")
        if not target.exists():
            return None
        if original.exists() or original.is_symlink():
            raise FileExistsError(f"Restore destination already exists: {original}")
        original.parent.mkdir(parents=True, exist_ok=True)
        move_without_replace(target, original)
        if record:
            self._record({"at": datetime.now(timezone.utc).isoformat(), "action": "restore", "from": str(target), "to": str(original)})
        return target, original


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
