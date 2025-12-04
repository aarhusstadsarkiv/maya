from maya.core.logging import get_log
import json
import dataclasses
from maya.core import date_format
import arrow
from maya.core import utils_core
from maya.core import api
from maya.core.templates import get_template_content
from maya.core.dynamic_settings import settings


log = get_log()


@dataclasses.dataclass
class RecordLocation:
    """
    Possible locations for a record
    """

    IN_STORAGE: int = 1
    PACKED_STORAGE: int = 2
    READING_ROOM: int = 4
    RETURN_TO_STORAGE: int = 5


RECORD_LOCATION = RecordLocation()
RECORD_LOCATION_HUMAN = {
    1: "På magasin",  # Initial status
    2: "Pakket til depot",
    4: "På læsesalen",
    5: "Pakket retur",
}


@dataclasses.dataclass
class OrderStatus:
    """
    Possible user statuses for an order
    NOTICE: In /static/js/orders.js the statuses are copied from here
    """

    ORDERED: int = 1
    COMPLETED: int = 2
    QUEUED: int = 3
    DELETED: int = 4


ORDER_STATUS = OrderStatus()
ORDER_STATUS_HUMAN = {
    1: "Bestilt",
    2: "Afsluttet",
    3: "I kø",
    4: "Slettet",
}

ORDER_STATUS_USER = OrderStatus()
ORDER_STATUS_USER_HUMAN = {
    1: "På vej",
    2: "Afsluttet",
    3: "I kø",
    4: "Slettet",
}


DEADLINE_DAYS_RENEWAL = 3
DEADLINE_DAYS = 30


def get_single_order_message(order: dict) -> str:
    """
    Get a single line message to display on a single material that the user has ordered.
    Only these options. "På vej", "I kø", "Tilgængeligt på læsesal"
    """
    message = ""
    if order["order_status"] == ORDER_STATUS.ORDERED:
        message = "Materialet er bestilt. Du modtager en e-mail fra os, når materialet er klar til gennemsyn."
        if order["location"] == RECORD_LOCATION.READING_ROOM:
            message = "Det bestilte materialle er tilgængeligt. Du kan gennemse det på læsesalen."
    elif order["order_status"] == ORDER_STATUS.QUEUED:
        message = "Din bestilling er i kø. Du modtager en e-mail fra os, når materialet er klar til gennemsyn."

    return message


def get_insert_user_data(me: dict) -> dict:
    """
    Get user data for inserting into users table
    """
    return {
        "user_id": me["id"],
        "user_email": me["email"],
        "user_display_name": me["display_name"],
    }


def get_insert_record_data(meta_data: dict, record_and_types: dict, location: int = 0) -> dict:
    """
    Get material data for inserting into records table
    """
    if not location:
        location = RECORD_LOCATION.IN_STORAGE

    data = {
        "record_id": meta_data["id"],
        "label": meta_data["meta_title"],
        "meta_data": json.dumps(meta_data),
        "record_and_types": json.dumps(record_and_types),
        "location": location,
    }

    return data


def get_order_data(user_id: str, record_id: str, order_status: int) -> dict:
    return {
        "user_id": user_id,
        "record_id": record_id,
        "order_status": order_status,
        "created_at": get_current_date_time(),
        "updated_at": get_current_date_time(),
    }


def format_order_display(order: dict):
    """
    Format dates in order for display. Change from UTC to Europe/Copenhagen
    """
    try:
        # convert created_at and updated_at to danish timezone
        order["created_at"] = date_format.timezone_alter(order["created_at"])
        order["updated_at"] = date_format.timezone_alter(order["updated_at"])

        # short version of created_at and updated_at
        order["created_at_short"] = arrow.get(order["created_at"]).format("YYYY-MM-DD")
        order["updated_at_short"] = arrow.get(order["updated_at"]).format("YYYY-MM-DD")

        # Add human readable date format for created_at
        created_at_human = arrow.get(order["created_at"], "YYYY-MM-DD HH:mm:ss")
        created_at_human_str = created_at_human.format("D. MMMM YYYY", locale="da")
        order["created_at_human"] = created_at_human_str

        # Load json data
        order["record_and_types"] = json.loads(order["record_and_types"])
        order["meta_data_dict"] = json.loads(order["meta_data"])

        # Convert record_and_types to string
        record_and_types = order["record_and_types"]

        used_keys = ["date_normalized", "series", "collection", "collectors"]
        record_and_types_strings = utils_core.get_record_and_types_as_strings(record_and_types, used_keys)

        resources = order["meta_data_dict"]["resources"]
        record_and_types_strings.update(resources)

        order["collectors"] = record_and_types_strings.get("collectors", "")

        # Convert expire_at to deadline date string
        if order["expire_at"]:
            # deadline is the day before expire_at
            deadline = arrow.get(order["expire_at"]).shift(days=-1)
            deadline_str = deadline.format("YYYY-MM-DD")
            order["deadline_human"] = deadline_str

        # Convert statuses to human readable. Backend
        order["order_status_human"] = ORDER_STATUS_HUMAN.get(order["order_status"])

        # Check if queued
        if order["order_status"] == ORDER_STATUS.QUEUED:
            order["queued"] = True

        order["location_human"] = RECORD_LOCATION_HUMAN.get(order["location"])
    except (json.JSONDecodeError, TypeError):
        log.exception("Error in format_order_display")
        log.debug(f"{type(order['record_and_types'])}")

    return order


