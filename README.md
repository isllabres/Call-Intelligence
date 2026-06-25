# Call Intelligence

Personal call intelligence tool — transcribe recordings, identify speakers, extract insights, and sync tasks and events to Google Suite.

## Features

- **Local transcription** with Whisper (private, no audio data leaves your machine)
- **Speaker diarization** to identify who said what
- **AI analysis** via Claude — action items, decisions, follow-ups
- **Project continuity** — automatically pulls context from previous calls of the same project
- **Gmail context** — fetches relevant email threads to enrich analysis
- **Google Calendar sync** — creates events for meetings and deadlines discussed
- **Google Tasks sync** — creates tasks from action items, organized by project
- **Speech coaching** — filler words, clarity, confidence, structure
- **Auto-processing** — watches `recordings/` folder for new files
- **GitHub-ready markdown** output for review and version tracking

## Setup

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- [ffmpeg](https://ffmpeg.org/) — required by Whisper for audio processing
- An [Anthropic API key](https://console.anthropic.com/) for AI analysis

```bash
# Install ffmpeg (macOS)
brew install ffmpeg

# Clone and install
cd call-intelligence
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY

uv sync
```

### Google Suite Integration (Optional)

Enables Gmail context, Google Calendar events, and Google Tasks.

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or use an existing one)
3. Enable these APIs:
   - Gmail API
   - Google Calendar API
   - Google Tasks API
4. Go to **APIs & Services → Credentials**
5. Create an **OAuth 2.0 Client ID** (type: Desktop application)
6. Download the JSON file
7. Save it as `.credentials/client_secret.json` in the project root
8. Run `call-intel auth` to authenticate in your browser

### Speaker Diarization (Optional)

```bash
uv sync --extra diarize
```

Requires a [HuggingFace token](https://huggingface.co/settings/tokens) in `.env` (`HF_TOKEN=hf_...`). Accept the model conditions at:
- https://huggingface.co/pyannote/speaker-diarization-3.1
- https://huggingface.co/pyannote/segmentation-3.0

## File Naming Convention

Name your recordings as: **`Project Name DD-MM-YYYY.m4a`**

Examples:
- `Website Redesign 25-06-2026.m4a`
- `Client Onboarding 01-07-2026.m4a`
- `Team Standup 25.06.2026.m4a`

The project name and date are automatically parsed from the filename. This groups calls by project and enables cross-call context.

## Usage

### Process a recording

```bash
# Auto-detects project & date from filename
call-intel process "recordings/Website Redesign 25-06-2026.m4a"

# With explicit metadata
call-intel process recordings/call.m4a \
  --project "Website Redesign" \
  --date 2026-06-25 \
  --speakers "Me,Sarah"

# Skip Google sync
call-intel process recordings/call.m4a --no-google

# Transcription only
call-intel process recordings/call.m4a --no-analysis
```

### Auto-process new recordings

```bash
# Watch mode — processes files as they appear
call-intel watch

# Process all unprocessed recordings at once
call-intel process-new
```

### Other commands

```bash
# Authenticate with Google Suite
call-intel auth

# List all processed calls
call-intel list

# Search across all calls
call-intel search "deadline"

# Re-analyze with fresh context
call-intel analyze output/2026-06-25-website-redesign/transcript.md
```

## Pipeline

When you process a recording, here's what happens:

```
Audio file (.m4a)
    │
    ├─→ Step 1: Whisper transcription (local)
    ├─→ Step 2: Speaker diarization (local, optional)
    ├─→ Step 3: Context gathering
    │       ├─ Previous calls for this project
    │       └─ Relevant Gmail threads
    ├─→ Step 4: Claude AI analysis
    │       ├─ Summary, decisions, follow-ups
    │       ├─ Action items → Google Tasks
    │       ├─ Meetings/deadlines → Google Calendar
    │       ├─ Development insights
    │       └─ Speech coaching feedback
    ├─→ Step 5: Google Suite sync
    │       ├─ Create calendar events
    │       └─ Create tasks (grouped by project)
    └─→ Step 6: Write markdown output
            ├─ transcript.md
            ├─ analysis.md
            └─ meta.json
```

## Output Structure

```
output/
├── index.md                              # Master index of all calls
└── 2026-06-25-website-redesign/
    ├── transcript.md                     # Full transcript with speakers & timestamps
    ├── analysis.md                       # AI analysis, tasks, events, coaching
    └── meta.json                         # Machine-readable metadata
```

## Configuration

All configuration via `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Required for AI analysis |
| `HF_TOKEN` | — | Required for speaker diarization |
| `WHISPER_MODEL` | `base.en` | Whisper model size |
| `MY_SPEAKER_NAME` | `Me` | Your name in transcripts (for targeted speech feedback) |

## Workflow

1. Record calls using Voice Memos on Mac/iPhone
2. Name the file: `Project Name DD-MM-YYYY`
3. Copy to `recordings/` (or run `call-intel watch` to auto-detect)
4. Review markdown output in `output/`
5. Check Google Calendar for new events and Google Tasks for action items
6. Commit output to git for tracking progress over time
