from dotify.i18n import Translator, detect_language


def test_explicit_language_and_turkish_translation():
    translator = Translator("tr_TR")
    assert translator.language == "tr"
    assert "başarılı" in translator(
        "finished", success=2, skipped=1, errors=0, duration="00:04"
    )


def test_environment_language_is_used_for_auto(monkeypatch):
    monkeypatch.setenv("DOTIFY_LANGUAGE", "tr-TR")
    assert detect_language("auto") == "tr"


def test_unsupported_language_falls_back_to_english():
    assert detect_language("de_DE") == "en"
    assert Translator("de")("queue_title") == "Download queue"
