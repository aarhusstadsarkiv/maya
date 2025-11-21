from maya.core.dynamic_settings import settings


def is_collection(record_dict: dict, collection_id: int) -> bool:
    """
    Check if the record belongs to a collection.
    """
    try:
        collection = record_dict["collection"].get("id")
    except KeyError:
        return False

    if collection == collection_id:
        return True

    return False


def is_collector(record_dict: dict, collector_id: int) -> bool:
    """
    Check if the record has a collector with id collector_id.
    """
    try:
        collectors = record_dict["collectors"]
    except KeyError:
        return False

    for collector in collectors:
        if collector["id"] == collector_id:
            return True

    return False


def is_curator(record_dict: dict, curator_id: int) -> bool:
    """
    Check if first curator is the same as curator_id.
    """

    try:
        curator = record_dict["curators"][0]
    except KeyError:
        return False

    if curator["id"] == curator_id:
        return True

    return False


def meaningful_substring(s: str, max_length: int) -> str:
    # Check if the string is shorter or equal to max_length
    if len(s) <= max_length:
        return s

    # Find the last space within the allowed length
    space_index = s.rfind(" ", 0, max_length)

    # If no space is found, we might cut in the middle of a word, but we respect the max_length
    if space_index == -1:
        return s[:max_length] + "..."

    # Return substring that ends at the last space within the limit
    return s[:space_index] + "..."


def get_record_url(record_id: str) -> str:
    """
    Return the url of the record.
    """
    return f"{settings.get('client_url')}/records/{record_id}"
