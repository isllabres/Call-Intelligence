from __future__ import annotations

import json
import time
from pathlib import Path

from rich.console import Console
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .config import get_output_dir, get_recordings_dir

console = Console()

AUDIO_EXTENSIONS = {".m4a", ".wav", ".mp3", ".mp4", ".webm", ".ogg", ".flac"}


class RecordingHandler(FileSystemEventHandler):
    def __init__(self, skip_google: bool = False):
        self.skip_google = skip_google
        self._processing: set[str] = set()

    def on_created(self, event):
        if event.is_directory:
            return

        path = Path(event.src_path)
        if path.suffix.lower() not in AUDIO_EXTENSIONS:
            return

        if path.name.startswith("."):
            return

        if str(path) in self._processing:
            return

        self._processing.add(str(path))
        console.print(f"\n[bold cyan]New recording detected:[/bold cyan] {path.name}")

        # Wait for file to finish writing (Voice Memos may still be syncing)
        self._wait_for_stable(path)

        try:
            from .pipeline import process_call

            process_call(
                audio_path=path,
                skip_google=self.skip_google,
            )
        except Exception as e:
            console.print(f"[red]Error processing {path.name}:[/red] {e}")
        finally:
            self._processing.discard(str(path))

    def _wait_for_stable(self, path: Path, checks: int = 3, interval: float = 2.0):
        prev_size = -1
        stable_count = 0
        while stable_count < checks:
            try:
                size = path.stat().st_size
            except FileNotFoundError:
                return
            if size == prev_size and size > 0:
                stable_count += 1
            else:
                stable_count = 0
            prev_size = size
            if stable_count < checks:
                time.sleep(interval)


def get_processed_files() -> set[str]:
    output_dir = get_output_dir()
    processed = set()
    for meta_path in output_dir.rglob("meta.json"):
        try:
            data = json.loads(meta_path.read_text())
            processed.add(data.get("audio_path", ""))
        except Exception:
            continue
    return processed


def find_unprocessed(recordings_dir: Path | None = None) -> list[Path]:
    recordings_dir = recordings_dir or get_recordings_dir()
    processed = get_processed_files()

    unprocessed = []
    for f in sorted(recordings_dir.iterdir()):
        if f.suffix.lower() in AUDIO_EXTENSIONS and not f.name.startswith("."):
            if str(f.resolve()) not in processed:
                unprocessed.append(f)

    return unprocessed


def watch_recordings(
    recordings_dir: Path | None = None,
    skip_google: bool = False,
):
    recordings_dir = recordings_dir or get_recordings_dir()
    recordings_dir.mkdir(parents=True, exist_ok=True)

    handler = RecordingHandler(
        skip_google=skip_google,
    )

    observer = Observer()
    observer.schedule(handler, str(recordings_dir), recursive=False)
    observer.start()

    console.print(f"[bold green]Watching for new recordings in:[/bold green] {recordings_dir}")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        console.print("\n[yellow]Watcher stopped.[/yellow]")

    observer.join()
