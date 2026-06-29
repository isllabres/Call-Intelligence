# Call Intelligence - Claude Code Guide

## Build & Test Commands
- Install dependencies: `uv sync`
- Run evaluations (Evals): `uv run python evals/run_evals.py`

## Workflow (EDD)
Before considering any functionality in `src/` complete, the success rate in `evals/run_evals.py` must be at least 90%.

## Architecture
- `src/call_intel/transcribe.py`: Processes audio to text using local Whisper.
- `src/call_intel/analyze.py`: Analyzes transcript + project history + emails using PydanticAI with Ollama backend.
- `src/call_intel/gmail.py`: Fetches relevant email threads from Gmail for context.
- `src/call_intel/gcalendar.py`: Creates Google Calendar events from detected meetings/deadlines.
- `src/call_intel/gtasks.py`: Creates Google Tasks from extracted action items.
- `src/call_intel/pipeline.py`: Orchestrates the full processing flow.
- `src/call_intel/watcher.py`: Watches recordings folder and auto-processes new files.
- `src/call_intel/cli.py`: CLI entry point (process, watch, list, search, analyze, auth).
