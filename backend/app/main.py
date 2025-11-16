"""Main FastAPI application with rate limiting and safe operations"""

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager
import psutil
import io

from .config import settings
from .database import get_db, init_db
from .dropbox_client import DropboxClient
from .models import FileMetadata, AnalysisJob
from .analyzers.duplicate import DuplicateDetector
from .analyzers.similar import SimilarImageDetector
from .analyzers.quality import ImageQualityScorer
from .analyzers.naming import FileNamingAnalyzer
from .logging_config import setup_logging, logger
from .validators import (
    validate_dropbox_path,
    validate_file_paths,
    validate_rename_operations,
    validate_limit_offset
)

from pydantic import BaseModel, validator


# Rate limiting configuration for Dropbox API
# Dropbox limits: ~300 requests per minute per user
RATE_LIMIT_REQUESTS = 250  # Conservative limit
RATE_LIMIT_WINDOW = 60  # seconds


class RateLimiter:
    """Simple rate limiter for Dropbox API calls"""

    def __init__(self, max_requests: int, window: int):
        self.max_requests = max_requests
        self.window = window
        self.requests = []

    async def wait_if_needed(self):
        """Wait if we're approaching rate limit"""
        now = datetime.now().timestamp()

        # Remove old requests outside the window
        self.requests = [r for r in self.requests if now - r < self.window]

        if len(self.requests) >= self.max_requests:
            # Wait until the oldest request is outside the window
            wait_time = self.window - (now - self.requests[0]) + 1
            if wait_time > 0:
                print(f"Rate limit approaching, waiting {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)
                self.requests = []

        self.requests.append(now)


rate_limiter = RateLimiter(RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup"""
    setup_logging(settings.debug)
    logger.info("Starting Dropbox Sorter...")
    init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down Dropbox Sorter...")


app = FastAPI(
    title="Dropbox Sorter",
    description="Intelligent file deduplication and organization for Dropbox",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for API
class ConnectionResponse(BaseModel):
    connected: bool
    account_id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    error: Optional[str] = None


class ScanRequest(BaseModel):
    path: str = ""
    recursive: bool = True
    analyze_images: bool = True

    @validator('path')
    def validate_path_field(cls, v):
        return validate_dropbox_path(v) if v else ""


class DeleteRequest(BaseModel):
    paths: List[str]
    confirm: bool = False  # Must be True to actually delete

    @validator('paths')
    def validate_paths_field(cls, v):
        return validate_file_paths(v)


class RenameRequest(BaseModel):
    operations: List[Dict[str, str]]  # [{"from": "old_path", "to": "new_path"}]
    confirm: bool = False  # Must be True to actually rename

    @validator('operations')
    def validate_ops_field(cls, v):
        return validate_rename_operations(v)


class AnalysisJobResponse(BaseModel):
    job_id: int
    status: str
    progress: float
    message: str


# Helper to get Dropbox client
def get_dropbox_client():
    """Get Dropbox client instance"""
    try:
        return DropboxClient()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/")
def read_root():
    """API root endpoint"""
    return {
        "name": "Dropbox Sorter API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Check database
        db.execute("SELECT 1")

        # Check system resources
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            "status": "healthy",
            "database": "connected",
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/api/system")
def system_info(db: Session = Depends(get_db)):
    """Get system information"""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    # Get database stats
    total_files = db.query(FileMetadata).count()
    total_jobs = db.query(AnalysisJob).count()

    return {
        "system": {
            "cpu_percent": cpu_percent,
            "memory_total": memory.total,
            "memory_available": memory.available,
            "memory_percent": memory.percent,
            "disk_total": disk.total,
            "disk_used": disk.used,
            "disk_free": disk.free,
            "disk_percent": disk.percent,
        },
        "database": {
            "total_files": total_files,
            "total_jobs": total_jobs,
        }
    }


@app.get("/api/thumbnail/{file_id}")
async def get_thumbnail(file_id: str, db: Session = Depends(get_db)):
    """Get thumbnail for a file"""
    try:
        # Find file by dropbox_id
        file = db.query(FileMetadata).filter(FileMetadata.dropbox_id == file_id).first()

        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        if not file.is_image:
            raise HTTPException(status_code=400, detail="File is not an image")

        # Get thumbnail from Dropbox
        client = DropboxClient()
        await rate_limiter.wait_if_needed()

        thumbnail_data = client.get_thumbnail(file.path)

        if not thumbnail_data:
            raise HTTPException(status_code=404, detail="Thumbnail not available")

        return Response(content=thumbnail_data, media_type="image/jpeg")

    except Exception as e:
        logger.error(f"Error getting thumbnail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/connection", response_model=ConnectionResponse)
def check_connection(client: DropboxClient = Depends(get_dropbox_client)):
    """Check Dropbox connection status"""
    return client.verify_connection()


@app.post("/api/scan", response_model=AnalysisJobResponse)
async def start_scan(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    client: DropboxClient = Depends(get_dropbox_client)
):
    """Start scanning Dropbox folder"""

    # Create analysis job
    job = AnalysisJob(
        job_type='full_scan',
        status='pending',
        progress=0.0
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Run scan in background
    background_tasks.add_task(
        run_scan_job,
        job.id,
        request.path,
        request.recursive,
        request.analyze_images
    )

    return {
        "job_id": job.id,
        "status": "pending",
        "progress": 0.0,
        "message": "Scan started"
    }


@app.get("/api/jobs/{job_id}")
def get_job_status(job_id: int, db: Session = Depends(get_db)):
    """Get analysis job status"""
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job.id,
        "type": job.job_type,
        "status": job.status,
        "progress": job.progress,
        "total_files": job.total_files,
        "processed_files": job.processed_files,
        "duplicates_found": job.duplicates_found,
        "similar_groups_found": job.similar_groups_found,
        "space_can_save": job.space_can_save,
        "error_message": job.error_message,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@app.get("/api/duplicates")
def get_duplicates(db: Session = Depends(get_db)):
    """Get all duplicate file groups"""
    detector = DuplicateDetector(db)
    groups = detector.find_duplicates()
    stats = detector.get_duplicate_stats()

    return {
        "groups": groups,
        "stats": stats
    }


@app.get("/api/similar")
def get_similar(db: Session = Depends(get_db)):
    """Get all similar image groups"""
    detector = SimilarImageDetector(db)
    groups = detector.find_similar_images()
    stats = detector.get_similar_stats()

    return {
        "groups": groups,
        "stats": stats
    }


@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get overall statistics"""
    total_files = db.query(FileMetadata).count()
    total_images = db.query(FileMetadata).filter(FileMetadata.is_image == True).count()

    duplicate_detector = DuplicateDetector(db)
    duplicate_stats = duplicate_detector.get_duplicate_stats()

    similar_detector = SimilarImageDetector(db)
    similar_stats = similar_detector.get_similar_stats()

    return {
        "total_files": total_files,
        "total_images": total_images,
        "duplicates": duplicate_stats,
        "similar": similar_stats,
    }


@app.get("/api/files")
def list_files(
    path: str = "",
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List files from database cache"""
    query = db.query(FileMetadata)

    if path:
        query = query.filter(FileMetadata.path.like(f"{path}%"))

    total = query.count()
    files = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "files": [
            {
                "path": f.path,
                "name": f.name,
                "size": f.size,
                "is_image": f.is_image,
                "modified": f.modified.isoformat() if f.modified else None,
                "quality_score": f.quality_score,
                "suggested_name": f.suggested_name,
            }
            for f in files
        ]
    }


@app.post("/api/delete")
async def delete_files(
    request: DeleteRequest,
    db: Session = Depends(get_db),
    client: DropboxClient = Depends(get_dropbox_client)
):
    """
    Delete files from Dropbox
    SAFETY: Requires confirm=True to actually delete
    SAFETY: Limited to 100 files per operation
    SAFETY: Logs all deletions for audit trail
    """
    if not request.confirm:
        # Preview mode - just return what would be deleted
        logger.info(f"Delete preview requested for {len(request.paths)} files")
        return {
            "preview": True,
            "files": request.paths,
            "count": len(request.paths),
            "message": "Set confirm=true to actually delete these files"
        }

    # SAFETY: Log deletion attempt
    logger.warning(f"DELETE OPERATION STARTED: {len(request.paths)} files requested for deletion")
    for path in request.paths[:5]:  # Log first 5
        logger.warning(f"  - {path}")
    if len(request.paths) > 5:
        logger.warning(f"  ... and {len(request.paths) - 5} more")

    # Actually delete files
    deleted = []
    failed = []

    for path in request.paths:
        await rate_limiter.wait_if_needed()
        try:
            # SAFETY: Extra validation before deletion
            if not path or path == '/':
                failed.append({"path": path, "error": "Invalid path - cannot delete root"})
                continue

            client.delete_file(path)
            deleted.append(path)
            logger.info(f"DELETED: {path}")

            # Remove from database
            db.query(FileMetadata).filter(FileMetadata.path == path).delete()

        except Exception as e:
            error_msg = str(e)
            logger.error(f"FAILED TO DELETE: {path} - {error_msg}")
            failed.append({"path": path, "error": error_msg})

    db.commit()

    # SAFETY: Log final results
    logger.warning(f"DELETE OPERATION COMPLETED: {len(deleted)} deleted, {len(failed)} failed")

    return {
        "deleted": deleted,
        "deleted_count": len(deleted),
        "failed": failed,
        "failed_count": len(failed),
    }


@app.post("/api/rename")
async def rename_files(
    request: RenameRequest,
    db: Session = Depends(get_db),
    client: DropboxClient = Depends(get_dropbox_client)
):
    """
    Rename/move files in Dropbox
    SAFETY: Requires confirm=True to actually rename
    """
    if not request.confirm:
        # Preview mode
        return {
            "preview": True,
            "operations": request.operations,
            "count": len(request.operations),
            "message": "Set confirm=true to actually rename these files"
        }

    # Actually rename files
    renamed = []
    failed = []

    for op in request.operations:
        from_path = op.get("from")
        to_path = op.get("to")

        if not from_path or not to_path:
            failed.append({"operation": op, "error": "Missing from or to path"})
            continue

        await rate_limiter.wait_if_needed()
        try:
            client.move_file(from_path, to_path)
            renamed.append(op)

            # Update in database
            file = db.query(FileMetadata).filter(FileMetadata.path == from_path).first()
            if file:
                file.path = to_path
                file.name = to_path.split('/')[-1]

        except Exception as e:
            failed.append({"operation": op, "error": str(e)})

    db.commit()

    return {
        "renamed": renamed,
        "renamed_count": len(renamed),
        "failed": failed,
        "failed_count": len(failed),
    }


@app.get("/api/naming/suggestions")
def get_naming_suggestions(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get file naming suggestions"""
    analyzer = FileNamingAnalyzer()

    files = db.query(FileMetadata).limit(limit).all()

    suggestions = []
    for file in files:
        suggested = analyzer.suggest_name(
            file.name,
            file.path,
            file.modified
        )

        if suggested:
            suggestions.append({
                "path": file.path,
                "current_name": file.name,
                "suggested_name": suggested,
                "needs_rename": True
            })

    return {"suggestions": suggestions, "count": len(suggestions)}


async def run_scan_job(
    job_id: int,
    path: str,
    recursive: bool,
    analyze_images: bool
):
    """Background task to scan Dropbox folder"""
    from .database import SessionLocal

    db = SessionLocal()
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()

    try:
        job.status = 'running'
        job.started_at = datetime.utcnow()
        db.commit()

        client = DropboxClient()
        quality_scorer = ImageQualityScorer()
        similar_detector = SimilarImageDetector(db)

        # List all files
        print(f"Scanning folder: {path}")
        entries = client.list_folder(path, recursive=recursive)

        job.total_files = len(entries)
        db.commit()

        # Process each file
        for i, entry in enumerate(entries):
            await rate_limiter.wait_if_needed()

            if entry['type'] != 'file':
                continue

            # Check if file exists in database
            existing = db.query(FileMetadata).filter(
                FileMetadata.path == entry['path']
            ).first()

            is_image = client.is_image(entry['name'])

            # Create or update file metadata
            if not existing:
                file_meta = FileMetadata(
                    path=entry['path'],
                    name=entry['name'],
                    size=entry['size'],
                    content_hash=entry.get('content_hash'),
                    dropbox_id=entry.get('id'),
                    modified=datetime.fromisoformat(entry['modified'].replace('Z', '+00:00')) if entry.get('modified') else None,
                    rev=entry.get('rev'),
                    is_image=is_image,
                )
                db.add(file_meta)
            else:
                existing.size = entry['size']
                existing.content_hash = entry.get('content_hash')
                existing.modified = datetime.fromisoformat(entry['modified'].replace('Z', '+00:00')) if entry.get('modified') else None
                file_meta = existing

            # Analyze images
            if analyze_images and is_image and not file_meta.perceptual_hash:
                try:
                    image = client.get_image_for_analysis(entry['path'])
                    if image:
                        # Compute perceptual hash
                        phash = similar_detector.compute_perceptual_hash(image)
                        file_meta.perceptual_hash = phash

                        # Compute quality score
                        quality = quality_scorer.compute_quality_score(image, entry['size'])
                        file_meta.quality_score = quality
                        file_meta.width = image.size[0]
                        file_meta.height = image.size[1]
                        file_meta.format = image.format

                except Exception as e:
                    print(f"Error analyzing image {entry['path']}: {e}")

            # Update progress
            job.processed_files = i + 1
            job.progress = (i + 1) / job.total_files * 100

            if i % 10 == 0:  # Commit every 10 files
                db.commit()

        db.commit()

        # Run duplicate detection
        print("Finding duplicates...")
        duplicate_detector = DuplicateDetector(db)
        duplicates = duplicate_detector.find_duplicates()
        job.duplicates_found = len(duplicates)

        # Run similar image detection
        if analyze_images:
            print("Finding similar images...")
            similar = similar_detector.find_similar_images()
            job.similar_groups_found = len(similar)

        # Calculate space savings
        dup_stats = duplicate_detector.get_duplicate_stats()
        similar_stats = similar_detector.get_similar_stats()
        job.space_can_save = dup_stats['space_wasted_bytes'] + similar_stats['space_can_save_bytes']

        job.status = 'completed'
        job.completed_at = datetime.utcnow()
        job.progress = 100.0

    except Exception as e:
        job.status = 'failed'
        job.error_message = str(e)
        print(f"Scan job failed: {e}")

    finally:
        db.commit()
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
