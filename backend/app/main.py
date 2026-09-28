"""Main FastAPI application with rate limiting and safe operations"""

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import text, func
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import datetime
from uuid import uuid4
import asyncio
from contextlib import asynccontextmanager
import psutil
import io

from .config import settings
from .database import get_db, init_db
from .dropbox_client import DropboxClient
from .local_client import LocalClient
from .models import FileMetadata, AnalysisJob, DuplicateGroup, SimilarGroup, ScanSeen, RecoveryRecord
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
    logger.info("Starting dbxclean...")
    init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down dbxclean...")


app = FastAPI(
    title="dbxclean",
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
    analyze_images: bool = False

    @validator('path')
    def validate_path_field(cls, v):
        return validate_dropbox_path(v) if v else ""


class DeleteRequest(BaseModel):
    paths: List[str]
    confirm: bool = False  # Must be True to actually delete

    @validator('paths')
    def validate_paths_field(cls, v):
        return validate_file_paths(v)


class RestoreRequest(BaseModel):
    ids: List[int]
    confirm: bool = False


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


"""Helper to get storage client (Dropbox or local filesystem)"""
def get_dropbox_client():
    try:
        mode = getattr(settings, "storage_mode", "local") or "local"
        if mode.lower() == "dropbox":
            return DropboxClient()
        return LocalClient()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/")
def read_root():
    """API root endpoint"""
    return {
        "name": "dbxclean API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Check database
        db.execute(text("SELECT 1"))

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

        # Get thumbnail from storage backend
        mode = getattr(settings, "storage_mode", "local") or "local"
        if mode.lower() == "dropbox":
            client = DropboxClient()
            await rate_limiter.wait_if_needed()
        else:
            client = LocalClient()

        thumbnail_data = client.get_thumbnail(file.path)

        if not thumbnail_data:
            raise HTTPException(status_code=404, detail="Thumbnail not available")

        return Response(content=thumbnail_data, media_type="image/jpeg")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting thumbnail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/image")
async def get_image(path: str, thumb: bool = True, db: Session = Depends(get_db)):
    """Serve an image (thumbnail by default) for local or Dropbox storage.

    In local mode this reads directly from the filesystem via LocalClient.
    In Dropbox mode it uses DropboxClient and respects rate limiting.
    """
    try:
        # Prefer DB metadata when available, but fall back to raw path for local files
        db_file = db.query(FileMetadata).filter(FileMetadata.path == path).first()

        if db_file and not db_file.is_image:
            raise HTTPException(status_code=400, detail="File is not an image")

        file_path = db_file.path if db_file else path

        mode = getattr(settings, "storage_mode", "local") or "local"
        use_rate_limit = mode.lower() == "dropbox"
        client = DropboxClient() if mode.lower() == "dropbox" else LocalClient()

        if thumb:
            if use_rate_limit:
                await rate_limiter.wait_if_needed()
            image_data = client.get_thumbnail(file_path)
            media_type = "image/jpeg"
        else:
            if use_rate_limit:
                await rate_limiter.wait_if_needed()
            image_data = client.download_file(file_path)
            # For simplicity we serve originals as binary stream; JPEG covers most
            media_type = "image/jpeg"

        if not image_data:
            raise HTTPException(status_code=404, detail="Image data not available")

        return Response(content=image_data, media_type=media_type)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting image: {e}")
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
    if db.query(AnalysisJob).filter(AnalysisJob.status.in_(["pending", "running"])).count():
        raise HTTPException(status_code=409, detail="A scan is already running")

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
def get_duplicates(limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    """Get one page of duplicate file groups."""
    validate_limit_offset(limit, offset)
    detector = DuplicateDetector(db)
    groups = detector.find_duplicates(limit, offset)
    stats = detector.get_duplicate_stats()

    return {
        "groups": groups,
        "stats": stats,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(groups) < stats["duplicate_groups"],
    }


@app.get("/api/similar")
def get_similar(db: Session = Depends(get_db)):
    """Get all similar image groups"""
    detector = SimilarImageDetector(db)
    groups = detector.list_saved_groups()
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


def _validate_review_selection(db: Session, client, paths: List[str]):
    """Reject unknown, changed, protected, or last-copy selections before a move."""
    selected = set(paths)
    if len(selected) != len(paths):
        raise HTTPException(status_code=400, detail="Duplicate paths in selection")
    if db.query(AnalysisJob).filter(AnalysisJob.status.in_(["pending", "running"])).count():
        raise HTTPException(status_code=409, detail="Wait for the scan to finish")

    selected_files = db.query(FileMetadata).filter(FileMetadata.path.in_(paths)).all()
    selected_hashes = {f.content_hash for f in selected_files if f.content_hash}
    groups = (
        db.query(DuplicateGroup).filter(DuplicateGroup.group_hash.in_(selected_hashes)).all()
        + db.query(SimilarGroup).all()
    )
    related = set()
    protected = set()
    for group in groups:
        members = set(group.file_paths or [])
        related.update(members)
        chosen = members & selected
        if chosen:
            keeper = getattr(group, "recommended_keep", None) or getattr(group, "best_quality_path", None)
            if keeper:
                protected.add(keeper)
            if keeper in chosen:
                raise HTTPException(status_code=409, detail=f"Protected recommended file: {keeper}")
            if not members - selected:
                raise HTTPException(status_code=409, detail="At least one reviewed file must remain")
    if not selected <= related:
        raise HTTPException(status_code=409, detail="Selection is not in the current review")

    cached = {}
    for path in selected | protected:
        file = db.query(FileMetadata).filter(FileMetadata.path == path).first()
        if file is None:
            raise HTTPException(status_code=409, detail=f"Stale selection: {path}")
        try:
            current = client.get_file_metadata(path)
        except Exception as exc:
            raise HTTPException(status_code=409, detail=f"Could not verify {path}: {exc}") from exc
        if (current.get("content_hash") != file.content_hash
                or current.get("rev") != file.rev
                or current.get("size") != file.size):
            raise HTTPException(status_code=409, detail=f"File changed since scan: {path}")
        cached[path] = file
    return cached


def _refresh_review_groups(db: Session):
    DuplicateDetector(db).rebuild_groups()
    for group in db.query(SimilarGroup).all():
        existing = {
            row.path for row in db.query(FileMetadata.path)
            .filter(FileMetadata.path.in_(group.file_paths)).all()
        }
        group.file_paths = [p for p in group.file_paths if p in existing]
        if len(group.file_paths) < 2:
            db.delete(group)
    db.commit()


def _reconcile_recovery(db: Session, client, backend: str):
    """Expose moves that finished before their final database commit."""
    pending = db.query(RecoveryRecord).filter(
        RecoveryRecord.backend == backend,
        RecoveryRecord.status == "pending",
    ).all()
    for row in pending:
        try:
            if client.path_exists(row.original_path):
                continue
            if backend == "local" and not client.recovery_exists(row.recovery_path):
                continue
            row.status = "active"
            db.query(FileMetadata).filter(FileMetadata.path == row.original_path).delete()
        except Exception as exc:
            logger.warning("Could not reconcile recovery record %s: %s", row.id, exc)
    if pending:
        db.commit()


@app.post("/api/trash")
@app.post("/api/delete")
async def trash_files(
    request: DeleteRequest,
    db: Session = Depends(get_db),
    client=Depends(get_dropbox_client),
):
    """Move reviewed files to Dropbox Deleted files or local quarantine."""
    cached = _validate_review_selection(db, client, request.paths)
    backend = (getattr(settings, "storage_mode", "local") or "local").lower()
    if not request.confirm:
        return {
            "preview": True, "files": request.paths, "count": len(request.paths),
            "message": "Set confirm=true to move these files into recovery",
        }

    moved, failed = [], []
    for path in request.paths:
        file = cached[path]
        token = uuid4().hex
        record = RecoveryRecord(
            backend=backend, original_path=path, revision=file.rev,
            content_hash=file.content_hash, size=file.size, status="pending",
            recovery_path=(str(client.quarantine_path(path, token)) if backend == "local" else None),
        )
        db.add(record)
        db.commit()
        try:
            # Check again immediately before the actual operation.
            current = client.get_file_metadata(path)
            if (current.get("content_hash"), current.get("rev"), current.get("size")) != (
                file.content_hash, file.rev, file.size
            ):
                raise ValueError("File changed since scan")
            if backend == "dropbox":
                await rate_limiter.wait_if_needed()
                client.delete_file(path)
            else:
                client.trash_file(path, token)
            record.status = "active"
            db.query(FileMetadata).filter(FileMetadata.path == path).delete()
            db.commit()
            moved.append(path)
        except Exception as exc:
            # A remote response can fail after the move happened. Keep the
            # recovery record discoverable when the source is now absent.
            try:
                moved_despite_error = not client.path_exists(path) and (
                    backend == "dropbox" or client.recovery_exists(record.recovery_path)
                )
            except Exception:
                moved_despite_error = False
            record.status = "active" if moved_despite_error else "failed"
            record.error = str(exc)
            if moved_despite_error:
                db.query(FileMetadata).filter(FileMetadata.path == path).delete()
            db.commit()
            if moved_despite_error:
                moved.append(path)
            else:
                failed.append({"path": path, "error": str(exc)})
    if moved:
        _refresh_review_groups(db)
    return {
        "trashed": moved, "trashed_count": len(moved),
        "deleted": moved, "deleted_count": len(moved),
        "failed": failed, "failed_count": len(failed),
    }


@app.get("/api/recovery")
def get_recovery(db: Session = Depends(get_db), client=Depends(get_dropbox_client)):
    backend = (getattr(settings, "storage_mode", "local") or "local").lower()
    _reconcile_recovery(db, client, backend)
    rows = db.query(RecoveryRecord).filter(
        RecoveryRecord.status == "active", RecoveryRecord.backend == backend,
    ).order_by(RecoveryRecord.id.desc()).all()
    return {"files": [
        {
            "id": row.id, "path": row.original_path, "backend": row.backend,
            "size": row.size, "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]}


@app.post("/api/restore")
async def restore_files(
    request: RestoreRequest,
    db: Session = Depends(get_db),
    client=Depends(get_dropbox_client),
):
    if not request.ids or len(request.ids) > 100 or len(set(request.ids)) != len(request.ids):
        raise HTTPException(status_code=400, detail="Select 1 to 100 distinct recovery records")
    rows = db.query(RecoveryRecord).filter(RecoveryRecord.id.in_(request.ids)).all()
    backend = (getattr(settings, "storage_mode", "local") or "local").lower()
    _reconcile_recovery(db, client, backend)
    if len(rows) != len(request.ids) or any(row.status != "active" or row.backend != backend for row in rows):
        raise HTTPException(status_code=409, detail="Recovery selection is no longer available")
    if not request.confirm:
        return {"preview": True, "files": [row.original_path for row in rows]}

    restored, failed = [], []
    for row in rows:
        try:
            if client.path_exists(row.original_path):
                raise FileExistsError(f"Destination already exists: {row.original_path}")
            if backend == "dropbox":
                await rate_limiter.wait_if_needed()
                metadata = client.restore_file(row.original_path, row.revision)
            else:
                client.restore_file(row.original_path, row.recovery_path)
                metadata = client.get_file_metadata(row.original_path)
            db.add(FileMetadata(
                path=metadata["path"], name=metadata["name"],
                size=metadata["size"], content_hash=metadata["content_hash"],
                dropbox_id=metadata.get("id"), rev=metadata.get("rev"),
                is_image=client.is_image(metadata["name"]),
            ))
            row.status = "restored"
            row.restored_at = datetime.utcnow()
            db.commit()
            restored.append(row.original_path)
        except Exception as exc:
            db.rollback()
            failed.append({"path": row.original_path, "error": str(exc)})
    if restored:
        _refresh_review_groups(db)
    return {
        "restored": restored, "restored_count": len(restored),
        "failed": failed, "failed_count": len(failed),
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

        try:
            file = db.query(FileMetadata).filter(FileMetadata.path == from_path).first()
            if not file:
                raise ValueError("Source is not in the latest scan")
            current = client.get_file_metadata(from_path)
            if (current.get("content_hash"), current.get("rev"), current.get("size")) != (
                file.content_hash, file.rev, file.size
            ):
                raise ValueError("Source changed since scan")
            if client.path_exists(to_path):
                raise FileExistsError(f"Destination already exists: {to_path}")
            if db.query(FileMetadata).filter(FileMetadata.path == to_path).first():
                raise ValueError("Destination is in the scan cache; run another scan")
            if (getattr(settings, "storage_mode", "local") or "local").lower() == "dropbox":
                await rate_limiter.wait_if_needed()
            client.move_file(from_path, to_path)
            renamed.append(op)

            # Update in database
            file.path = to_path
            file.name = to_path.split('/')[-1]
            for group in db.query(SimilarGroup).all():
                if from_path in group.file_paths:
                    group.file_paths = [to_path if path == from_path else path for path in group.file_paths]
                    if group.best_quality_path == from_path:
                        group.best_quality_path = to_path

        except Exception as e:
            failed.append({"operation": op, "error": str(e)})

    db.commit()
    if renamed:
        _refresh_review_groups(db)

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


def run_scan_job(
    job_id: int,
    path: str,
    recursive: bool,
    analyze_images: bool
):
    """Scan metadata in a worker thread without holding the listing in RAM."""
    from .database import SessionLocal

    db = SessionLocal()
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()

    try:
        job.status = 'running'
        job.started_at = datetime.utcnow()
        db.commit()

        quality_scorer = ImageQualityScorer()
        similar_detector = SimilarImageDetector(db)

        print(f"Scanning folder: {path}")
        mode = getattr(settings, "storage_mode", "local") or "local"
        if mode.lower() == "dropbox":
            client = DropboxClient()
        else:
            client = LocalClient()

        entries = (
            client.iter_folder(path, recursive=recursive)
            if hasattr(client, "iter_folder")
            else client.list_folder(path, recursive=recursive)
        )
        def ingest(batch):
            if not batch:
                return
            existing = {
                row.path: row for row in db.query(FileMetadata)
                .filter(FileMetadata.path.in_([entry["path"] for entry in batch])).all()
            }
            ids = [entry["id"] for entry in batch if entry.get("id")]
            existing_by_id = {
                row.dropbox_id: row for row in db.query(FileMetadata)
                .filter(FileMetadata.dropbox_id.in_(ids)).all()
            } if ids else {}
            for entry in batch:
                db.add(ScanSeen(job_id=job_id, path=entry["path"]))
                file_meta = existing_by_id.get(entry.get("id")) if entry.get("id") else None
                occupant = existing.get(entry["path"])
                if occupant is not None and occupant.path != entry["path"]:
                    occupant = None
                if file_meta is None and (occupant is None or not entry.get("id")):
                    file_meta = occupant
                if occupant is not None and occupant is not file_meta:
                    # A different file now owns this Dropbox path. Remove the
                    # stale cache row before moving the matching ID into it.
                    existing_by_id.pop(occupant.dropbox_id, None)
                    db.delete(occupant)
                    db.flush()
                if file_meta is None:
                    file_meta = FileMetadata(path=entry["path"])
                    db.add(file_meta)
                else:
                    old_path = file_meta.path
                    file_meta.path = entry["path"]
                    if old_path != entry["path"]:
                        db.flush()
                existing[entry["path"]] = file_meta
                changed = (
                    file_meta.content_hash != entry.get("content_hash")
                    or file_meta.rev != entry.get("rev")
                )
                file_meta.name = entry["name"]
                file_meta.size = entry["size"]
                file_meta.content_hash = entry.get("content_hash")
                file_meta.dropbox_id = entry.get("id")
                file_meta.rev = entry.get("rev")
                file_meta.modified = (
                    datetime.fromisoformat(entry["modified"].replace("Z", "+00:00"))
                    if entry.get("modified") else None
                )
                file_meta.is_image = client.is_image(entry["name"])
                if changed:
                    file_meta.perceptual_hash = None
                    file_meta.quality_score = None
                if analyze_images and file_meta.is_image and not file_meta.perceptual_hash:
                    try:
                        image = client.get_image_for_analysis(entry["path"])
                        if image:
                            file_meta.perceptual_hash = similar_detector.compute_perceptual_hash(image)
                            file_meta.quality_score = quality_scorer.compute_quality_score(image, entry["size"])
                            file_meta.width, file_meta.height = image.size
                            file_meta.format = image.format
                    except Exception as exc:
                        logger.warning("Image analysis failed for %s: %s", entry["path"], exc)
                job.processed_files += 1
            db.commit()

        batch = []
        for entry in entries:
            job.total_files += 1
            if entry["type"] == "file":
                batch.append(entry)
            if len(batch) == 500:
                ingest(batch)
                batch = []
        ingest(batch)

        # Remove stale records only inside the scanned folder. ScanSeen keeps
        # this comparison in SQLite instead of a 700,000-path Python set.
        normalized_path = '/' + path.strip('/') if path.strip('/') else ''
        stale = db.query(FileMetadata)
        if normalized_path:
            stale = stale.filter(FileMetadata.path.startswith(normalized_path + '/', autoescape=True))
        if not recursive:
            depth = normalized_path.count('/') + 1
            stale = stale.filter(
                func.length(FileMetadata.path) - func.length(func.replace(FileMetadata.path, '/', '')) == depth
            )
        stale.filter(
            ~db.query(ScanSeen).filter(
                ScanSeen.job_id == job_id,
                ScanSeen.path == FileMetadata.path,
            ).exists()
        ).delete(synchronize_session=False)
        db.query(ScanSeen).filter(ScanSeen.job_id == job_id).delete(synchronize_session=False)
        db.commit()

        duplicate_detector = DuplicateDetector(db)
        job.duplicates_found = duplicate_detector.rebuild_groups()

        if analyze_images:
            similar = similar_detector.find_similar_images()
            job.similar_groups_found = len(similar)
        else:
            db.query(SimilarGroup).delete()
            job.similar_groups_found = 0

        # Calculate space savings
        dup_stats = duplicate_detector.get_duplicate_stats()
        similar_stats = similar_detector.get_similar_stats()
        job.space_can_save = dup_stats['space_wasted_bytes'] + similar_stats['space_can_save_bytes']

        job.status = 'completed'
        job.completed_at = datetime.utcnow()
        job.progress = 100.0

    except Exception as e:
        db.rollback()
        job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        job.status = 'failed'
        job.error_message = str(e)
        db.query(ScanSeen).filter(ScanSeen.job_id == job_id).delete(synchronize_session=False)
        db.query(DuplicateGroup).delete(synchronize_session=False)
        db.query(SimilarGroup).delete(synchronize_session=False)
        logger.error("Scan job failed: %s", e)

    finally:
        db.commit()
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
