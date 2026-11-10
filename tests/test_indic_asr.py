"""Indic language voting, script seeds and per-language caption fonts."""
import numpy as np

import indic_asr
import subtitles


class FakeModel:
    """faster-whisper detect_language stand-in: one (lang, prob) per call."""

    def __init__(self, answers):
        self.answers = list(answers)

    def detect_language(self, audio):
        return self.answers.pop(0)


def _windows(monkeypatch, n=3, duration=300):
    monkeypatch.setattr(indic_asr, "_video_duration", lambda p: duration)
    monkeypatch.setattr(indic_asr, "_extract_audio_window",
                        lambda *a, **k: np.zeros(16000 * 5, dtype=np.float32))


def test_majority_vote_beats_first_window(monkeypatch):
    _windows(monkeypatch)
    model = FakeModel([("hi", 0.55), ("mr", 0.8), ("mr", 0.7)])
    assert indic_asr._detect_language_robust(model, "x.mp4") == ("mr", 0.8)


def test_whisper_params_pin_marathi_with_devanagari_seed(monkeypatch):
    _windows(monkeypatch)
    model = FakeModel([("mr", 0.9)] * 3)
    params = indic_asr.whisper_params(model, "x.mp4")
    assert params["language"] == "mr"
    assert "मराठी" in params["initial_prompt"]


def test_unsure_latin_language_is_left_to_whisper(monkeypatch):
    _windows(monkeypatch)
    model = FakeModel([("en", 0.4)] * 3)
    assert indic_asr.whisper_params(model, "x.mp4") == {}


def test_detection_failure_never_raises(monkeypatch):
    _windows(monkeypatch)

    class Boom:
        def detect_language(self, audio):
            raise RuntimeError("cuda")

    assert indic_asr.whisper_params(Boom(), "x.mp4") == {}


def test_env_switch_and_explicit_language(monkeypatch):
    assert indic_asr.is_enabled_for({}) is True
    assert indic_asr.is_enabled_for({"language": "de"}) is False
    monkeypatch.setenv("INDIC_ASR", "0")
    assert indic_asr.is_enabled_for({}) is False
    assert indic_asr.whisper_params(FakeModel([]), "x.mp4") == {}


def test_font_for_language():
    assert subtitles.font_for_language("Anton", "mr") == "Noto Sans Devanagari"
    assert subtitles.font_for_language("Anton", "hi") == "Noto Sans Devanagari"
    assert subtitles.font_for_language("Anton", "en") == "Anton"
    assert subtitles.font_for_language("Anton", None) == "Anton"
