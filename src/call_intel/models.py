from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field


class Segment(BaseModel):
    start: float
    end: float
    text: str
    speaker: str | None = None


class Transcript(BaseModel):
    segments: list[Segment]
    duration_seconds: float
    language: str = "en"

    @property
    def full_text(self) -> str:
        return " ".join(s.text.strip() for s in self.segments)

    def as_labeled_text(self) -> str:
        lines: list[str] = []
        current_speaker = None
        for seg in self.segments:
            speaker = seg.speaker or "Unknown"
            if speaker != current_speaker:
                current_speaker = speaker
                lines.append(f"\n**{speaker}**: {seg.text.strip()}")
            else:
                lines.append(seg.text.strip())
        return " ".join(lines).strip()


class ActionItem(BaseModel):
    description: str
    assignee: str | None = None
    deadline: str | None = None
    priority: str = "medium"


class SpeechFeedback(BaseModel):
    category: str
    observation: str
    suggestion: str
    example: str | None = None


class CalendarEvent(BaseModel):
    title: str
    date: str
    time: str | None = None
    duration_minutes: int = 30
    description: str = ""
    attendees: list[str] = Field(default_factory=list)


class TaskItem(BaseModel):
    title: str
    notes: str = ""
    due_date: str | None = None
    priority: str = "medium"


class Analysis(BaseModel):
    summary: str
    key_topics: list[str] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    key_decisions: list[str] = Field(default_factory=list)
    follow_ups: list[str] = Field(default_factory=list)
    development_insights: list[str] = Field(default_factory=list)
    speech_feedback: list[SpeechFeedback] = Field(default_factory=list)
    sentiment: str = ""
    participant_summary: dict[str, str] = Field(default_factory=dict)
    calendar_events: list[CalendarEvent] = Field(default_factory=list)
    tasks: list[TaskItem] = Field(default_factory=list)


class CallRecord(BaseModel):
    title: str
    project: str = ""
    date: datetime
    audio_path: str
    duration_seconds: float
    speakers: list[str] = Field(default_factory=list)
    transcript: Transcript
    analysis: Analysis
    output_dir: str
