"""Credential-free end-to-end checks through the running API."""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app import database, main
from backend.app.local_client import LocalClient
from backend.app.models import Base, RecoveryRecord


@pytest.fixture
def app_client(monkeypatch, tmp_path):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(database, "SessionLocal", factory)
    monkeypatch.setattr(main.settings, "storage_mode", "local")
    monkeypatch.setattr(main.settings, "local_root", str(tmp_path))

    def get_db():
        with factory() as session:
            yield session

    main.app.dependency_overrides[main.get_db] = get_db
    main.app.dependency_overrides[main.get_dropbox_client] = lambda: LocalClient(str(tmp_path))
    with TestClient(main.app) as client:
        yield client, tmp_path
    main.app.dependency_overrides.clear()


def scan(client, images=False):
    result = client.post("/api/scan", json={"analyze_images": images})
    assert result.status_code == 200, result.text
    job = client.get(f"/api/jobs/{result.json()['job_id']}").json()
    assert job["status"] == "completed", job
    return job


def test_local_scan_review_quarantine_and_restore(app_client):
    client, root = app_client
    (root / "one.txt").write_bytes(b"matching payload")
    (root / "two.txt").write_bytes(b"matching payload")
    (root / "other.txt").write_bytes(b"unrelated")
    scan(client)
    groups = client.get("/api/duplicates").json()["groups"]
    assert len(groups) == 1
    keeper = groups[0]["recommended_keep"]
    removable = next(file["path"] for file in groups[0]["files"] if not file["is_recommended"])
    assert client.post("/api/trash", json={"paths": [keeper], "confirm": True}).status_code == 409
    assert client.post("/api/trash", json={"paths": ["/other.txt"], "confirm": True}).status_code == 409
    assert client.post("/api/trash", json={"paths": [removable, removable], "confirm": True}).status_code == 400
    assert client.post("/api/trash", json={"paths": [removable]}).json()["preview"]
    assert (root / removable.lstrip("/")).exists()

    keeper_file = root / keeper.lstrip("/")
    keeper_file.write_bytes(b"changed keeper")
    assert client.post("/api/trash", json={"paths": [removable], "confirm": True}).status_code == 409
    keeper_file.write_bytes(b"matching payload")

    (root / removable.lstrip("/")).write_bytes(b"changed content")
    assert client.post("/api/trash", json={"paths": [removable], "confirm": True}).status_code == 409
    (root / removable.lstrip("/")).write_bytes(b"matching payload")
    result = client.post("/api/delete", json={"paths": [removable], "confirm": True})
    assert result.status_code == 200, result.text
    assert result.json()["trashed_count"] == 1
    assert not (root / removable.lstrip("/")).exists()
    assert (root / keeper.lstrip("/")).read_bytes() == b"matching payload"
    recovery = client.get("/api/recovery").json()["files"]
    assert len(recovery) == 1
    record_id = recovery[0]["id"]

    destination = root / removable.lstrip("/")
    destination.write_bytes(b"new unrelated data")
    refused = client.post("/api/restore", json={"ids": [record_id], "confirm": True})
    assert refused.json()["failed_count"] == 1
    assert destination.read_bytes() == b"new unrelated data"
    destination.unlink()
    restored = client.post("/api/restore", json={"ids": [record_id], "confirm": True})
    assert restored.json()["restored_count"] == 1, restored.text
    assert destination.read_bytes() == b"matching payload"
    assert client.get("/api/recovery").json()["files"] == []
    assert len(client.get("/api/duplicates").json()["groups"]) == 1


