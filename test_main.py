import pytest
from fastapi.testclient import TestClient

from main import create_app


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(str(tmp_path / "test.db")))


def send(client, text="Hello"):
    return client.post(
        "/messages", json={"sender_id": 1, "recipient_id": 2, "text": text}
    )


def set_status(client, mid, status, user_id=2):
    return client.patch(
        f"/messages/{mid}/status", json={"user_id": user_id, "status": status}
    )


def test_send_creates_message_with_sent_status(client):
    r = send(client)
    assert r.status_code == 201
    assert r.json()["status"] == "Sent"
    assert "id" in r.json()


def test_empty_text_is_refused_and_creates_nothing(client):
    r = send(client, "   ")
    assert r.status_code == 400
    assert client.get("/messages/1", params={"user_id": 1}).status_code == 404


def test_recipient_moves_sent_to_delivered_to_read(client):
    mid = send(client).json()["id"]
    assert set_status(client, mid, "Delivered").json()["status"] == "Delivered"
    assert set_status(client, mid, "Read").json()["status"] == "Read"
    got = client.get(f"/messages/{mid}", params={"user_id": 1}).json()
    assert got["status"] == "Read"


def test_backward_change_is_refused_and_status_kept(client):
    mid = send(client).json()["id"]
    set_status(client, mid, "Delivered")
    set_status(client, mid, "Read")
    assert set_status(client, mid, "Delivered").status_code == 409
    got = client.get(f"/messages/{mid}", params={"user_id": 1}).json()
    assert got["status"] == "Read"


def test_skipping_delivered_is_refused(client):
    mid = send(client).json()["id"]
    assert set_status(client, mid, "Read").status_code == 409


def test_repeated_request_returns_current_status(client):
    mid = send(client).json()["id"]
    first = set_status(client, mid, "Delivered")
    second = set_status(client, mid, "Delivered")
    assert first.status_code == second.status_code == 200
    assert second.json()["status"] == "Delivered"


def test_other_user_cannot_read_or_change_message(client):
    mid = send(client).json()["id"]
    assert client.get(f"/messages/{mid}", params={"user_id": 3}).status_code == 404
    assert set_status(client, mid, "Delivered", user_id=3).status_code == 404


def test_sender_cannot_mark_own_message_delivered(client):
    mid = send(client).json()["id"]
    assert set_status(client, mid, "Delivered", user_id=1).status_code == 403