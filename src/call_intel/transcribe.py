from __future__ import annotations

from pathlib import Path

from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import get_whisper_model
from .models import Segment, Transcript


def transcribe(audio_path: Path, model_size: str | None = None) -> Transcript:
    from faster_whisper import WhisperModel

    model_size = model_size or get_whisper_model()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        progress.add_task(f"Loading Whisper model ({model_size})...", total=None)
        model = WhisperModel(model_size, device="auto", compute_type="auto")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        progress.add_task("Transcribing audio...", total=None)
        raw_segments, info = model.transcribe(
            str(audio_path),
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,
        )
        segments = [
            Segment(start=s.start, end=s.end, text=s.text)
            for s in raw_segments
        ]

    return Transcript(
        segments=segments,
        duration_seconds=info.duration,
        language=info.language,
    )
