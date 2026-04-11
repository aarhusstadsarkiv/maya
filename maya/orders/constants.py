from dataclasses import dataclass

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
