"""File naming suggestions and improvements"""

import re
from typing import Optional, List
from datetime import datetime
import os


class FileNamingAnalyzer:
    """Analyze and suggest better file names"""

    def __init__(self):
        # Patterns of bad naming
        self.bad_patterns = [
            r'^IMG_\d+',  # IMG_1234
            r'^DSC\d+',   # DSC1234
            r'^Photo\s+\d+',  # Photo 123
            r'^Screenshot.*\d{4}-\d{2}-\d{2}',  # Screenshot 2024-01-01
            r'^Untitled',
            r'^Copy\s+of',
            r'^Copy\s+\(\d+\)',
            r'^\d{8}_\d{6}',  # 20240101_123456 (could be improved)
        ]

    def needs_rename(self, filename: str) -> bool:
        """Check if filename needs improvement"""
        name_without_ext = os.path.splitext(filename)[0]

        # Check against bad patterns
        for pattern in self.bad_patterns:
            if re.search(pattern, name_without_ext, re.IGNORECASE):
                return True

        # Check for very short names
        if len(name_without_ext) < 3:
            return True

        # Check for only numbers
        if name_without_ext.replace('_', '').replace('-', '').isdigit():
            return True

        # Check for excessive special characters
        special_chars = len(re.findall(r'[^a-zA-Z0-9\s\-_]', name_without_ext))
        if special_chars > len(name_without_ext) * 0.3:
            return True

        return False

    def suggest_name(
        self,
        current_name: str,
        path: str,
        modified_date: Optional[datetime] = None,
        context: Optional[str] = None
    ) -> Optional[str]:
        """Suggest a better filename"""
        if not self.needs_rename(current_name):
            return None

        name_without_ext = os.path.splitext(current_name)[0]
        extension = os.path.splitext(current_name)[1]

        # Extract any useful information from current name
        suggestions = []

        # Try to extract date from filename
        date_match = re.search(r'(\d{4})[_-]?(\d{2})[_-]?(\d{2})', name_without_ext)
        date_str = None

        if date_match:
            date_str = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
        elif modified_date:
            date_str = modified_date.strftime('%Y-%m-%d')

        # Use folder name as context
        folder_name = os.path.basename(os.path.dirname(path))
        if folder_name and folder_name != '/':
            # Clean folder name
            folder_clean = re.sub(r'[^\w\s-]', '', folder_name)
            folder_clean = re.sub(r'[\s_-]+', '_', folder_clean).strip('_')

            if date_str:
                suggestions.append(f"{folder_clean}_{date_str}{extension}")
            else:
                suggestions.append(f"{folder_clean}{extension}")

        # Generic date-based name
        if date_str:
            suggestions.append(f"photo_{date_str}{extension}")

        # If we have context (e.g., from image content analysis)
        if context:
            context_clean = re.sub(r'[^\w\s-]', '', context)
            context_clean = re.sub(r'[\s_-]+', '_', context_clean).strip('_')
            if date_str:
                suggestions.append(f"{context_clean}_{date_str}{extension}")
            else:
                suggestions.append(f"{context_clean}{extension}")

        # Return first suggestion or None
        return suggestions[0] if suggestions else None

    def clean_filename(self, filename: str) -> str:
        """Clean up a filename (remove special chars, normalize spaces)"""
        name_without_ext = os.path.splitext(filename)[0]
        extension = os.path.splitext(filename)[1]

        # Replace special characters with underscores
        cleaned = re.sub(r'[^\w\s\-]', '_', name_without_ext)

        # Normalize whitespace and underscores
        cleaned = re.sub(r'[\s_-]+', '_', cleaned)

        # Remove leading/trailing underscores
        cleaned = cleaned.strip('_')

        # Lowercase
        cleaned = cleaned.lower()

        return f"{cleaned}{extension}"

    def batch_rename_suggestions(
        self,
        files: List[dict],
        strategy: str = 'smart'
    ) -> List[dict]:
        """
        Generate batch rename suggestions

        Strategies:
        - 'smart': Use context and dates
        - 'sequential': Add sequential numbers
        - 'date': Use only dates
        - 'clean': Just clean up current names
        """
        suggestions = []

        for i, file in enumerate(files, 1):
            current_name = file.get('name', '')
            path = file.get('path', '')
            modified = file.get('modified')

            if modified and isinstance(modified, str):
                try:
                    modified = datetime.fromisoformat(modified.replace('Z', '+00:00'))
                except:
                    modified = None

            suggested = None

            if strategy == 'sequential':
                name_without_ext = os.path.splitext(current_name)[0]
                extension = os.path.splitext(current_name)[1]
                suggested = f"{name_without_ext}_{i:04d}{extension}"

            elif strategy == 'date':
                extension = os.path.splitext(current_name)[1]
                if modified:
                    date_str = modified.strftime('%Y-%m-%d')
                    suggested = f"photo_{date_str}_{i:04d}{extension}"

            elif strategy == 'clean':
                suggested = self.clean_filename(current_name)

            else:  # smart
                suggested = self.suggest_name(current_name, path, modified)

            suggestions.append({
                'original': current_name,
                'suggested': suggested or current_name,
                'needs_rename': suggested is not None,
                'path': path
            })

        return suggestions

    def validate_filename(self, filename: str) -> dict:
        """Validate a filename and return issues"""
        issues = []

        # Check length
        if len(filename) > 255:
            issues.append("Filename too long (max 255 characters)")

        # Check for illegal characters (Dropbox/Windows/Mac)
        illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in illegal_chars:
            if char in filename:
                issues.append(f"Contains illegal character: '{char}'")

        # Check for leading/trailing spaces
        if filename != filename.strip():
            issues.append("Has leading or trailing spaces")

        # Check for multiple consecutive spaces
        if '  ' in filename:
            issues.append("Has multiple consecutive spaces")

        return {
            'valid': len(issues) == 0,
            'issues': issues
        }
