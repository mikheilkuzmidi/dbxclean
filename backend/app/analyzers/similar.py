"""Similar image detection using perceptual hashing"""

import imagehash
from PIL import Image
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from sqlalchemy.orm import Session
from ..models import FileMetadata, SimilarGroup
from ..config import settings


class SimilarImageDetector:
    """Detect similar images using perceptual hashing"""

    def __init__(self, db: Session):
        self.db = db
        self.hash_size = settings.perceptual_hash_size
        self.similarity_threshold = settings.similarity_threshold

    def compute_perceptual_hash(self, image: Image.Image) -> str:
        """Compute perceptual hash for an image"""
        # Use phash (more discriminative than average_hash for complex scenes)
        try:
            ph = imagehash.phash(image, hash_size=self.hash_size)
            return str(ph)
        except Exception as e:
            print(f"Error computing hash: {e}")
            return None

    def hamming_distance(self, hash1: str, hash2: str) -> int:
        """Calculate Hamming distance between two hashes"""
        try:
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)
            return h1 - h2
        except:
            return 999  # Return large number if comparison fails

    def find_similar_images(self) -> List[Dict]:
        """Find similar images in the database"""
        # Get all images with perceptual hashes
        images = self.db.query(FileMetadata).filter(
            FileMetadata.is_image == True,
            FileMetadata.perceptual_hash.isnot(None)
        ).all()

        if not images:
            return []

        # Compare all pairs to find similar images
        similar_groups = []
        processed = set()

        for i, img1 in enumerate(images):
            if img1.path in processed:
                continue

            similar_to_img1 = [img1]

            for img2 in images[i + 1:]:
                if img2.path in processed:
                    continue

                distance = self.hamming_distance(
                    img1.perceptual_hash,
                    img2.perceptual_hash
                )

                if distance <= self.similarity_threshold:
                    similar_to_img1.append(img2)
                    processed.add(img2.path)

            if len(similar_to_img1) > 1:
                processed.add(img1.path)
                group = self._create_similar_group(similar_to_img1)
                similar_groups.append(group)

        # Save to database
        self._save_similar_groups(similar_groups)

        return similar_groups

    def _create_similar_group(self, images: List[FileMetadata]) -> Dict:
        """Create a similar image group with quality ranking and distance metrics"""
        # Use the first image's hash as representative
        representative_hash = images[0].perceptual_hash

        # Sort by quality score (highest first)
        images_sorted = sorted(
            images,
            key=lambda x: x.quality_score or 0,
            reverse=True
        )

        best_quality = images_sorted[0]

        # 64 bits for an 8x8 hash
        max_bits = self.hash_size * self.hash_size

        files_data = []
        for img in images_sorted:
            dist = self.hamming_distance(representative_hash, img.perceptual_hash)
            # Similarity as 0.0 to 1.0 where 1.0 is identical
            similarity = max(0.0, 1.0 - (dist / max_bits)) if dist != 999 else 0.0
            files_data.append({
                "path": img.path,
                "name": img.name,
                "size": img.size,
                "width": img.width,
                "height": img.height,
                "quality_score": img.quality_score,
                "is_best_quality": img.path == best_quality.path,
                "distance": dist,
                "similarity_score": round(similarity, 3),
            })

        return {
            "representative_hash": representative_hash,
            "files": files_data,
            "file_count": len(images),
            "best_quality_path": best_quality.path,
        }

    def _save_similar_groups(self, groups: List[Dict]):
        """Save similar groups to database"""
        # Clear existing groups
        self.db.query(SimilarGroup).delete()

        for group in groups:
            # Compute similarity matrix
            similarity_scores = {}
            files = group["files"]

            for i, f1 in enumerate(files):
                for f2 in files[i + 1:]:
                    key = f"{f1['path']}|{f2['path']}"
                    # Placeholder - could compute actual similarity
                    similarity_scores[key] = 0.9

            db_group = SimilarGroup(
                representative_hash=group["representative_hash"],
                file_paths=[f["path"] for f in group["files"]],
                similarity_scores=similarity_scores,
                best_quality_path=group["best_quality_path"],
            )
            self.db.add(db_group)

        self.db.commit()

    def get_similar_stats(self) -> Dict:
        """Get statistics about similar images"""
        groups = self.db.query(SimilarGroup).all()

        total_similar = sum(len(g.file_paths) - 1 for g in groups)  # Exclude best quality

        # Calculate potential space savings (keep best, delete others)
        total_space_can_save = 0
        for group in groups:
            file_paths = group.file_paths
            best_path = group.best_quality_path

            for path in file_paths:
                if path != best_path:
                    file = self.db.query(FileMetadata).filter(FileMetadata.path == path).first()
                    if file:
                        total_space_can_save += file.size

        return {
            "similar_groups": len(groups),
            "total_similar_files": total_similar,
            "space_can_save_bytes": total_space_can_save,
            "space_can_save_gb": round(total_space_can_save / (1024 ** 3), 2),
        }

    def merge_similar_with_duplicates(self, duplicate_groups: List[Dict]) -> List[Dict]:
        """Merge similar groups, excluding exact duplicates"""
        duplicate_hashes = {g["group_hash"] for g in duplicate_groups}

        # Only return similar groups that aren't exact duplicates
        similar = self.find_similar_images()

        filtered = []
        for group in similar:
            # Check if any file in the group is an exact duplicate
            is_duplicate = False
            for file_data in group["files"]:
                file = self.db.query(FileMetadata).filter(
                    FileMetadata.path == file_data["path"]
                ).first()
                if file and file.content_hash in duplicate_hashes:
                    is_duplicate = True
                    break

            if not is_duplicate:
                filtered.append(group)

        return filtered
