"""
Dynamic settings loader for Maya.

This module attempts to load configuration settings in the following order of precedence:

1. Base configuration:
   - settings.yml or settings.py (maya.settings)

2. Local overrides:
   - settings_local.yml or settings_local.py

3. Facet-specific settings:
   - facets.yml or facets.py (overrides contents of `maya.settings_facets`)

4. Test-specific overrides (applied if the TEST environment variable is set):
   - tests/settings_test.py
   - BASE_DIR/settings_test.yml or BASE_DIR/settings_test.py

Settings are merged into the `settings` and `settings_facets` dictionaries.
Supports both YAML (.yml) and Python (.py) formats, with preference given to YAML when both exist.
"""

from maya.settings import settings
from maya.settings_facets import settings_facets
from maya.core.paths import get_base_dir_path
from maya.core.module_loader import load_attr_from_file
import importlib
import logging
import os
import yaml
import copy


def _debug(message: str) -> None:
    """
    Log debug messages without importing maya.core.logging during module import.
    """
    logger = logging.getLogger("main")
    logger.debug(message)


def _load_yaml_settings(file_name):
    """
    Load settings from a .yml file
    """
    if os.path.exists(get_base_dir_path(file_name)):
        # load from .yml file
        try:
            with open(get_base_dir_path(file_name), "r", encoding="utf-8") as stream:
                settings_yml = yaml.safe_load(stream)
                settings.update(settings_yml)
                _debug(f"Local {file_name} loaded: {get_base_dir_path(file_name)}")
        except Exception:
            _debug(f"Local {file_name} NOT loaded: {get_base_dir_path(file_name)}")


def _load_py_settings(file_name):
    """
    Load settings from a .py file
    """
    if os.path.exists(get_base_dir_path(file_name)):
        # load from .py file
        try:
            settings_config = load_attr_from_file("settings_config", "settings", get_base_dir_path(file_name))
            settings.update(settings_config)
            _debug(f"Local {file_name} loaded: {get_base_dir_path(file_name)}")
        except Exception:
            _debug(f"Local {file_name} NOT loaded: {get_base_dir_path(file_name)}")


# load settings from .yml file or .py
if os.path.exists(get_base_dir_path("settings.yml")):
    _load_yaml_settings("settings.yml")
elif os.path.exists(get_base_dir_path("settings.py")):
    _load_py_settings("settings.py")


# load settings from .yml file or .py
if os.path.exists(get_base_dir_path("settings_local.yml")):
    _load_yaml_settings("settings_local.yml")
elif os.path.exists(get_base_dir_path("settings_local.py")):
    _load_py_settings("settings_local.py")


# load local settings_facets (overrides settings_facets)
if os.path.exists(get_base_dir_path("facets.yml")):
    try:
            with open(get_base_dir_path("facets.yml"), "r", encoding="utf-8") as stream:
                settings_facets_local = yaml.safe_load(stream)
                settings_facets.update(settings_facets_local)
            _debug(f"Local facets.yml loaded: {get_base_dir_path('facets.yml')}")
    except Exception:
        _debug(f"Local facets.yml NOT loaded: {get_base_dir_path('facets.yml')}")

elif os.path.exists(get_base_dir_path("facets.py")):
    try:
        settings_facets_local = load_attr_from_file("settings_facets_local", "settings_facets", get_base_dir_path("facets.py"))
        settings_facets.update(settings_facets_local)
        _debug(f"Local facets.py loaded: {get_base_dir_path('facets.py')}")

    except Exception:
        _debug(f"Local facets.py file NOT loaded: {get_base_dir_path('facets.py')}")


# load settings for tests (overrides settings)
if os.getenv("TEST"):
    module_name = "tests.settings_test"
    submodule = importlib.import_module(module_name)
    settings_test = getattr(submodule, "settings")
    settings.update(settings_test)

    if os.path.exists(get_base_dir_path("settings_test.yml")):
        _load_yaml_settings("settings_test.yml")
    elif os.path.exists(get_base_dir_path("settings_test.py")):
        _load_py_settings("settings_test.py")


def get_setting(key):
    """
    Get a setting by key
    """
    return settings.get(key, None)


def get_settings_facets():
    """
    Get settings_facets
    """
    # return deep copy
    return copy.deepcopy(settings_facets)


def init_settings():
    """
    Dummy function to indicate that settings are loaded
    And to avoid vscode warning about unused import
    """
    pass
