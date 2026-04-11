from maya.core import api
from maya.core.dynamic_settings import settings
from maya.core.logging import get_log
from maya.core.templates import get_template_content
from maya.database import utils_orders

log = get_log()


async def send_ready_orders_message(title: str, orders: list[dict]):
    """
    Send a mail to the user when one or more orders are ready for review.
    """
    if not orders:
        raise ValueError("orders must contain at least one order")

    first_order = orders[0]
    user_ids = {order["user_id"] for order in orders}
    if len(user_ids) != 1:
        raise ValueError("orders must belong to the same user")

    template_values = {
        "title": title,
        "orders": orders,
        "client_domain_url": settings["client_url"],
        "client_name": settings["client_name"],
    }

    html_content = await get_template_content("mails/order_mail.html", template_values)
    reply_to_email = settings["client_email_orders_reply_to"] if settings.get("client_email_orders_reply_to") else settings["client_email"]

    mail_dict = {
        "data": {
            "user_id": first_order["user_id"],
            "subject": title,
            "sender": {"email": settings["client_email"], "name": settings["client_name"]},
            "reply_to": {"email": reply_to_email, "name": settings["client_name"]},
            "html_content": html_content,
            "text_content": html_content,
        }
    }

    await api.mail_post(mail_dict)
    log.info(f"Sent ready mail Orders: {[order['order_id'] for order in orders]}")


async def send_renew_order_message(title: str, orders: list[dict]):
    """
    Send a renewal mail covering multiple orders for the same user.
    """
    if not orders:
        raise ValueError("orders must contain at least one order")

    first_order = orders[0]
    user_ids = {order["user_id"] for order in orders}
    if len(user_ids) != 1:
        raise ValueError("orders must belong to the same user")

    template_values = {
        "title": title,
        "orders": orders,
        "client_domain_url": settings["client_url"],
        "renew_orders_url": f'{settings["client_url"]}/auth/orders/active',
        "deadline_days": utils_orders.DEADLINE_DAYS_RENEWAL,
        "client_name": settings["client_name"],
    }

    html_content = await get_template_content("mails/order_renew_mail.html", template_values)
    reply_to_email = settings["client_email_orders_reply_to"] if settings.get("client_email_orders_reply_to") else settings["client_email"]

    mail_dict = {
        "data": {
            "user_id": first_order["user_id"],
            "subject": title,
            "sender": {"email": settings["client_email"], "name": settings["client_name"]},
            "reply_to": {"email": reply_to_email, "name": settings["client_name"]},
            "html_content": html_content,
            "text_content": html_content,
        }
    }

    await api.mail_post(mail_dict)
    log.info(f"Sent renewal mail Orders: {[order['order_id'] for order in orders]}")