def get_days_until_expire(order: dict) -> int:
    """
    Get days until an order expires.
    """
    days_remaining = 0
    if order["order_status"] == ORDER_STATUS.ORDERED and order["expire_at"]:
        expire_ = arrow.get(order["expire_at"], "YYYY-MM-DD")
        days_remaining = (expire_ - arrow.utcnow()).days

    return days_remaining


def get_date_indicating_renewal_mail() -> str:
    """
    This def gets a date string DEADLINE_DAYS_RENEWAL days into the future.
    If this date corresponds to the expire_at of an order a mail can be sent to the user
    so they can renew the order.
    """
    # deadline is the last day the order is valid. Therefor we add one extra day which is the day it expires
    date_send_renewal = arrow.utcnow().floor("day").shift(days=DEADLINE_DAYS_RENEWAL + 1)
    date_send_renewal_str = date_send_renewal.format("YYYY-MM-DD HH:mm:ss")
    return date_send_renewal_str


def format_order_display_user(order: dict, status: str = "active"):
    """
    Orders are displayed differently for the user
    """
    if status == "active":
        order["order_status_human"] = "Tilgængelig"
    if status == "reserved":
        order["order_status_human"] = ORDER_STATUS_USER_HUMAN.get(order["order_status"])

    return order


def format_log_display(log: dict):
    """
    Format dates in log for display. Change from UTC to Europe/Copenhagen
    """
    updated_location = RECORD_LOCATION_HUMAN.get(log["updated_location"], "")
    update_order_status = ORDER_STATUS_HUMAN.get(log["updated_order_status"], "")
    log["updated_location"] = updated_location
    log["updated_order_status"] = update_order_status

    # convert created_at to danish timezone
    log["updated_at"] = format_order_display(log)["updated_at"]

    return log


def get_lb_number(record_and_types: dict) -> str:
    admin_data = record_and_types.get("admin_data", {}).get("value", [])
    if admin_data and isinstance(admin_data, list):
        first_admin_data = admin_data[0]
        box = first_admin_data.get("Æske")
        if box:
            return box
        lbnr = first_admin_data.get("MeE_Lbnr")
        if lbnr:
            return lbnr
    return ""


def get_expire_at_date() -> str:
    """
    Get a expire_at date
    Set this on a order when the order is status is ORDERED and location is READING_ROOM
    """
    utc_now = arrow.utcnow()
    # expire_at will look like this: 2025-02-08 00:00:00
    # The extra day is added to make sure at least one full day is available
    expire_at = utc_now.floor("day").shift(days=DEADLINE_DAYS + 1)
    return expire_at.format("YYYY-MM-DD HH:mm:ss")


def get_current_date_time() -> str:
    return arrow.utcnow().format("YYYY-MM-DD HH:mm:ss")


async def send_order_message(title: str, message: str, order: dict):
    """
    Send a mail to the user when the order is ready for review
    """

    template_values = {
        "title": title,
        "message": message,
        "order": order,
        "client_domain_url": settings["client_url"],
        "client_name": settings["client_name"],
    }

    html_content = await get_template_content("mails/order_mail.html", template_values)
    reply_to_email = settings["client_email_orders_reply_to"] if settings.get("client_email_orders_reply_to") else settings["client_email"]

    mail_dict = {
        "data": {
            "user_id": order["user_id"],
            "subject": title,
            "sender": {"email": settings["client_email"], "name": settings["client_name"]},
            "reply_to": {"email": reply_to_email, "name": settings["client_name"]},
            "html_content": html_content,
            "text_content": html_content,
        }
    }

    await api.mail_post(mail_dict)
    log.info(f"Sent mail message: {message} Order: {order['order_id']}")
