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
    description: str = Field(description="What needs to be done")
    assignee: str | None = Field(default=None, description="Who should do it")
    deadline: str | None = Field(default=None, description="YYYY-MM-DD — infer reasonable deadlines from context")
    priority: str = Field(default="medium", description="high, medium, or low")


class SpeechFeedback(BaseModel):
    category: str = Field(description="clarity, confidence, structure, vocabulary, filler_words, pace, active_listening, or persuasion")
    observation: str = Field(description="What was observed in the speaker's communication")
    suggestion: str = Field(description="Specific actionable improvement")
    example: str | None = Field(default=None, description="Quote or paraphrase from the transcript illustrating the point")


class CalendarEvent(BaseModel):
    title: str = Field(description="Event title")
    date: str = Field(description="YYYY-MM-DD")
    time: str | None = Field(default=None, description="HH:MM or null")
    duration_minutes: int = Field(default=30, description="Duration in minutes")
    description: str = Field(default="", description="What the event is about")
    attendees: list[str] = Field(default_factory=list, description="Email addresses or names")


class TaskItem(BaseModel):
    title: str = Field(description="Short actionable task title")
    notes: str = Field(default="", description="Additional detail about the task")
    due_date: str | None = Field(default=None, description="YYYY-MM-DD or null")
    priority: str = Field(default="medium", description="high, medium, or low")


class Analysis(BaseModel):
    summary: str = Field(description="2-3 sentence overview, noting connections to previous discussions if applicable")
    key_topics: list[str] = Field(default_factory=list, description="Main topics discussed")
    action_items: list[ActionItem] = Field(default_factory=list)
    key_decisions: list[str] = Field(default_factory=list, description="Decisions that were made")
    follow_ups: list[str] = Field(default_factory=list, description="Things to follow up on")
    development_insights: list[str] = Field(default_factory=list, description="Professional growth opportunities, skills to develop, or career paths discussed")
    speech_feedback: list[SpeechFeedback] = Field(default_factory=list)
    sentiment: str = Field(default="", description="Overall emotional tone of the call")
    participant_summary: dict[str, str] = Field(default_factory=dict, description="Mapping of speaker name to brief summary of their contributions")
    calendar_events: list[CalendarEvent] = Field(default_factory=list)
    tasks: list[TaskItem] = Field(default_factory=list)


class CallRecord(BaseModel):
    title: str
    project: str = ""
    date: datetime
    source_path: str = ""
    audio_path: str = ""
    duration_seconds: float
    speakers: list[str] = Field(default_factory=list)
    transcript: Transcript
    analysis: Analysis
    output_dir: str
