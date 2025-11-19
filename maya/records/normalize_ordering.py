"""
Normalize ordering (Bestilling)

"""

from maya.core.logging import get_log
from maya.core.translate import translate

log = get_log()


def normalize_ordering(record: dict, meta_data: dict):
    """Add ordering to record"""
    availability_id = meta_data.get("availability_id", None)
    legal_id = meta_data.get("legal_id", None)
    contractual_id = meta_data.get("contractual_id", 0)

    curators: list = record.get("curators", [])

    result = []
    if availability_id == 2 and legal_id == 1 and contractual_id > 2:
        result.append(translate("ordering_by_mail"))
        for curator in curators:
            if curator.get("id") == 4:
                result.append(translate("ordering_aarhus_teatret"))

    elif availability_id == 2 and legal_id in [2, 3] and contractual_id == 2:
        result.append(translate("ordering_by_application"))

    if result:
        record["ordering_normalized"] = result

    return record
