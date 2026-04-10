from dataclasses import dataclass
from typing import Optional


@dataclass
class OrderFilter:
    """
    OrderFilter for seach
    filter_status can be: active, completed, order_history
    """

    filter_status: str = "active"
    filter_location: Optional[str] = ""
    filter_email: Optional[str] = ""
    filter_user: Optional[str] = ""
    filter_show_queued: Optional[str] = ""
    filter_limit: int = 100
    filter_offset: int = 0

    # Pagination
    filter_has_next: bool = False
    filter_has_prev: bool = False
    filter_next_offset: int = 0
    filter_prev_offset: int = 0
