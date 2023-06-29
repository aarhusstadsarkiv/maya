from stadsarkiv_client.core.translate import translate


def normalize_contractual_status(record, creators=None):
    """Add contractual_status_normalized to record"""

    contractual_id = record.get("contractual_id")
    text = translate("contractual_status_default")

    if contractual_id == 1:
        text = translate("contractual_status_id_1")
    elif contractual_id == 2:
        text = translate("contractual_status_id_2")
    elif contractual_id == 3:
        text = translate("contractual_status_id_3")
    elif contractual_id == 4:
        creators = {"pp": False}

        if record.get("creators"):
            for i in record.get("creators"):
                if i.get("id") == 108691:
                    creators.update({"pp": True})

        if creators["pp"]:
            text = translate("contractual_status_id_4_pp")
        else:
            text = translate("contractual_status_id_4")

    record["contractual_status_normalized"] = text
    return record
