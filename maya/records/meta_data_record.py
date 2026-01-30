"""
Get some usefull meta data for a record
"""

from maya.core.logging import get_log
from starlette.requests import Request
from maya.records import record_utils
from maya.records.constants import LEGAL, CONTRACT, AVAILABILITY, USABILITY
from maya.core import api
from maya.core.dynamic_settings import settings


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


def get_record_meta_data_resolve(request: Request, record: dict):
    """
    Get meta data from record originated from 'proxies_resolve' endpoint
    """
    meta_data = {}
    meta_data["id"] = record["id"]
    meta_data["path"] = f"/records/{meta_data['id']}"
    meta_data["title"] = _get_record_title(record)
    meta_data["date_normalized"] = record.get("date_normalized")
    meta_data["collection_label"] = record.get("collection", {}).get("label", "")
    meta_data["content_types_label"] = _get_content_type_label(record)
    meta_data["portrait"] = record.get("portrait")
    return meta_data


async def get_record_meta_data(
    request: Request,
    record: dict,
) -> dict:
    """
    Get usefull meta data for a record
    """
    is_logged_in = await api.is_logged_in(request)
    verified = await api.me_verified(request)
    is_employee = await api.has_permission(request, "employee")

    meta_data = {}

    _fix_missing_representation(request, record)

    meta_data["id"] = record["id"]
    meta_data["real_id"] = _strip_pre_zeroes(record["id"])
    meta_data["_allowed_by_ip"] = _is_allowed_by_ip(request)
    meta_data["_permission_granted"] = is_employee

    meta_data["title"] = _get_record_title(record)
    meta_data["meta_title"] = _get_meta_title(record)
    meta_data["summary"] = record.get("summary", "")
    meta_data["meta_description"] = _get_meta_description(record)

    meta_data["icon"] = _get_icon(record)
    meta_data["copyright_id"] = record["copyright_status"].get("id")
    meta_data["legal_id"] = record["other_legal_restrictions"].get("id")
    meta_data["contractual_id"] = record["contractual_status"].get("id")
    meta_data["availability_id"] = record["availability"].get("id")
    meta_data["usability_id"] = record["usability"].get("id")
    meta_data["collection_id"] = record.get("collection", {}).get("id")
    meta_data["content_types_label"] = _get_content_type_label(record)
    meta_data["orderable"] = _is_orderable(meta_data)
    meta_data["orderable_online"] = _is_orderable_online(meta_data)
    meta_data["orderable_by_form"] = _is_orderable_by_form(meta_data)

    order_message = get_order_message(meta_data, is_logged_in, verified)
    meta_data["order_message"] = order_message
    meta_data["resources"] = _get_order_resources(record)

    if _has_representation_permission(meta_data) and _has_representation(record):
        meta_data["record_type"] = record["representations"].get("record_type")
        meta_data["representations"] = _build_representations(record)
        meta_data["portrait"] = record.get("portrait")
        meta_data["is_representations_online"] = True

    elif _is_sejrs_collection(record):
        meta_data["record_type"] = "sejrs_sedler"
        meta_data["representations"] = _build_representations(record)
        meta_data["is_representations_online"] = True

    else:
        meta_data["record_type"] = "icon"

    meta_data["is_downloadable"] = _is_downloadable(meta_data)
    return meta_data


def _fix_missing_representation(request: Request, record: dict) -> None:
    if "representations" in record and "record_type" not in record["representations"]:
        extra = {"error_code": 499, "error_url": request.url}
        log.error(f"Record {record['id']}. Representations but no record_type", extra=extra)
        del record["representations"]


def _has_representation(record: dict) -> bool:
    return "representations" in record


def _get_icon(record: dict) -> dict:
    """
    Get icon for the record based on content type
    content-types is in this format: [{'id': [10], 'label': ['Forskrifter og vedtægter']}]
    """
    try:
        content_type = record["content_types"][0][0]
        content_type_id = str(content_type["id"])
        return ICONS[content_type_id]
    except Exception:
        return ICONS["99"]


def get_order_message(meta_data: dict, is_logged_in: bool, is_verified: bool) -> str:
    """
    Get message for ordering online
    """
    if not settings.get("allow_online_ordering", False):
        return ""

    id = meta_data["id"]

    login_url = f"<a href='/auth/login?next=/records/{id}'>Log ind</a>"
    register_url = "<a href='/auth/register'>opret bruger</a>"

    if is_logged_in and is_verified:
        return "<p>Materialet kan bestilles hjem til læsesalen.</p>"

    elif not is_verified:
        verify_url = "<a href='/auth/me'>verificere</a>"
        return f"<p>Du skal {verify_url} din konto for at bestille.</p>"

    else:
        return "<p>Materialet kan bestilles hjem til læsesalen.<br>" f" {login_url} eller {register_url} for at bestille.</p>"


