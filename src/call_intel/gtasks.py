from __future__ import annotations

from datetime import datetime

from googleapiclient.discovery import build
from rich.console import Console

from .google_auth import get_credentials
from .models import TaskItem

console = Console()


def create_google_tasks(
    tasks: list[TaskItem], task_list_name: str = "Call Intelligence"
) -> int:
    if not tasks:
        return 0

    creds = get_credentials()
    service = build("tasks", "v1", credentials=creds)

    list_id = _get_or_create_task_list(service, task_list_name)
    created = 0

    for task in tasks:
        try:
            body: dict = {
                "title": task.title,
                "notes": task.notes,
            }

            if task.due_date:
                due_dt = _parse_due_date(task.due_date)
                if due_dt:
                    body["due"] = due_dt.strftime("%Y-%m-%dT00:00:00.000Z")

            service.tasks().insert(tasklist=list_id, body=body).execute()
            created += 1
            console.print(f"[green]✓[/green] Task created: {task.title}")

        except Exception as e:
            console.print(f"[yellow]⚠ Failed to create task '{task.title}':[/yellow] {e}")

    return created


def _get_or_create_task_list(service, name: str) -> str:
    results = service.tasklists().list(maxResults=100).execute()
    for tl in results.get("items", []):
        if tl["title"] == name:
            return tl["id"]

    new_list = service.tasklists().insert(body={"title": name}).execute()
    console.print(f"[green]✓[/green] Created task list: {name}")
    return new_list["id"]


def _parse_due_date(date_str: str) -> datetime | None:
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None
