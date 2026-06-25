"""
Evals-Driven Development (EDD) runner for Call Intelligence.

Run all evaluations and report pass/fail. Every feature in src/ must
reach 100% eval pass rate before being considered complete.

Usage:
    uv run python evals/run_evals.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

EVALS_DIR = Path(__file__).parent
FIXTURES_DIR = EVALS_DIR / "fixtures"

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@dataclass
class EvalResult:
    name: str
    passed: bool
    message: str = ""


@dataclass
class EvalSuite:
    results: list[EvalResult] = field(default_factory=list)

    def add(self, name: str, passed: bool, message: str = ""):
        self.results.append(EvalResult(name=name, passed=passed, message=message))

    def report(self) -> bool:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed

        print(f"\n{'=' * 60}")
        print(f"  EVAL RESULTS: {passed}/{total} passed")
        print(f"{'=' * 60}\n")

        for r in self.results:
            icon = "✅" if r.passed else "❌"
            print(f"  {icon} {r.name}")
            if not r.passed and r.message:
                print(f"     → {r.message}")

        print()
        if failed:
            print(f"  ❌ {failed} eval(s) FAILED")
        else:
            print(f"  ✅ All {total} evals PASSED")
        print()

        return failed == 0


# ---------------------------------------------------------------------------
# Eval: filename parser
# ---------------------------------------------------------------------------

def eval_filename_parsing(suite: EvalSuite):
    from call_intel.filename import parse_recording_name

    cases = [
        ("Website Redesign 25-06-2026.m4a", "Website Redesign", "2026-06-25"),
        ("Client Onboarding 01.07.2026.m4a", "Client Onboarding", "2026-07-01"),
        ("Standup 15_12_2026.wav", "Standup", "2026-12-15"),
    ]

    for filename, expected_project, expected_date in cases:
        try:
            project, date = parse_recording_name(Path(filename))
            if project != expected_project:
                suite.add(
                    f"filename_parse: {filename} → project",
                    False,
                    f"Expected '{expected_project}', got '{project}'",
                )
                continue
            if date.strftime("%Y-%m-%d") != expected_date:
                suite.add(
                    f"filename_parse: {filename} → date",
                    False,
                    f"Expected '{expected_date}', got '{date.strftime('%Y-%m-%d')}'",
                )
                continue
            suite.add(f"filename_parse: {filename}", True)
        except Exception as e:
            suite.add(f"filename_parse: {filename}", False, str(e))

    # Negative case: invalid filename
    try:
        parse_recording_name(Path("no-date-here.m4a"))
        suite.add("filename_parse: rejects invalid name", False, "Should have raised ValueError")
    except ValueError:
        suite.add("filename_parse: rejects invalid name", True)
    except Exception as e:
        suite.add("filename_parse: rejects invalid name", False, str(e))


# ---------------------------------------------------------------------------
# Eval: models
# ---------------------------------------------------------------------------

def eval_models(suite: EvalSuite):
    from call_intel.models import (
        ActionItem,
        Analysis,
        CalendarEvent,
        CallRecord,
        Segment,
        SpeechFeedback,
        TaskItem,
        Transcript,
    )

    # Transcript labeled text
    try:
        t = Transcript(
            segments=[
                Segment(start=0.0, end=5.0, text="Hello there", speaker="Alice"),
                Segment(start=5.0, end=10.0, text="How are you?", speaker="Alice"),
                Segment(start=10.0, end=15.0, text="I'm fine", speaker="Bob"),
            ],
            duration_seconds=15.0,
        )
        labeled = t.as_labeled_text()
        assert "**Alice**" in labeled, "Missing Alice label"
        assert "**Bob**" in labeled, "Missing Bob label"
        assert "Hello there" in labeled, "Missing text"
        suite.add("models: transcript labeled text", True)
    except Exception as e:
        suite.add("models: transcript labeled text", False, str(e))

    # Analysis with all fields
    try:
        a = Analysis(
            summary="Test summary",
            key_topics=["topic1"],
            action_items=[ActionItem(description="Do thing", priority="high")],
            calendar_events=[CalendarEvent(title="Meeting", date="2026-07-01")],
            tasks=[TaskItem(title="Task 1", priority="medium")],
            speech_feedback=[SpeechFeedback(category="clarity", observation="Good", suggestion="Keep it up")],
            sentiment="positive",
        )
        assert len(a.action_items) == 1
        assert len(a.calendar_events) == 1
        assert len(a.tasks) == 1
        suite.add("models: analysis full construction", True)
    except Exception as e:
        suite.add("models: analysis full construction", False, str(e))

    # Analysis defaults
    try:
        a = Analysis(summary="Minimal")
        assert a.calendar_events == []
        assert a.tasks == []
        assert a.action_items == []
        suite.add("models: analysis defaults", True)
    except Exception as e:
        suite.add("models: analysis defaults", False, str(e))


# ---------------------------------------------------------------------------
# Eval: markdown generation
# ---------------------------------------------------------------------------

def eval_markdown(suite: EvalSuite):
    from call_intel.markdown import generate_analysis_md, generate_transcript_md
    from call_intel.models import (
        ActionItem,
        Analysis,
        CalendarEvent,
        CallRecord,
        Segment,
        TaskItem,
        Transcript,
    )
    from datetime import datetime

    record = CallRecord(
        title="Test Call",
        project="TestProject",
        date=datetime(2026, 6, 25),
        audio_path="/fake/path.m4a",
        duration_seconds=600.0,
        speakers=["Alice", "Bob"],
        transcript=Transcript(
            segments=[
                Segment(start=0.0, end=5.0, text="Hello", speaker="Alice"),
                Segment(start=5.0, end=10.0, text="Hi there", speaker="Bob"),
            ],
            duration_seconds=600.0,
        ),
        analysis=Analysis(
            summary="A productive call",
            action_items=[ActionItem(description="Send report", assignee="Alice", priority="high")],
            calendar_events=[CalendarEvent(title="Follow-up", date="2026-07-01", duration_minutes=30)],
            tasks=[TaskItem(title="Draft proposal", priority="medium")],
            sentiment="positive",
        ),
        output_dir="/tmp/test-output",
    )

    try:
        transcript_md = generate_transcript_md(record)
        assert "# Test Call — Transcript" in transcript_md
        assert "TestProject" in transcript_md
        assert "Alice" in transcript_md
        suite.add("markdown: transcript generation", True)
    except Exception as e:
        suite.add("markdown: transcript generation", False, str(e))

    try:
        analysis_md = generate_analysis_md(record)
        assert "# Test Call — Analysis" in analysis_md
        assert "Send report" in analysis_md
        assert "Calendar Events Created" in analysis_md
        assert "Follow-up" in analysis_md
        assert "Tasks Created" in analysis_md
        assert "Draft proposal" in analysis_md
        suite.add("markdown: analysis generation", True)
    except Exception as e:
        suite.add("markdown: analysis generation", False, str(e))


# ---------------------------------------------------------------------------
# Eval: project context
# ---------------------------------------------------------------------------

def eval_project_context(suite: EvalSuite):
    from call_intel.filename import project_slug

    try:
        assert project_slug("Website Redesign") == "website-redesign"
        assert project_slug("  My Project  ") == "my-project"
        assert project_slug("TEST") == "test"
        suite.add("project_context: slug generation", True)
    except Exception as e:
        suite.add("project_context: slug generation", False, str(e))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    suite = EvalSuite()

    eval_filename_parsing(suite)
    eval_models(suite)
    eval_markdown(suite)
    eval_project_context(suite)

    all_passed = suite.report()
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
