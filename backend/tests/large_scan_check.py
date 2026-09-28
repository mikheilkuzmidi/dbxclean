"""Run separately to exercise a 700,000-file metadata scan without credentials."""

import resource
import tempfile
import time
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app import database, main
from backend.app.models import AnalysisJob, Base, DuplicateGroup, FileMetadata, ScanSeen


COUNT = 700_000


class SyntheticDropbox:
    def iter_folder(self, path, recursive):
        assert path == "" and recursive
        for index in range(COUNT):
            yield {
                "type": "file",
                "path": f"/archive/{index:07d}.bin",
                "name": f"{index:07d}.bin",
                "id": f"id:{index}",
                "size": 8,
                "content_hash": "0" * 64 if index < 2 else f"{index:064x}",
                "rev": "r1",
                "modified": None,
            }

    def is_image(self, name):
        return False

    def get_image_for_analysis(self, path):
        raise AssertionError("Exact scan must not download contents")


def main_check():
    with tempfile.TemporaryDirectory(prefix="dbxclean-large-") as temp:
        engine = create_engine(f"sqlite:///{Path(temp) / 'scan.db'}")
        Base.metadata.create_all(engine)
        factory = sessionmaker(bind=engine)
        old_factory = database.SessionLocal
        old_client = main.DropboxClient
        old_mode = main.settings.storage_mode
        database.SessionLocal = factory
        main.DropboxClient = SyntheticDropbox
        main.settings.storage_mode = "dropbox"
        try:
            with factory() as db:
                job = AnalysisJob(job_type="full_scan", status="pending", progress=0)
                db.add(job)
                db.commit()
                job_id = job.id
            start = time.monotonic()
            main.run_scan_job(job_id, "", True, False)
            duration = time.monotonic() - start
            with factory() as db:
                job = db.get(AnalysisJob, job_id)
                assert job.status == "completed", job.error_message
                assert job.processed_files == COUNT
                assert job.duplicates_found == 1
                assert db.query(FileMetadata).count() == COUNT
                assert db.query(DuplicateGroup).count() == 1
                assert db.query(ScanSeen).count() == 0
            peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)
            print(f"PASS: {COUNT:,} entries, {duration:.1f}s, peak RSS {peak:.1f} MiB")
        finally:
            database.SessionLocal = old_factory
            main.DropboxClient = old_client
            main.settings.storage_mode = old_mode


if __name__ == "__main__":
    main_check()
