from maya.core.translate import translate
from maya.records.constants import CONTRACT

PAUL_PEDERSEN_CREATOR_ID = 108691


def normalize_contractual_status(record: dict, meta_data: dict) -> dict:
    """
    Add contractual_status_normalized to record
    """

    contractual_id = meta_data.get("contractual_id")
    text = translate("contractual_status_default")

    if contractual_id == CONTRACT.UNAVAILABLE:
        text = translate("contractual_status_id_1")
    elif contractual_id == CONTRACT.APPLICATION_ONLY:
        text = translate("contractual_status_id_2")
    elif contractual_id == CONTRACT.READING_ROOM:
        text = translate("contractual_status_id_3")
    elif contractual_id == CONTRACT.INTERNET:
        creators = record.get("creators") or []

        if any(c.get("id") == PAUL_PEDERSEN_CREATOR_ID for c in creators):
            text = translate("contractual_status_id_4_pp")
        else:
            text = translate("contractual_status_id_4")

    record["contractual_status_normalized"] = text
    return record
