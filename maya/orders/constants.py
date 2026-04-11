from dataclasses import dataclass

from maya.core.dynamic_settings import settings
from maya.database import utils_orders


@dataclass
class LogMessages:
    ORDER_CREATED: str = "Bestilling oprettet"
    ORDER_RENEWED: str = "Bestilling fornyet"
    STATUS_CHANGED: str = "Bruger status ændret"
    LOCATION_CHANGED: str = "Lokation ændret"
    MAIL_SENT: str = "Mail sendt"
    RENEWAL_SENT: str = "Mail fornyelse sendt"


LOG_MESSAGES = LogMessages()
SYSTEM_USER_ID = "SYSTEM"

MAIL_MESSAGE_ORDER_READY_TITLE = "Din bestilling er klar til gennemsyn"
MAIL_MESSAGE_ORDER_RENEW_TITLE = "Udløb af materiale"


def get_mail_message_order_renew() -> str:
    return f"""Din bestilling udløber om {utils_orders.DEADLINE_DAYS_RENEWAL} dage.<br>
Login og forny dit materiale på <a href="{settings.get("client_url", "")}/auth/orders/active">www.aarhusarkivet.dk</a>"""
