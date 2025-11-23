"""Local filesystem client that matches Dropbox client interface"""

import os
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import io
from PIL import Image
import shutil
from .config import settings


class LocalFilesystemClient:
    """Local filesystem client with the same interface as DropboxClient"""

    def __init__(self, root_path: Optional[str] = None):
        """
        Initialize local filesystem client

        Args:
            root_path: Root directory to work with. Defaults to user's home directory.
        """
        self.root_path = Path(root_path or Path.home()).resolve()
        if not self.root_path.exists():
            raise ValueError(f"Root path does not exist: {self.root_path}")
        if not self.root_path.is_dir():
            raise ValueError(f"Root path is not a directory: {self.root_path}")

    def verify_connection(self) -> Dict[str, Any]:
        """Verify filesystem access and return info"""
        try:
            # Test read access
            _ = list(self.root_path.iterdir())
            return {
                "connected": True,
                "mode": "local",
                "root_path": str(self.root_path),
                "readable": os.access(self.root_path, os.R_OK),
                "writable": os.access(self.root_path, os.W_OK),
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}

    def _normalize_path(self, path: str) -> Path:
        """Convert Dropbox-style path to local filesystem path"""
        # Remove leading slash if present (Dropbox style)
        path = path.lstrip('/')

        # If empty, return root
        if not path:
            return self.root_path

        # Construct full path
        full_path = self.root_path / path
        return full_path.resolve()

    def _to_dropbox_path(self, local_path: Path) -> str:
        """Convert local filesystem path to Dropbox-style path"""
        try:
            rel_path = local_path.relative_to(self.root_path)
            # Convert to forward slashes and add leading slash
            return '/' + str(rel_path).replace(os.sep, '/')
        except ValueError:
            # Path is not relative to root
            return '/' + local_path.name

    def list_folder(self, path: str = "", recursive: bool = False) -> List[Dict[str, Any]]:
        """List files in a folder"""
        try:
            full_path = self._normalize_path(path)

            if not full_path.exists():
                raise Exception(f"Path does not exist: {path}")

            if not full_path.is_dir():
                raise Exception(f"Path is not a directory: {path}")

            entries = []

            if recursive:
                # Recursive listing
                for root, dirs, files in os.walk(full_path):
                    root_path = Path(root)

                    # Add directories
                    for dir_name in dirs:
                        dir_path = root_path / dir_name
                        try:
                            entry_data = self._parse_entry(dir_path)
                            entries.append(entry_data)
                        except Exception as e:
                            print(f"Error reading directory {dir_path}: {e}")

                    # Add files
                    for file_name in files:
                        file_path = root_path / file_name
                        try:
                            entry_data = self._parse_entry(file_path)
                            entries.append(entry_data)
                        except Exception as e:
                            print(f"Error reading file {file_path}: {e}")
            else:
                # Non-recursive listing
                for item in full_path.iterdir():
                    try:
                        entry_data = self._parse_entry(item)
                        entries.append(entry_data)
                    except Exception as e:
                        print(f"Error reading {item}: {e}")

            return entries
        except Exception as e:
            raise Exception(f"Error listing folder: {str(e)}")

    def _parse_entry(self, path: Path) -> Dict[str, Any]:
        """Parse filesystem entry to match Dropbox metadata format"""
        stat = path.stat()

        data = {
            "name": path.name,
            "path": self._to_dropbox_path(path),
            "id": str(hash(str(path))),  # Generate stable ID from path
        }

        if path.is_file():
            # Compute content hash for files
            content_hash = self._compute_file_hash(path)

            data.update({
                "type": "file",
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "content_hash": content_hash,
                "rev": str(stat.st_mtime),  # Use mtime as revision
                "is_downloadable": True,
            })
        elif path.is_dir():
            data.update({
                "type": "folder",
                "is_downloadable": False,
            })

        return data

    def _compute_file_hash(self, path: Path) -> str:
        """Compute Dropbox-style content hash for a file"""
        try:
            block_size = 4 * 1024 * 1024  # 4MB blocks
            hash_digests = []

            with open(path, 'rb') as f:
                while True:
                    block = f.read(block_size)
                    if not block:
                        break
                    hash_digests.append(hashlib.sha256(block).digest())

            if not hash_digests:
                return hashlib.sha256(b'').hexdigest()

            # Combine block hashes
            combined_hash = hashlib.sha256()
            for digest in hash_digests:
                combined_hash.update(digest)

            return combined_hash.hexdigest()
        except Exception as e:
            print(f"Error computing hash for {path}: {e}")
            return ""

    def download_file(self, path: str) -> bytes:
        """Read file content"""
        try:
            full_path = self._normalize_path(path)

            if not full_path.exists():
                raise Exception(f"File does not exist: {path}")

            if not full_path.is_file():
                raise Exception(f"Path is not a file: {path}")

            with open(full_path, 'rb') as f:
                return f.read()
        except Exception as e:
            raise Exception(f"Error reading file: {str(e)}")

    def download_file_partial(self, path: str, start: int = 0, length: int = 1024 * 1024) -> bytes:
        """Read partial file content"""
        try:
            full_path = self._normalize_path(path)

            if not full_path.exists():
                raise Exception(f"File does not exist: {path}")

            if not full_path.is_file():
                raise Exception(f"Path is not a file: {path}")

            with open(full_path, 'rb') as f:
                f.seek(start)
                return f.read(length)
        except Exception as e:
            raise Exception(f"Error reading file: {str(e)}")

    def get_thumbnail(self, path: str, size: str = "w128h128") -> Optional[bytes]:
        """Generate thumbnail for an image file"""
        try:
            full_path = self._normalize_path(path)

            if not full_path.exists() or not full_path.is_file():
                return None

            # Parse size (e.g., "w256h256" -> (256, 256))
            size_parts = size.replace('w', '').split('h')
            if len(size_parts) == 2:
                width = int(size_parts[0])
                height = int(size_parts[1])
            else:
                width, height = 256, 256

            # Open and resize image
            img = Image.open(full_path)
            img.thumbnail((width, height), Image.Resampling.LANCZOS)

            # Convert to JPEG bytes
            output = io.BytesIO()
            img.convert('RGB').save(output, format='JPEG', quality=85)
            return output.getvalue()
        except Exception as e:
            print(f"Error generating thumbnail for {path}: {e}")
            return None

    def is_image(self, filename: str) -> bool:
        """Check if file is an image based on extension"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic'}
        return any(filename.lower().endswith(ext) for ext in image_extensions)

    def get_file_metadata(self, path: str) -> Dict[str, Any]:
        """Get detailed file metadata"""
        try:
            full_path = self._normalize_path(path)

            if not full_path.exists():
                raise Exception(f"Path does not exist: {path}")

            return self._parse_entry(full_path)
        except Exception as e:
            raise Exception(f"Error getting metadata: {str(e)}")

    def delete_file(self, path: str) -> bool:
        """Delete a file from filesystem"""
        try:
            full_path = self._normalize_path(path)

            if not full_path.exists():
                raise Exception(f"Path does not exist: {path}")

            if full_path.is_file():
                full_path.unlink()
            elif full_path.is_dir():
                shutil.rmtree(full_path)

            return True
        except Exception as e:
            raise Exception(f"Error deleting file: {str(e)}")

    def move_file(self, from_path: str, to_path: str) -> bool:
        """Move/rename a file in filesystem"""
        try:
            full_from_path = self._normalize_path(from_path)
            full_to_path = self._normalize_path(to_path)

            if not full_from_path.exists():
                raise Exception(f"Source path does not exist: {from_path}")

            # Create parent directory if it doesn't exist
            full_to_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.move(str(full_from_path), str(full_to_path))
            return True
        except Exception as e:
            raise Exception(f"Error moving file: {str(e)}")

    def get_image_for_analysis(self, path: str, max_size_mb: Optional[int] = None) -> Optional[Image.Image]:
        """Open image for analysis (with size limit)"""
        try:
            full_path = self._normalize_path(path)

            if not full_path.exists() or not full_path.is_file():
                return None

            # Check file size
            file_size = full_path.stat().st_size
            max_size = (max_size_mb or settings.max_file_size_mb) * 1024 * 1024

            if file_size > max_size:
                # For large files, generate and use thumbnail
                thumb_data = self.get_thumbnail(path, "w2048h1536")
                if thumb_data:
                    return Image.open(io.BytesIO(thumb_data))
                return None

            # Open full image
            return Image.open(full_path)
        except Exception as e:
            print(f"Error loading image {path}: {str(e)}")
            return None

    def compute_local_hash(self, content: bytes) -> str:
        """Compute Dropbox-style content hash"""
        block_size = 4 * 1024 * 1024  # 4MB blocks
        hash_digests = []

        for i in range(0, len(content), block_size):
            block = content[i:i + block_size]
            hash_digests.append(hashlib.sha256(block).digest())

        if not hash_digests:
            return hashlib.sha256(b'').hexdigest()

        # Combine block hashes
        combined_hash = hashlib.sha256()
        for digest in hash_digests:
            combined_hash.update(digest)

        return combined_hash.hexdigest()
