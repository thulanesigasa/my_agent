"""Run on your own computer: python connect_gmail.py authorize --account you@gmail.com."""

import argparse
import json
import sys
from pathlib import Path


class SetupError(ValueError):
    """A safe, user-facing setup message without credential values."""


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "apps" / "agent"))
from auth.gmail_credentials import SCOPES, write_private_json


def authorize(client_path, token_path, account, port=8765):
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from services.contacts import normalize_email

    account = normalize_email(account)
    config = json.loads(Path(client_path).read_text(encoding="utf-8"))
    if "installed" not in config and "web" not in config:
        raise SetupError(
            "Use a Google OAuth Desktop or Web client JSON, not an API key or service-account key"
        )
    if "web" in config:
        redirect = f"http://localhost:{port}/"
        if redirect not in config["web"].get("redirect_uris", []):
            raise SetupError(
                f"Register {redirect} as an authorised redirect URI on this Web client, or use a Desktop client JSON"
            )
    flow = InstalledAppFlow.from_client_config(config, SCOPES)
    credentials = flow.run_local_server(
        host="localhost",
        port=port if "web" in config else 0,
        timeout_seconds=180,
        access_type="offline",
        prompt="consent",
        login_hint=account,
        success_message="Gmail authorisation finished. You can close this tab and return to the terminal.",
    )
    granted = credentials.granted_scopes or credentials.scopes or []
    if not credentials.refresh_token or not set(SCOPES).issubset(set(granted)):
        raise SetupError(
            "Google did not grant both permissions and offline access. Reconnect and approve both permissions"
        )
    profile = (
        build("gmail", "v1", credentials=credentials, cache_discovery=False)
        .users()
        .getProfile(userId="me")
        .execute()
    )
    if profile["emailAddress"].lower() != account:
        raise SetupError(
            "The selected Google account does not match --account. No token was saved"
        )
    token = json.loads(credentials.to_json())
    token["scopes"] = list(granted)
    token["gmail_account"] = account
    write_private_json(token_path, token)
    return account


def main():
    parser = argparse.ArgumentParser(
        description="Connect your local Gmail account. Never upload credentials to chat or GitHub."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    auth = commands.add_parser("authorize")
    auth.add_argument("--account", required=True)
    auth.add_argument(
        "--credentials", type=Path, default=ROOT / ".secrets" / "gmail-client.json"
    )
    auth.add_argument("--web-port", type=int, default=8765)
    commands.add_parser("check")
    args = parser.parse_args()
    try:
        from config import settings

        if args.command == "authorize":
            mailbox = authorize(
                args.credentials, settings.GMAIL_TOKEN_PATH, args.account, args.web_port
            )
            print(
                f"Connected: {mailbox}. Token saved locally. Restart API and worker, then verify in Dashboard > Settings."
            )
            print(
                "External OAuth apps in Testing mode generally require reauthorisation after seven days for Gmail scopes."
            )
        else:
            import asyncio
            from services.email_service import email_service

            profile = asyncio.run(email_service.get_profile())
            print(
                f"Verified Gmail account: {profile['emailAddress']}. No email was sent."
            )
    except SetupError as exc:
        print(f"Setup stopped: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError:
        print(
            "Credentials JSON was not found. Put your downloaded file at .secrets/gmail-client.json.",
            file=sys.stderr,
        )
        return 1
    except ValueError:
        print(
            "Configuration or credentials are invalid. Check your .env, account address and OAuth client JSON. No secrets were printed.",
            file=sys.stderr,
        )
        return 1
    except Exception:
        print(
            "Gmail connection failed. Check account access, API enablement, permissions and network; rerun authorisation if needed. No secrets were printed.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
