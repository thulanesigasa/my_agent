"""Durable single-host workflow ledger shared by API and worker processes.

SQLite transactions claim dispatches before network I/O. An interrupted dispatch is
held for reconciliation, never automatically retried. Keep this file on local disk
or a Docker named volume, not a network filesystem.
"""

import json
import sqlite3
import time
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

    def snapshot(self, kinds):
        """Read report inputs in one consistent SQLite transaction."""
        with self.connect() as db:
            db.execute("BEGIN")
            result = {}
            for kind in kinds:
                rows = db.execute(
                    "SELECT id, data FROM records WHERE kind=? ORDER BY rowid", (kind,)
                ).fetchall()
                result[kind] = [
                    {**json.loads(data), "id": record_id} for record_id, data in rows
                ]
            return result

    def insert_once(self, kind, record_id, data):
        value = {**data, "id": record_id, "created_at": now()}
        with self.connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO records VALUES (?, ?, ?)",
                (kind, record_id, json.dumps(value)),
            )
        return self.get(kind, record_id)

    def record_outcome(self, mailbox, thread_id, recipient, outcome, note):
        event_id = uuid4().hex
        value = {
            "id": event_id,
            "mailbox": mailbox,
            "thread_id": thread_id,
            "recipient": recipient,
            "outcome": outcome,
            "note": note,
            "created_at": now(),
        }
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "INSERT INTO records VALUES ('outcomes', ?, ?)",
                (event_id, json.dumps(value)),
            )
            if outcome == "unsubscribed":
                row = db.execute(
                    "SELECT data FROM records WHERE kind='contacts' AND id=?",
                    (recipient,),
                ).fetchone()
                contact = json.loads(row[0]) if row else {"email": recipient}
                contact.update(
                    consent="unsubscribed", suppression_reason=note, updated_at=now()
                )
                db.execute(
                    "INSERT INTO records VALUES ('contacts', ?, ?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data",
                    (recipient, json.dumps(contact)),
                )
            db.execute(
                "INSERT INTO activity VALUES (?, ?, ?, ?, ?)",
                (
                    uuid4().hex,
                    "outcomes.recorded",
                    event_id,
                    now(),
                    json.dumps({"outcome": outcome}),
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

    def confirm_submission(self, record_id, provider_id, thread_id):
        """Commit provider evidence and approval completion together, idempotently."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT data FROM records WHERE kind='messages' AND id=?", (record_id,)
            ).fetchone()
            if row is None:
                raise KeyError(record_id)
            message = json.loads(row[0])
            if message["status"] not in ("sending", "delivery_unknown", "sent"):
                raise ConflictError("Submission is not held or sent")
            if (
                message["status"] == "sent"
                and message.get("provider_message_id") != provider_id
            ):
                raise ConflictError(
                    "Provider evidence conflicts with the confirmed send"
                )
            approval = None
            if message.get("approval_id"):
                row = db.execute(
                    "SELECT data FROM records WHERE kind='approvals' AND id=?",
                    (message["approval_id"],),
                ).fetchone()
                if row is None:
                    raise KeyError(message["approval_id"])
                approval = json.loads(row[0])
                if approval.get("dispatch_id") != record_id or approval[
                    "status"
                ] not in ("sending", "delivery_unknown", "sent"):
                    raise ConflictError("Approval no longer refers to this submission")
                if (
                    approval["status"] == "sent"
                    and approval.get("provider_message_id") != provider_id
                ):
                    raise ConflictError("Approval has different provider evidence")
                approval.update(
                    status="sent",
                    provider_message_id=provider_id,
                    provider_thread_id=thread_id,
                    updated_at=now(),
                )
                db.execute(
                    "UPDATE records SET data=? WHERE kind='approvals' AND id=?",
                    (json.dumps(approval), message["approval_id"]),
                )
            was_sent = message["status"] == "sent"
            message.update(
                status="sent",
                provider_message_id=provider_id,
                thread_id=thread_id,
                updated_at=now(),
            )
            db.execute(
                "UPDATE records SET data=? WHERE kind='messages' AND id=?",
                (json.dumps(message), record_id),
            )
            if not was_sent:
                db.execute(
                    "INSERT INTO activity VALUES (?, ?, ?, ?, ?)",
                    (uuid4().hex, "messages.sent", record_id, now(), "{}"),
                )
        return message

    def acquire_lease(self, key, owner, seconds=300):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT data FROM records WHERE kind='leases' AND id=?", (key,)
            ).fetchone()
            if row and json.loads(row[0]).get("expires", 0) > time.time():
                raise ConflictError("Mailbox synchronisation is already running")
            db.execute(
                "INSERT INTO records VALUES ('leases', ?, ?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data",
                (key, json.dumps({"owner": owner, "expires": time.time() + seconds})),
            )

    def renew_lease(self, key, owner):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT data FROM records WHERE kind='leases' AND id=?", (key,)
            ).fetchone()
            if not row or json.loads(row[0]).get("owner") != owner:
                raise ConflictError(
                    "Mailbox sync lease was lost; cursor was not changed"
                )
            db.execute(
                "UPDATE records SET data=? WHERE kind='leases' AND id=?",
                (json.dumps({"owner": owner, "expires": time.time() + 300}), key),
            )

    def release_lease(self, key, owner):
        with self.connect() as db:
            row = db.execute(
                "SELECT data FROM records WHERE kind='leases' AND id=?", (key,)
            ).fetchone()
            if row and json.loads(row[0]).get("owner") == owner:
                db.execute("DELETE FROM records WHERE kind='leases' AND id=?", (key,))

    def ingest_mailbox(self, owner, mailbox, history_id, messages, thread_ids=None):
        # Inbox and cursor commit together: a crash cannot advance past unrecorded replies.
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            lease = db.execute(
                "SELECT data FROM records WHERE kind='leases' AND id='gmail-sync'"
            ).fetchone()
            if not lease or json.loads(lease[0]).get("owner") != owner:
                raise ConflictError("Mailbox sync lease was lost")
            inserted = 0
            for mail in messages:
                record_id = f"{mailbox}:{mail['id']}"
                value = {
                    **mail,
                    "provider_message_id": mail["id"],
                    "id": record_id,
                    "mailbox": mailbox,
                    "status": "pending",
                    "created_at": now(),
                }
                result = db.execute(
                    "INSERT OR IGNORE INTO records VALUES ('inbox', ?, ?)",
                    (record_id, json.dumps(value)),
                )
                inserted += result.rowcount
                if mail.get("unsubscribe") and not mail.get("automated"):
                    row = db.execute(
                        "SELECT data FROM records WHERE kind='contacts' AND id=?",
                        (mail["sender"],),
                    ).fetchone()
                    contact = json.loads(row[0]) if row else {"email": mail["sender"]}
                    contact.update(
                        consent="unsubscribed",
                        suppression_reason=f"Gmail reply {mail['id']}",
                        updated_at=now(),
                    )
                    db.execute(
                        "INSERT INTO records VALUES ('contacts', ?, ?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data",
                        (mail["sender"], json.dumps(contact)),
                    )
            db.execute(
                "INSERT INTO records VALUES ('gmail_cursor', ?, ?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data",
                (
                    mailbox,
                    json.dumps(
                        {
                            "history_id": history_id,
                            "thread_ids": thread_ids or [],
                            "updated_at": now(),
                        }
                    ),
                ),
            )
        return inserted

    def email_logs(self):
        inbox = self.list("inbox")
        logs = []
        for message in self.list("messages"):
            if message.get("status") != "sent" or message.get("purpose") != "outreach":
                continue
            replies = [
                mail
                for mail in inbox
                if mail.get("matched_outbound_id") == message["id"]
            ]
            human = [mail for mail in replies if not mail.get("automated")]
            status = (
                "Responded"
                if human
                else (
                    "Bounced" if any(mail.get("bounce") for mail in replies) else "Sent"
                )
            )
            logs.append(
                {
                    "id": message["id"],
                    "recipient": message["to"],
                    "company": message.get("company", ""),
                    "subject": message["subject"],
                    "dateSent": message["created_at"],
                    "status": status,
                    "thread": message["body"],
                    "reply": human[-1]["body"] if human else None,
                }
            )
        return logs

    def metrics(self):
        from services.report_service import all_time_metrics

        return all_time_metrics()


store = StateStore()
