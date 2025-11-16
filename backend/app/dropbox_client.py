"""Dropbox API client wrapper"""

import dropbox
from dropbox.exceptions import ApiError, AuthError
from typing import List, Optional, Dict, Any
import io
from PIL import Image
import hashlib
from .config import settings


class DropboxClient:
    """Wrapper for Dropbox API with file analysis capabilities"""

    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or settings.dropbox_access_token
        if not self.access_token:
            raise ValueError("Dropbox access token is required")

        self.dbx = dropbox.Dropbox(self.access_token)

    def verify_connection(self) -> Dict[str, Any]:
        """Verify Dropbox connection and return account info"""
        try:
            account = self.dbx.users_get_current_account()
            return {
                "connected": True,
                "account_id": account.account_id,
                "name": account.name.display_name,
                "email": account.email,
            }
        except AuthError as e:
            return {"connected": False, "error": str(e)}

    def list_folder(self, path: str = "", recursive: bool = False) -> List[Dict[str, Any]]:
        """List files in a folder"""
        try:
            entries = []
            result = self.dbx.files_list_folder(path, recursive=recursive)

            while True:
                for entry in result.entries:
                    entry_data = self._parse_entry(entry)
                    entries.append(entry_data)

                if not result.has_more:
                    break

                result = self.dbx.files_list_folder_continue(result.cursor)

            return entries
        except ApiError as e:
            raise Exception(f"Error listing folder: {str(e)}")

    def _parse_entry(self, entry) -> Dict[str, Any]:
        """Parse Dropbox metadata entry"""
        data = {
            "name": entry.name,
            "path": entry.path_display,
            "id": entry.id if hasattr(entry, 'id') else None,
        }

        if isinstance(entry, dropbox.files.FileMetadata):
            data.update({
                "type": "file",
                "size": entry.size,
                "modified": entry.client_modified.isoformat() if entry.client_modified else None,
                "content_hash": entry.content_hash,
                "rev": entry.rev,
                "is_downloadable": True,
            })
        elif isinstance(entry, dropbox.files.FolderMetadata):
            data.update({
                "type": "folder",
                "is_downloadable": False,
            })

        return data

    def download_file(self, path: str) -> bytes:
        """Download file content"""
        try:
            _, response = self.dbx.files_download(path)
            return response.content
        except ApiError as e:
            raise Exception(f"Error downloading file: {str(e)}")

    def download_file_partial(self, path: str, start: int = 0, length: int = 1024 * 1024) -> bytes:
        """Download partial file content (for large files)"""
        try:
            _, response = self.dbx.files_download(path, start=start, length=length)
            return response.content
        except ApiError as e:
            raise Exception(f"Error downloading file: {str(e)}")

    def get_thumbnail(self, path: str, size: str = "w128h128") -> Optional[bytes]:
        """Get thumbnail for an image file"""
        try:
            # size options: w32h32, w64h64, w128h128, w256h256, w480h320, w640h480, w960h640, w1024h768, w2048h1536
            result = self.dbx.files_get_thumbnail_v2(
                dropbox.files.PathOrLink.path(path),
                format=dropbox.files.ThumbnailFormat.jpeg,
                size=dropbox.files.ThumbnailSize.w256h256,
            )
            return result.content
        except ApiError:
            return None

    def is_image(self, filename: str) -> bool:
        """Check if file is an image based on extension"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic'}
        return any(filename.lower().endswith(ext) for ext in image_extensions)

    def get_file_metadata(self, path: str) -> Dict[str, Any]:
        """Get detailed file metadata"""
        try:
            metadata = self.dbx.files_get_metadata(path)
            return self._parse_entry(metadata)
        except ApiError as e:
            raise Exception(f"Error getting metadata: {str(e)}")

    def delete_file(self, path: str) -> bool:
        """Delete a file from Dropbox"""
        try:
            self.dbx.files_delete_v2(path)
            return True
        except ApiError as e:
            raise Exception(f"Error deleting file: {str(e)}")

    def move_file(self, from_path: str, to_path: str) -> bool:
        """Move/rename a file in Dropbox"""
        try:
            self.dbx.files_move_v2(from_path, to_path)
            return True
        except ApiError as e:
            raise Exception(f"Error moving file: {str(e)}")

    def get_image_for_analysis(self, path: str, max_size_mb: Optional[int] = None) -> Optional[Image.Image]:
        """Download and open image for analysis (with size limit)"""
        try:
            # First check file size
            metadata = self.get_file_metadata(path)
            if not metadata.get('is_downloadable'):
                return None

            file_size = metadata.get('size', 0)
            max_size = (max_size_mb or settings.max_file_size_mb) * 1024 * 1024

            if file_size > max_size:
                # For large files, try to get thumbnail instead
                thumb_data = self.get_thumbnail(path, "w2048h1536")
                if thumb_data:
                    return Image.open(io.BytesIO(thumb_data))
                return None

            # Download full file
            file_data = self.download_file(path)
            return Image.open(io.BytesIO(file_data))
        except Exception as e:
            print(f"Error loading image {path}: {str(e)}")
            return None

    def compute_local_hash(self, content: bytes) -> str:
        """Compute Dropbox-style content hash"""
        block_size = 4 * 1024 * 1024  # 4MB blocks
        hash_digest = hashlib.sha256()

        for i in range(0, len(content), block_size):
            block = content[i:i + block_size]
            hash_digest.update(hashlib.sha256(block).digest())

        return hash_digest.hexdigest()
