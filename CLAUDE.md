# Call Intelligence - Claude Code Guide

## Build & Test Commands
- Install dependencies: `uv sync`
- Run evaluations (Evals): `uv run python testing/evals/run_evals.py`

## Workflow (EDD)
Before considering any functionality in `src/` complete, the success rate in `testing/evals/run_evals.py` must be at least 90%.

## Architecture
- `src/call_intel/transcribe.py`: Processes audio to text using local Whisper.
- `src/call_intel/analyze.py`: Analyzes transcript + project history + emails using PydanticAI with Ollama backend.
- `src/call_intel/gmail.py`: Fetches relevant email threads from Gmail for context.
- `src/call_intel/gcalendar.py`: Creates Google Calendar events from detected meetings/deadlines.
- `src/call_intel/gtasks.py`: Creates Google Tasks from extracted action items.
- `src/call_intel/transcript_parser.py`: Parses VTT and DOCX transcript files into Transcript models.
- `src/call_intel/pipeline.py`: Orchestrates the full processing flow (audio and transcript inputs).
- `src/call_intel/watcher.py`: Watches data/input/recordings/ and data/input/transcripts/ for new files.
- `src/call_intel/cli.py`: CLI entry point (process, process-transcript, watch, list, search, analyze, auth).

## Data Directory Structure
- `data/input/recordings/`: Audio files (.m4a, .wav, etc.)
- `data/input/transcripts/`: Transcript files (.vtt, .docx)
- `data/output/`: Processed call output (transcript.md, analysis.md, meta.json per call)
