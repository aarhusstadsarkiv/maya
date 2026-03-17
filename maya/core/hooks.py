"""
This module provides functionality for dynamically loading a `Hooks` implementation
based on the presence of a local `hooks.py` file in the base directory. It supports
a plug-in system that allows applications to override default behavior by supplying
a local `Hooks` class.

Functions:
- `get_hooks(request)`: Returns an instance of the local or default `Hooks` class,
  depending on whether a local override is found. Accepts an optional Starlette
  `Request` object; if none is provided, a mock request is generated.
- `_get_mock_request()`: Creates a mock Starlette request to support standalone
  hook loading outside of a live request context.

"""

from starlette.requests import Request
from maya.core.logging import get_log
from maya.core.hooks_spec import HooksSpec
from maya.hooks import Hooks
from maya.core.paths import get_base_dir_path
from maya.core.module_loader import load_module_attr
import typing
import os
import sys

log = get_log()


# On startup log if hooks will be loaded
hooks_path = get_base_dir_path("hooks.py")
if os.path.exists(hooks_path):
    log.debug(f"Local hooks exists. Will load local hooks {hooks_path}")
else:
    log.debug("Local hooks does not exist. Will load default hooks")


def _get_mock_request() -> Request:
    # generate a fake request
    scope = {"type": "http", "method": "GET", "path": "/", "headers": []}

    async def receive():
        return {"type": "http.disconnect"}

    request = Request(scope, receive=receive)

    return request


def get_hooks(request: typing.Optional[Request] = None) -> HooksSpec:
    if not request:
        request = _get_mock_request()

    base_dir = get_base_dir_path()
    hooks_path = get_base_dir_path("hooks.py")

    try:
        if os.path.exists(hooks_path):
            if base_dir not in sys.path:
                sys.path.insert(0, base_dir)

            HooksLocal = load_module_attr("hooks", "Hooks")
            return HooksLocal(request)
    except ImportError:
        pass

    return Hooks(request)
