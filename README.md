# Message Status API

A small REST API that tracks the delivery status of one-to-one text messages
(Sent -> Delivered -> Read). Built as a course project (CS391, Assiut University)
inspired by the message status feature in WhatsApp. It is a simplified class
design, not WhatsApp's real implementation.

## Tech stack
Python 3.13, FastAPI, SQLite, pytest

## Rules implemented
1. A valid message is saved with status `Sent`; an empty message is refused and nothing is saved.
2. Only the recipient can move a message forward, one step at a time: `Sent` -> `Delivered` -> `Read`.
   Skipping a step or going backward is refused and the status is kept.
3. A repeated request for the current status returns that status without a change.
4. A user who is not the sender or recipient cannot read or change the message.

## Run
```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install fastapi uvicorn pytest httpx
uvicorn main:app --reload
```
Open http://127.0.0.1:8000/docs to try the API.

## Test
```
pytest -v
```
8 tests cover the success path, refusals, repeated requests, and access control.

## Endpoints
- `POST /messages` - send a message
- `GET /messages/{id}?user_id=` - read a message
- `PATCH /messages/{id}/status` - update the status