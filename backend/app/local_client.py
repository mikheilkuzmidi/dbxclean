"""Local filesystem client wrapper implementing the same interface as DropboxClient"""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import io
import hashlib

import rawpy
import numpy as np
from PIL import Image

from .config import settings


class LocalClient:
    """Local filesystem client with file analysis capabilities"""

    def __init__(self, root_path: Optional[str] = None):
        base = root_path or getattr(settings, "local_root", None)
        if not base:
            raise ValueError("Set LOCAL_ROOT before using local mode")
        self.root_path = Path(base).expanduser().resolve()
        if not self.root_path.is_dir():
            raise ValueError(f"Local root is not a directory: {self.root_path}")

    def verify_connection(self) -> Dict[str, Any]:
        return {
            "connected": True,
            "account_id": "local",
            "name": str(self.root_path),
            "email": None,
        }

    def _to_local_path(self, path: str) -> Path:
        normalized = (path or "").strip()
        if normalized.startswith("/"):
            normalized = normalized[1:]
        raw = (self.root_path / normalized) if normalized else self.root_path
        current = self.root_path
        for part in Path(normalized).parts:
            current = current / part
            if current.is_symlink():
                raise ValueError("Symlink paths are not supported")
        full = raw.resolve()
        if not full.is_relative_to(self.root_path):
            raise ValueError("Path outside of local root")
        return full

    def _relative_path(self, full_path: Path) -> str:
        rel = full_path.resolve().relative_to(self.root_path)
        return "/" + str(rel).replace(os.sep, "/")

    def compute_local_hash(self, content: bytes) -> str:
        block_size = 4 * 1024 * 1024
        hash_digest = hashlib.sha256()
        for i in range(0, len(content), block_size):
            block = content[i : i + block_size]
            hash_digest.update(hashlib.sha256(block).digest())
        return hash_digest.hexdigest()

    def _hash_path(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while block := handle.read(4 * 1024 * 1024):
                digest.update(hashlib.sha256(block).digest())
        return digest.hexdigest()

    def list_folder(self, path: str = "", recursive: bool = False) -> List[Dict[str, Any]]:
        return list(self.iter_folder(path, recursive=recursive))

    def iter_folder(self, path: str = "", recursive: bool = False):
        try:
            base_path = self._to_local_path(path)

            if recursive:
                for dirpath, dirnames, filenames in os.walk(base_path):
                    current_dir = Path(dirpath)
                    dirnames[:] = [name for name in dirnames if name != ".dbxclean-quarantine" and not (current_dir / name).is_symlink()]

                    for name in dirnames:
                        full = current_dir / name
                        data: Dict[str, Any] = {
                            "name": name,
                            "path": self._relative_path(full),
                            "id": None,
                            "type": "folder",
                            "is_downloadable": False,
                        }
                        yield data

                    for name in filenames:
                        full = current_dir / name
                        if full.is_symlink():
                            continue
                        stat = full.stat()
                        data = {
                            "name": name,
                            "path": self._relative_path(full),
                            "id": None,
                            "type": "file",
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "content_hash": self._hash_path(full),
                            "rev": None,
                            "is_downloadable": True,
                        }
                        yield data
            else:
                for child in base_path.iterdir():
                    if child.name == ".dbxclean-quarantine" or child.is_symlink():
                        continue
                    name = child.name
                    if child.is_dir():
                        data = {
                            "name": name,
                            "path": self._relative_path(child),
                            "id": None,
                            "type": "folder",
                            "is_downloadable": False,
                        }
                    else:
                        stat = child.stat()
                        data = {
                            "name": name,
                            "path": self._relative_path(child),
                            "id": None,
                            "type": "file",
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "content_hash": self._hash_path(child),
                            "rev": None,
                            "is_downloadable": True,
                        }
                    yield data
        except Exception as e:
            raise Exception(f"Error listing folder: {str(e)}")

    def is_image(self, filename: str) -> bool:
        image_extensions = {
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".heic",
            ".nef", ".cr2", ".arw", ".dng", ".orf", ".rw2",
        }
        lower = filename.lower()
        return any(lower.endswith(ext) for ext in image_extensions)

    def get_file_metadata(self, path: str) -> Dict[str, Any]:
        full = self._to_local_path(path)
        if not full.is_file():
            raise FileNotFoundError(str(full))
        stat = full.stat()
        return {
            "name": full.name,
            "path": self._relative_path(full),
            "id": None,
            "type": "file",
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "content_hash": self._hash_path(full),
            "rev": None,
            "is_downloadable": True,
        }

    def path_exists(self, path: str) -> bool:
        full = self._to_local_path(path)
        return full.exists() or full.is_symlink()

    @staticmethod
    def _move_without_replace(source: Path, target: Path) -> None:
        """Create the destination atomically, then remove the source link."""
        os.link(source, target)
        try:
            source.unlink()
        except OSError:
            target.unlink()
            raise

    def download_file(self, path: str) -> bytes:
        full = self._to_local_path(path)
        if not full.is_file():
            raise FileNotFoundError(str(full))
        with open(full, "rb") as f:
            return f.read()

    def get_thumbnail(self, path: str, size: str = "w128h128") -> Optional[bytes]:
        try:
            # Reuse analysis loader so RAW and standard formats behave the same
            image = self.get_image_for_analysis(path)
            if image is None:
                print(f"THUMB DEBUG: get_image_for_analysis returned None for {path}")
                return None

            image.thumbnail((256, 256))
            buf = io.BytesIO()
            image.save(buf, format="JPEG")
            return buf.getvalue()
        except Exception as e:
            print(f"THUMB ERROR: failed to build thumbnail for {path}: {e}")
            return None

    def delete_file(self, path: str) -> bool:
        raise RuntimeError("Permanent local deletion is disabled; use trash_file")

    def quarantine_path(self, path: str, token: str) -> Path:
        source = self._to_local_path(path)
        return self.root_path / ".dbxclean-quarantine" / "web" / token / source.relative_to(self.root_path)

    def recovery_exists(self, recovery_path: str) -> bool:
        raw_source = Path(recovery_path)
        if raw_source.is_symlink():
            return False
        source = raw_source.resolve()
        recovery_root = (self.root_path / ".dbxclean-quarantine" / "web").resolve()
        return source.is_relative_to(recovery_root) and source.is_file()

    def trash_file(self, path: str, token: str) -> str:
        source = self._to_local_path(path)
        if not source.is_file() or source.is_symlink():
            raise FileNotFoundError(str(source))
        quarantine = self.root_path / ".dbxclean-quarantine"
        web = quarantine / "web"
        if quarantine.is_symlink() or web.is_symlink():
            raise ValueError("Quarantine path cannot be a symlink")
        target = self.quarantine_path(path, token)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.parent.resolve().is_relative_to(web.resolve()):
            raise ValueError("Quarantine path escaped its root")
        if target.exists() or target.is_symlink():
            raise FileExistsError(str(target))
        self._move_without_replace(source, target)
        return str(target)

    def restore_file(self, path: str, recovery_path: str) -> None:
        target = self._to_local_path(path)
        raw_source = Path(recovery_path)
        if raw_source.is_symlink():
            raise ValueError("Recovery file cannot be a symlink")
        source = raw_source.resolve()
        recovery_root = (self.root_path / ".dbxclean-quarantine" / "web").resolve()
        if not source.is_relative_to(recovery_root) or not source.is_file():
            raise ValueError("Recovery file is missing or outside quarantine")
        if target.exists() or target.is_symlink():
            raise FileExistsError(str(target))
        target.parent.mkdir(parents=True, exist_ok=True)
        self._move_without_replace(source, target)

    def move_file(self, from_path: str, to_path: str) -> bool:
        src = self._to_local_path(from_path)
        dst = self._to_local_path(to_path)
        if dst.exists() or dst.is_symlink():
            raise FileExistsError(str(dst))
        if not src.is_file() or src.is_symlink():
            raise FileNotFoundError(str(src))
        dst.parent.mkdir(parents=True, exist_ok=True)
        self._move_without_replace(src, dst)
        return True

    def get_image_for_analysis(self, path: str, max_size_mb: Optional[int] = None) -> Optional[Image.Image]:
        try:
            full = self._to_local_path(path)
            if not full.is_file():
                return None
            stat = full.stat()
            max_size = (max_size_mb or settings.max_file_size_mb) * 1024 * 1024
            if stat.st_size > max_size:
                return None
            suffix = full.suffix.lower()
            raw_exts = {".nef", ".cr2", ".arw", ".dng", ".orf", ".rw2"}

            if suffix in raw_exts:
                # Decode RAW file via rawpy and convert to PIL Image
                with rawpy.imread(str(full)) as raw:
                    rgb = raw.postprocess(output_bps=8)
                return Image.fromarray(rgb)

            with open(full, "rb") as f:
                data = f.read()
            return Image.open(io.BytesIO(data))
        except Exception:
            return None
