from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


_DATE_PATTERN = re.compile(
    r"^(.+?)\s+(\d{1,2})[.\-_/](\d{1,2})[.\-_/](\d{4})$"
)


def parse_recording_name(path: Path) -> tuple[str, datetime]:
    stem = path.stem
    match = _DATE_PATTERN.match(stem)
    if not match:
        raise ValueError(
            f"Filename '{path.name}' doesn't match expected format: "
            f"'project_name DD-MM-YYYY.ext' (separators: - . _ /)"
        )

    project = match.group(1).strip()
    day, month, year = int(match.group(2)), int(match.group(3)), int(match.group(4))
    date = datetime(year, month, day)

    return project, date


def project_slug(project: str) -> str:
    slug = project.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    return re.sub(r"[\s_]+", "-", slug)
