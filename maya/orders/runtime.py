from maya.core.dynamic_settings import settings
from maya.core.logging import get_custom_log, get_log

log = get_log()
cron_log = get_custom_log("cron")


try:
    orders_url = settings["sqlite3"]["orders"]
except KeyError:
    orders_url = ""
