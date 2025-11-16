"""Image quality scoring"""

from PIL import Image, ImageFilter
import numpy as np
from typing import Dict


class ImageQualityScorer:
    """Score image quality based on multiple factors"""

    def compute_quality_score(self, image: Image.Image, file_size: int) -> float:
        """
        Compute overall quality score for an image

        Factors:
        - Resolution (higher is better)
        - Sharpness (Laplacian variance)
        - File size per pixel (compression quality indicator)
        - Aspect ratio (penalize extreme stretching)

        Returns score from 0-100
        """
        try:
            scores = {
                'resolution': self._score_resolution(image),
                'sharpness': self._score_sharpness(image),
                'compression': self._score_compression(image, file_size),
                'aspect': self._score_aspect_ratio(image),
            }

            # Weighted average
            weights = {
                'resolution': 0.35,
                'sharpness': 0.30,
                'compression': 0.25,
                'aspect': 0.10,
            }

            total_score = sum(scores[k] * weights[k] for k in scores)
            return round(total_score, 2)

        except Exception as e:
            print(f"Error computing quality score: {e}")
            return 50.0  # Default mid-range score

    def _score_resolution(self, image: Image.Image) -> float:
        """Score based on resolution (megapixels)"""
        width, height = image.size
        megapixels = (width * height) / 1_000_000

        # Score curve: 0-1MP=0-30, 1-4MP=30-60, 4-12MP=60-90, 12+MP=90-100
        if megapixels < 1:
            return megapixels * 30
        elif megapixels < 4:
            return 30 + (megapixels - 1) * 10
        elif megapixels < 12:
            return 60 + (megapixels - 4) * 3.75
        else:
            return min(100, 90 + (megapixels - 12) * 0.5)

    def _score_sharpness(self, image: Image.Image) -> float:
        """Score based on sharpness using Laplacian variance"""
        try:
            # Convert to grayscale
            if image.mode != 'L':
                gray = image.convert('L')
            else:
                gray = image

            # Resize if too large (for performance)
            if gray.size[0] > 1024 or gray.size[1] > 1024:
                gray.thumbnail((1024, 1024))

            # Apply Laplacian filter
            laplacian = gray.filter(ImageFilter.FIND_EDGES)

            # Calculate variance
            np_img = np.array(laplacian)
            variance = np_img.var()

            # Map variance to 0-100 score
            # Typical range: 0-500 variance for most images
            score = min(100, (variance / 500) * 100)
            return score

        except Exception as e:
            print(f"Error computing sharpness: {e}")
            return 50.0

    def _score_compression(self, image: Image.Image, file_size: int) -> float:
        """Score based on compression quality (bytes per pixel)"""
        try:
            width, height = image.size
            total_pixels = width * height

            if total_pixels == 0:
                return 50.0

            bytes_per_pixel = file_size / total_pixels

            # Good quality JPEG: 0.5-3 bytes/pixel
            # PNG: 2-8 bytes/pixel
            # Over-compressed: < 0.3 bytes/pixel
            # Uncompressed/RAW: > 10 bytes/pixel

            if bytes_per_pixel < 0.3:
                return bytes_per_pixel * 100  # Penalize over-compression
            elif bytes_per_pixel < 3:
                return 80 + (bytes_per_pixel - 0.3) * 7.4  # Good range
            else:
                return max(50, 100 - (bytes_per_pixel - 3) * 2)  # Penalize bloat

        except Exception as e:
            print(f"Error computing compression score: {e}")
            return 50.0

    def _score_aspect_ratio(self, image: Image.Image) -> float:
        """Score based on aspect ratio (penalize extreme stretching)"""
        width, height = image.size

        if height == 0:
            return 0

        aspect = width / height

        # Ideal aspects: 1:1, 4:3, 3:2, 16:9, 9:16
        ideal_aspects = [1.0, 4/3, 3/2, 16/9, 9/16, 2/3, 3/4]

        # Find closest ideal aspect
        min_diff = min(abs(aspect - ideal) for ideal in ideal_aspects)

        # Score based on difference from ideal
        if min_diff < 0.1:
            return 100
        elif min_diff < 0.3:
            return 80
        elif min_diff < 0.5:
            return 60
        else:
            return max(20, 60 - (min_diff - 0.5) * 40)

    def compare_images(self, img1_data: Dict, img2_data: Dict) -> str:
        """
        Compare two images and return which is better quality

        Returns: 'first', 'second', or 'similar'
        """
        score1 = img1_data.get('quality_score', 0)
        score2 = img2_data.get('quality_score', 0)

        diff = abs(score1 - score2)

        if diff < 5:
            return 'similar'
        elif score1 > score2:
            return 'first'
        else:
            return 'second'

    def get_quality_metrics(self, image: Image.Image, file_size: int) -> Dict:
        """Get detailed quality metrics"""
        return {
            'overall_score': self.compute_quality_score(image, file_size),
            'resolution_score': self._score_resolution(image),
            'sharpness_score': self._score_sharpness(image),
            'compression_score': self._score_compression(image, file_size),
            'aspect_ratio_score': self._score_aspect_ratio(image),
            'dimensions': {
                'width': image.size[0],
                'height': image.size[1],
                'megapixels': round((image.size[0] * image.size[1]) / 1_000_000, 2)
            }
        }
