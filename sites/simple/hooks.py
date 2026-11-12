from maya.core.hooks_spec import HooksSpec
from maya.records.record_utils import is_curator, is_collection


class Hooks(HooksSpec):

    async def before_get_auto_complete(self, query_params: list) -> list:
        """
        Alter the query params before the autocomplete is executed.
        """
        query_params.append(("limit", "25"))  # default limit
        return query_params

    async def after_get_auto_complete(self, query_params: list) -> list:
        """
        Alter the query params after the autocomplete is executed.
        """
        return query_params

    async def before_context(self, context: dict) -> dict:
        """
        Alter the context dictionary. Before the context is returned to the template.
        """
        context["meta_title"] = context["meta_title"] + " | SimpleConfig"

        return context

    async def after_get_record(self, record: dict, meta_data: dict) -> tuple:
        """
        Alter the record and meta_data dictionaries after the api call
        """
        if is_collection(record, 1):
            meta_title = f"[{record['summary'][:60]} ... ]"
            meta_data["meta_title"] = meta_title
            meta_data["record_type"] = "sejrs_sedler"

            meta_data["representation_text"] = record["summary"]
            del record["summary"]

        if is_curator(record, 4):
            if record.get("summary"):
                title = record["summary"]
                meta_data["title"] = f"[{title}]"
                meta_data["meta_title"] = f"[{title}]"

        return record, meta_data

    async def after_get_record_and_types(self, record: dict, record_and_types: dict) -> tuple:
        """
        Alter the record and meta_data dictionaries after the api call
        """
        return record, record_and_types

    async def before_get_search(self, query_params: list) -> list:
        """
        Alter the search query params. Before the search is executed.
        This example only shows online images (content_type 61) and available online (availability 4)
        """

        # This site's availability restriction replaces the user's selection.
        query_params = [(key, value) for key, value in query_params if key not in {"availability", "-availability"}]
        content_types = [value for key, value in query_params if key == "content_types"]
        if "61" not in content_types:
            query_params.append(("content_types", "61"))

        query_params.append(("availability", "4"))

        return query_params

    async def after_get_search(self, query_params: list) -> list:
        """
        Alter the search query params. After the search is executed.
        Remove content_type 61 and availability 4 so that we don't see them as filters
        These filters are hidden.
        """
        # remove content_type 61 as this should not be shown in the filters
        query_params = [(key, value) for key, value in query_params if key != "content_types" or value != "61"]

        # remove availability 4 as this should not be shown in the filters
        query_params = [(key, value) for key, value in query_params if key != "availability" or value != "4"]

        return query_params

    async def after_get_resource(self, type: str, resource: dict) -> dict:
        """
        Alter the json returned from the proxies api.
        """
        return resource
