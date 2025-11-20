from maya.core.translate import translate
from maya.records.constants import LEGAL, CONTRACT, AVAILABILITY


def normalize_availability(record: dict, meta_data: dict):
    """
    Add availability_normalized to record
    """
    legal_id = meta_data["legal_id"]
    contractual_id = meta_data["contractual_id"]
    availability_id = meta_data["availability_id"]

    output_text = translate("availability_common")

    if legal_id not in [LEGAL.NO_OTHER_RESTRICTIONS] or contractual_id == CONTRACT.UNAVAILABLE:
        output_text = translate("availability_contractual_id_1")
    elif contractual_id == CONTRACT.APPLICATION_ONLY:
        output_text = translate("availability_contractual_id_2")
    elif availability_id == AVAILABILITY.IN_STORAGE:
        output_text = translate("availability_availability_id_2")
    elif availability_id == AVAILABILITY.IN_READING_ROOM:
        output_text = translate("availability_availability_id_3")

    record["availability_normalized"] = output_text
    return record
