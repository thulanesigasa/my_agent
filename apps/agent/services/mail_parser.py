"""Decode Gmail MIME safely; quoted text and automated mail are kept separate."""

import base64
import re
from email.header import decode_header, make_header
from email.utils import parseaddr
from html.parser import HTMLParser


class TextFromHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "blockquote"):
            self.hidden += 1
        if tag in ("br", "p", "div", "li") and not self.hidden:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "blockquote") and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def decode_data(data, charset="utf-8"):
    try:
        raw = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
        return raw.decode(charset, errors="replace")
    except (ValueError, TypeError, LookupError):
        return ""


def new_text(text):
    lines = []
    for line in text.splitlines():
        if re.match(
            r"^\s*(On .+wrote:|-----Original Message-----|From:\s)", line, re.I
        ):
            break
        if not line.lstrip().startswith(">"):
            lines.append(line)
    return "\n".join(lines).strip()


def parse_message(message):
    payload = message.get("payload", {})
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
    plain, html = [], []

    def walk(part):
        if part.get("filename") or "attachment" in next(
            (
                h["value"].lower()
                for h in part.get("headers", [])
                if h["name"].lower() == "content-disposition"
            ),
            "",
        ):
            return
        mime = part.get("mimeType", "")
        content_type = next(
            (
                h["value"]
                for h in part.get("headers", [])
                if h["name"].lower() == "content-type"
            ),
            "",
        )
        charset = re.search(r'charset=["\']?([^;"\'\s]+)', content_type, re.I)
        text = decode_data(
            part.get("body", {}).get("data", ""),
            charset.group(1) if charset else "utf-8",
        )
        if mime == "text/plain":
            plain.append(text)
        elif mime == "text/html":
            parser = TextFromHTML()
            parser.feed(text)
            html.append("".join(parser.parts))
        for child in part.get("parts", []):
            walk(child)

    walk(payload)
    body = new_text("\n".join(plain or html))
    sender = parseaddr(headers.get("from", ""))[1].lower()
    auto = headers.get("auto-submitted", "no").lower() != "no" or bool(
        headers.get("x-autoreply") or headers.get("x-autorespond")
    )
    bounce = payload.get("mimeType") == "multipart/report" or "mailer-daemon@" in sender
    try:
        subject = str(make_header(decode_header(headers.get("subject", ""))))
    except (ValueError, TypeError, LookupError):
        subject = headers.get("subject", "")
    return {
        "id": message["id"],
        "thread_id": message.get("threadId"),
        "sender": sender,
        "subject": subject,
        "body": body,
        "rfc_message_id": headers.get("message-id", ""),
        "in_reply_to": headers.get("in-reply-to", ""),
        "references": headers.get("references", ""),
        "provider_timestamp": message.get("internalDate"),
        "labels": message.get("labelIds", []),
        "automated": auto or bounce,
        "bounce": bounce,
        "unsubscribe": bool(
            re.search(
                r"\b(unsubscribe|remove me|stop emailing|do not (?:email|contact)|don't (?:email|contact))\b",
                body,
                re.I,
            )
        ),
    }
