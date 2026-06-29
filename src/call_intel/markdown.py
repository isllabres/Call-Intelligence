from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .models import Analysis, CallRecord, Transcript


def _fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def generate_transcript_md(record: CallRecord) -> str:
    lines = [
        f"# {record.title} — Transcript",
        "",
        f"**Date:** {record.date.strftime('%Y-%m-%d')}  ",
        f"**Project:** {record.project or '—'}  ",
        f"**Duration:** {_fmt_time(record.duration_seconds)}  ",
        f"**Speakers:** {', '.join(record.speakers) or 'Unknown'}",
        "",
        "---",
        "",
    ]

    current_speaker = None
    for seg in record.transcript.segments:
        speaker = seg.speaker or "Unknown"
        timestamp = _fmt_time(seg.start)
        if speaker != current_speaker:
            current_speaker = speaker
            lines.append(f"### {speaker} `[{timestamp}]`")
            lines.append("")
        lines.append(f"{seg.text.strip()}")
        lines.append("")

    return "\n".join(lines)


def generate_analysis_md(record: CallRecord) -> str:
    a = record.analysis
    lines = [
        f"# {record.title} — Analysis",
        "",
        f"**Date:** {record.date.strftime('%Y-%m-%d')}  ",
        f"**Project:** {record.project or '—'}  ",
        f"**Duration:** {_fmt_time(record.duration_seconds)}  ",
        f"**Sentiment:** {a.sentiment}",
        "",
        "## Summary",
        "",
        a.summary,
        "",
    ]

    if a.key_topics:
        lines.extend(["## Key Topics", ""])
        for topic in a.key_topics:
            lines.append(f"- {topic}")
        lines.append("")

    if a.action_items:
        lines.extend(["## Action Items", ""])
        lines.append("| Priority | Task | Assignee | Deadline |")
        lines.append("|----------|------|----------|----------|")
        for item in a.action_items:
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                item.priority, "⚪"
            )
            lines.append(
                f"| {priority_icon} {item.priority} | {item.description} "
                f"| {item.assignee or '—'} | {item.deadline or '—'} |"
            )
        lines.append("")

    if a.key_decisions:
        lines.extend(["## Key Decisions", ""])
        for d in a.key_decisions:
            lines.append(f"- {d}")
        lines.append("")

    if a.follow_ups:
        lines.extend(["## Follow-ups", ""])
        for f in a.follow_ups:
            lines.append(f"- [ ] {f}")
        lines.append("")

    if a.development_insights:
        lines.extend(["## Development Insights", ""])
        for insight in a.development_insights:
            lines.append(f"- {insight}")
        lines.append("")

    if a.speech_feedback:
        lines.extend(["## Speech & Communication Feedback", ""])
        for fb in a.speech_feedback:
            lines.append(f"### {fb.category.replace('_', ' ').title()}")
            lines.append("")
            lines.append(f"**Observation:** {fb.observation}")
            lines.append("")
            lines.append(f"**Suggestion:** {fb.suggestion}")
            if fb.example:
                lines.append("")
                lines.append(f"> *\"{fb.example}\"*")
            lines.append("")

    if a.calendar_events:
        lines.extend(["## Calendar Events Created", ""])
        for ev in a.calendar_events:
            time_str = f" at {ev.time}" if ev.time else ""
            lines.append(f"- **{ev.title}** — {ev.date}{time_str} ({ev.duration_minutes} min)")
            if ev.description:
                lines.append(f"  {ev.description}")
            if ev.attendees:
                lines.append(f"  Attendees: {', '.join(ev.attendees)}")
        lines.append("")

    if a.tasks:
        lines.extend(["## Tasks Created", ""])
        for task in a.tasks:
            due = f" (due {task.due_date})" if task.due_date else ""
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task.priority, "⚪")
            lines.append(f"- {priority_icon} **{task.title}**{due}")
            if task.notes:
                lines.append(f"  {task.notes}")
        lines.append("")

    if a.participant_summary:
        lines.extend(["## Participant Summary", ""])
        for name, summary in a.participant_summary.items():
            lines.append(f"- **{name}:** {summary}")
        lines.append("")

    return "\n".join(lines)


def write_call_output(record: CallRecord) -> Path:
    output_dir = Path(record.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    transcript_path = output_dir / "transcript.md"
    transcript_path.write_text(generate_transcript_md(record))

    analysis_path = output_dir / "analysis.md"
    analysis_path.write_text(generate_analysis_md(record))

    return output_dir


def update_index(output_root: Path, records: list[CallRecord]) -> None:
    sorted_records = sorted(records, key=lambda r: r.date, reverse=True)

    lines = [
        "# Call Intelligence — Index",
        "",
        f"_Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
        "",
        "| Date | Project | Title | Duration | Links |",
        "|------|---------|-------|----------|-------|",
    ]

    for r in sorted_records:
        try:
            rel_dir = Path(r.output_dir).relative_to(output_root)
        except ValueError:
            continue
        date = r.date.strftime("%Y-%m-%d")
        duration = _fmt_time(r.duration_seconds)
        project = r.project or "—"
        links = (
            f"[Transcript]({rel_dir}/transcript.md) · "
            f"[Analysis]({rel_dir}/analysis.md)"
        )
        lines.append(f"| {date} | {project} | {r.title} | {duration} | {links} |")

    lines.append("")
    (output_root / "index.md").write_text("\n".join(lines))
