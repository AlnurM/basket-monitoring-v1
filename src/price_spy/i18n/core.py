from . import en, ru

_LANGS: dict[str, dict[str, str]] = {
    "ru": ru.STRINGS,
    "en": en.STRINGS,
}

SUPPORTED_LANGUAGES = list(_LANGS.keys())


def get_text(key: str, lang: str = "en", **kwargs: object) -> str:
    """Look up a translated string by key and language.

    Falls back to English, then returns the key itself.
    """
    template = _LANGS.get(lang, _LANGS["en"]).get(key)
    if template is None:
        template = _LANGS["en"].get(key, key)
    return template.format(**kwargs) if kwargs else template
