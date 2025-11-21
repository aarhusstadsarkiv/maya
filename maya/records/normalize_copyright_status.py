"""
Normalize copyright status.
"""

from maya.core.logging import get_log
from maya.core.translate import translate


log = get_log()


creative_commons_license = translate("copyright_creative_commons_license")
creative_commons_license_nc = translate("copyright_creative_commons_license_nc")
special_notice = translate("copyright_special_notice")


def normalize_copyright_status(record: dict, meta_data: dict) -> dict:
    """Add copyright_status_normalized to record"""
    copyright_id = meta_data["copyright_id"]

    lines = []
    label = record["copyright_status"].get("label")
    lines.append(label)

    if copyright_id == 1:
        text = translate("copyright_id_1")
        lines.append(text)

    if copyright_id == 2:
        text = translate("copyright_id_2")
        lines.append(text)

    if copyright_id == 3:
        text = translate("copyright_id_3")
        lines.append(text)

    if copyright_id == 4:
        lines.append(creative_commons_license)
        text = translate("copyright_id_4")
        lines.append(text)

    if copyright_id == 5:
        lines.append(creative_commons_license_nc)
        text = translate("copyright_id_5")
        lines.append(text)

    if copyright_id == 6:
        text = translate("copyright_id_6")
        lines.append(text)

    if copyright_id == 7:
        text = translate("copyright_id_7")
        lines.append(text)

    if copyright_id == 8:
        text = translate("copyright_id_8")
        lines.append(text)

    if copyright_id == 9:
        text = translate("copyright_id_9")
        lines.append(text)

    if copyright_id in [7, 8, 9]:
        if _get_special_notice_id(record):
            lines.append(special_notice)

    record["copyright_status_normalized"] = lines
    return record


def _get_special_notice_id(record: dict) -> bool:
    try:
        id = record["content_types"][0][0].get("id")
    except KeyError:
        id = None

    if id != 36:
        return True

    return False