def _strip_pre_zeroes(value: str) -> str:
    """
    Strip pre zeroes from a string
    """
    return value.lstrip("0")


def _allow_all(meta_data: dict) -> bool:
    return (
        meta_data["legal_id"] == LEGAL.NO_OTHER_RESTRICTIONS
        and meta_data["contractual_id"] in [CONTRACT.INTERNET, CONTRACT.NO_CLAUSES]
        and meta_data["availability_id"] == AVAILABILITY.ONLINE_ACCESS
        and meta_data["usability_id"] not in [USABILITY.ALL_RIGHTS_RESERVED]
    )


def _allow_employee(meta_data: dict) -> bool:
    return meta_data["_permission_granted"] and meta_data["legal_id"] == LEGAL.NO_OTHER_RESTRICTIONS


def _allow_reading_room(meta_data: dict) -> bool:
    return (
        meta_data["_allowed_by_ip"]
        and meta_data["legal_id"] == LEGAL.NO_OTHER_RESTRICTIONS
        and meta_data["availability_id"] in [AVAILABILITY.IN_READING_ROOM]
    )


def _is_downloadable(meta_data: dict) -> bool:
    return meta_data["record_type"] == "image" and _has_representation_permission(meta_data)


def _has_representation_permission(meta_data: dict) -> bool:
    """
    Check if representation permission is granted
    """
    if _allow_all(meta_data):
        return True

    if _allow_employee(meta_data):
        return True

    if _allow_reading_room(meta_data):
        return True

    return False


def _is_sejrs_collection(record: dict) -> bool:
    return record.get("collection", {}).get("id") == 1


def _build_representations(record: dict) -> dict:
    representations = dict(record.get("representations", {}) or {})

    if not representations:
        return representations

    if "large_image" not in representations:
        representations["large_image"] = representations.get("record_image")

    if "full_image" in representations:
        representations["large_image"] = representations["full_image"]

    return representations


def _is_allowed_by_ip(request: Request) -> bool:
    try:
        ip = request["client"][0]
        if ip in IP_ALLOW:
            return True
    except Exception:
        pass
    return False


def _get_record_title(record: dict) -> str:
    """
    Try to get a title for the record. This is used as the title of the document, not the meta title
    """

    title = ""
    record_title = record.get("title", "")
    if not record_title:
        record_title = record.get("heading", "")

    if record_title:
        title = record_title

    return title


def _get_meta_title(record: dict) -> str:
    """
    Get the meta title for the record. This is used as the meta title of the document, the <title> tag
    """
    meta_title = _get_record_title(record)

    if not meta_title:
        meta_title = record_utils.meaningful_substring(record.get("summary", ""), 60)

    return meta_title


def _get_meta_description(record: dict) -> str:

    meta_description = record_utils.meaningful_substring(record.get("summary", ""), 120)
    if not meta_description:
        meta_description = _get_meta_title(record)
    return meta_description


def _get_content_type_label(record: dict) -> str:
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


def _is_orderable_online(meta_data: dict) -> bool:
    """
    Get info describing if the record can be ordered online
    """
    legal_id = meta_data["legal_id"]
    contractual_id = meta_data["contractual_id"]
    availability_id = meta_data["availability_id"]

    if (
        availability_id in [AVAILABILITY.IN_STORAGE, AVAILABILITY.IN_READING_ROOM]
        and legal_id == LEGAL.NO_OTHER_RESTRICTIONS
        and contractual_id in [CONTRACT.INTERNET, CONTRACT.READING_ROOM, CONTRACT.NO_CLAUSES]
    ):
        return True

    return False


def _is_orderable_by_form(meta_data: dict) -> bool:
    """
    Get info describing if the record can be ordered by form
    """
    legal_id = meta_data["legal_id"]
    contractual_id = meta_data["contractual_id"]
    availability_id = meta_data["availability_id"]

    if (
        availability_id == AVAILABILITY.IN_STORAGE
        and legal_id in [LEGAL.PERSONAL_DATA, LEGAL.ARCHIVE_LAW, LEGAL.SPECIAL_CIRCUMSTANCES]
        or contractual_id == CONTRACT.APPLICATION_ONLY
    ):
        return True

    return False


def _is_orderable(meta_data: dict) -> bool:
    """
    Get info describing if the record can be ordered
    """
    return _is_orderable_online(meta_data) or _is_orderable_by_form(meta_data)


def _get_order_resources(record: dict):
    try:
        resources = record["resources"][0]
    except KeyError:
        resources = {}

    return resources
