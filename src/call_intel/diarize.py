from __future__ import annotations

from pathlib import Path

from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import get_hf_token
from .models import Segment, Transcript


def diarize(audio_path: Path, transcript: Transcript, num_speakers: int | None = None) -> Transcript:
    hf_token = get_hf_token()
    if not hf_token:
        raise RuntimeError(
            "HF_TOKEN not set. Speaker diarization requires a HuggingFace token.\n"
            "Get one at https://huggingface.co/settings/tokens and add it to .env.\n"
            "You also need to accept conditions at:\n"
            "  https://huggingface.co/pyannote/speaker-diarization-3.1\n"
            "  https://huggingface.co/pyannote/segmentation-3.0"
        )

    try:
        from pyannote.audio import Pipeline as DiarizationPipeline
    except ImportError:
        raise RuntimeError(
            "pyannote.audio not installed. Install with:\n"
            "  uv pip install 'call-intel[diarize]'"
        )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        progress.add_task("Loading diarization model...", total=None)
        pipeline = DiarizationPipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=hf_token,
        )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        progress.add_task("Identifying speakers...", total=None)
        params = {}
        if num_speakers is not None:
            params["num_speakers"] = num_speakers
        diarization = pipeline(str(audio_path), **params)

    speaker_segments: list[tuple[float, float, str]] = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        speaker_segments.append((turn.start, turn.end, speaker))

    labeled = []
    for seg in transcript.segments:
        mid = (seg.start + seg.end) / 2
        speaker = _find_speaker(mid, speaker_segments)
        labeled.append(seg.model_copy(update={"speaker": speaker}))

    return transcript.model_copy(update={"segments": labeled})


def _find_speaker(
    timestamp: float, speaker_segments: list[tuple[float, float, str]]
) -> str:
    best_speaker = "Unknown"
    best_overlap = 0.0
    for start, end, speaker in speaker_segments:
        if start <= timestamp <= end:
            overlap = end - start
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = speaker
    return best_speaker
