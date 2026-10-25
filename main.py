import os
import sqlite3
from contextlib import closing

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

RANK = {"Sent": 1, "Delivered": 2, "Read": 3}


class SendMessage(BaseModel):
    sender_id: int
    recipient_id: int
    text: str


class StatusUpdate(BaseModel):
    user_id: int
    status: str


def create_app(db_path: str = "messages.db") -> FastAPI:
    app = FastAPI(title="Message Status API")

    def connect():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    with closing(connect()) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                recipient_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Sent',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP)"""
        )
        conn.commit()

    def fetch(conn, message_id):
        return conn.execute(
            "SELECT * FROM messages WHERE id = ?", (message_id,)
        ).fetchone()

    @app.post("/messages", status_code=201)
    def send_message(body: SendMessage):
        if not body.text.strip():
            raise HTTPException(400, "Message text must not be empty")
        with closing(connect()) as conn:
            cur = conn.execute(
                "INSERT INTO messages (sender_id, recipient_id, text, status) "
                "VALUES (?, ?, ?, 'Sent')",
                (body.sender_id, body.recipient_id, body.text),
            )
            conn.commit()
            return {"id": cur.lastrowid, "status": "Sent"}

    @app.get("/messages/{message_id}")
    def get_message(message_id: int, user_id: int):
        with closing(connect()) as conn:
            row = fetch(conn, message_id)
        if row is None or user_id not in (row["sender_id"], row["recipient_id"]):
            raise HTTPException(404, "Message not found")
        return dict(row)

    @app.patch("/messages/{message_id}/status")
    def update_status(message_id: int, body: StatusUpdate):
        if body.status not in RANK:
            raise HTTPException(400, "Unknown status")
        with closing(connect()) as conn:
            row = fetch(conn, message_id)
            if row is None or body.user_id not in (row["sender_id"], row["recipient_id"]):
                raise HTTPException(404, "Message not found")
            if body.user_id != row["recipient_id"]:
                raise HTTPException(403, "Only the recipient can update the status")
            current = row["status"]
            if body.status == current:
                return {"id": message_id, "status": current}
            if RANK[body.status] != RANK[current] + 1:
                raise HTTPException(
                    409, f"Cannot change {current} to {body.status}; status remains {current}"
                )
            cur = conn.execute(
                "UPDATE messages SET status = ? WHERE id = ? AND status = ?",
                (body.status, message_id, current),
            )
            conn.commit()
            if cur.rowcount == 0:
                latest = fetch(conn, message_id)["status"]
                raise HTTPException(409, f"Status already changed to {latest}")
            return {"id": message_id, "status": body.status}

    return app


app = create_app(os.getenv("MSG_DB", "messages.db"))