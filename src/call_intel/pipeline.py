from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from rich.console import Console

from .analyze import analyze
from .config import get_output_dir
from .filename import parse_filename, parse_recording_name, project_slug
from .google_auth import is_authenticated
from .markdown import update_index, write_call_output
from .models import CallRecord
from .transcribe import transcribe
from .transcript_parser import parse_transcript_file

console = Console()


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_]+", "-", text)[:60]


def _build_output_dir(
    project: str, subtitle: str, date: datetime,
) -> Path:
    date_str = date.strftime("%d-%m-%Y")
    if project:
        subfolder = f"{subtitle} {date_str}" if subtitle else f"Meeting {date_str}"
        return get_output_dir() / project / subfolder
    return get_output_dir() / f"Meeting {date_str}"


def _load_existing_records(output_dir: Path) -> list[CallRecord]:
    records = []
    for meta_path in output_dir.rglob("meta.json"):
        try:
            data = json.loads(meta_path.read_text())
            records.append(CallRecord(**data))
        except Exception:
            continue
    return records


def process_call(
    audio_path: Path,
    title: str | None = None,
    project: str | None = None,
    date: datetime | None = None,
    speakers: list[str] | None = None,
    skip_analysis: bool = False,
    skip_google: bool = False,
    context: str = "",
    whisper_model: str | None = None,
) -> CallRecord:
    subtitle = ""
    if project is None or date is None:
        try:
            parsed = parse_filename(audio_path)
            project = project or parsed.project
            subtitle = parsed.subtitle
            date = date or parsed.date
            console.print(f"[dim]Parsed from filename → project: {project}, date: {parsed.date.strftime('%Y-%m-%d')}[/dim]")
        except ValueError:
            date = date or datetime.now()

    project = project or ""
    title = title or (f"{project} — {date.strftime('%Y-%m-%d')}" if project else audio_path.stem.replace("_", " ").replace("-", " ").title())
    output_dir = _build_output_dir(project, subtitle, date)

    console.print(f"\n[bold]Processing:[/bold] {audio_path.name}")
    console.print(f"[bold]Title:[/bold] {title}")
    console.print(f"[bold]Project:[/bold] {project or '(none)'}")
    console.print(f"[bold]Date:[/bold] {date.strftime('%Y-%m-%d')}")
    console.print()

    # Step 1: Transcription
    console.rule("[bold blue]Step 1: Transcription")
    transcript = transcribe(audio_path, model_size=whisper_model)
    console.print(
        f"[green]✓[/green] Transcribed {len(transcript.segments)} segments "
        f"({transcript.duration_seconds / 60:.1f} min)"
    )

    if speakers:
        for seg in transcript.segments:
            seg.speaker = speakers[0] if len(speakers) == 1 else None

    detected_speakers = sorted(
        {s.speaker for s in transcript.segments if s.speaker and s.speaker != "Unknown"}
    )

    # Step 2: Gather context
    project_context_text = ""
    email_context_text = ""

    if project and not skip_analysis:
        console.rule("[bold blue]Step 2: Gathering Context")

        from .project_context import format_project_context, get_project_history

        history = get_project_history(project)
        if history:
            project_context_text = format_project_context(history)
            console.print(f"[green]✓[/green] Found {len(history)} previous calls for project '{project}'")
        else:
            console.print(f"[dim]No previous calls found for project '{project}'[/dim]")

        if not skip_google and is_authenticated():
            try:
                from .gmail import fetch_project_emails, format_emails_as_context

                emails = fetch_project_emails(project)
                email_context_text = format_emails_as_context(emails)
                if emails:
                    console.print(f"[green]✓[/green] Retrieved {len(emails)} relevant email threads")
            except Exception as e:
                console.print(f"[yellow]⚠ Gmail fetch failed:[/yellow] {e}")

    # Step 4: AI Analysis
    analysis_result = None
    if not skip_analysis:
        console.rule("[bold blue]Step 3: AI Analysis")
        analysis_result = analyze(
            transcript,
            title=title,
            context=context,
            project_context=project_context_text,
            email_context=email_context_text,
            today=date.strftime("%Y-%m-%d"),
        )
        console.print("[green]✓[/green] Analysis complete")

        if analysis_result.action_items:
            console.print(f"  → {len(analysis_result.action_items)} action items identified")
        if analysis_result.calendar_events:
            console.print(f"  → {len(analysis_result.calendar_events)} calendar events detected")
        if analysis_result.tasks:
            console.print(f"  → {len(analysis_result.tasks)} tasks extracted")
    else:
        from .models import Analysis
        analysis_result = Analysis(summary="Analysis skipped.")

    # Step 5: Google Suite integration
    if not skip_analysis and not skip_google and is_authenticated():
        console.rule("[bold blue]Step 4: Google Suite Sync")

        if analysis_result.calendar_events:
            try:
                from .gcalendar import create_calendar_events

                links = create_calendar_events(analysis_result.calendar_events)
                console.print(f"[green]✓[/green] Created {len(links)} calendar events")
            except Exception as e:
                console.print(f"[yellow]⚠ Calendar sync failed:[/yellow] {e}")

        if analysis_result.tasks:
            try:
                from .gtasks import create_google_tasks

                list_name = f"Call Intel: {project}" if project else "Call Intelligence"
                count = create_google_tasks(analysis_result.tasks, task_list_name=list_name)
                console.print(f"[green]✓[/green] Created {count} tasks in Google Tasks")
            except Exception as e:
                console.print(f"[yellow]⚠ Tasks sync failed:[/yellow] {e}")
    elif not skip_google and not is_authenticated() and not skip_analysis:
        if analysis_result.calendar_events or analysis_result.tasks:
            console.print(
                "[dim]Tip: Run 'call-intel auth' to enable Google Calendar & Tasks sync[/dim]"
            )

    # Step 6: Write output
    record = CallRecord(
        title=title,
        project=project,
        date=date,
        source_path=str(audio_path.resolve()),
        audio_path=str(audio_path.resolve()),
        duration_seconds=transcript.duration_seconds,
        speakers=detected_speakers,
        transcript=transcript,
        analysis=analysis_result,
        output_dir=str(output_dir),
    )

    console.rule("[bold blue]Writing Output")
    write_call_output(record)

    meta_path = output_dir / "meta.json"
    meta_path.write_text(record.model_dump_json(indent=2))

    all_records = _load_existing_records(get_output_dir())
    update_index(get_output_dir(), all_records)

    console.print(f"[green]✓[/green] Output written to [bold]{output_dir}[/bold]")
    console.print()

    return record


