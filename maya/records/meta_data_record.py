"""
Get some usefull meta data for a record
"""

from maya.core.logging import get_log
from starlette.requests import Request
from maya.records import record_utils


log = get_log()


IP_ALLOW = ["193.33.148.24"]


ICONS = {
    "61": {"icon": "image", "label": "Billeder"},
    "95": {"icon": "laptop_windows", "label": "Elektronisk materiale"},
    "10": {"icon": "gavel", "label": "Forskrifter og vedtægter"},
    "1": {"icon": "folder_open", "label": "Kommunale sager og planer"},
    "75": {"icon": "map", "label": "Kortmateriale"},
    "49": {"icon": "description", "label": "Manuskripter"},
    "87": {"icon": "movie", "label": "Medieproduktioner"},
    "81": {"icon": "audio_file", "label": "Musik og lydoptagelser"},
    "36": {"icon": "article", "label": "Publikationer"},
    "18": {"icon": "menu_book", "label": "Registre og protokoller"},
    "29": {"icon": "bar_chart", "label": "Statistisk og økonomisk materiale"},
    "99": {"icon": "description", "label": "Andet materiale"},
}


def _get_icon(record: dict):
    """
    Get icon for the record based on content type
    content-types is in this format: [{'id': [10], 'label': ['Forskrifter og vedtægter']}]
    """
    try:
        content_type = record["content_types"][0][0]
        content_type_id = str(content_type["id"])
        return ICONS[content_type_id]
    except (KeyError, IndexError, TypeError):
        return ICONS["99"]


def _strip_pre_zeroes(value: str) -> str:
    """
    Strip pre zeroes from a string
    """
    return value.lstrip("0")


def get_record_meta_data(request: Request, record: dict, user_permissions=[]) -> dict:
    """
    Get usefull meta data for a record
    """
    meta_data = {}

    if "representations" in record and "record_type" not in record["representations"]:
        extra = {"error_code": 499, "error_url": request.url}
        log.error(f"Record {record['id']}. Representations but no record_type", extra=extra)
        del record["representations"]

    title = _get_record_title(record)
    if not title:
        quote_title = record_utils.meaningful_substring(record.get("summary", ""), 200)
        title = f"[{quote_title}]"

    # check if "user" in user_permissions
    # then the user has the permission as if the user is allowed_by_ip
    permssion_granted = "employee" in user_permissions

    meta_data["id"] = record["id"]
    meta_data["real_id"] = _strip_pre_zeroes(record["id"])
    meta_data["allowed_by_ip"] = _is_allowed_by_ip(request) or permssion_granted
    meta_data["permission_granted"] = permssion_granted
    meta_data["title"] = title
    meta_data["meta_title"] = _get_meta_title(record)
    meta_data["summary"] = record.get("summary", "")
    meta_data["meta_description"] = record_utils.meaningful_substring(record.get("summary", ""), 120)

    if not meta_data["meta_description"]:
        meta_data["meta_description"] = meta_data["meta_title"]

    meta_data["icon"] = _get_icon(record)
    meta_data["copyright_id"] = record["copyright_status"].get("id")
    meta_data["legal_id"] = record["other_legal_restrictions"].get("id")
    meta_data["contractual_id"] = record["contractual_status"].get("id")
    meta_data["availability_id"] = record["availability"].get("id")
    meta_data["usability_id"] = record["usability"].get("id")
    meta_data["collection_id"] = record.get("collection", {}).get("id")
    meta_data["content_types_label"] = _get_content_type_label(record)

    meta_data = _set_order_info(meta_data, record)
    meta_data = _set_representations(meta_data, record)

    meta_data["is_downloadable"] = _is_downloadable(meta_data)

    return meta_data


def _set_representations(meta_data: dict, record: dict):
    """
    This indicates if the record has representations, which images, audio, video, pdf, sejrs_sedler
    """

    meta_data["is_representations_online"] = False

    if meta_data["legal_id"] == 1 and meta_data["contractual_id"] > 2:
        if meta_data["availability_id"] == 4 or meta_data["permission_granted"] or meta_data["allowed_by_ip"]:
            if "representations" in record:
                meta_data["record_type"] = record["representations"].get("record_type")

                meta_data["is_representations_online"] = True
                meta_data["representations"] = record["representations"]

                if "large_image" not in meta_data["representations"]:
                    meta_data["representations"]["large_image"] = meta_data["representations"].get("record_image")

                if "full_image" in meta_data["representations"]:
                    meta_data["representations"]["large_image"] = meta_data["representations"]["full_image"]

                meta_data["portrait"] = record.get("portrait")
    else:
        meta_data["record_type"] = "icon"
        meta_data["is_representations_online"] = True

    collection_id = record.get("collection", {}).get("id")
    if collection_id == 1:
        meta_data["record_type"] = "sejrs_sedler"
        meta_data["is_representations_online"] = True

    return meta_data


def _is_allowed_by_ip(request: Request) -> bool:
    try:
        ip = request["client"][0]
    except KeyError:
        return False
    except TypeError:
        return False

    if ip in IP_ALLOW:
        return True
    return False


def _is_downloadable(meta_data: dict) -> bool:
    return (
        meta_data.get("representations", False)
        and meta_data["legal_id"] == 1
        and meta_data["contractual_id"] > 3
        and meta_data["usability_id"] in [1, 2, 3]
        and meta_data["record_type"] != "video"
    )


def _get_record_title(record: dict):
    """
    Try to get a title for the record. This is used as the title of the document, not the meta title
    """

    title = ""
    record_title = record.get("title")
    if not record_title:
        record_title = record.get("heading")

    if record_title:
        title = record_title

    return title


def _get_content_type_label(record: dict):
    """
    content_types of a record is a list of lists of dicts, e.g.:

    'content_types': [[{'id': 36, 'label': 'Publikationer'}, {'id': 37, 'label': 'Faglitteratur'}]],
    This def return first content_type as a string, e.g. "Publikationer > Faglitteratur"
    """
    content_types = record.get("content_types", [])
    content_type: dict = content_types[0] if content_types else {}

    if "label" in content_type:
        formatted_label = " > ".join(content_type["label"])
    else:
        formatted_label = ""

    return formatted_label


def _get_meta_title(record: dict):
    """
    Get the meta title for the record. This is used as the meta title of the document, the <title> tag
    """
    meta_title = _get_record_title(record)

    if not meta_title:
        meta_title = record_utils.meaningful_substring(record.get("summary", ""), 60)

    return meta_title


def _set_order_info(meta_data: dict, record: dict):
    """
    Get info describing if the record can be ordered
    """
    try:
        resources = record["resources"][0]
    except KeyError:
        resources = {}

    meta_data["resources"] = resources
    legal_id = meta_data["legal_id"]
    contractual_id = meta_data["contractual_id"]
    availability_id = meta_data["availability_id"]

    orderable = False
    orderable_online = False
    orderable_by_form = False

    if availability_id == 2 and legal_id == 1 and contractual_id > 2:
        orderable = True
        orderable_online = True

    if availability_id == 2 and legal_id in [2, 3] and contractual_id == 2:
        orderable = True
        orderable_by_form = True

    meta_data["orderable"] = orderable
    meta_data["orderable_online"] = orderable_online
    meta_data["orderable_by_form"] = orderable_by_form
    return meta_data
