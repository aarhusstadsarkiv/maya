"""
This module provides cookie utility functions:

- get_search_cookie: Parses the 'search' cookie from the request and returns a
  SearchCookie dataclass instance, applying any dynamic settings adjustments.
- get_search_query_params: Extracts the search query parameters from the cookie
  as a list of (key, value) tuples.
- get_search_query_str: Retrieves a query string representation of the search
  parameters, formatted as a standard query string.

"""

import json
from starlette.requests import Request
from maya.core.dynamic_settings import settings
from maya.core.dataclasses import SearchCookie


def get_search_cookie(request: Request) -> SearchCookie:
    """
    Get search cookie from request and return it as a SearchCookie dataclass object
    """

    try:
        search_cookie_str = request.cookies.get("search", None)
        assert isinstance(search_cookie_str, str)

        search_cookie = json.loads(search_cookie_str)
        assert isinstance(search_cookie, dict)

        # Query params is a list of tuples, but when converting to JSON it is converted to a list of lists
        # Convert back to list of tuples
        query_params = search_cookie["query_params"]
        query_params = [tuple(item) for item in query_params]
        search_cookie["query_params"] = query_params

        assert isinstance(search_cookie, dict)

        # If the search results should not be kept then remove the query string
        if not settings["search_keep_results"]:
            search_cookie["search_query_str"] = ""

        # return search_cookie
        return SearchCookie(**search_cookie)

    except Exception:
        return SearchCookie()


def get_search_query_params(request: Request) -> list:
    """
    Get query string from search cookie and return it as a list of tuples
    E.g. [('content_types', '96'), ('content_types', '97')]
    """
    search_cookie = get_search_cookie(request)
    return search_cookie.query_params


def get_search_query_str(request: Request) -> str:
    """
    Get query string from search cookie and return it as a string.
    E.g. 'content_types=96&content_types=97&'
    """
    search_cookie = get_search_cookie(request)
    return search_cookie.search_query_str
