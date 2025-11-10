"""
Translation utility module for managing multilingual support in the Maya application.

This module handles loading and managing language translation files (`.yml`) for multiple locales,
currently supporting Danish ("da") and English ("en"). It enables translating strings based on the
current language setting and allows optional addition of missing keys to the translation files during
development (if enabled in settings).

Functionality includes:
- Loading default locale files (`da.yml`, `en.yml`) from the `locales` directory.
- Optionally loading a local override translation file (`language.yml`) for custom translations.
- Automatically appending missing keys to translation files during development.

Functions:
- `translate(key: str, translation_add_key=True) -> str`: Returns the translated string for the given key.

"""

from maya.core.dynamic_settings import settings
from maya.core.paths import get_base_dir_path
from maya.core.logging import get_log
import yaml
from pathlib import Path
import os


log = get_log()

# Load built-in languages
locales_path = Path(__file__).parent.parent / "locales"
da_path = locales_path / "da.yml"
with open(da_path, "r", encoding="utf-8") as stream:
    da = yaml.safe_load(stream)

en_path = locales_path / "en.yml"
with open(en_path, "r", encoding="utf-8") as stream:
    en = yaml.safe_load(stream)


# load local yml file if it exists
language_local = {}
if os.path.exists(get_base_dir_path("language.yml")):
    with open(get_base_dir_path("language.yml"), "r", encoding="utf-8") as stream:
        language_local = yaml.safe_load(stream)
        log.debug(f"Loaded local language file: {get_base_dir_path('language.yml')}")


def _get_translation_override(key: str) -> str:
    """Get translation from local language file if exists"""
    translation = ""

    if language_local:
        if key in language_local:
            translation = language_local[key]

    return translation


def _add_key_language_file(lang, key) -> None:
    if lang == "da":
        da[key] = key

        _save_file_dict("da")

    if lang == "en":
        en[key] = key

        _save_file_dict("en")


def _save_file_dict(lang) -> None:
    """
    Save language files with new key
    But do not update and save language files in production
    """
    if not settings.get("update_translations"):
        return

    if lang == "en":
        with open("maya/locales/en.yml", "w", encoding="utf8") as file:
            yaml.dump(en, file, allow_unicode=True, sort_keys=True)

    if lang == "da":
        with open("maya/locales/da.yml", "w", encoding="utf8") as file:
            yaml.dump(da, file, allow_unicode=True, sort_keys=True)


def translate(key: str, translation_add_key=True) -> str:
    translation = ""

    # Add key to language files if not exists
    if key not in da and translation_add_key:
        _add_key_language_file("da", key)

    if key not in en and translation_add_key:
        _add_key_language_file("en", key)

    # If local language file exists, use that. Else use default language
    if settings["language"] == "da":
        translation = _get_translation_override(key)
        if not translation:
            translation = da.get(key, key)

    if settings["language"] == "en":
        translation = _get_translation_override(key)
        if not translation:
            translation = en.get(key, key)

    return translation
