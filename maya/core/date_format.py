"""
This module provides utility functions for working with dates and times

Functions included:
- timezone_alter: Converts a UTC timestamp string to a specified timezone (default is Europe/Copenhagen).
- date_format: Formats a datetime string into Danish date-time format (e.g., "19. november 2024 13:45").
- date_format_day: Formats a date string into Danish date-only format (e.g., "19. november 2024").
"""

import arrow
from maya.core.logging import get_log

log = get_log()


def timezone_alter(utc_timestamp: str, target_timezone: str = "Europe/Copenhagen") -> str:
    """
    Convert utc timestamp to a target timezone
    E.g. convert a SQL timestamp like '2024-11-19 11:25:58' to 'Europe/Copenhagen' and get e.g. '2024-11-19 12:25:58'
    """
    try:
        utc_dt = arrow.get(utc_timestamp, "YYYY-MM-DD HH:mm:ss").replace(tzinfo="UTC")
        target_dt = utc_dt.to(target_timezone)
        return target_dt.format("YYYY-MM-DD HH:mm:ss")
    except Exception:
        log.exception("Error in timezone_alter")
        return utc_timestamp


def date_format(date_string: str) -> str:
    """
    Format a date string to a Danish format
    """
    try:
        date_string = _sanitize_date_string(date_string)
        date = arrow.get(date_string, "YYYY-MM-DDTHH:mm:ss")
        return date.format("D. MMMM YYYY HH:mm", locale="da")
    except Exception:
        log.exception("Error in date_format")
        return date_string


def date_format_day(date_string: str) -> str:
    """
    Format a date string to a Danish format
    """
    try:
        date = arrow.get(date_string, "YYYY-MM-DD")
        # Use strftime with Danish locale
        return date.format("D. MMMM YYYY", locale="da")
    except Exception:
        log.exception("Error in date_format_day")
        return date_string


def _sanitize_date_string(date_string: str) -> str:
    """
    Remove microseconds from date string
    so that it can be parsed properly
    """
    if "." in date_string:
        return date_string.split(".")[0]
    return date_string
