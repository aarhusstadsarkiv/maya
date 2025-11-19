from maya.core.translate import translate


def normalize_contractual_status(record, meta_data):
    """
    Add contractual_status_normalized to record
    """

    contractual_id = meta_data.get("contractual_id")
    text = translate("contractual_status_default")

    if contractual_id == 1:
        # Materialet er utilgængeligt. Ifølge aftale.
        text = translate("contractual_status_id_1")
    elif contractual_id == 2:
        # Materialet er kun tilgængeligt gennem ansøgning. Ifølge aftale.
        text = translate("contractual_status_id_2")
    elif contractual_id == 3:
        # Materialet må kun ses på læsesalen. Ifølge aftale.
        text = translate("contractual_status_id_3")
    elif contractual_id == 4:
        creators = {"pp": False}

        if record.get("creators"):
            for i in record.get("creators"):
                if i.get("id") == 108691:
                    creators.update({"pp": True})

        if creators["pp"]:
            # Materialet må kun offentliggøres på Aarhus Stadsarkivs hjemmesider. Ifølge aftale.
            text = translate("contractual_status_id_4_pp")
        else:
            # Materialet må offentliggøres på internettet. Ifølge aftale.
            text = translate("contractual_status_id_4")

    record["contractual_status_normalized"] = text
    return record
