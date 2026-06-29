from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .config import get_output_dir

console = Console()


@click.group()
def cli():
    """Call Intelligence — transcribe, analyze, and grow from your calls."""


@cli.command()
@click.argument("audio_file", type=click.Path(exists=True, path_type=Path))
@click.option("--title", "-t", help="Title for the call")
@click.option("--project", "-p", help="Project name (auto-detected from filename)")
@click.option("--date", "-d", help="Date of the call (YYYY-MM-DD). Auto-detected from filename.")
@click.option(
    "--speakers", "-s",
    help="Comma-separated speaker names in order (e.g. 'Me,Sarah,John')",
)
@click.option("--no-analysis", is_flag=True, help="Skip AI analysis")
@click.option("--no-google", is_flag=True, help="Skip Google Suite sync (Calendar, Tasks)")
@click.option("--context", "-c", help="Additional context about the call")
@click.option("--model", "-m", help="Whisper model size (e.g. base, medium, large-v3)")
def process(
    audio_file: Path,
    title: str | None,
    project: str | None,
    date: str | None,
    speakers: str | None,
    no_analysis: bool,
    no_google: bool,
    context: str | None,
    model: str | None,
):
    """Process a call recording through the full pipeline.

    Filename convention: 'project_name DD-MM-YYYY.m4a'
    The project name and date are auto-parsed from the filename.
    """
    from .pipeline import process_call

    parsed_date = datetime.strptime(date, "%Y-%m-%d") if date else None
    speaker_list = [s.strip() for s in speakers.split(",")] if speakers else None

    record = process_call(
        audio_path=audio_file,
        title=title,
        project=project,
        date=parsed_date,
        speakers=speaker_list,
        skip_analysis=no_analysis,
        skip_google=no_google,
        context=context or "",
        whisper_model=model,
    )

    console.print("\n[bold green]Done![/bold green]")
    console.print(f"  Transcript: {record.output_dir}/transcript.md")
    console.print(f"  Analysis:   {record.output_dir}/analysis.md")


@cli.command(name="process-transcript")
@click.argument("transcript_file", type=click.Path(exists=True, path_type=Path))
@click.option("--title", "-t", help="Title for the call")
@click.option("--project", "-p", help="Project name (auto-detected from filename)")
@click.option("--date", "-d", help="Date of the call (YYYY-MM-DD). Auto-detected from filename.")
@click.option(
    "--speakers", "-s",
    help="Comma-separated speaker names in order (e.g. 'Me,Sarah,John')",
)
@click.option("--no-analysis", is_flag=True, help="Skip AI analysis")
@click.option("--no-google", is_flag=True, help="Skip Google Suite sync (Calendar, Tasks)")
@click.option("--context", "-c", help="Additional context about the call")
def process_transcript_cmd(
    transcript_file: Path,
    title: str | None,
    project: str | None,
    date: str | None,
    speakers: str | None,
    no_analysis: bool,
    no_google: bool,
    context: str | None,
):
    """Process a transcript file (.vtt or .docx) through the analysis pipeline.

    Filename convention: 'project_name DD-MM-YYYY.vtt'
    The project name and date are auto-parsed from the filename.
    """
    from .pipeline import process_transcript

    parsed_date = datetime.strptime(date, "%Y-%m-%d") if date else None
    speaker_list = [s.strip() for s in speakers.split(",")] if speakers else None

    record = process_transcript(
        transcript_path=transcript_file,
        title=title,
        project=project,
        date=parsed_date,
        speakers=speaker_list,
        skip_analysis=no_analysis,
        skip_google=no_google,
        context=context or "",
    )

    console.print("\n[bold green]Done![/bold green]")
    console.print(f"  Transcript: {record.output_dir}/transcript.md")
    console.print(f"  Analysis:   {record.output_dir}/analysis.md")


@cli.command()
def auth():
    """Authenticate with Google Suite (Gmail, Calendar, Tasks).

    Opens a browser for OAuth consent. Credentials are saved locally
    in .credentials/ and reused for future runs.
    """
    from .google_auth import CREDENTIALS_DIR, get_credentials, is_authenticated

    if is_authenticated():
        console.print("[green]✓[/green] Already authenticated with Google.")
        console.print(f"  Credentials at: {CREDENTIALS_DIR}")
        console.print("  To re-authenticate, delete .credentials/token.json and run again.")
        return

    console.print("Opening browser for Google authentication...")
    console.print("Grant access to Gmail (read), Calendar, and Tasks.\n")

    try:
        get_credentials()
        console.print("\n[bold green]Authentication successful![/bold green]")
        console.print("Google Calendar events and Tasks will now sync automatically.")
    except RuntimeError as e:
        console.print(f"\n[red]Error:[/red] {e}")
        raise SystemExit(1)


@cli.command()
@click.option("--no-google", is_flag=True, help="Skip Google Suite sync")
def watch(no_google: bool):
    """Watch for new recordings and transcripts.

    Monitors data/input/recordings/ and data/input/transcripts/ and
    automatically runs the full pipeline when a file appears.
    Filenames must follow the convention: 'project_name DD-MM-YYYY.ext'
    """
    from .watcher import watch_recordings

    watch_recordings(skip_google=no_google)


