"""Validate public identifiers before interpolating them into backend paths."""

from starlette.exceptions import HTTPException

RESOURCE_TYPES = frozenset({"collections", "people", "locations", "creators", "events", "organisations", "collectors"})


def validate_proxy_id(resource_id: str) -> None:
    # Restrict IDs to ASCII digits; preserve leading zeroes for the backend.
    if not resource_id.isascii() or not resource_id.isdigit():
        raise HTTPException(status_code=404, detail="Resource id not found")


def validate_resource_path(resource_type: str, resource_id: str, *, allow_records: bool = False) -> None:
    if resource_type not in RESOURCE_TYPES and not (allow_records and resource_type == "records"):
        raise HTTPException(status_code=404, detail="Resource type not found")
    validate_proxy_id(resource_id)
