"""Durable single-host workflow ledger shared by API and worker processes.

SQLite transactions claim dispatches before network I/O. An interrupted dispatch is
held for reconciliation, never automatically retried. Keep this file on local disk
or a Docker named volume, not a network filesystem.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from config import settings


def now():
    return datetime.now(timezone.utc).isoformat()


class ConflictError(ValueError):
    pass


class StateStore:
    def __init__(self, path=None):
        self.path = str(Path(path or settings.STATE_DB_PATH).resolve())
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS records (
                    kind TEXT NOT NULL, id TEXT NOT NULL, data TEXT NOT NULL,
                    PRIMARY KEY (kind, id)
                );
                CREATE TABLE IF NOT EXISTS activity (
                    id TEXT PRIMARY KEY, kind TEXT NOT NULL, record_id TEXT NOT NULL,
                    created_at TEXT NOT NULL, data TEXT NOT NULL
                );
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, kind, record_id):
        with self.connect() as db:
            row = db.execute(
                "SELECT data FROM records WHERE kind=? AND id=?", (kind, record_id)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def list(self, kind):
        with self.connect() as db:
            rows = db.execute(
                "SELECT data FROM records WHERE kind=? ORDER BY rowid", (kind,)
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def put(self, kind, record_id, data):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute(
                "SELECT data FROM records WHERE kind=? AND id=?", (kind, record_id)
            ).fetchone()
            created = json.loads(previous[0]).get("created_at") if previous else None
            value = {
                **data,
                "id": record_id,
                "created_at": created or now(),
                "updated_at": now(),
            }
            db.execute(
                "INSERT INTO records VALUES (?, ?, ?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data",
                (kind, record_id, json.dumps(value)),
            )
            db.execute(
                "INSERT INTO activity VALUES (?, ?, ?, ?, ?)",
                (
                    uuid4().hex,
                    f"{kind}.{value.get('status', 'saved')}",
                    record_id,
                    now(),
                    "{}",
                ),
            )
        return value

    def delete(self, kind, record_id):
        with self.connect() as db:
            result = db.execute(
                "DELETE FROM records WHERE kind=? AND id=?", (kind, record_id)
            )
        return bool(result.rowcount)

    def event(self, kind, record_id, data=None):
        with self.connect() as db:
            db.execute(
                "INSERT INTO activity VALUES (?, ?, ?, ?, ?)",
                (uuid4().hex, kind, record_id, now(), json.dumps(data or {})),
            )

    def transition(self, kind, record_id, allowed, status, **changes):
        """Compare-and-set across processes. State change and audit event are atomic."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT data FROM records WHERE kind=? AND id=?", (kind, record_id)
            ).fetchone()
            if row is None:
                raise KeyError(record_id)
            value = json.loads(row[0])
            if value.get("status") not in allowed:
                raise ConflictError(
                    f"Record is {value.get('status')}; cannot change to {status}"
                )
            value.update(changes, status=status, updated_at=now())
            db.execute(
                "UPDATE records SET data=? WHERE kind=? AND id=?",
                (json.dumps(value), kind, record_id),
            )
            db.execute(
                "INSERT INTO activity VALUES (?, ?, ?, ?, ?)",
                (uuid4().hex, f"{kind}.{status}", record_id, now(), "{}"),
            )
        return value

    def queue_approval(self, approval_id, data):
        """Insert once: rerunning discovery must not overwrite reviewed/sent drafts."""
        value = {
            **data,
            "id": approval_id,
            "thread_id": approval_id,
            "status": "pending",
            "created_at": now(),
        }
        with self.connect() as db:
            result = db.execute(
                "INSERT OR IGNORE INTO records VALUES ('approvals', ?, ?)",
                (approval_id, json.dumps(value)),
            )
            if result.rowcount:
                db.execute(
                    "INSERT INTO activity VALUES (?, ?, ?, ?, ?)",
                    (uuid4().hex, "approvals.pending", approval_id, now(), "{}"),
                )
        return self.get("approvals", approval_id)

    def claim_workflow(self, thread_id):
        """Prevent two processes from mutating the same conversation concurrently.

        A process crash leaves the thread held. An operator must reconcile and
        release that record; we do not guess whether its external work completed.
        """
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT data FROM records WHERE kind='threads' AND id=?", (thread_id,)
            ).fetchone()
            if row and json.loads(row[0])["status"] == "running":
                raise ConflictError(
                    "Conversation is running or interrupted; inspect its activity before retrying"
                )
            data = {"id": thread_id, "status": "running", "created_at": now()}
            db.execute(
                "INSERT INTO records VALUES ('threads', ?, ?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data",
                (thread_id, json.dumps(data)),
            )

    def activities(self, limit=100):
        with self.connect() as db:
            rows = db.execute(
                "SELECT id, kind, record_id, created_at, data FROM activity ORDER BY rowid DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            dict(
                id=r[0],
                kind=r[1],
                record_id=r[2],
                created_at=r[3],
                data=json.loads(r[4]),
            )
            for r in rows
        ]

    def email_logs(self):
        # Notifications and simulated/test data never count as outreach.
        return [
            {
                "id": m["id"],
                "recipient": m["to"],
                "company": m.get("company", ""),
                "subject": m["subject"],
                "dateSent": m["created_at"],
                "status": "Sent",
                "thread": m["body"],
            }
            for m in self.list("messages")
            if m.get("status") == "sent" and m.get("purpose") == "outreach"
        ]

    def metrics(self):
        return {
            "totalEmailsSent": len(self.email_logs()),
            "totalResponsesReceived": None,
            "responseRatePercent": None,
            "activeLeadsInPipeline": len(self.list("leads")),
            "replyTrackingAvailable": False,
        }


store = StateStore()
