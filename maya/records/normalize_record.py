"""
Normalize record data from the API to a more sane data structure
"""

from maya.core.logging import get_log
import urllib.parse
from maya.records.record_definitions import get_record_definitions
from maya.core.dynamic_settings import settings
from maya.core import cookie
from starlette.requests import Request

log = get_log()

_record_definitions = get_record_definitions()
_search_base_url = settings["search_base_url"]


class RecordNormalizer:
    def __init__(self):
        self.search_query_params = []

    def normalize_record_data(self, request: Request, record: dict, meta_data: dict):
        """
        Normalize record data to a more sane data structure.
        """

        self.search_query_params = cookie.get_search_query_params(request)

        record = self._normalize_dict_data(record)
        record = self._normalize_series(record)
        record = self._normalize_content_types(record)
        record = self._normalize_subjects(record)
        record = self._normalize_labels(record)
        record = self._normalize_resources(record)

        link_list = self._get_list_of_type("link_list")
        link_list.remove("collection_tags")
        record = self._normalize_link_lists(link_list, record)

        link_dict = self._get_list_of_type("link_dict")
        record = self._normalize_link_dicts(link_dict, record)

        record = self._normalize_collection_tags(record)
        record = self._normalize_representations(record, meta_data)

        return record

    def _normalize_search_query(self, search_str: str):
        """
        Normalizes the search query by filtering and combining parameters.
        The commented out code is extending the search query with new parameters
        found in the query string. This is not used in the current implementation.
        """

        return search_str, True

        search_query_params = list(self.search_query_params)
        query_str = search_str.split("?")[1]

        link_query_list = [tuple(query.split("=")) for query in query_str.split("&")]

        display_as_link = False
        for link_query in link_query_list:
            if link_query not in search_query_params:
                search_query_params.append(link_query)
                display_as_link = True

        search_str = "/search?"
        for link_query in search_query_params:
            search_str += f"{link_query[0]}={link_query[1]}&"

        return search_str, display_as_link

    def _normalize_representations(self, record: dict, meta_data: dict):
        if "representations" in record:
            # Check if the record type is not "web_document" or "image"
            is_invalid_type = record["representations"]["record_type"] not in ["web_document", "image"]

            # Check if the meta_data indicates it's not downloadable
            is_not_downloadable = not meta_data["is_downloadable"]

            if is_invalid_type or is_not_downloadable:
                del record["representations"]

        return record

    def _normalize_series(self, record: dict):
        """
        create a normalized series list with URL queries for each series

        "series": [
            {
                "label": "Personalsedler"
            },
            {
                "label": "V"
            }
        ],

        """

        if "series" in record and "collection" in record:
            """
            Add search_query to each series
            """
            series = record["series"]

            last_label = ""
            series_normalized = []
            for serie in series:
                label = last_label + serie["label"]
                last_label = label + "/"

                search_query = f"{_search_base_url}?collection={str(record['collection']['id'])}&series={label}"
                search_query, display_as_link = self._normalize_search_query(search_query)
                serie["search_query"] = search_query
                serie["display_as_link"] = display_as_link
                series_normalized.append(serie)

            record["series"] = [series_normalized]

        if "series" in record and "collection" not in record:
            del record["series"]  # some series exist where there is no collection. Remove these as they are not searchable
        return record

    def _normalize_content_types(self, record: dict):
        """
        Add search query to each content type
        """
        if "content_types" in record:
            content_types_list = record["content_types"]
            for content_type in content_types_list:
                for item in content_type:
                    search_query = f"{_search_base_url}?content_types={str(item['id'])}"
                    search_query, diplay_as_link = self._normalize_search_query(search_query)
                    item["search_query"] = search_query
                    item["display_as_link"] = diplay_as_link

            record["content_types"] = content_types_list
        return record

    def _normalize_subjects(self, record: dict):
        """
        Add search query to each subject
        """
        if "subjects" in record:
            subjects = record["subjects"]
            for subject in subjects:
                for item in subject:
                    search_query = f"{_search_base_url}?subjects={str(item['id'])}"
                    search_query, display_as_link = self._normalize_search_query(search_query)
                    item["search_query"] = search_query
                    item["display_as_link"] = display_as_link

        return record

    def _normalize_collection_tags(self, record: dict):
        """
        Add search query to each collection tag
        """

        collection_tags = []

        try:
            collection_id: int = record["collection"]["id"]
        except KeyError:
            return record

        if "collection_tags" in record:
            collection_tags = record["collection_tags"]

            for tag in collection_tags:
                query_str = str(urllib.parse.quote(tag["path"]))
                search_query = f"{_search_base_url}?collection={str(collection_id)}&collection_tags={query_str}"
                search_query, display_as_link = self._normalize_search_query(search_query)
                tag["search_query"] = search_query
                tag["display_as_link"] = display_as_link

            record["collection_tags"] = collection_tags

        return record

    def _normalize_dict_data(self, record: dict):
        """
        Transform dict value data to list of dict data. Then there is only one data structure to handle
        """
        if "admin_data" in record:
            record["admin_data"] = [record["admin_data"]]

        if "desc_data" in record:
            record["desc_data"] = [record["desc_data"]]
        return record

    def _normalize_labels(self, record: dict):
        if "desc_data" in record and "source" in record["desc_data"]:
            record["desc_data"]["Kilde"] = record["desc_data"]["source"]
            del record["desc_data"]["source"]

        return record

    def _normalize_resources(self, record: dict):
        """Transform resources to a more sane data structure: Same as content_types"""
        if "resources" in record:
            resources = record["resources"]
            item_dict_list = []
            for item_dict in resources:
                # move type to type
                item_dict = dict(sorted(item_dict.items(), key=lambda item: item[0] != "type"))
                item_dict_list.append(item_dict)

            record["resources"] = item_dict_list
        return record

    def _normalize_link_lists(self, keys, record: dict):
        """add search_query to each link_list given in keys list"""
        for key in keys:
            if key in record:
                for item in record[key]:
                    search_query = f"{_search_base_url}?{key}={str(item['id'])}"
                    search_query, display_as_link = self._normalize_search_query(search_query)
                    item["search_query"] = search_query
                    item["display_as_link"] = display_as_link
        return record

    def _normalize_link_dicts(self, keys, record: dict):
        """add search_query to each link_dict given in keys list"""
        for key in keys:
            if key in record:
                item = record[key]
                search_query = f"{_search_base_url}?{key}={str(item['id'])}"
                search_query, display_as_link = self._normalize_search_query(search_query)
                item["search_query"] = search_query
                item["display_as_link"] = display_as_link
        return record

    def _get_list_of_type(self, type: str):
        """get a list of a type, e.g. string from record_definitions"""
        type_list = []
        for key, item in _record_definitions.items():  # type: ignore
            if item["type"] == type:
                type_list.append(key)

        return type_list
