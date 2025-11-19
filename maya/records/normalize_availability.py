from maya.core.translate import translate


def normalize_availability(record: dict, meta_data: dict):
    """
    Add availability_normalized to record
    """
    legal_id = meta_data["legal_id"]
    contractual_id = meta_data["contractual_id"]
    availability_id = meta_data["availability_id"]

    output_text = translate("availability_common")

    if legal_id > 1 or contractual_id == 1:
        # Materialet er utilgængeligt som følge af nævnte juridiske forhold.
        output_text = translate("availability_contractual_id_1")
    elif contractual_id == 2:
        # Materialet er kun tilgængeligt gennem ansøgning.
        output_text = translate("availability_contractual_id_2")
    elif availability_id == 2:
        # Materialet skal bestilles hjem til læsesalen, før det kan beses.
        output_text = translate("availability_availability_id_2")
    elif availability_id == 3:
        """
        Materialet er tilgængeligt på læsesalen. Der kræves
        ikke forudgående bestilling for at se materialet på læsesalen. Man skal blot møde
        op i åbningstiderne.
        """
        output_text = translate("availability_availability_id_3")

    record["availability_normalized"] = output_text
    return record
