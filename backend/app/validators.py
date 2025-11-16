"""Input validation utilities"""

import re
from typing import Optional
from fastapi import HTTPException


def validate_dropbox_path(path: str) -> str:
    """Validate and normalize Dropbox path"""
    if not path:
        return ""

    # Remove leading/trailing whitespace
    path = path.strip()

    # Empty path is valid (means root)
    if not path:
        return ""

    # Must start with /
    if not path.startswith('/'):
        path = '/' + path

    # Remove trailing slash
    if path.endswith('/') and path != '/':
        path = path.rstrip('/')

    # Check for invalid characters
    invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
    for char in invalid_chars:
        if char in path:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid character in path: {char}"
            )

    # Check length
    if len(path) > 1024:
        raise HTTPException(
            status_code=400,
            detail="Path too long (max 1024 characters)"
        )

    return path


def validate_file_paths(paths: list) -> list:
    """Validate a list of file paths"""
    if not paths:
        raise HTTPException(status_code=400, detail="No paths provided")

    # SAFETY: Limit deletions to 100 files at once to prevent accidents
    if len(paths) > 100:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files selected ({len(paths)}). Maximum 100 files per operation for safety. Please delete in smaller batches."
        )

    validated = []
    for path in paths:
        if not isinstance(path, str):
            raise HTTPException(status_code=400, detail="Path must be a string")

        validated_path = validate_dropbox_path(path)
        if not validated_path:
            raise HTTPException(status_code=400, detail="Empty path not allowed in list")

        # SAFETY: Prevent accidental root deletion
        if validated_path == '/':
            raise HTTPException(
                status_code=400,
                detail="Cannot delete root folder"
            )

        validated.append(validated_path)

    return validated


def validate_rename_operations(operations: list) -> list:
    """Validate rename operations"""
    if not operations:
        raise HTTPException(status_code=400, detail="No operations provided")

    if len(operations) > 500:
        raise HTTPException(
            status_code=400,
            detail="Too many operations (max 500 at once)"
        )

    validated = []
    for op in operations:
        if not isinstance(op, dict):
            raise HTTPException(status_code=400, detail="Operation must be an object")

        if 'from' not in op or 'to' not in op:
            raise HTTPException(
                status_code=400,
                detail="Operation must have 'from' and 'to' fields"
            )

        from_path = validate_dropbox_path(op['from'])
        to_path = validate_dropbox_path(op['to'])

        if not from_path or not to_path:
            raise HTTPException(
                status_code=400,
                detail="Both 'from' and 'to' paths must be provided"
            )

        if from_path == to_path:
            raise HTTPException(
                status_code=400,
                detail=f"Source and destination are the same: {from_path}"
            )

        validated.append({'from': from_path, 'to': to_path})

    return validated


def validate_limit_offset(limit: int, offset: int) -> tuple:
    """Validate pagination parameters"""
    if limit < 1:
        raise HTTPException(status_code=400, detail="Limit must be at least 1")

    if limit > 1000:
        raise HTTPException(status_code=400, detail="Limit too large (max 1000)")

    if offset < 0:
        raise HTTPException(status_code=400, detail="Offset must be non-negative")

    return limit, offset


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename for safe usage"""
    # Remove any path separators
    filename = filename.replace('/', '_').replace('\\', '_')

    # Remove invalid characters
    filename = re.sub(r'[<>:"|?*]', '', filename)

    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        max_name_len = 255 - len(ext) - 1
        filename = name[:max_name_len] + ('.' + ext if ext else '')

    return filename