def test_interrupted_local_move_remains_recoverable(app_client):
    client, root = app_client
    (root / "one.txt").write_bytes(b"same")
    (root / "two.txt").write_bytes(b"same")
    scan(client)
    group = client.get("/api/duplicates").json()["groups"][0]
    candidate = next(f["path"] for f in group["files"] if not f["is_recommended"])
    local = LocalClient(str(root))
    with database.SessionLocal() as db:
        record = RecoveryRecord(
            backend="local", original_path=candidate,
            recovery_path=str(local.quarantine_path(candidate, "interrupted")),
            status="pending", size=4,
        )
        db.add(record)
        db.commit()
        record_id = record.id
    local.trash_file(candidate, "interrupted")

    recovery = client.get("/api/recovery").json()["files"]
    assert [item["id"] for item in recovery] == [record_id]
    restored = client.post("/api/restore", json={"ids": [record_id], "confirm": True})
    assert restored.json()["restored_count"] == 1, restored.text
    assert (root / candidate.lstrip("/")).read_bytes() == b"same"


def test_local_path_validation_and_no_overwrite(app_client):
    _, root = app_client
    local = LocalClient(str(root))
    with pytest.raises(ValueError):
        local.get_file_metadata("/../sibling/file.txt")
    (root / "a.txt").write_text("a")
    (root / "b.txt").write_text("b")
    with pytest.raises(FileExistsError):
        local.move_file("/a.txt", "/b.txt")
    assert (root / "a.txt").read_text() == "a"
    assert (root / "b.txt").read_text() == "b"
    (root / "alias.txt").symlink_to(root / "a.txt")
    with pytest.raises(ValueError):
        local.get_file_metadata("/alias.txt")


def test_naming_response_and_rename_conflict(app_client):
    client, root = app_client
    (root / "IMG_0001.jpg").write_bytes(b"image bytes")
    scan(client)
    suggestions = client.get("/api/naming/suggestions").json()["suggestions"]
    suggestion = next(item for item in suggestions if item["path"] == "/IMG_0001.jpg")
    assert suggestion["current_name"] == "IMG_0001.jpg"
    assert suggestion["suggested_name"].endswith(".jpg")
    target = "/" + suggestion["suggested_name"]
    (root / target.lstrip("/")).write_bytes(b"existing data")
    blocked = client.post("/api/rename", json={
        "operations": [{"from": suggestion["path"], "to": target}],
        "confirm": True,
    })
    assert blocked.json()["failed_count"] == 1
    assert (root / target.lstrip("/")).read_bytes() == b"existing data"
    (root / target.lstrip("/")).unlink()
    moved = client.post("/api/rename", json={
        "operations": [{"from": suggestion["path"], "to": target}],
        "confirm": True,
    })
    assert moved.json()["renamed_count"] == 1, moved.text
    assert not (root / "IMG_0001.jpg").exists()
    assert (root / target.lstrip("/")).read_bytes() == b"image bytes"


def test_optional_image_analysis_and_recovery(app_client):
    client, root = app_client
    for name, color in [("a.png", (100, 110, 120)), ("b.png", (101, 111, 121))]:
        image = Image.new("RGB", (32, 32), color)
        image.save(root / name)
    scan(client, images=False)
    assert client.get("/api/similar").json()["groups"] == []
    scan(client, images=True)
    groups = client.get("/api/similar").json()["groups"]
    assert len(groups) == 1
    candidate = next(file["path"] for file in groups[0]["files"] if not file["is_best_quality"])
    result = client.post("/api/trash", json={"paths": [candidate], "confirm": True})
    assert result.json()["trashed_count"] == 1, result.text
    record = client.get("/api/recovery").json()["files"][0]
    assert client.post("/api/restore", json={"ids": [record["id"]], "confirm": True}).json()["restored_count"] == 1
    assert Image.open(root / candidate.lstrip("/")).size == (32, 32)


