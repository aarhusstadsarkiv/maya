"""
Utility functions for extracting and formatting query parameters from HTTP requests.

This module provides helper functions to process query parameters from Starlette `Request` objects.
It allows filtering, formatting, and encoding of query parameters, which is useful for building
URLs, logging, or reusing query strings in downstream requests.

Functions:
- get_list: Extracts query parameters based on allowed keys and merges them with default values.
- get_str_from_list: Converts a list of (key, value) tuples into a URL-encoded query string with
  optional filtering. Values are preserved exactly.
- get_search: Extracts the "q" (search) parameter from a request.
"""

from starlette.requests import Request
from urllib.parse import urlencode
from maya.core.logging import get_log

log = get_log()


def get_list(request: Request, accept_keys: list | None = None, default_query_params: list | None = None) -> list:
    """
    Get query params from request and return it as a list of tuples.
    e.g. [('content_types', '96')]
    """
    query_params = request.query_params
    items = query_params.multi_items()

    items = [(key, value) for key, value in items if key in (accept_keys or [])]
    items.extend(default_query_params or [])

    return items


def get_str_from_list(query_params: list, accept_keys: list | None = None, remove_keys: list | None = None) -> str:
    """Encode pairs without changing their values.

    Keep the trailing separator used by search links that append parameters.
    """
    items = [
        (key, value)
        for key, value in query_params
        if (not accept_keys or key in accept_keys) and (not remove_keys or key not in remove_keys)
    ]
    encoded = urlencode(items)
    return encoded + "&" if encoded else ""


def get_search(request: Request) -> str:
    """Get search query "q" from request and return it as a string.
    E.g. 'test search'"""
    query_params = request.query_params
    q = query_params.get("q", "")
    return q
