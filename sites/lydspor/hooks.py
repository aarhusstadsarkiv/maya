from maya.core.logging import get_log
from maya.core.hooks_spec import HooksSpec
from maya.records import record_utils
from maya.records import record_alter
import json

log = get_log()


class Hooks(HooksSpec):
    def __init__(self, request):
        super().__init__(request)

    async def before_get_auto_complete(self, query_params: list) -> list:
        query_params.append(("limit", "10"))

        """
        Alter the query params before the autocomplete is executed.
        """
        return query_params

    async def before_context(self, context: dict) -> dict:
        """
        Alter the context dictionary. Before the context is returned to the template.
        """
        context["meta_title"] = context["meta_title"] + " | Demo Client"

        return context

    async def before_get_search(self, query_params: list) -> list:
        """
        Alter the search query params. Before the search is executed.
        This example removes all curators from the query params and adds Aarhus Teater as curator (4).
        """
        # Remove all curators from the query params and add curator (4)
        query_params = [(key, value) for key, value in query_params if key != "admin_tags"]
        query_params.append(("admin_tags", "Lydspor"))

        return query_params

    async def after_get_search(self, query_params: list) -> list:
        """
        Alter the search query params. After the search is executed.
        This example removes all curators from the query params.
        This is done to avoid that the curator added in the before_search method is added to filters and search cookie.
        """
        query_params = [(key, value) for key, value in query_params if key != "admin_tags"]

        return query_params

    async def after_get_record(self, record: dict, meta_data: dict) -> tuple:
        """
        Alter the record and meta_data dictionaries after the api call
        """
        # sejrs sedler
        if record_utils.is_collection(record, 1):
            meta_data["title"] = ""
            meta_data["record_type"] = "sejrs_sedler"
            meta_data["representation_text"] = record["summary"]
            del record["summary"]

        # teater arkivet
        if record_utils.is_curator(record, 4):
            if record.get("summary"):
                meta_data["title"] = f"[{record['summary']}]"

        return record, meta_data

    async def after_get_record_and_types(self, record: dict, record_and_types: dict) -> tuple:
        if record_utils.is_collection(record, 48):
            agenda_items = record.get("admin_data", {}).get("agendaItems")

            if agenda_items:
                agenda_items = json.loads(agenda_items)
                agenda_items = _convert_agenda_items_to_link_list(agenda_items)
                record_alter.set_record_and_type(record_and_types, "agenda_items", agenda_items, "link_list")

            original_id = record.get("original_id")
            if original_id:
                record_alter.set_record_and_type(record_and_types, "original_id", original_id, "string")

        return record, record_and_types

    async def after_get_resource(self, type: str, resource: dict) -> dict:
        """
        Alter the entity json is returned from the proxies api.
        """
        return resource


def _convert_agenda_items_to_link_list(agenda_items: list) -> list:
    """
    Convert agenda items to link dictionary
    agenda items is a list of dicts, e.g.:
    [{"href": "https://storage.googleapis.com/openaws-webonly/19010523_149.pdf", "start_page": 1}]
    This will be converted to a type, 'link_list' that can be used in the templates
    """
    agenda_items_parsed = []
    for item in agenda_items:
        agenda_item = {}

        href = item.get("href")

        # from e.g. https://storage.googleapis.com/openaws-webonly/19010523_149.pdf get '19010523'
        date = href.split("/")[-1].split("_")[0]

        # convert to date: 1901-05-23
        date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"

        agenda_item["label"] = date
        agenda_item["search_query"] = item.get("href") + "#page=" + str(item.get("start_page", 1))
        agenda_items_parsed.append(agenda_item)
    return agenda_items_parsed
