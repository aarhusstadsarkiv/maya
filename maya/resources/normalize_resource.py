"""
File contains functions for normalizing fields in resources,
e.g. linkify strings, set outer years, etc.
"""

from maya.core.logging import get_log
from maya.resources.resource_definitions import resource_definitions
from maya.core.translate import translate
import re
from urllib.parse import unquote
from maya.core.dynamic_settings import settings

_search_base_url = settings["search_base_url"]


log = get_log()


def get_link_list(name: str, value: list):
    """
    Get string list and convert to link list if string contains ';'
    Ignore if string does not contain ';'
    """
    link_list = []
    for item in value:
        item = item.strip()
        if item.find(";") == -1:
            continue

        link = _generate_semi_colon_link(name, item)
        link_list.append(link)

    return link_list


def set_sources_normalized(data: dict):
    """
    Set 'sources_normalized' field on dict
    """
    if "sources" in data:
        data["sources_normalized"] = _get_sources_normalized(data["sources"])

    return data


def set_outer_years(data: dict):
    """
    Set 'outer_years' field on dict
    """

    if data["schema"] != "collection":
        return data

    if "date_from" in data and "date_to" in data:
        outer_years = data["date_from"] + "-" + data["date_to"]
        data["outer_years"] = outer_years
    elif "date_from" in data:
        data["outer_years"] = data["date_from"]
    return data


def set_created_decommissioned(data: dict):
    """
    copy 'date_from' to 'date_created' and 'date_to' to 'date_decommissioned'
    This only applies to schema 'organisation'
    """

    if data["schema"] != "organisation":
        return data

    if "date_from" in data:
        data["date_created"] = data["date_from"]

    if "date_to" in data:
        data["date_decommissioned"] = data["date_to"]

    return data


def set_latitude_longitude(data: dict):
    """
    Set 'latitude_longitude_normalized' field on dict
    """
    if "latitude" in data and "longitude" in data:
        data["latitude_longitude_normalized"] = {
            "latitude": str(data["latitude"]),
            "longitude": str(data["longitude"]),
        }

    return data


def set_creators_link_list(data: dict, schema):
    """
    Set creator_link field on dict.
    """
    is_creator = data.get("is_creator")
    is_creative_creator = data.get("is_creative_creator")

    if is_creator and is_creative_creator:
        label_key = "creator" if schema == "person" else "organization"
        label = translate(f"See all records this {label_key} has created")

        data["creators_link"] = [
            {
                "search_query": f"{_search_base_url}?creators={data['id_real']}",
                "label": label,
            }
        ]

    return data


def set_collectors_link_list(data: dict, schema):
    """
    Set collectors_link field on dict.
    """
    is_creator = data.get("is_creator")

    if is_creator:
        label_key = "creator" if schema == "person" else "organization"
        label = translate(f"See all records this {label_key} has collected")

        data["collectors_link"] = [
            {
                "search_query": f"{_search_base_url}?collectors={data['id_real']}",
                "label": label,
            }
        ]

    return data


def set_persons_link_list(data: dict, schema):
    """
    Set person_link field on dict.
    """
    if schema == "person":
        data["persons_links"] = [
            {
                "search_query": f"{_search_base_url}?people={data['id_real']}",
                "label": translate("See all records about this person"),
            },
            {
                "search_query": f"{_search_base_url}?creators={data['id_real']}",
                "label": translate("See all records this person has created"),
            },
        ]

    return data


def alter_portrait_hightlights(resource: dict):
    if "portrait" in resource:
        resource["portrait"] = [_http_to_https(val) for val in resource["portrait"]]

    if "highlights" in resource:
        resource["highlights"] = [_http_to_https(val) for val in resource["highlights"]]

    return resource


def normalize_curators_collectors(resource: dict):
    string_list_or_link_list = [
        "collectors",
        "curators",
    ]

    for elem in string_list_or_link_list:
        if elem in resource:
            resource[elem] = get_link_list(elem, resource[elem])

    return resource


def get_resource_and_types(resource):
    """
    Get resource with types
    """
    resource_altered = {}
    resource_altered["meta"] = {}
    for key, value in resource.items():
        if not value:
            continue

        resource_item = {}
        resource_item["value"] = value
        resource_item["name"] = key

        try:
            definition = resource_definitions[key]
            resource_item["type"] = definition["type"]
            resource_item["label"] = translate("label_" + key)
            resource_altered[key] = resource_item

        except KeyError:
            # create meta dict
            if key in ["id_real", "schema"]:
                resource_altered["meta"][key] = value

    return resource_altered


def _get_sources_normalized(sources: list):
    """
    Generate sources_normalized for sources
    """
    sources_normalized = []
    for i in range(len(sources)):
        sources_normalized.append(_linkify_str(sources[i]))

    return sources_normalized


def _generate_semi_colon_link(name: str, value: str):
    query_id_or_label = value.split(";")
    query_id = query_id_or_label[0]
    label = query_id_or_label[1]

    return {
        "search_query": f"{_search_base_url}?{name}={query_id}",
        "label": f"{label}",
    }


def _http_to_https(url: str):
    if url.startswith("http://"):
        url = url.replace("http://", "https://")

    return url


def _linkify_str(text):
    pattern = r"(https?://\S+)"

    def replace_with_link(match):
        url = match.group(1)

        url = _http_to_https(url)

        decoded_url = unquote(url)
        return f'<a href="{url}">{decoded_url}</a>'

    return re.sub(pattern, replace_with_link, text)