def test_simulated_dropbox_pagination_cleanup_restore_and_failure(app_client, monkeypatch):
    client, _ = app_client
    monkeypatch.setattr(main.settings, "storage_mode", "dropbox")

    class SimulatedDropbox:
        active = {
            "/folder/one.txt": ("a" * 64, "rev-one", b"same"),
            "/folder/two.txt": ("a" * 64, "rev-two", b"same"),
            "/folder/other.txt": ("b" * 64, "rev-other", b"other"),
        }
        deleted = {}
        fail_delete = False
        page_visits = 0

        def iter_folder(self, path, recursive):
            assert path == "" and recursive
            items = list(self.active.items())
            for page in (items[:2], items[2:]):
                self.page_visits += 1
                for path, (digest, revision, content) in page:
                    yield {
                        "type": "file", "path": path, "name": path.rsplit("/", 1)[-1],
                        "id": "id:" + path, "size": len(content),
                        "content_hash": digest, "rev": revision, "modified": None,
                    }

        def is_image(self, name):
            return False

        def get_image_for_analysis(self, path):
            raise AssertionError("Default exact scan downloaded an image")

        def download_file(self, path):
            raise AssertionError("Default exact scan downloaded file contents")

        def get_file_metadata(self, path):
            digest, revision, content = self.active[path]
            return {
                "type": "file", "path": path, "name": path.rsplit("/", 1)[-1],
                "id": "id:" + path, "size": len(content),
                "content_hash": digest, "rev": revision,
            }

        def path_exists(self, path):
            return path in self.active

        def delete_file(self, path):
            if self.fail_delete:
                raise RuntimeError("Simulated Dropbox failure")
            self.deleted[path] = self.active.pop(path)

        def restore_file(self, path, rev):
            if path in self.active:
                raise FileExistsError(path)
            digest, revision, content = self.deleted[path]
            assert rev == revision
            self.active[path] = self.deleted.pop(path)
            return self.get_file_metadata(path)

    fake = SimulatedDropbox()
    monkeypatch.setattr(main, "DropboxClient", lambda: fake)
    main.app.dependency_overrides[main.get_dropbox_client] = lambda: fake
    scan(client)
    assert fake.page_visits == 2
    group = client.get("/api/duplicates").json()["groups"][0]
    candidate = next(f["path"] for f in group["files"] if not f["is_recommended"])
    assert client.post("/api/trash", json={"paths": [group["recommended_keep"]], "confirm": True}).status_code == 409
    fake.active[candidate] = ("changed", "new-rev", b"same")
    assert client.post("/api/trash", json={"paths": [candidate], "confirm": True}).status_code == 409
    fake.active[candidate] = ("a" * 64, "rev-one" if candidate.endswith("one.txt") else "rev-two", b"same")

    fake.fail_delete = True
    failed = client.post("/api/trash", json={"paths": [candidate], "confirm": True})
    assert failed.json()["failed_count"] == 1
    assert candidate in fake.active
    fake.fail_delete = False
    moved = client.post("/api/trash", json={"paths": [candidate], "confirm": True})
    assert moved.json()["trashed_count"] == 1, moved.text
    assert candidate in fake.deleted and candidate not in fake.active
    record = client.get("/api/recovery").json()["files"][0]
    restored = client.post("/api/restore", json={"ids": [record["id"]], "confirm": True})
    assert restored.json()["restored_count"] == 1, restored.text
    assert candidate in fake.active and candidate not in fake.deleted


def test_failed_scan_invalidates_review(app_client, monkeypatch):
    client, root = app_client
    (root / "a.txt").write_text("same")
    (root / "b.txt").write_text("same")
    scan(client)
    assert client.get("/api/duplicates").json()["groups"]

    class BrokenLocal(LocalClient):
        def __init__(self):
            super().__init__(str(root))

        def iter_folder(self, path="", recursive=False):
            yield self.get_file_metadata("/a.txt")
            raise RuntimeError("Simulated listing failure")

    monkeypatch.setattr(main, "LocalClient", BrokenLocal)
    result = client.post("/api/scan", json={})
    assert result.status_code == 200
    job = client.get(f"/api/jobs/{result.json()['job_id']}").json()
    assert job["status"] == "failed"
    assert "Simulated listing failure" in job["error_message"]
    assert client.get("/api/duplicates").json()["groups"] == []
