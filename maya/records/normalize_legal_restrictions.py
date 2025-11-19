"""
Normalize legal restrictions
"""

from maya.core.translate import translate


def normalize_legal_restrictions(record: dict, meta_data: dict):
    """Add legal_restrictions_normalized to record"""

    text = ""
    legal_id = meta_data["legal_id"]
    if legal_id == 1:
        # Materialet er ikke underlagt andre juridiske begrænsninger
        text = translate("legal_restrictions_id_1")
    elif legal_id == 2:
        # Materialet er utilgængeligt ifølge persondatalovgivningen.
        text = translate("legal_restrictions_id_2")
    elif legal_id == 3:
        # Materialet er utilgængeligt ifølge arkivlovgivningen.
        text = translate("legal_restrictions_id_3")
    elif legal_id == 4:
        # Materialet er utilgængeligt som følge af særlige juridiske forhold
        text = translate("legal_restrictions_id_4")

    record["other_legal_restrictions_normalized"] = text
    return record
