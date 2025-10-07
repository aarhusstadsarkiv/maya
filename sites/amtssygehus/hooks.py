from maya.core.logging import get_log
from maya.core.hooks_spec import HooksSpec
from maya.records import record_utils


log = get_log()


def _alter_search_url(main_menu_top: dict) -> dict:
    """
    Alter the search url in the main menu top.
    This is done to avoid that the search url is changed in the main menu top.
    """
    for item in main_menu_top:
        if item.get("name") == "search_get":
            item["url"] = "/search"
            break
    return main_menu_top


class Hooks(HooksSpec):
    def __init__(self, request):
        super().__init__(request)

    async def before_context(self, context: dict) -> dict:
        """
        Alter the context dictionary. Before the context is returned to the template.
        """
        context["meta_title"] = context["meta_title"] + " | AmtssygehusArkivet"

        try:
            main_menu_top = context["main_menu_top"]
            main_menu_top = _alter_search_url(main_menu_top)

            search_result = context["search_result"]["result"]
            for result in search_result:
                if result.get("thumbnail") and result.get("portrait"):
                    result["thumbnail"] = result["portrait"]
        except KeyError:
            pass

        return context

    async def before_get_search(self, query_params: list) -> list:
        """
        Alter the search query params. Before the search is executed.
        This example removes all curators from the query params and adds Aarhus Teater as curator (4).
        """
        # Remove all curators from the query params and add curator (4)
        query_params = [(key, value) for key, value in query_params if key != "organisations"]
        query_params.append(("organisations", "111356"))

        # online
        # query_params.append(("availability", "4"))
        # images
        # query_params.append(("content_types", "61"))

        return query_params

    async def after_get_search(self, query_params: list) -> list:
        """
        Alter the search query params. After the search is executed.
        This example removes all curators from the query params.
        This is done to avoid that the curator added in the before_search method is added to filters and search cookie.
        """
        # organisations=107434
        query_params = [(key, value) for key, value in query_params if key != "organisations"]

        # online
        # query_params = [(key, value) for key, value in query_params if key != "availability"]
        # images
        # query_params = [(key, value) for key, value in query_params if key != "content_types"]

        return query_params

    async def after_get_record(self, record: dict, meta_data: dict) -> tuple:
        """
        Alter the record and meta_data dictionaries after the api call
        """
        # sejrs sedler
        if record_utils.is_collection(record, 1):
            meta_data["title"] = ""
            meta_data["record_type"] = "sejrs_sedler"
            meta_data["representation_text"] = record.get("summary", "")
            if record.get("summary"):
                del record["summary"]
            else:
                record_id = record.get("id")
                assert isinstance(record_id, str)
                extra = {"error_code": 499, "error_url": record_utils.get_record_url(record_id)}
                log.error("Sejrs sedler should have a summary", extra=extra)

        # teater arkivet
        if record_utils.is_curator(record, 4):
            if record.get("summary"):
                meta_data["title"] = f"[{record['summary']}]"

        return record, meta_data
