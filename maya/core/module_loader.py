"""
Module for dynamically loading Python modules and their attributes.

This module provides utility functions for importing Python modules and retrieving specific
attributes (such as functions, classes, or variables) from them. It supports two main use cases:
1. Loading modules and attributes directly from file paths.
2. Loading attributes from standard importable modules.

Functions:
- load_module_from_file(module_name: str, file_path: str):
    Dynamically loads a module from a specified Python file path.

- load_attr_from_file(module_name: str, attr_name: str, file_path: str):
    Loads a specific attribute from a module defined in a given file path.

- load_module_attr(module_name: str, attr_name: str):
    Loads a specific attribute from an already importable module.

Typical use cases include dynamic plugin systems, test frameworks, or any context where
Python code needs to be loaded and interacted with at runtime.
"""

import importlib
import importlib.util
import os


def load_module_from_file(module_name: str, file_path: str):
    """
    Loads a module from a Python file.

    Parameters:
    - module_name: A unique name to register the module internally.
    - file_path: The path to the Python file containing the module.

    Returns:
    - The loaded module object.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File path not found: {file_path}")

    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None:
        raise ImportError(f"Could not load spec for module {module_name} from {file_path}")

    if spec.loader is None:
        raise ImportError(f"No loader found for module {module_name} from {file_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def load_attr_from_file(module_name: str, attr_name: str, file_path: str):
    """
    Loads an attribute (e.g., a class or function) from a module file.

    Parameters:
    - module_name: A unique name for the module used internally.
    - attr_name: The name of the attribute to load from the module.
    - file_path: The path to the Python file containing the module.

    Returns:
    - The specified attribute from the loaded module.
    """
    module = load_module_from_file(module_name, file_path)
    attr = getattr(module, attr_name)

    return attr


def load_module_attr(module_name: str, attr_name: str):
    """
    Loads an attribute from an already importable module (without executing its source file directly).

    Parameters:
    - module_name: The importable module name (as used with `import`).
    - attr_name: The name of the attribute to retrieve from the module.

    Returns:
    - The specified attribute from the imported module.
    """
    submodule = importlib.import_module(module_name)
    attr = getattr(submodule, attr_name)
    return attr
