"""Language selection shared by chat, memory, learning and the dashboard."""
from __future__ import annotations

LANGUAGES = {
    "english": {"name": "English", "locale": "en-IN", "tts_voice": "en-IN-PrabhatNeural", "speech": True},
    "hindi": {"name": "Hindi", "locale": "hi-IN", "tts_voice": "hi-IN-MadhurNeural", "speech": True},
    "telugu": {"name": "Telugu", "locale": "te-IN", "tts_voice": "te-IN-MohanNeural", "speech": True},
    "kannada": {"name": "Kannada", "locale": "kn-IN", "tts_voice": "kn-IN-GaganNeural", "speech": True},
    "lambani": {"name": "Lambani / Banjara", "locale": None, "tts_voice": None, "speech": False},
}


def normalize_language(language: str | None, *, allow_auto: bool = False) -> str:
    value = (language or ("auto" if allow_auto else "english")).strip().lower()
    allowed = set(LANGUAGES) | ({"auto"} if allow_auto else set())
    if value not in allowed:
        raise ValueError(f"Unsupported language: {value}")
    return value


def language_from_locale(locale: str | None) -> str:
    code = (locale or "").lower().replace("_", "-").split("-")[0]
    return {"en": "english", "hi": "hindi", "te": "telugu", "kn": "kannada"}.get(code, "english")


def resolve_language(language: str | None, locale: str | None = None) -> str:
    selected = normalize_language(language, allow_auto=True)
    return language_from_locale(locale) if selected == "auto" else selected


def build_language_instruction(language: str) -> str:
    language = normalize_language(language)
    if language == "lambani":
        return ("The user selected experimental Lambani/Banjara. Preserve their wording, "
                "do not falsely claim dialect fluency, and ask for clarification when uncertain. "
                "If you cannot confidently produce Lambani, say so and ask whether another language is acceptable.")
    name = LANGUAGES[language]["name"]
    return (f"Respond naturally in {name}. Preserve names, numbers, code, and technical identifiers. "
            "If the user explicitly requests another language for this answer, follow that request. "
            "Do not claim a translation is exact when uncertain.")
