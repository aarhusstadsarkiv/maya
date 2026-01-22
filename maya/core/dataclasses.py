"""
This module defines data structures used to manage pagination and search state within the Maya application.

Classes:
    - RecordPagination: Encapsulates metadata and navigation pointers for paginated record views.
    - SearchCookie: Stores the state of a search query, including parameters and display strings.
"""

import dataclasses
import typing


@dataclasses.dataclass
class RecordPagination:
    """ "
    Record pagination object
    """

    search_query_str: str
    total: int = 0
    next_page: typing.Optional[int] = None
    prev_page: typing.Optional[int] = None
    next_record: typing.Optional[int] = None
    prev_record: typing.Optional[int] = None
    current_page: typing.Optional[int] = None


@dataclasses.dataclass
class SearchCookie:
    """
    The search cookie is used to keep track of the search state
    """

    search_query_str: str = ""
    query_params: list = dataclasses.field(default_factory=list)
    total: int = 0
    q: str = ""
