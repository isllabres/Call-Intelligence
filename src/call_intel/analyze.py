from __future__ import annotations

import json

import ollama as ollama_client
from pydantic_ai import Agent
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import get_my_speaker_name, get_ollama_model
from .models import Analysis, Transcript

ANALYSIS_SYSTEM_PROMPT = """\
You are an expert meeting analyst and personal development coach. \
You analyze call transcripts to extract actionable insights.

You will receive the transcript along with optional context: previous calls from the \
same project and relevant email threads. Use this context to provide continuity — \
reference prior decisions, track progress on action items, and identify evolving patterns.

Today's date is provided so you can set realistic deadlines.

You MUST respond with valid JSON only — no markdown, no explanation, no text outside the JSON object.

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


def _ollama_model_function(messages: list, info: AgentInfo) -> ModelResponse:
    """Bridge between PydanticAI's Agent and the native Ollama API."""
    ollama_messages = []
    for msg in messages:
        if msg.kind == "request":
            for part in msg.parts:
                if hasattr(part, "content"):
                    role = "system" if part.part_kind == "system-prompt" else "user"
                    ollama_messages.append({"role": role, "content": part.content})
        elif msg.kind == "response":
            for part in msg.parts:
                if hasattr(part, "content"):
                    ollama_messages.append({"role": "assistant", "content": part.content})

    model_name = get_ollama_model()
    response = ollama_client.chat(
        model=model_name,
        messages=ollama_messages,
        format="json",
        options={"num_ctx": 8192},
    )

    content = response["message"]["content"]
    return ModelResponse(parts=[TextPart(content=content)])


analysis_agent = Agent(
    model=FunctionModel(_ollama_model_function, model_name="ollama"),
    system_prompt=ANALYSIS_SYSTEM_PROMPT,
)


def analyze(
    transcript: Transcript,
    title: str = "",
    context: str = "",
    project_context: str = "",
    email_context: str = "",
    today: str = "",
) -> Analysis:
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
        progress.add_task(f"Analyzing with Ollama ({get_ollama_model()})...", total=None)
        result = analysis_agent.run_sync(user_prompt)

    text = result.output
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise RuntimeError(f"Failed to parse analysis response: {text[:200]}")

    data = json.loads(text[start:end])
    return Analysis(**_strip_nulls(data))


def _strip_nulls(obj: object) -> object:
    """Remove null values so Pydantic uses field defaults."""
    if isinstance(obj, dict):
        return {k: _strip_nulls(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_strip_nulls(item) for item in obj]
    return obj
