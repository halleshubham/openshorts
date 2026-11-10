"""Indic-aware faster-whisper decoding: language detection + script anchoring.

Whisper identifies closely related languages (Hindi/Marathi/Urdu/Nepali)
unreliably from one 30 s window, and without a prior it drifts into the wrong
script (Hindi in Arabic letters, Marathi in Latin). This module:

  * votes on the language over up to three windows of the media, and
  * returns a native-script ``initial_prompt`` that anchors the decoder to the
    right Unicode block.

``whisper_params(model, media_path)`` returns the extra faster-whisper kwargs
(``language``, ``initial_prompt``) that transcribe_backends merges into its
decode params. Detection failure returns ``{}`` so callers fall back to
Whisper's own auto-detect.

Env: ``INDIC_ASR=0`` disables the whole thing; ``INDIC_WHISPER_MODEL`` names a
larger model (e.g. ``large-v3``) used only when an Indic language is detected.
"""
import os
import subprocess

# Languages for which we pass a native-script seed. Others keep Whisper's own
# detection untouched (the seed would only add noise for Latin-script audio).
INDIC_LANGS = {"hi", "mr", "ne", "sa", "ur"}

_SCRIPT_SEED = {
    # Longer prompts are intentional: Whisper's decoder uses the prompt as prior
    # context, so more Devanagari/native-script tokens = stronger script anchoring.
    # Single words are not enough for Hindi/Urdu disambiguation.
    'hi': 'नमस्ते। यह वीडियो हिंदी भाषा में है। आज हम हिंदी में बात करेंगे।',
    'mr': 'नमस्कार। हे व्हिडिओ मराठी भाषेत आहे। आज आपण मराठीत बोलणार आहोत।',
    'ne': 'नमस्ते। यो भिडियो नेपाली भाषामा छ।',
    'sa': 'नमस्ते। एतत् संस्कृतभाषायां वीडियो अस्ति।',
    'ar': 'مرحباً. هذا الفيديو باللغة العربية.',
    'fa': 'سلام. این ویدیو به زبان فارسی است.',
    'ur': 'السلام علیکم۔ یہ ویڈیو اردو زبان میں ہے۔',
    'ta': 'வணக்கம். இந்த வீடியோ தமிழ் மொழியில் உள்ளது.',
    'te': 'నమస్కారం. ఈ వీడియో తెలుగు భాషలో ఉంది.',
    'kn': 'ನಮಸ್ಕಾರ. ಈ ವೀಡಿಯೋ ಕನ್ನಡ ಭಾಷೆಯಲ್ಲಿದೆ.',
    'ml': 'നമസ്കാരം. ഈ വീഡിയോ മലയാളത്തിലാണ്.',
    'th': 'สวัสดี. วิดีโอนี้เป็นภาษาไทย.',
    'zh': '你好。这个视频是用中文制作的。',
    'ja': 'こんにちは。この動画は日本語です。',
    'ko': '안녕하세요. 이 영상은 한국어로 되어 있습니다.',
}


def _extract_audio_window(audio_path, offset_s=0, duration_s=30):
    """Extract a window of audio as a 16 kHz mono float32 numpy array."""
    import numpy as np
    cmd = [
        'ffmpeg', '-y', '-ss', str(offset_s), '-i', audio_path,
        '-t', str(duration_s),
        '-ar', '16000', '-ac', '1', '-f', 'f32le',
        'pipe:1',
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return np.frombuffer(result.stdout, dtype=np.float32)


def _video_duration(audio_path):
    """Return video duration in seconds via ffprobe, or None on failure."""
    cmd = [
        'ffprobe', '-v', 'quiet',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        audio_path,
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        return float(result.stdout.strip())
    except (ValueError, AttributeError):
        return None


def _detect_language_robust(model, audio_path):
    """Detect language by sampling up to 3 windows and taking a majority vote.

    Sampling only the first 30 s is unreliable for closely related languages
    (e.g. Hindi vs Marathi) because the opening may not be representative.
    """
    duration = _video_duration(audio_path) or 60
    offsets = [0]
    if duration > 90:
        offsets.append(int(duration / 3))
    if duration > 180:
        offsets.append(int(2 * duration / 3))

    votes = {}
    best_prob = {}
    for offset in offsets:
        sample = _extract_audio_window(audio_path, offset_s=offset, duration_s=30)
        if len(sample) < 4000:   # < 0.25 s of audio — skip empty windows
            continue
        detected = model.detect_language(sample)
        if isinstance(detected, tuple) and len(detected) >= 1:
            lang = str(detected[0])
            prob = float(detected[1]) if len(detected) >= 2 else 0.0
        elif isinstance(detected, list) and detected:
            head = detected[0]
            if isinstance(head, (list, tuple)) and len(head) >= 2:
                lang, prob = str(head[0]), float(head[1])
            else:
                lang, prob = str(head), 0.0
        else:
            continue
        votes[lang] = votes.get(lang, 0) + 1
        best_prob[lang] = max(best_prob.get(lang, 0.0), prob)

    if not votes:
        return 'en', None
    # Majority vote; break ties with highest probability
    lang = max(votes, key=lambda l: (votes[l], best_prob.get(l, 0.0)))
    return lang, best_prob.get(lang)


def indic_model_size():
    """Larger model for Indic audio, or None to keep the configured one."""
    return os.environ.get("INDIC_WHISPER_MODEL") or None


def is_enabled_for(params):
    """True unless disabled by env or the caller already pinned a language."""
    return os.environ.get("INDIC_ASR", "1") != "0" and not params.get("language")


def is_indic(lang):
    return lang in INDIC_LANGS


def whisper_params(model, media_path):
    """Extra decode kwargs for ``model.transcribe``; ``{}`` = leave it to Whisper.

    Returns ``{"language": ..., "initial_prompt": ...}`` for languages with a
    seed, ``{"language": ...}`` for confidently detected others.
    """
    if os.environ.get("INDIC_ASR", "1") == "0":
        return {}
    try:
        lang, prob = _detect_language_robust(model, media_path)
    except Exception as e:  # never fail a job over detection
        print(f"   ⚠️ language vote failed ({type(e).__name__}: {e}) — using Whisper auto-detect")
        return {}
    seed = _SCRIPT_SEED.get(lang)
    prob_str = f" ({prob:.2f})" if prob is not None else ""
    print(f"   Language vote: '{lang}'{prob_str}{' — script seed on' if seed else ''}")
    # Only pin the language when we are sure or it is Indic (where auto-detect
    # is the known failure); otherwise let Whisper decide.
    if seed is None and (prob is None or prob < 0.6):
        return {}
    params = {"language": lang}
    if seed:
        params["initial_prompt"] = seed
    return params
