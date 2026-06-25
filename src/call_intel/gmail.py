from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from googleapiclient.discovery import build
from rich.console import Console

from .google_auth import get_credentials

console = Console()


@dataclass
class EmailThread:
    subject: str
    snippet: str
    messages: list[EmailMessage]


@dataclass
class EmailMessage:
    sender: str
    date: str
    body: str


def fetch_project_emails(
    project_name: str,
    days_back: int = 30,
    max_results: int = 10,
) -> list[EmailThread]:
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds)

    after_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y/%m/%d")
    query = f"{project_name} after:{after_date}"

    console.print(f"[dim]Searching Gmail for: {query}[/dim]")

    results = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )

    messages = results.get("messages", [])
    if not messages:
        return []

    thread_ids_seen: set[str] = set()
    threads: list[EmailThread] = []

    for msg_ref in messages:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=msg_ref["id"], format="full")
            .execute()
        )

        thread_id = msg.get("threadId", "")
        if thread_id in thread_ids_seen:
            continue
        thread_ids_seen.add(thread_id)

        headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
        subject = headers.get("Subject", "(no subject)")
        sender = headers.get("From", "Unknown")
        date = headers.get("Date", "")

        body = _extract_body(msg["payload"])

        threads.append(
            EmailThread(
                subject=subject,
                snippet=msg.get("snippet", ""),
                messages=[EmailMessage(sender=sender, date=date, body=body)],
            )
        )

    console.print(f"[green]✓[/green] Found {len(threads)} relevant email threads")
    return threads


def _extract_body(payload: dict) -> str:
    if payload.get("body", {}).get("data"):
        return _decode_body(payload["body"]["data"])

    for part in payload.get("parts", []):
        if part["mimeType"] == "text/plain" and part.get("body", {}).get("data"):
            return _decode_body(part["body"]["data"])

    for part in payload.get("parts", []):
        if part["mimeType"] == "text/html" and part.get("body", {}).get("data"):
            raw = _decode_body(part["body"]["data"])
            return re.sub(r"<[^>]+>", "", raw)

    return ""


def _decode_body(data: str) -> str:
    decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    return decoded[:2000]


def format_emails_as_context(threads: list[EmailThread]) -> str:
    if not threads:
        return ""

    lines = ["## Relevant Email Context\n"]
    for thread in threads[:5]:
        lines.append(f"### {thread.subject}")
        for msg in thread.messages:
            lines.append(f"**From:** {msg.sender}  **Date:** {msg.date}")
            lines.append(msg.body[:500])
            lines.append("")
        lines.append("---")

    return "\n".join(lines)