def process_transcript(
    transcript_path: Path,
    title: str | None = None,
    project: str | None = None,
    date: datetime | None = None,
    speakers: list[str] | None = None,
    skip_analysis: bool = False,
    skip_google: bool = False,
    context: str = "",
) -> CallRecord:
    subtitle = ""
    if project is None or date is None:
        try:
            parsed = parse_filename(transcript_path)
            project = project or parsed.project
            subtitle = parsed.subtitle
            date = date or parsed.date
            console.print(f"[dim]Parsed from filename → project: {project}, date: {parsed.date.strftime('%Y-%m-%d')}[/dim]")
        except ValueError:
            date = date or datetime.now()

    project = project or ""
    title = title or (f"{project} — {date.strftime('%Y-%m-%d')}" if project else transcript_path.stem.replace("_", " ").replace("-", " ").title())
    output_dir = _build_output_dir(project, subtitle, date)

    console.print(f"\n[bold]Processing transcript:[/bold] {transcript_path.name}")
    console.print(f"[bold]Title:[/bold] {title}")
    console.print(f"[bold]Project:[/bold] {project or '(none)'}")
    console.print(f"[bold]Date:[/bold] {date.strftime('%Y-%m-%d')}")
    console.print()

    console.rule("[bold blue]Step 1: Parsing Transcript")
    transcript = parse_transcript_file(transcript_path)
    console.print(
        f"[green]✓[/green] Parsed {len(transcript.segments)} segments "
        f"from {transcript_path.suffix} file"
    )

    if speakers:
        for seg in transcript.segments:
            seg.speaker = speakers[0] if len(speakers) == 1 else None

    detected_speakers = sorted(
        {s.speaker for s in transcript.segments if s.speaker and s.speaker != "Unknown"}
    )

    project_context_text = ""
    email_context_text = ""

    if project and not skip_analysis:
        console.rule("[bold blue]Step 2: Gathering Context")

        from .project_context import format_project_context, get_project_history

        history = get_project_history(project)
        if history:
            project_context_text = format_project_context(history)
            console.print(f"[green]✓[/green] Found {len(history)} previous calls for project '{project}'")
        else:
            console.print(f"[dim]No previous calls found for project '{project}'[/dim]")

        if not skip_google and is_authenticated():
            try:
                from .gmail import fetch_project_emails, format_emails_as_context

                emails = fetch_project_emails(project)
                email_context_text = format_emails_as_context(emails)
                if emails:
                    console.print(f"[green]✓[/green] Retrieved {len(emails)} relevant email threads")
            except Exception as e:
                console.print(f"[yellow]⚠ Gmail fetch failed:[/yellow] {e}")

    analysis_result = None
    if not skip_analysis:
        console.rule("[bold blue]Step 3: AI Analysis")
        analysis_result = analyze(
            transcript,
            title=title,
            context=context,
            project_context=project_context_text,
            email_context=email_context_text,
            today=date.strftime("%Y-%m-%d"),
        )
        console.print("[green]✓[/green] Analysis complete")

        if analysis_result.action_items:
            console.print(f"  → {len(analysis_result.action_items)} action items identified")
        if analysis_result.calendar_events:
            console.print(f"  → {len(analysis_result.calendar_events)} calendar events detected")
        if analysis_result.tasks:
            console.print(f"  → {len(analysis_result.tasks)} tasks extracted")
    else:
        from .models import Analysis
        analysis_result = Analysis(summary="Analysis skipped.")

    if not skip_analysis and not skip_google and is_authenticated():
        console.rule("[bold blue]Step 4: Google Suite Sync")

        if analysis_result.calendar_events:
            try:
                from .gcalendar import create_calendar_events

                links = create_calendar_events(analysis_result.calendar_events)
                console.print(f"[green]✓[/green] Created {len(links)} calendar events")
            except Exception as e:
                console.print(f"[yellow]⚠ Calendar sync failed:[/yellow] {e}")

        if analysis_result.tasks:
            try:
                from .gtasks import create_google_tasks

                list_name = f"Call Intel: {project}" if project else "Call Intelligence"
                count = create_google_tasks(analysis_result.tasks, task_list_name=list_name)
                console.print(f"[green]✓[/green] Created {count} tasks in Google Tasks")
            except Exception as e:
                console.print(f"[yellow]⚠ Tasks sync failed:[/yellow] {e}")
    elif not skip_google and not is_authenticated() and not skip_analysis:
        if analysis_result.calendar_events or analysis_result.tasks:
            console.print(
                "[dim]Tip: Run 'call-intel auth' to enable Google Calendar & Tasks sync[/dim]"
            )

    record = CallRecord(
        title=title,
        project=project,
        date=date,
        source_path=str(transcript_path.resolve()),
        duration_seconds=transcript.duration_seconds,
        speakers=detected_speakers,
        transcript=transcript,
        analysis=analysis_result,
        output_dir=str(output_dir),
    )

    console.rule("[bold blue]Writing Output")
    write_call_output(record)

    meta_path = output_dir / "meta.json"
    meta_path.write_text(record.model_dump_json(indent=2))

    all_records = _load_existing_records(get_output_dir())
    update_index(get_output_dir(), all_records)

    console.print(f"[green]✓[/green] Output written to [bold]{output_dir}[/bold]")
    console.print()

    return record
