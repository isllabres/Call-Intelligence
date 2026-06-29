from __future__ import annotations

import re
from pathlib import Path

from .models import Segment, Transcript

_VTT_TIMESTAMP = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})\.(\d{3})"
)


def _ts_to_seconds(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_vtt(path: Path) -> Transcript:
    text = path.read_text(encoding="utf-8")
    lines = text.strip().splitlines()

    if not lines or not lines[0].strip().startswith("WEBVTT"):
        raise ValueError(f"Invalid VTT file '{path.name}': missing WEBVTT header")

    segments: list[Segment] = []
    i = 1
    while i < len(lines):
        line = lines[i].strip()
        match = _VTT_TIMESTAMP.match(line)
        if match:
            start = _ts_to_seconds(*match.groups()[:4])
            end = _ts_to_seconds(*match.groups()[4:])
            cue_lines: list[str] = []
            i += 1
            while i < len(lines) and lines[i].strip():
                cue_lines.append(lines[i].strip())
                i += 1
            segments.append(Segment(start=start, end=end, text=" ".join(cue_lines)))
        else:
            i += 1

    duration = segments[-1].end if segments else 0.0
    return Transcript(segments=segments, duration_seconds=duration)


def parse_docx(path: Path) -> Transcript:
    from docx import Document

    doc = Document(str(path))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    if not paragraphs:
        raise ValueError(f"Empty DOCX file '{path.name}': no text content found")

    full_text = "\n".join(paragraphs)
    return Transcript(
        segments=[Segment(start=0.0, end=0.0, text=full_text)],
        duration_seconds=0.0,
    )


def parse_transcript_file(path: Path) -> Transcript:
    suffix = path.suffix.lower()
    if suffix == ".vtt":
        return parse_vtt(path)
    if suffix == ".docx":
        return parse_docx(path)
    raise ValueError(f"Unsupported transcript format: {suffix}")
