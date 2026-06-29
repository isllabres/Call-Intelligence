from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


_DATE_PATTERN = re.compile(
    r"^(.+?)\s+(\d{1,2})[.\-_/](\d{1,2})[.\-_/](\d{4})$"
)


@dataclass
class ParsedFilename:
    project: str
    subtitle: str
    date: datetime


def parse_recording_name(path: Path) -> tuple[str, datetime]:
    parsed = parse_filename(path)
    return parsed.project, parsed.date


def parse_filename(path: Path) -> ParsedFilename:
    stem = path.stem
    match = _DATE_PATTERN.match(stem)
    if not match:
        raise ValueError(
            f"Filename '{path.name}' doesn't match expected format: "
            f"'project_name DD-MM-YYYY.ext' or "
            f"'project_name - subtitle DD-MM-YYYY.ext'"
        )

    raw_name = match.group(1).strip()
    day, month, year = int(match.group(2)), int(match.group(3)), int(match.group(4))
    date = datetime(year, month, day)

    if " - " in raw_name:
        project, subtitle = raw_name.split(" - ", 1)
        return ParsedFilename(project=project.strip(), subtitle=subtitle.strip(), date=date)

    return ParsedFilename(project=raw_name, subtitle="", date=date)


def project_slug(project: str) -> str:
    slug = project.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    return re.sub(r"[\s_]+", "-", slug)
