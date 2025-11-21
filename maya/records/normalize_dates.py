"""
Normalize a date in a strange way.
Copy of the original code.
"""

from maya.core.translate import translate
from maya.core.logging import get_log
from maya.core.date_format import date_format_day


log = get_log()


def _split_date_str(date: str) -> str:
    """
    Alter a string date like 19570101 into 1957-01-01
    """
    return f"{date[0:4]}-{date[4:6]}-{date[6:8]}"


def split_date_strings(record: dict) -> dict:
    """
    Split date strings in a record
    """
    if "date_from" in record:
        record["date_from"] = _split_date_str(record["date_from"])
    if "date_to" in record:
        record["date_to"] = _split_date_str(record["date_to"])
    return record


def _iso_8601_date(date_string: str) -> str:
    """
    Convert date strings from ISO 8601 dates as  'YYYY-MM-DD'
    to a more human readable format as 1. January 2020 (but in Danish)
    """
    # check if format is yyyy-mm-dd
    if len(date_string) == 10:
        return date_format_day(date_string)

    return date_string


def _extract_dates(record: dict) -> tuple:
    """
    Extracts 'date_from' and 'date_to' from the record dictionary and return them as a tuple.
    """
    date_from = record.get("date_from")
    date_to = record.get("date_to")
    return (date_from, date_to)


def normalize_dates(record: dict) -> dict:
    """
    Takes a record and returns a formatted date string.
    """
    date_tuple = _extract_dates(record)
    date_from, date_to = date_tuple

    if date_from and date_to:
        # same date
        if date_from == date_to:
            date_string = _iso_8601_date(date_from)
        # year string
        elif date_from[:4] == date_to[:4] and date_from[5:10] == "01-01":
            date_string = date_from[:4]
        # year string with interval
        elif date_from[5:10] == "01-01" and date_to[5:10] == "12-31":
            date_string = f"{date_from[:4]} ~ {date_to[:4]}"
        else:
            # date interval
            date_string = f"{_iso_8601_date(date_from)} ~ {_iso_8601_date(date_to)}"
    elif date_from:
        date_string = f"{_iso_8601_date(date_from)} ~"
    elif date_to:
        date_string = f"~ {_iso_8601_date(date_to)}"
    else:
        date_string = translate("No Date")

    record["date_normalized"] = date_string
    return record
