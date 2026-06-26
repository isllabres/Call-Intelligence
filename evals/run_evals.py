"""
Evals-Driven Development (EDD) runner for Call Intelligence.

Run all evaluations and report pass/fail. Every feature in src/ must
reach 100% eval pass rate before being considered complete.

Usage:
    uv run python evals/run_evals.py              # all evals
    uv run python evals/run_evals.py --unit        # unit evals only (no LLM)
    uv run python evals/run_evals.py --golden      # golden dataset only (needs Ollama)
    uv run python evals/run_evals.py --case case_04  # run a specific golden case
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

EVALS_DIR = Path(__file__).parent
FIXTURES_DIR = EVALS_DIR / "fixtures"

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ===================================================================
# Eval infrastructure
# ===================================================================

@dataclass
class EvalResult:
    name: str
    passed: bool
    message: str = ""
    category: str = "unit"


@dataclass
class EvalSuite:
    results: list[EvalResult] = field(default_factory=list)

    def add(self, name: str, passed: bool, message: str = "", category: str = "unit"):
        self.results.append(EvalResult(name=name, passed=passed, message=message, category=category))

    def report(self) -> bool:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed

        categories = sorted(set(r.category for r in self.results))

        print(f"\n{'=' * 70}")
        print(f"  EVAL RESULTS: {passed}/{total} passed")
        print(f"{'=' * 70}")

        for cat in categories:
            cat_results = [r for r in self.results if r.category == cat]
            cat_passed = sum(1 for r in cat_results if r.passed)
            print(f"\n  [{cat.upper()}] {cat_passed}/{len(cat_results)}")
            print(f"  {'-' * 50}")
            for r in cat_results:
                icon = "✅" if r.passed else "❌"
                print(f"  {icon} {r.name}")
                if not r.passed and r.message:
                    for line in r.message.split("\n"):
                        print(f"     → {line}")

        print(f"\n{'=' * 70}")
        if failed:
            print(f"  ❌ {failed} eval(s) FAILED")
        else:
            print(f"  ✅ All {total} evals PASSED")
        print(f"{'=' * 70}\n")

        return failed == 0


# ===================================================================
# Unit evals — no LLM required
# ===================================================================

def eval_filename_parsing(suite: EvalSuite):
    from call_intel.filename import parse_recording_name

    cases = [
        ("Website Redesign 25-06-2026.m4a", "Website Redesign", "2026-06-25"),
        ("Client Onboarding 01.07.2026.m4a", "Client Onboarding", "2026-07-01"),
        ("Standup 15_12_2026.wav", "Standup", "2026-12-15"),
        ("My Project 5-1-2026.m4a", "My Project", "2026-01-05"),
    ]

    for filename, expected_project, expected_date in cases:
        try:
            project, date = parse_recording_name(Path(filename))
            if project != expected_project:
                suite.add(f"filename: {filename} → project", False,
                          f"Expected '{expected_project}', got '{project}'")
                continue
            if date.strftime("%Y-%m-%d") != expected_date:
                suite.add(f"filename: {filename} → date", False,
                          f"Expected '{expected_date}', got '{date.strftime('%Y-%m-%d')}'")
                continue
            suite.add(f"filename: {filename}", True)
        except Exception as e:
            suite.add(f"filename: {filename}", False, str(e))

    try:
        parse_recording_name(Path("no-date-here.m4a"))
        suite.add("filename: rejects invalid name", False, "Should have raised ValueError")
    except ValueError:
        suite.add("filename: rejects invalid name", True)
    except Exception as e:
        suite.add("filename: rejects invalid name", False, str(e))

    try:
        parse_recording_name(Path("nodatehere.m4a"))
        suite.add("filename: rejects no-separator name", False, "Should have raised ValueError")
    except ValueError:
        suite.add("filename: rejects no-separator name", True)
    except Exception as e:
        suite.add("filename: rejects no-separator name", False, str(e))


def eval_models(suite: EvalSuite):
    from call_intel.models import (
        ActionItem, Analysis, CalendarEvent, CallRecord,
        Segment, SpeechFeedback, TaskItem, Transcript,
    )

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
        assert "**Alice**" in labeled
        assert "**Bob**" in labeled
        assert "Hello there" in labeled
        suite.add("models: transcript labeled text", True)
    except Exception as e:
        suite.add("models: transcript labeled text", False, str(e))

    try:
        a = Analysis(
            summary="Test",
            action_items=[ActionItem(description="Do thing", priority="high")],
            calendar_events=[CalendarEvent(title="Meeting", date="2026-07-01")],
            tasks=[TaskItem(title="Task 1", priority="medium")],
            speech_feedback=[SpeechFeedback(category="clarity", observation="x", suggestion="y")],
            sentiment="positive",
        )
        assert len(a.action_items) == 1
        assert len(a.calendar_events) == 1
        assert len(a.tasks) == 1
        suite.add("models: full construction", True)
    except Exception as e:
        suite.add("models: full construction", False, str(e))

    try:
        a = Analysis(summary="Minimal")
        assert a.calendar_events == []
        assert a.tasks == []
        assert a.action_items == []
        assert a.speech_feedback == []
        suite.add("models: defaults are empty", True)
    except Exception as e:
        suite.add("models: defaults are empty", False, str(e))


def eval_markdown(suite: EvalSuite):
    from datetime import datetime
    from call_intel.markdown import generate_analysis_md, generate_transcript_md
    from call_intel.models import (
        ActionItem, Analysis, CalendarEvent, CallRecord,
        Segment, TaskItem, Transcript,
    )

    record = CallRecord(
        title="Test Call", project="TestProject",
        date=datetime(2026, 6, 25), audio_path="/fake/path.m4a",
        duration_seconds=600.0, speakers=["Alice", "Bob"],
        transcript=Transcript(
            segments=[
                Segment(start=0.0, end=5.0, text="Hello", speaker="Alice"),
                Segment(start=5.0, end=10.0, text="Hi", speaker="Bob"),
            ],
            duration_seconds=600.0,
        ),
        analysis=Analysis(
            summary="A productive call",
            action_items=[ActionItem(description="Send report", assignee="Alice", priority="high")],
            calendar_events=[CalendarEvent(title="Follow-up", date="2026-07-01")],
            tasks=[TaskItem(title="Draft proposal", priority="medium")],
            sentiment="positive",
        ),
        output_dir="/tmp/test-output",
    )

    try:
        md = generate_transcript_md(record)
        assert "# Test Call" in md
        assert "TestProject" in md
        assert "Alice" in md and "Bob" in md
        suite.add("markdown: transcript has title, project, speakers", True)
    except Exception as e:
        suite.add("markdown: transcript has title, project, speakers", False, str(e))

    try:
        md = generate_analysis_md(record)
        assert "Send report" in md
        assert "Calendar Events Created" in md
        assert "Follow-up" in md
        assert "Tasks Created" in md
        assert "Draft proposal" in md
        suite.add("markdown: analysis has all sections", True)
    except Exception as e:
        suite.add("markdown: analysis has all sections", False, str(e))

    try:
        empty_record = CallRecord(
            title="Empty", project="", date=datetime(2026, 1, 1),
            audio_path="/x.m4a", duration_seconds=60.0, speakers=[],
            transcript=Transcript(segments=[], duration_seconds=60.0),
            analysis=Analysis(summary="Nothing happened"),
            output_dir="/tmp/empty",
        )
        md = generate_analysis_md(empty_record)
        assert "Calendar Events" not in md
        assert "Tasks Created" not in md
        suite.add("markdown: empty analysis omits empty sections", True)
    except Exception as e:
        suite.add("markdown: empty analysis omits empty sections", False, str(e))


def eval_project_context(suite: EvalSuite):
    from call_intel.filename import project_slug

    cases = [
        ("Website Redesign", "website-redesign"),
        ("  My Project  ", "my-project"),
        ("TEST", "test"),
        ("hello world foo", "hello-world-foo"),
    ]
    for input_name, expected in cases:
        try:
            result = project_slug(input_name)
            assert result == expected, f"Expected '{expected}', got '{result}'"
            suite.add(f"slug: '{input_name}' → '{expected}'", True)
        except Exception as e:
            suite.add(f"slug: '{input_name}'", False, str(e))


def eval_watcher(suite: EvalSuite):
    from call_intel.watcher import AUDIO_EXTENSIONS

    valid = [".m4a", ".wav", ".mp3", ".mp4", ".webm", ".ogg", ".flac"]
    for ext in valid:
        suite.add(f"watcher: accepts {ext}", ext in AUDIO_EXTENSIONS,
                  f"{ext} not in AUDIO_EXTENSIONS" if ext not in AUDIO_EXTENSIONS else "")

    invalid = [".txt", ".pdf", ".py", ".json", ".md"]
    for ext in invalid:
        suite.add(f"watcher: rejects {ext}", ext not in AUDIO_EXTENSIONS,
                  f"{ext} should not be in AUDIO_EXTENSIONS" if ext in AUDIO_EXTENSIONS else "")


def eval_config_defaults(suite: EvalSuite):
    import os
    saved = {k: os.environ.pop(k, None) for k in ["OLLAMA_MODEL", "WHISPER_MODEL", "MY_SPEAKER_NAME"]}

    try:
        from call_intel.config import get_ollama_model, get_whisper_model, get_my_speaker_name
        assert get_ollama_model() == "llama3.1:8b"
        assert get_whisper_model() == "base.en"
        assert get_my_speaker_name() == "Me"
        suite.add("config: default values", True)
    except Exception as e:
        suite.add("config: default values", False, str(e))
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v


def eval_gmail_formatting(suite: EvalSuite):
    from call_intel.gmail import format_emails_as_context, EmailThread, EmailMessage

    try:
        result = format_emails_as_context([])
        assert result == ""
        suite.add("gmail: empty list returns empty string", True)
    except Exception as e:
        suite.add("gmail: empty list returns empty string", False, str(e))

    try:
        threads = [
            EmailThread(
                subject="NDA for signing",
                snippet="Please review and sign",
                messages=[EmailMessage(sender="client@co.com", date="2026-06-24", body="Attached NDA")],
            )
        ]
        result = format_emails_as_context(threads)
        assert "NDA for signing" in result
        assert "client@co.com" in result
        assert "Attached NDA" in result
        suite.add("gmail: formats thread with subject, sender, body", True)
    except Exception as e:
        suite.add("gmail: formats thread with subject, sender, body", False, str(e))


def eval_date_parsing(suite: EvalSuite):
    from call_intel.gcalendar import _parse_event_datetime
    from call_intel.gtasks import _parse_due_date

    try:
        dt = _parse_event_datetime("2026-07-01", "16:00")
        assert dt.year == 2026 and dt.month == 7 and dt.day == 1
        assert dt.hour == 16 and dt.minute == 0
        suite.add("gcalendar: parses YYYY-MM-DD + HH:MM", True)
    except Exception as e:
        suite.add("gcalendar: parses YYYY-MM-DD + HH:MM", False, str(e))

    try:
        dt = _parse_event_datetime("01-07-2026", None)
        assert dt.month == 7 and dt.day == 1
        assert dt.hour == 9  # default
        suite.add("gcalendar: parses DD-MM-YYYY, defaults to 9:00", True)
    except Exception as e:
        suite.add("gcalendar: parses DD-MM-YYYY, defaults to 9:00", False, str(e))

    try:
        dt = _parse_due_date("2026-07-15")
        assert dt is not None and dt.day == 15
        suite.add("gtasks: parses YYYY-MM-DD", True)
    except Exception as e:
        suite.add("gtasks: parses YYYY-MM-DD", False, str(e))

    try:
        result = _parse_due_date("not-a-date")
        assert result is None
        suite.add("gtasks: returns None for invalid date", True)
    except Exception as e:
        suite.add("gtasks: returns None for invalid date", False, str(e))


# ===================================================================
# Golden dataset evals — requires Ollama running
# ===================================================================

def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text


def _keywords_match(keywords: list[str], text: str) -> bool:
    norm_text = _normalize(text)
    return any(_normalize(kw) in norm_text for kw in keywords)


def _check_golden_case(case: dict, suite: EvalSuite):
    from call_intel.analyze import analyze
    from call_intel.models import Segment, Transcript

    case_id = case["id"]
    current_date = case["metadata"]["current_date"]
    inp = case["input"]
    expected = case["expected_output"]

    transcript = Transcript(
        segments=[Segment(start=0.0, end=30.0, text=inp["transcription"], speaker="Me")],
        duration_seconds=30.0,
        language="es",
    )

    project_context = ""
    if inp["historical_tasks"]:
        project_context = f"## Historical Tasks\n{inp['historical_tasks']}"

    email_context = ""
    if inp["historical_emails"]:
        email_context = f"## Recent Emails\n{inp['historical_emails']}"

    try:
        analysis = analyze(
            transcript,
            title="Eval Call",
            project_context=project_context,
            email_context=email_context,
            today=current_date,
        )
    except Exception as e:
        suite.add(f"golden: {case_id}", False, f"Analysis failed: {e}", category="golden")
        return

    errors: list[str] = []

    # --- Check task count ---
    expected_tasks = expected["new_tasks"]
    actual_tasks = analysis.tasks
    if len(expected_tasks) == 0:
        if len(actual_tasks) > 0:
            task_titles = [t.title for t in actual_tasks]
            errors.append(f"Expected 0 tasks, got {len(actual_tasks)}: {task_titles}")
    else:
        if len(actual_tasks) < len(expected_tasks):
            errors.append(f"Expected {len(expected_tasks)} task(s), got {len(actual_tasks)}")

        for i, exp_task in enumerate(expected_tasks):
            matched = False
            for act_task in actual_tasks:
                title_ok = _keywords_match(exp_task["title_keywords"], act_task.title + " " + act_task.notes)
                date_ok = True
                if "due_date" in exp_task and exp_task["due_date"]:
                    date_ok = act_task.due_date == exp_task["due_date"]
                if title_ok and date_ok:
                    matched = True
                    break
            if not matched:
                kw = exp_task["title_keywords"]
                due = exp_task.get("due_date", "any")
                actual_repr = [(t.title, t.due_date) for t in actual_tasks]
                errors.append(f"Task {i+1} not found — keywords={kw}, due={due}. Got: {actual_repr}")

    # --- Check event count ---
    expected_events = expected["new_events"]
    actual_events = analysis.calendar_events
    if len(expected_events) == 0:
        if len(actual_events) > 0:
            event_titles = [e.title for e in actual_events]
            errors.append(f"Expected 0 events, got {len(actual_events)}: {event_titles}")
    else:
        if len(actual_events) < len(expected_events):
            errors.append(f"Expected {len(expected_events)} event(s), got {len(actual_events)}")

        for i, exp_event in enumerate(expected_events):
            matched = False
            for act_event in actual_events:
                title_ok = _keywords_match(exp_event["title_keywords"], act_event.title + " " + act_event.description)
                date_ok = act_event.date == exp_event["date"]
                time_ok = True
                if "time" in exp_event and exp_event["time"] and act_event.time:
                    time_ok = act_event.time == exp_event["time"]
                if title_ok and date_ok and time_ok:
                    matched = True
                    break
            if not matched:
                kw = exp_event["title_keywords"]
                date = exp_event.get("date", "any")
                actual_repr = [(e.title, e.date, e.time) for e in actual_events]
                errors.append(f"Event {i+1} not found — keywords={kw}, date={date}. Got: {actual_repr}")

    if errors:
        suite.add(f"golden: {case_id}", False, "\n".join(errors), category="golden")
    else:
        suite.add(f"golden: {case_id}", True, category="golden")


def eval_golden_dataset(suite: EvalSuite, case_filter: str | None = None):
    cases_path = FIXTURES_DIR / "golden_cases.json"
    cases = json.loads(cases_path.read_text())

    if case_filter:
        cases = [c for c in cases if case_filter in c["id"]]
        if not cases:
            suite.add(f"golden: filter '{case_filter}'", False,
                      "No cases matched the filter", category="golden")
            return

    # Check Ollama is reachable
    try:
        import ollama
        ollama.list()
    except Exception as e:
        suite.add("golden: ollama connection", False,
                  f"Ollama not reachable — start it with 'ollama serve'. Error: {e}",
                  category="golden")
        return

    for case in cases:
        print(f"  ⏳ Running {case['id']}...", flush=True)
        _check_golden_case(case, suite)


# ===================================================================
# Main
# ===================================================================

def main():
    parser = argparse.ArgumentParser(description="Call Intelligence EDD runner")
    parser.add_argument("--unit", action="store_true", help="Run unit evals only")
    parser.add_argument("--golden", action="store_true", help="Run golden dataset evals only")
    parser.add_argument("--case", type=str, help="Run a specific golden case (substring match)")
    args = parser.parse_args()

    run_unit = not args.golden
    run_golden = not args.unit or args.golden or args.case is not None

    suite = EvalSuite()

    if run_unit:
        eval_filename_parsing(suite)
        eval_models(suite)
        eval_markdown(suite)
        eval_project_context(suite)
        eval_watcher(suite)
        eval_config_defaults(suite)
        eval_gmail_formatting(suite)
        eval_date_parsing(suite)

    if run_golden:
        eval_golden_dataset(suite, case_filter=args.case)

    all_passed = suite.report()
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
