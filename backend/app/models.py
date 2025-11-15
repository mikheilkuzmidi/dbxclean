"""Database models"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class FileMetadata(Base):
    """File metadata cache"""
    __tablename__ = "file_metadata"

    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, unique=True, index=True)
    name = Column(String, index=True)
    size = Column(Integer)
    content_hash = Column(String, index=True)
    perceptual_hash = Column(String, index=True, nullable=True)
    is_image = Column(Boolean, default=False)

    # Image-specific metadata
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    format = Column(String, nullable=True)
    quality_score = Column(Float, nullable=True)

    # Dropbox metadata
    dropbox_id = Column(String, unique=True, index=True)
    modified = Column(DateTime)
    rev = Column(String)

    # Analysis metadata
    last_analyzed = Column(DateTime, default=datetime.utcnow)
    suggested_name = Column(String, nullable=True)
    tags = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DuplicateGroup(Base):
    """Duplicate file groups"""
    __tablename__ = "duplicate_groups"

    id = Column(Integer, primary_key=True, index=True)
    group_hash = Column(String, index=True)
    file_paths = Column(JSON)  # List of file paths in this group
    total_size = Column(Integer)
    file_count = Column(Integer)
    recommended_keep = Column(String, nullable=True)  # Path of recommended file to keep

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SimilarGroup(Base):
    """Similar image groups"""
    __tablename__ = "similar_groups"

    id = Column(Integer, primary_key=True, index=True)
    representative_hash = Column(String, index=True)
    file_paths = Column(JSON)  # List of similar image paths
    similarity_scores = Column(JSON)  # Similarity scores for each pair
    best_quality_path = Column(String, nullable=True)  # Path of highest quality image

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AnalysisJob(Base):
    """Analysis job tracking"""
    __tablename__ = "analysis_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_type = Column(String)  # 'full_scan', 'duplicates', 'similar', 'naming'
    status = Column(String, default='pending')  # 'pending', 'running', 'completed', 'failed'
    progress = Column(Float, default=0.0)
    total_files = Column(Integer, default=0)
    processed_files = Column(Integer, default=0)

    # Results summary
    duplicates_found = Column(Integer, default=0)
    similar_groups_found = Column(Integer, default=0)
    space_can_save = Column(Integer, default=0)

    error_message = Column(Text, nullable=True)

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
