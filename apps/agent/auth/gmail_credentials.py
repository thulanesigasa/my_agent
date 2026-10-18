"""Local Gmail credentials. No token values are logged or returned by the API."""

import json
import os
import tempfile
from pathlib import Path

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


def write_private_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=".gmail-", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_credentials(settings):
    from google.oauth2.credentials import Credentials

    path = Path(settings.GMAIL_TOKEN_PATH)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        expected = settings.GMAIL_USER_EMAIL or data.get("gmail_account", "")
        if not expected:
            raise ValueError("Reconnect Gmail with --account to bind the mailbox")
        credentials = Credentials.from_authorized_user_info(data, scopes=SCOPES)
        if not credentials.refresh_token or not set(SCOPES).issubset(
            set(data.get("scopes", []))
        ):
            raise ValueError("Reconnect Gmail to grant reading and sending permissions")
        return credentials, expected.lower()
    values = (
        settings.GMAIL_CLIENT_ID,
        settings.GMAIL_CLIENT_SECRET,
        settings.GMAIL_REFRESH_TOKEN,
    )
    if all(values):
        if not settings.GMAIL_USER_EMAIL:
            raise ValueError(
                "Set GMAIL_USER_EMAIL to bind legacy OAuth credentials to a mailbox"
            )
        return (
            Credentials(
                token=None,
                refresh_token=values[2],
                client_id=values[0],
                client_secret=values[1],
                token_uri="https://oauth2.googleapis.com/token",
                scopes=SCOPES,
            ),
            settings.GMAIL_USER_EMAIL.lower(),
        )
    return None, None
