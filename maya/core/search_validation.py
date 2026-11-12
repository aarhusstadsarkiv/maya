"""Validate structured search values before contacting the records API."""

from datetime import date

from starlette.exceptions import HTTPException

from maya.settings_query_params import settings_query_params

ALLOWED_SEARCH_SORTS = frozenset({"_score", "date_from", "date_to", "created_at"})
ALLOWED_SEARCH_VIEWS = frozenset({"list", "gallery", "grid"})


class SearchQueryError(HTTPException):
    def __init__(self, parameter: str, reason: str):
        super().__init__(status_code=400, detail=f"Invalid search query: '{parameter}' {reason}.")


def _is_digits(value: str) -> bool:
    return value.isascii() and value.isdigit()


def validate_search_query(items: list[tuple[str, str]], *, ids_view: bool = False) -> None:
    """Check every occurrence, including negated filters, without rewriting text.

    Empty filters are permitted because the search form treats them as unset.
    Unknown keys are left to the existing parameter selection. Do not impose
    keyword rules on free text, tags, series paths, or opaque cursor tokens.
    """
    for key, value in items:
        name = key.removeprefix("-")
        spec = settings_query_params.get(name)
        if spec is None or (key.startswith("-") and not spec.get("negatable")):
            continue

        if spec["search_filter"] and not value:
            continue

        if spec["type"] in {"object", "integer"}:
            if not _is_digits(value):
                raise SearchQueryError(key, "must contain only digits (0-9)")
            if name in {"size", "start"}:
                # Check length before int() so oversized input cannot cause a 500.
                digits = value.lstrip("0") or "0"
                maximum = (10000 if ids_view else 1000) if name == "size" else 9999
                minimum = 1 if name == "size" else 0
                if len(digits) > len(str(maximum)) or not minimum <= int(digits) <= maximum:
                    raise SearchQueryError(key, f"must be between {minimum} and {maximum}")
                try:
                    int(value)
                except ValueError:
                    raise SearchQueryError(key, "is too long") from None

        if spec["type"] == "date":
            if len(value) != 8 or not _is_digits(value):
                raise SearchQueryError(key, "must be a valid date in YYYYMMDD format")
            try:
                date(int(value[:4]), int(value[4:6]), int(value[6:]))
            except ValueError:
                raise SearchQueryError(key, "must be a valid date in YYYYMMDD format") from None

        if name == "direction" and value not in {"asc", "desc"}:
            raise SearchQueryError(key, "must be asc or desc")
        if name == "sort" and value not in ALLOWED_SEARCH_SORTS:
            raise SearchQueryError(key, "must be _score, date_from, date_to, or created_at")
        if name == "view" and value not in ALLOWED_SEARCH_VIEWS and not (ids_view and value == "ids"):
            raise SearchQueryError(key, "has an unsupported view")
