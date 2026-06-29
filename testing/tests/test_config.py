from __future__ import annotations

from call_intel.config import get_whisper_model


def test_should_default_to_multilingual_base_model(monkeypatch):
    monkeypatch.delenv("WHISPER_MODEL", raising=False)
    assert get_whisper_model() == "base"


def test_should_respect_custom_whisper_model_env_var(monkeypatch):
    monkeypatch.setenv("WHISPER_MODEL", "large-v3")
    assert get_whisper_model() == "large-v3"
