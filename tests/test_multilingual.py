import pytest
from multilingual import LANGUAGES, build_language_instruction, language_from_locale, normalize_language, resolve_language

@pytest.mark.parametrize("name", ["english", "hindi", "telugu", "kannada", "lambani"])
def test_all_languages_are_configured(name):
    assert name in LANGUAGES
    assert build_language_instruction(name)

@pytest.mark.parametrize(("locale", "expected"), [
    ("en-IN", "english"), ("hi-IN", "hindi"), ("te-IN", "telugu"), ("kn-IN", "kannada")
])
def test_locale_detection(locale, expected):
    assert language_from_locale(locale) == expected


def test_manual_selection_overrides_locale():
    assert resolve_language("kannada", "hi-IN") == "kannada"


def test_auto_uses_locale():
    assert resolve_language("auto", "te-IN") == "telugu"


def test_unknown_language_rejected():
    with pytest.raises(ValueError):
        normalize_language("unknown")


def test_lambani_is_text_experimental():
    assert LANGUAGES["lambani"]["speech"] is False
    assert LANGUAGES["lambani"]["tts_voice"] is None
