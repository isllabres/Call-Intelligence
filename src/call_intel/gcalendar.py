from __future__ import annotations

from datetime import datetime, timedelta

from googleapiclient.discovery import build
from rich.console import Console

from .google_auth import get_credentials
from .models import CalendarEvent

console = Console()


def create_calendar_events(events: list[CalendarEvent]) -> list[str]:
    if not events:
        return []

    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)
    created_links: list[str] = []

    for event in events:
        try:
            start_dt = _parse_event_datetime(event.date, event.time)
            end_dt = start_dt + timedelta(minutes=event.duration_minutes)

            body: dict = {
                "summary": event.title,
                "description": event.description,
                "start": _format_datetime(start_dt),
                "end": _format_datetime(end_dt),
            }

            if event.attendees:
                body["attendees"] = [{"email": a} for a in event.attendees]

            result = service.events().insert(calendarId="primary", body=body).execute()
            link = result.get("htmlLink", "")
            created_links.append(link)
            console.print(
                f"[green]✓[/green] Calendar event created: {event.title} ({event.date})"
            )

        except Exception as e:
            console.print(f"[yellow]⚠ Failed to create event '{event.title}':[/yellow] {e}")

    return created_links


def _parse_event_datetime(date_str: str, time_str: str | None) -> datetime:
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(date_str, fmt)
            break
        except ValueError:
            continue
    else:
        dt = datetime.now() + timedelta(days=7)

    if time_str:
        for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p"):
            try:
                t = datetime.strptime(time_str, fmt)
                dt = dt.replace(hour=t.hour, minute=t.minute)
                return dt
            except ValueError:
                continue

    dt = dt.replace(hour=9, minute=0)
    return dt


def _format_datetime(dt: datetime) -> dict:
    return {
        "dateTime": dt.isoformat(),
        "timeZone": "Europe/Madrid",
    }
