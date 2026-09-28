"""Credential-free checks for the Dropbox metadata-only duplicate workflow."""

from datetime import datetime, timezone
from types import SimpleNamespace

from dropbox.files import FileMetadata as DropboxFileMetadata
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app import database, main
from backend.app.dropbox_client import DropboxClient
from backend.app.models import AnalysisJob, Base, DuplicateGroup, FileMetadata


def test_dropbox_folder_listing_uses_all_metadata_pages():
    modified = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def file(name, path, content_hash):
        return DropboxFileMetadata(
            name=name,
            id="id:" + name,
            path_display=path,
            client_modified=modified,
            server_modified=modified,
            rev="a" * 9,
            size=12,
            content_hash=content_hash,
        )

    class FakeSdk:
        def files_list_folder(self, path, recursive):
            assert path == ""
            assert recursive is True
            return SimpleNamespace(
                entries=[file("first.txt", "/a/first.txt", "a" * 64)],
                has_more=True,
                cursor="next-page",
            )

        def files_list_folder_continue(self, cursor):
            assert cursor == "next-page"
            return SimpleNamespace(
                entries=[file("second.txt", "/b/second.txt", "a" * 64)],
                has_more=False,
            )

    client = DropboxClient.__new__(DropboxClient)
    client.dbx = FakeSdk()
    entries = client.list_folder("", recursive=True)

    assert [entry["path"] for entry in entries] == [
        "/a/first.txt", "/b/second.txt"
    ]
    assert all(entry["content_hash"] == "a" * 64 for entry in entries)


def test_cloud_scan_finds_duplicates_without_downloading_and_refreshes_results(monkeypatch):
    assert main.ScanRequest().analyze_images is False
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    monkeypatch.setattr(database, "SessionLocal", session_factory)
    monkeypatch.setattr(main.settings, "storage_mode", "dropbox")

    class FakeDropboxClient:
        files = [
            ("/one/report.txt", "id:one", "a" * 64),
            ("/two/copy.txt", "id:two", "a" * 64),
            ("/two/other.txt", "id:other", "b" * 64),
        ]

        def list_folder(self, path, recursive):
            assert path == ""
            assert recursive is True
            return [
                {
                    "type": "file", "path": path, "name": path.rsplit("/", 1)[-1],
                    "id": file_id, "size": 12, "content_hash": content_hash,
                    "modified": None, "rev": "rev-1",
                }
                for path, file_id, content_hash in self.files
            ]

        def is_image(self, name):
            return False

        def get_image_for_analysis(self, path):
            raise AssertionError("exact duplicate scan must not fetch file content")

    monkeypatch.setattr(main, "DropboxClient", FakeDropboxClient)

    def get_test_db():
        with session_factory() as session:
            yield session

    main.app.dependency_overrides[main.get_db] = get_test_db
    main.app.dependency_overrides[main.get_dropbox_client] = FakeDropboxClient
    client = TestClient(main.app)
    try:
        response = client.post("/api/scan", json={"path": "", "recursive": True})
        assert response.status_code == 200, response.text
        job_id = response.json()["job_id"]
        status = client.get(f"/api/jobs/{job_id}")
        assert status.status_code == 200
        assert status.json()["status"] == "completed", status.json()
    finally:
        main.app.dependency_overrides.clear()

    with session_factory() as session:
        job = session.get(AnalysisJob, job_id)
        groups = session.query(DuplicateGroup).all()
        assert job.status == "completed", job.error_message
        assert job.duplicates_found == 1
        assert len(groups) == 1
        assert sorted(groups[0].file_paths) == ["/one/report.txt", "/two/copy.txt"]

    FakeDropboxClient.files = FakeDropboxClient.files[1:]
    main.app.dependency_overrides[main.get_db] = get_test_db
    main.app.dependency_overrides[main.get_dropbox_client] = FakeDropboxClient
    try:
        response = client.post("/api/scan", json={"path": "", "recursive": True})
        assert response.status_code == 200, response.text
        job_id = response.json()["job_id"]
        assert client.get("/api/duplicates").json()["groups"] == []
    finally:
        main.app.dependency_overrides.clear()

    with session_factory() as session:
        job = session.get(AnalysisJob, job_id)
        assert job.status == "completed", job.error_message
        assert job.duplicates_found == 0
        assert session.query(DuplicateGroup).count() == 0
        assert session.query(FileMetadata).count() == 2
