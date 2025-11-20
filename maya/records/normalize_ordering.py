"""
Normalize ordering (Bestilling)

"""

from maya.core.logging import get_log
from maya.core.translate import translate

log = get_log()


def normalize_ordering(record: dict, meta_data: dict):
    """
    Add information about ordering to record
    """
    curators: list = record.get("curators", [])

    result = []
    if not meta_data.get("orderable", False):
        return record

    if meta_data.get("orderable_online"):
        result.append(translate("ordering_by_mail"))
        for curator in curators:
            if curator.get("id") == 4:
                result.append(translate("ordering_aarhus_teatret"))

    elif meta_data.get("orderable_by_form"):
        result.append(translate("ordering_by_application"))

    if result:
        record["ordering_normalized"] = result

    return record