@cli.command(name="process-new")
@click.option("--no-google", is_flag=True, help="Skip Google Suite sync")
def process_new(no_google: bool):
    """Process all unprocessed recordings and transcripts."""
    from .pipeline import process_call, process_transcript
    from .watcher import find_unprocessed, find_unprocessed_transcripts

    unprocessed_audio = find_unprocessed()
    unprocessed_transcripts = find_unprocessed_transcripts()

    if not unprocessed_audio and not unprocessed_transcripts:
        console.print("[green]✓[/green] All recordings and transcripts have been processed.")
        return

    if unprocessed_audio:
        console.print(f"Found {len(unprocessed_audio)} unprocessed recording(s):\n")
        for f in unprocessed_audio:
            console.print(f"  • {f.name}")
        console.print()

    if unprocessed_transcripts:
        console.print(f"Found {len(unprocessed_transcripts)} unprocessed transcript(s):\n")
        for f in unprocessed_transcripts:
            console.print(f"  • {f.name}")
        console.print()

    for audio_path in unprocessed_audio:
        try:
            process_call(
                audio_path=audio_path,
                skip_google=no_google,
            )
        except Exception as e:
            console.print(f"[red]Error processing {audio_path.name}:[/red] {e}")
            continue

    for transcript_path in unprocessed_transcripts:
        try:
            process_transcript(
                transcript_path=transcript_path,
                skip_google=no_google,
            )
        except Exception as e:
            console.print(f"[red]Error processing {transcript_path.name}:[/red] {e}")
            continue


@cli.command()
@click.argument("transcript_file", type=click.Path(exists=True, path_type=Path))
@click.option("--title", "-t", help="Title for the call")
@click.option("--context", "-c", help="Additional context about the call")
@click.option("--no-google", is_flag=True, help="Skip Google Suite sync")
def analyze(transcript_file: Path, title: str | None, context: str | None, no_google: bool):
    """Re-analyze an existing transcript with Claude."""
    from .analyze import analyze as run_analysis
    from .google_auth import is_authenticated

    meta_dir = transcript_file.parent
    meta_path = meta_dir / "meta.json"

    if not meta_path.exists():
        console.print("[red]Error:[/red] No meta.json found next to transcript.")
        raise SystemExit(1)

    from .models import CallRecord
    record = CallRecord(**json.loads(meta_path.read_text()))

    project_context_text = ""
    email_context_text = ""

    if record.project:
        from .project_context import format_project_context, get_project_history
        history = [r for r in get_project_history(record.project) if r.date < record.date]
        project_context_text = format_project_context(history)

        if not no_google and is_authenticated():
            try:
                from .gmail import fetch_project_emails, format_emails_as_context
                emails = fetch_project_emails(record.project)
                email_context_text = format_emails_as_context(emails)
            except Exception:
                pass

    console.print(f"[bold]Re-analyzing:[/bold] {record.title}")
    new_analysis = run_analysis(
        record.transcript,
        title=title or record.title,
        context=context or "",
        project_context=project_context_text,
        email_context=email_context_text,
        today=record.date.strftime("%Y-%m-%d"),
    )

    record.analysis = new_analysis

    if not no_google and is_authenticated():
        if new_analysis.calendar_events:
            from .gcalendar import create_calendar_events
            create_calendar_events(new_analysis.calendar_events)
        if new_analysis.tasks:
            from .gtasks import create_google_tasks
            list_name = f"Call Intel: {record.project}" if record.project else "Call Intelligence"
            create_google_tasks(new_analysis.tasks, task_list_name=list_name)

    from .markdown import write_call_output
    write_call_output(record)
    meta_path.write_text(record.model_dump_json(indent=2))

    console.print(f"[green]✓[/green] Updated analysis at {meta_dir}/analysis.md")


@cli.command(name="list")
def list_calls():
    """List all processed calls."""
    output_dir = get_output_dir()

    records = []
    for meta_path in sorted(output_dir.rglob("meta.json"), reverse=True):
        try:
            data = json.loads(meta_path.read_text())
            records.append(data)
        except Exception:
            continue

    if not records:
        console.print("[yellow]No processed calls found.[/yellow]")
        console.print("Process your first call with: call-intel process <audio-file>")
        return

    table = Table(title="Processed Calls")
    table.add_column("Date", style="cyan")
    table.add_column("Project", style="magenta")
    table.add_column("Title", style="bold")
    table.add_column("Duration")
    table.add_column("Speakers")

    for r in records:
        date = datetime.fromisoformat(r["date"]).strftime("%Y-%m-%d")
        duration_min = r["duration_seconds"] / 60
        speakers = ", ".join(r.get("speakers", [])) or "—"
        table.add_row(
            date,
            r.get("project", "") or "—",
            r["title"],
            f"{duration_min:.0f} min",
            speakers,
        )

    console.print(table)


@cli.command()
@click.argument("query")
def search(query: str):
    """Search across all transcripts and analyses."""
    output_dir = get_output_dir()
    query_lower = query.lower()
    results = []

    for md_path in sorted(output_dir.rglob("*.md")):
        if md_path.name == "index.md":
            continue
        content = md_path.read_text()
        if query_lower in content.lower():
            lines = content.split("\n")
            matches = [
                (i + 1, line.strip())
                for i, line in enumerate(lines)
                if query_lower in line.lower()
            ]
            results.append((md_path, matches))

    if not results:
        console.print(f"[yellow]No results for '{query}'[/yellow]")
        return

    for path, matches in results:
        rel = path.relative_to(output_dir)
        console.print(f"\n[bold cyan]{rel}[/bold cyan]")
        for line_num, line in matches[:5]:
            highlighted = line.replace(query, f"[bold red]{query}[/bold red]")
            console.print(f"  L{line_num}: {highlighted}")
        if len(matches) > 5:
            console.print(f"  ... and {len(matches) - 5} more matches")


if __name__ == "__main__":
    cli()
