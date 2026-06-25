from __future__ import annotations

import json

import anthropic
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import get_anthropic_key, get_my_speaker_name
from .models import Analysis, Transcript

ANALYSIS_SYSTEM_PROMPT = """\
You are an expert meeting analyst and personal development coach. \
You analyze call transcripts to extract actionable insights.

You will receive the transcript along with optional context: previous calls from the \
same project and relevant email threads. Use this context to provide continuity — \
reference prior decisions, track progress on action items, and identify evolving patterns.

Today's date is provided so you can set realistic deadlines.

Respond with a JSON object matching this exact schema:
{
  "summary": "2-3 sentence overview of the call, noting connections to previous discussions if applicable",
  "key_topics": ["topic1", "topic2"],
  "action_items": [
    {
      "description": "what needs to be done",
      "assignee": "who should do it or null",
      "deadline": "YYYY-MM-DD or null — infer reasonable deadlines from context",
      "priority": "high|medium|low"
    }
  ],
  "key_decisions": ["decision that was made"],
  "follow_ups": ["thing to follow up on"],
  "development_insights": [
    "observation about professional growth opportunities, skills to develop, or career paths discussed"
  ],
  "speech_feedback": [
    {
      "category": "clarity|confidence|structure|vocabulary|filler_words|pace|active_listening|persuasion",
      "observation": "what was observed in the speaker's communication",
      "suggestion": "specific actionable improvement",
      "example": "quote or paraphrase from the transcript illustrating the point, or null"
    }
  ],
  "sentiment": "overall emotional tone of the call",
  "participant_summary": {
    "Speaker Name": "brief summary of their contributions and stance"
  },
  "calendar_events": [
    {
      "title": "event title",
      "date": "YYYY-MM-DD",
      "time": "HH:MM or null",
      "duration_minutes": 30,
      "description": "what the event is about",
      "attendees": ["email@example.com or name if email unknown"]
    }
  ],
  "tasks": [
    {
      "title": "short task title",
      "notes": "additional detail about the task",
      "due_date": "YYYY-MM-DD or null",
      "priority": "high|medium|low"
    }
  ]
}

Guidelines for calendar_events:
- Create events for any meetings, deadlines, or appointments mentioned or implied
- If a follow-up meeting is discussed, create an event for it
- Use reasonable defaults for time/duration when not explicitly stated

Guidelines for tasks:
- Convert all action items into tasks with clear, actionable titles
- Include context from the call in the notes field
- Reference relevant prior context if it adds value
- If a previous action item was discussed as completed, do NOT recreate it
"""


def analyze(
    transcript: Transcript,
    title: str = "",
    context: str = "",
    project_context: str = "",
    email_context: str = "",
    today: str = "",
) -> Analysis:
    client = anthropic.Anthropic(api_key=get_anthropic_key())
    my_name = get_my_speaker_name()

    labeled_text = transcript.as_labeled_text()

    context_sections = []
    if context:
        context_sections.append(f"Additional context: {context}")
    if project_context:
        context_sections.append(f"\n{project_context}")
    if email_context:
        context_sections.append(f"\n{email_context}")

    user_prompt = f"""Analyze this call transcript.

Title: {title or "Untitled Call"}
Duration: {transcript.duration_seconds / 60:.1f} minutes
Today's date: {today or "unknown"}
My name in the transcript: {my_name}
{chr(10).join(context_sections)}

Focus speech feedback specifically on "{my_name}" — I want to improve my own communication.

Transcript:
{labeled_text}"""

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        progress.add_task("Analyzing with Claude...", total=None)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8192,
            system=ANALYSIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

    text = response.content[0].text
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise RuntimeError(f"Failed to parse analysis response: {text[:200]}")

    data = json.loads(text[start:end])
    return Analysis(**data)
