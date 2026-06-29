# Call Intelligence

100% local and free call intelligence tool — transcribe recordings, identify speakers, extract insights, and sync tasks and events to Google Suite. No data leaves your machine.

## Features

- **Fully local & free** — no API keys, no cloud processing, no subscriptions
- **Local transcription** with Whisper (via faster-whisper)
- **Local AI analysis** with Ollama (Llama, Mistral, Qwen, etc.)
- **Project continuity** — automatically pulls context from previous calls of the same project
- **Gmail context** — fetches relevant email threads to enrich analysis
- **Google Calendar sync** — creates events for meetings and deadlines discussed
- **Google Tasks sync** — creates tasks from action items, organized by project
- **Speech coaching** — filler words, clarity, confidence, structure
- **Auto-processing** — LaunchAgent checks for new recordings every hour
- **GitHub-ready markdown** output for review and version tracking

## Setup

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- [ffmpeg](https://ffmpeg.org/) — required by Whisper
- [Ollama](https://ollama.com/) — local LLM runtime

```bash
# Install dependencies (macOS)
brew install ffmpeg ollama

# Pull the default model
ollama pull llama3.1:8b

# Clone and install
cd call-intelligence
cp .env.example .env
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
8. Run `uv run call-intel auth` to authenticate in your browser

## File Naming Convention

Name your recordings and transcripts as: **`Project Name DD-MM-YYYY.ext`**

Recording examples:
- `Website Redesign 25-06-2026.m4a`
- `Client Onboarding 01-07-2026.m4a`
- `Team Standup 25.06.2026.m4a`

Transcript examples:
- `Website Redesign 25-06-2026.vtt`
- `Client Onboarding 01-07-2026.docx`

The project name and date are automatically parsed from the filename. This groups calls by project and enables cross-call context. Supported transcript formats: `.vtt` (WebVTT) and `.docx` (Google Docs export).

## Usage

### Process a recording

```bash
# Auto-detects project & date from filename
uv run call-intel process "data/input/recordings/Website Redesign 25-06-2026.m4a"

# With explicit metadata
uv run call-intel process data/input/recordings/call.m4a \
  --project "Website Redesign" \
  --date 2026-06-25 \
  --speakers "Me,Sarah"

# Skip Google sync
uv run call-intel process data/input/recordings/call.m4a --no-google

# Transcription only
uv run call-intel process data/input/recordings/call.m4a --no-analysis
```

### Process a transcript

```bash
# Process a VTT transcript
uv run call-intel process-transcript "data/input/transcripts/Website Redesign 25-06-2026.vtt"

# Process a DOCX transcript
uv run call-intel process-transcript "data/input/transcripts/Client Call 01-07-2026.docx"

# With explicit metadata
uv run call-intel process-transcript data/input/transcripts/call.vtt \
  --project "Website Redesign" \
  --date 2026-06-25
```

### Auto-process new recordings and transcripts

```bash
# Watch mode — monitors data/input/ for new recordings and transcripts
uv run call-intel watch

# Process all unprocessed recordings and transcripts at once
uv run call-intel process-new
```

A macOS LaunchAgent is also included that runs `process-new` every hour automatically. It starts on login.

### Other commands

```bash
# Authenticate with Google Suite
uv run call-intel auth

# List all processed calls
uv run call-intel list

# Search across all calls
uv run call-intel search "deadline"

# Re-analyze with fresh context
uv run call-intel analyze data/output/2026-06-25-website-redesign/transcript.md
```

## Pipeline

The system accepts two input sources: audio recordings and pre-generated transcripts.

```
Audio file (.m4a)                  Transcript file (.vtt, .docx)
    │                                      │
    ├─→ Step 1: Whisper transcription      ├─→ Step 1: Parse transcript
    │                                      │
    └──────────────┬───────────────────────┘
                   │
                   ├─→ Step 2: Context gathering
                   │       ├─ Previous calls for this project
                   │       └─ Relevant Gmail threads
                   ├─→ Step 3: Ollama AI analysis (local)
                   │       ├─ Summary, decisions, follow-ups
                   │       ├─ Action items → Google Tasks
                   │       ├─ Meetings/deadlines → Google Calendar
                   │       ├─ Development insights
                   │       └─ Speech coaching feedback
                   ├─→ Step 4: Google Suite sync
                   │       ├─ Create calendar events
                   │       └─ Create tasks (grouped by project)
                   └─→ Step 5: Write markdown output
                           ├─ transcript.md
                           ├─ analysis.md
                           └─ meta.json
```

## Output Structure

```
data/
├── input/
│   ├── recordings/                       # Audio files (.m4a, .wav, etc.)
│   └── transcripts/                      # Transcript files (.vtt, .docx)
└── output/
    ├── index.md                          # Master index of all calls
    └── 2026-06-25-website-redesign/
        ├── transcript.md                 # Full transcript with speakers & timestamps
        ├── analysis.md                   # AI analysis, tasks, events, coaching
        └── meta.json                     # Machine-readable metadata
```

## Configuration

All configuration via `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `llama3.1:8b` | Ollama model for analysis |
| `WHISPER_MODEL` | `base` | Whisper model size (multilingual) |
| `MY_SPEAKER_NAME` | `Me` | Your name in transcripts (for targeted speech feedback) |

### Ollama Model Options

| Model | RAM | Quality | Speed |
|-------|-----|---------|-------|
| `llama3.1:8b` | ~5 GB | Good | Fast |
| `qwen2.5:7b` | ~5 GB | Good | Fast |
| `mistral:7b` | ~5 GB | Good | Fast |
| `gemma2:9b` | ~6 GB | Better | Medium |
| `llama3.1:70b` | ~40 GB | Best | Slow |

## Workflow

1. Record calls using Voice Memos on Mac/iPhone, or obtain a transcript (.vtt or .docx)
2. Name the file: `Project Name DD-MM-YYYY.ext`
3. Copy recordings to `data/input/recordings/` or transcripts to `data/input/transcripts/` — the LaunchAgent auto-processes every hour
4. Review markdown output in `data/output/`
5. Check Google Calendar for new events and Google Tasks for action items
6. Commit output to git for tracking progress over time
