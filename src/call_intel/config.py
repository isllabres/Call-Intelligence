from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def _find_project_root() -> Path:
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return current


PROJECT_ROOT = _find_project_root()

load_dotenv(PROJECT_ROOT / ".env")


def get_ollama_model() -> str:
    return os.environ.get("OLLAMA_MODEL", "llama3.1:8b")


def get_whisper_model() -> str:
    return os.environ.get("WHISPER_MODEL", "base")


def get_my_speaker_name() -> str:
    return os.environ.get("MY_SPEAKER_NAME", "Me")


def get_output_dir() -> Path:
    return PROJECT_ROOT / "output"


def get_transcripts_dir() -> Path:
    return PROJECT_ROOT / "transcripts"


def get_recordings_dir() -> Path:
    return PROJECT_ROOT / "recordings"
