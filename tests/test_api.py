import io

from aihub.api.app import create_app
from tests.conftest import FakeServices


def test_health(client):
    assert client.get("/health").get_json()["status"] == "ok"


def test_chat_validation(client):
    assert client.post("/api/chat", json={}).status_code == 400
    assert client.post("/api/chat", data="not json").status_code == 400
    assert client.post("/api/chat", json={"message": "x" * 5000}).status_code == 400


def test_chat_ok(client):
    r = client.post("/api/chat", json={"message": "hello", "session_id": "s1"})
    assert r.status_code == 200 and r.get_json()["answer"] == "hi"


def test_upload_rejects_non_pdf(client):
    r = client.post("/api/documents", data={"file": (io.BytesIO(b"hello"), "a.txt")},
                    content_type="multipart/form-data")
    assert r.status_code == 400
    r = client.post("/api/documents", data={"file": (io.BytesIO(b"not pdf"), "a.pdf")},
                    content_type="multipart/form-data")
    assert r.status_code == 400


def test_api_key_enforced(settings):
    settings.api_key = "secret"
    c = create_app(settings, FakeServices()).test_client()
    assert c.get("/health").status_code == 200
    assert c.get("/api/documents").status_code == 401
    assert c.get("/api/documents", headers={"X-API-Key": "secret"}).status_code == 200


def test_unknown_route_is_json(client):
    r = client.get("/nope")
    assert r.status_code == 404 and "error" in r.get_json()
