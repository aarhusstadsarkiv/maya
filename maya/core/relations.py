"""
Module for formatting and sorting relation data obtained from the Proxies API.

It is used primarily in the context of theater archives (tearterakivet) to manage
relation entries such as actors and their roles in productions. The module provides

This module provides utility functions for handling relation data. It includes tools for separating onstage and offstage
roles based on their labels, as well as custom sorting logic to handle inconsistent
or missing date information in the dataset.

Functions:
- format_relations(type: str, relations: list):
    Separates relation entries into onstage and offstage groups based on naming patterns.

- sort_data(data: list, key: str):
    Sorts a list of relation groups by a specified key, with special handling for
    extracting year values from textual labels.

- _sort_by_value(list_of_dicts: list, key_name: str, default=None):
    Sorts a list of dictionaries by the value of a specified key, using a default if needed.
"""

import re

from maya.core.logging import get_log

log = get_log()
MISSING_ENTITY = "MISSING_ENTITY"


def _replace_missing_relation_value(item: dict, key: str, error_url: str | None = None) -> str:
    value = item.get(key)
    if value is not None:
        return value

    item[key] = MISSING_ENTITY
    log.error(
        f"Missing relation value for {key} on relation id={item.get('id')} rel_id={item.get('rel_id')}",
        extra={
            "error_code": 499,
            "error_type": "MissingRelationValue",
            "error_url": error_url,
        },
    )
    return MISSING_ENTITY


def format_relations(type: str, relations: list, error_url: str | None = None):
    """
    Format relations obtained from the proxies api.
    Used with tearterakivet
    """

    onstage = []
    offstage = []
    for rel in relations:
        label = _replace_missing_relation_value(rel, "rel_label", error_url)
        if label.startswith("Skuespiller") and label.find("("):
            start_index = label.find("(") + 1
            rel["rel_label"] = label[start_index:-1]
            onstage.append(rel)
        elif label.startswith("Skuespiller") or label.startswith("Statist"):
            onstage.append(rel)
        else:
            offstage.append(rel)

    return [
        {"label": "Sceneroller", "data": onstage},
        {"label": "Produktion", "data": offstage},
    ]


def sort_data(data: list, key: str, error_url: str | None = None):
    """
    Sorting is a mess. Sometimes "rel_date_from" is present when sorting by a date
    and sometime is is not. Best way to sort is to extract the year from the display_label.
    """

    def get_sort_key(item: dict):
        if key == "rel_label":
            return _replace_missing_relation_value(item, "rel_label", error_url)
        elif key == "display_label":
            # Extract year from display_label, if present
            display_label = _replace_missing_relation_value(item, "display_label", error_url)
            match = re.search(r"(\d{4})", display_label)
            year = int(match.group(1)) if match else float("inf")  # Set to infinity if no year present
            return (year, display_label)
        return ("",)  # Default return value

    sorted_data = []
    for section in data:
        if "data" in section:
            section["data"] = sorted(section["data"], key=get_sort_key)
        sorted_data.append(section)

    return sorted_data


def _sort_by_value(list_of_dicts: list, key_name: str, default=None):
    decorated = [(dict_.get(key_name, default), dict_) for dict_ in list_of_dicts]
    return [dict_ for (key, dict_) in decorated]
