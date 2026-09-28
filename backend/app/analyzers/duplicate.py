"""Exact duplicate detection from provider content hashes."""

from typing import Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import DuplicateGroup, FileMetadata


class DuplicateDetector:
    def __init__(self, db: Session):
        self.db = db

    def rebuild_groups(self) -> int:
        """Group only duplicate hashes, keeping the complete listing in SQLite."""
        self.db.query(DuplicateGroup).delete()
        hashes = (
            self.db.query(FileMetadata.content_hash)
            .filter(FileMetadata.content_hash.isnot(None), FileMetadata.content_hash != "")
            .group_by(FileMetadata.content_hash)
            .having(func.count(FileMetadata.id) > 1)
        )
        count = 0
        for (content_hash,) in hashes.yield_per(100):
            files = (
                self.db.query(FileMetadata)
                .filter(FileMetadata.content_hash == content_hash)
                .order_by(FileMetadata.path)
                .all()
            )
            group = self._create_duplicate_group(content_hash, files)
            self.db.add(DuplicateGroup(
                group_hash=content_hash,
                file_paths=[f.path for f in files],
                total_size=group["total_size"],
                file_count=len(files),
                recommended_keep=group["recommended_keep"],
            ))
            count += 1
            if count % 100 == 0:
                self.db.commit()
        self.db.commit()
        return count

    def find_duplicates(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Read one page of stored groups and their current file metadata."""
        groups = (
            self.db.query(DuplicateGroup)
            .order_by(DuplicateGroup.id)
            .offset(offset)
            .limit(limit)
            .all()
        )
        result = []
        for group in groups:
            files = (
                self.db.query(FileMetadata)
                .filter(FileMetadata.path.in_(group.file_paths))
                .order_by(FileMetadata.path)
                .all()
            )
            if len(files) > 1:
                result.append(self._create_duplicate_group(group.group_hash, files))
        return result

    def _create_duplicate_group(self, content_hash: str, files: List[FileMetadata]) -> Dict:
        recommended = self._recommend_file_to_keep(files)
        total_size = sum(f.size for f in files)
        return {
            "group_hash": content_hash,
            "files": [
                {
                    "path": f.path,
                    "name": f.name,
                    "size": f.size,
                    "is_image": f.is_image,
                    "modified": f.modified.isoformat() if f.modified else None,
                    "is_recommended": f.path == recommended,
                }
                for f in files
            ],
            "file_count": len(files),
            "total_size": total_size,
            "space_can_save": total_size - files[0].size,
            "recommended_keep": recommended,
        }

    def _recommend_file_to_keep(self, files: List[FileMetadata]) -> str:
        def score(file):
            generic = ['img_', 'image', 'screenshot', 'copy', 'untitled', 'photo']
            penalty = 50 if any(p in file.name.lower() for p in generic) else 0
            recency = file.modified.timestamp() / 1000000 if file.modified else 0
            return (-file.path.count('/') * 10 - penalty + recency, file.path)

        return max(files, key=score).path

    def get_duplicate_stats(self) -> Dict:
        count, files, total, retained = self.db.query(
            func.count(DuplicateGroup.id),
            func.coalesce(func.sum(DuplicateGroup.file_count - 1), 0),
            func.coalesce(func.sum(DuplicateGroup.total_size), 0),
            func.coalesce(func.sum(DuplicateGroup.total_size / DuplicateGroup.file_count), 0),
        ).one()
        wasted_bytes = int(total - retained)
        return {
            "duplicate_groups": count,
            "total_duplicate_files": files,
            "space_wasted_bytes": wasted_bytes,
            "space_wasted_gb": round(wasted_bytes / (1024 ** 3), 2),
        }
