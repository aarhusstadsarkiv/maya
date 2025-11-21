from maya.core.translate import translate
from maya.records.constants import LEGAL


def normalize_legal_restrictions(record: dict, meta_data: dict) -> dict:
    """Add other_legal_restrictions_normalized to record"""

    legal_id = meta_data.get("legal_id")

    if legal_id == LEGAL.NO_OTHER_RESTRICTIONS:
        text = translate("legal_restrictions_id_1")
    elif legal_id == LEGAL.PERSONAL_DATA:
        text = translate("legal_restrictions_id_2")
    elif legal_id == LEGAL.ARCHIVE_LAW:
        text = translate("legal_restrictions_id_3")
    elif legal_id == LEGAL.SPECIAL_CIRCUMSTANCES:
        text = translate("legal_restrictions_id_4")

    record["other_legal_restrictions_normalized"] = text
    return record
