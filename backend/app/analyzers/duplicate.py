"""Duplicate file detection"""

from typing import List, Dict, Set
from collections import defaultdict
from sqlalchemy.orm import Session
from ..models import FileMetadata, DuplicateGroup


class DuplicateDetector:
    """Detect duplicate files based on content hash"""

    def __init__(self, db: Session):
        self.db = db

    def find_duplicates(self) -> List[Dict]:
        """Find all duplicate files in the database"""
        # Group files by content hash
        hash_groups = defaultdict(list)

        all_files = self.db.query(FileMetadata).filter(
            FileMetadata.content_hash.isnot(None)
        ).all()

        for file in all_files:
            if file.content_hash:
                hash_groups[file.content_hash].append(file)

        # Filter to only groups with duplicates
        duplicate_groups = []
        for content_hash, files in hash_groups.items():
            if len(files) > 1:
                group_data = self._create_duplicate_group(content_hash, files)
                duplicate_groups.append(group_data)

        # Save to database
        self._save_duplicate_groups(duplicate_groups)

        return duplicate_groups

    def _create_duplicate_group(self, content_hash: str, files: List[FileMetadata]) -> Dict:
        """Create a duplicate group with recommendations"""
        file_paths = [f.path for f in files]
        total_size = sum(f.size for f in files)
        space_can_save = total_size - files[0].size  # Keep one, delete others

        # Recommend which file to keep (prefer shorter paths, better names)
        recommended = self._recommend_file_to_keep(files)

        return {
            "group_hash": content_hash,
            "files": [
                {
                    "path": f.path,
                    "name": f.name,
                    "size": f.size,
                    "modified": f.modified.isoformat() if f.modified else None,
                    "is_recommended": f.path == recommended,
                }
                for f in files
            ],
            "file_count": len(files),
            "total_size": total_size,
            "space_can_save": space_can_save,
            "recommended_keep": recommended,
        }

    def _recommend_file_to_keep(self, files: List[FileMetadata]) -> str:
        """Recommend which file to keep based on various criteria"""
        # Scoring factors:
        # 1. Shorter path depth (prefer root files)
        # 2. Better filename (not IMG_xxxx, Screenshot, etc.)
        # 3. Most recent modification date

        def score_file(file: FileMetadata) -> float:
            score = 0

            # Prefer shorter paths
            path_depth = file.path.count('/')
            score -= path_depth * 10

            # Penalize generic names
            generic_patterns = ['img_', 'image', 'screenshot', 'copy', 'untitled', 'photo']
            name_lower = file.name.lower()
            if any(pattern in name_lower for pattern in generic_patterns):
                score -= 50

            # Prefer more recent files (slight bonus)
            if file.modified:
                # Newer files get slight bonus
                score += file.modified.timestamp() / 1000000

            return score

        scored = [(score_file(f), f) for f in files]
        scored.sort(reverse=True)
        return scored[0][1].path

    def _save_duplicate_groups(self, groups: List[Dict]):
        """Save duplicate groups to database"""
        # Clear existing groups
        self.db.query(DuplicateGroup).delete()

        for group in groups:
            db_group = DuplicateGroup(
                group_hash=group["group_hash"],
                file_paths=[f["path"] for f in group["files"]],
                total_size=group["total_size"],
                file_count=group["file_count"],
                recommended_keep=group["recommended_keep"],
            )
            self.db.add(db_group)

        self.db.commit()

    def get_duplicate_stats(self) -> Dict:
        """Get statistics about duplicates"""
        groups = self.db.query(DuplicateGroup).all()

        total_duplicates = sum(g.file_count - 1 for g in groups)  # Exclude one file per group
        total_space_wasted = sum(g.total_size - (g.total_size // g.file_count) for g in groups)

        return {
            "duplicate_groups": len(groups),
            "total_duplicate_files": total_duplicates,
            "space_wasted_bytes": total_space_wasted,
            "space_wasted_gb": round(total_space_wasted / (1024 ** 3), 2),
        }
