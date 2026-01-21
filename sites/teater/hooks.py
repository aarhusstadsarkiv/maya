from maya.core.logging import get_log
from maya.core.hooks_spec import HooksSpec
from maya.core import api
from maya.core.relations import format_relations, sort_data
from maya.endpoints.endpoints_search import get_search_context_values, set_response_cookie, get_size_sort_view
import asyncio
from starlette.responses import HTMLResponse
from maya.records import record_utils
from starlette.exceptions import HTTPException

log = get_log()


def _alter_people(context: dict) -> dict:
    """
    Alter people so that search_query from e.g 'search_query': 'people=107465' to /people/107465
    But add the query_display_str to the context so that it can be displayed in the template.
    """
    try:
        people_id = context["request"].path_params["id"]
        people_id = people_id.lstrip("0")
        context["query_str_display"] = "people=" + people_id

    except KeyError:
        log.exception("KeyError")

    return context


def _alter_events(context: dict) -> dict:
    """
    Alter events so that search_query from e.g 'search_query': 'events=107465' to /events/107465
    But add the query_display_str to the context so that it can be displayed in the template.
    """

    # get seoncd path params from self.request
    try:
        event_id = context["request"].path_params["id"]
        event_id = event_id.lstrip("0")
        context["query_str_display"] = "events=" + event_id

    except KeyError:
        log.exception("KeyError")

    return context


def _alter_record(context: dict) -> dict:

    try:
        people = context["record_and_types"]["people"]["value"]
        for person in people:
            person["search_query"] = "/people/" + str(person["id"])
    except KeyError:
        pass

    try:
        events = context["record_and_types"]["events"]["value"]
        for event in events:
            event["search_query"] = "/events/" + str(event["id"])
    except KeyError:
        pass

    return context


class Hooks(HooksSpec):

    search_context = {}
    query_str_display = ""

    def __init__(self, request):
        super().__init__(request)
        self.curator = "4"

    async def before_get_auto_complete(self, query_params: list) -> list:
        query_params.append(("auto_group", "2"))
        query_params.append(("limit", "25"))

        """
        Alter the query params before the autocomplete is executed.
        """
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
        context["meta_title"] = context["meta_title"] + " | Aarhus Teaters Arkiv"
        if context["identifier"] == "people":
            context = _alter_people(context)
        if context["identifier"] == "events":
            context = _alter_events(context)
        if context["identifier"] == "record":
            context = _alter_record(context)

        return context

    async def before_get_search(self, query_params: list) -> list:
        """
        Alter the search query params. Before the search is executed.
        This example removes all curators from the query params and adds Aarhus Teater as curator (4).
        """
        # Remove all curators from the query params and add curator (4)
        query_params = [(key, value) for key, value in query_params if key != "curators"]
        query_params.append(("curators", "4"))

        return query_params

    async def after_get_search(self, query_params: list) -> list:
        """
        Alter the search query params. After the search is executed.
        This example removes all curators from the query params.
        This is done to avoid that the curator added in the before_search method is added to filters and search cookie.
        """
        query_params = [(key, value) for key, value in query_params if key != "curators"]

        return query_params

    async def _alter_types_people_events(self, type: str, resource: dict) -> dict:
        """
        Add relations and search results to people and events.
        """
        id = resource["id"]

        # Set ext data
        if "ext_data" in resource:
            ext_data = resource["ext_data"]
            for key in ext_data:
                resource["ext_data_" + key] = ext_data[key]

        # set date_from_premier
        if type == "events" and "date_from" in resource:
            resource["date_from_premier"] = resource["date_from"]

        if type == "people":
            query_params = [("people", id), ("size", "10")]
        if type == "events":
            query_params = [("events", id), ("size", "10")]

        _, _, view = get_size_sort_view(self.request)
        query_params.append(("view", view))

        # fetch search result and relations
        search_context, relations = await asyncio.gather(
            get_search_context_values(self.request, extra_query_params=query_params),
            api.proxies_get_relations(self.request, type, id),
        )

        Hooks.search_context = search_context

        search_result = search_context["search_result"]
        relations_formatted = format_relations(type, relations)

        # sort
        if type == "people":
            relations_formatted = sort_data(relations_formatted, "display_label")
        if type == "events":
            relations_formatted = sort_data(relations_formatted, "rel_label")

        resource["relations"] = relations_formatted
        resource["search_result"] = search_result

        return resource

    async def after_get_resource(self, type: str, resource: dict) -> dict:
        """
        Alter the entity json is returned from the proxies api.
        """

        if type == "people" or type == "events":
            resource = await self._alter_types_people_events(type, resource)
        return resource

    async def before_response(self, response: HTMLResponse) -> HTMLResponse:
        """
        This is a small hack in order to set the search cookie on people and events pages.
        So we can browse the inline search results as a normal search.
        """
        if "endpoint" not in self.request.scope:
            return response

        # Ignore static files
        if not hasattr(self.request.scope["endpoint"], "__name__"):
            return response

        route_name = self.request.scope["endpoint"].__name__
        if route_name == "get_resource":
            """
            Before the response is returned to the template.
            """
            resource_type = self.request.path_params["resource_type"]
            # only set cookie on 'people' and 'events' because we know a search has been performed
            alter_response_on = ["people", "events"]
            if resource_type in alter_response_on:
                set_response_cookie(response, Hooks.search_context)

        return response

    async def after_get_record(self, record: dict, meta_data: dict) -> tuple:
        if not record_utils.is_curator(record, 4):
            raise HTTPException(404)
        return record, meta_data
