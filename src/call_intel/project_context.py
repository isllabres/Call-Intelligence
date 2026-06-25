from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console

from .config import get_output_dir
from .filename import project_slug
from .models import CallRecord

console = Console()


def get_project_history(project_name: str) -> list[CallRecord]:
    output_dir = get_output_dir()
    slug = project_slug(project_name)
    records: list[CallRecord] = []

    for meta_path in output_dir.rglob("meta.json"):
        try:
            data = json.loads(meta_path.read_text())
            record = CallRecord(**data)
            if project_slug(record.project) == slug:
                records.append(record)
        except Exception:
            continue

    records.sort(key=lambda r: r.date)
    return records


def format_project_context(records: list[CallRecord]) -> str:
    if not records:
        return ""

    lines = ["## Previous Calls for This Project\n"]

    for r in records[-5:]:
        lines.append(f"### {r.title} ({r.date.strftime('%Y-%m-%d')})")
        lines.append(f"**Summary:** {r.analysis.summary}")

        if r.analysis.action_items:
            lines.append("**Action Items:**")
            for item in r.analysis.action_items:
                lines.append(f"- [{item.priority}] {item.description}")

        if r.analysis.key_decisions:
            lines.append("**Decisions:**")
            for d in r.analysis.key_decisions:
                lines.append(f"- {d}")

        if r.analysis.follow_ups:
            lines.append("**Open Follow-ups:**")
            for f in r.analysis.follow_ups:
                lines.append(f"- {f}")

        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)
