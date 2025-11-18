""""
Entities endpoints
"""

from starlette.requests import Request
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse, PlainTextResponse
from maya.core.templates import templates
from maya.core.context import get_context
from maya.core.logging import get_log
from maya.core.auth import is_authenticated
from maya.core import flash
from maya.core import api
import json
import asyncio


log = get_log()


async def entities_create(request: Request):
    await is_authenticated(request, permissions=["employee"])
    try:
        schema = await api.schema_get(request)
        context_values = {"title": "Opret entitet", "schema": schema}
        context = await get_context(request, context_values=context_values)
        return templates.TemplateResponse(request, "entities/entities_create.html", context)

    except Exception as e:
        log.exception("Error in entities_create")
        raise HTTPException(500, detail=str(e), headers=None)


async def entities_update(request: Request):
    await is_authenticated(request, permissions=["employee"])

    uuid = request.path_params["uuid"]
    entity = await api.entity_get(request)

    schema_name, schema_version = api.schema_get_name_version_from_entity(entity)
    schema = await api.schema_get_by_name_version(request, schema_name, schema_version)
    schema_latest = await api.schema_get_latest(request, schema_name)

    is_lastest_schema = False
    if schema["name"] == schema_latest["name"] and schema["version"] == schema_latest["version"]:
        is_lastest_schema = True

    context_values = {
        "title": "Opdater entitet",
        "schema": schema,
        "schema_latest": schema_latest,
        "entity": entity,
        "is_lastest_schema": is_lastest_schema,
        "uuid": uuid,
    }

    context = {"context": context_values}
    context = await get_context(request, context_values=context)

    return templates.TemplateResponse(request, "entities/entities_update.html", context)


async def entities_patch(request: Request):
    await is_authenticated(request, permissions=["employee"])
    try:
        await api.entity_patch(request)
        flash.set_message(request, "Entitet opdateret", type="success")
        return JSONResponse({"message": "Entitet opdateret", "error": False})

    except Exception:
        log.info("Entity update error", exc_info=True)
        return JSONResponse({"message": "Entitet kunne ikke opdateres", "error": True})


async def entities_delete(request: Request):
    await is_authenticated(request, permissions=["employee"])
    if request.method == "DELETE":
        delete_type = request.path_params["delete_type"]
        try:
            await api.entity_delete(request, "hard")
            flash.set_message(request, f"Entitet er slettet '{delete_type}'", type="success")
            return JSONResponse({"message": f"Entitet er slettet '{delete_type}", "error": False})

        except Exception:
            log.info("Entity delete error", exc_info=True)
            return JSONResponse({"message": "Entitet kunne ikke slettes. Måske den allerede er slettet.", "error": True})

    try:
        entity = await api.entity_get(request)
        uuid = request.path_params["uuid"]
        context_values = {"title": "Slet entitet", "uuid": uuid, "entity": entity}
        context = await get_context(request, context_values=context_values)
        return templates.TemplateResponse(request, "entities/entities_delete_soft.html", context)

    except Exception as e:
        log.exception("Error in entities_delete")
        raise HTTPException(500, detail=str(e), headers=None)


async def entities_post(request: Request):
    await is_authenticated(request, permissions=["employee"])
    try:
        await api.entity_post(request)
        flash.set_message(request, "Entitet oprettet", type="success")
        return JSONResponse({"message": "Entitet oprettet", "error": False})

    except Exception:
        log.info("Entity create error", exc_info=True)
        return JSONResponse({"message": "Entitet kunne ikke oprettes", "error": True})


async def entities_get_list(request: Request):
    await is_authenticated(request, permissions=["employee"])
    try:
        entities, schemas = await asyncio.gather(api.entities_get(request), api.schemas(request))

        # sort entities by timestamp string like: 2023-11-02T12:39:32.049975+00:00
        entities = sorted(entities, key=lambda k: k["timestamp"], reverse=True)

        # remove from entities if property 'is_soft_deleted' is True
        entities = [entity for entity in entities if not entity["is_soft_deleted"]]

        # remove from entities if property 'is_hard_deleted' is True
        entities = [entity for entity in entities if not entity["is_hard_deleted"]]

        context_values = {"title": "Entiteter", "schemas": schemas, "entities": entities}
        context = await get_context(request, context_values=context_values)
        return templates.TemplateResponse(request, "entities/entities_list.html", context)

    except Exception as e:
        log.exception("Error in entities_get_list")
        raise HTTPException(500, detail=str(e), headers=None)


def _get_types_and_values(schema, entity):
    """
    This function adds the values from the entity to the schema
    """
    schema_and_values = schema["data"]["properties"]
    data_and_values = {}

    for key, value in schema_and_values.items():
        try:
            type = value["_meta"]["type"]
            entity_value = entity["data"][key]
            label = value.get("title", key)

            # don't display empty values
            if not entity_value:
                continue

            data_and_values[key] = {"type": type, "name": key, "value": entity_value, "label": label}

        except KeyError:
            pass

    return data_and_values


async def entities_get_single(request: Request):
    """
    Get single entity endpoint. Not protected, as entities are public.
    """
    entity: dict = await api.entity_get(request)
    schema_name, schema_version = api.schema_get_name_version_from_entity(entity)

    schema = await api.schema_get_by_name_version(request, schema_name, schema_version)
    types_and_values = _get_types_and_values(schema, entity)

    context_values = {
        "title": types_and_values["display_label"]["value"],
        "types_and_values": types_and_values,
        "entity": entity,
        "schema": schema,
    }
    context = await get_context(request, context_values=context_values)
    return templates.TemplateResponse(request, "entities/entities_single.html", context)


async def entities_get_single_json(request: Request):
    """
    Get single entity as JSON endpoint. Not protected, as entities are public.
    """
    type = request.path_params["type"]
    entity: dict = await api.entity_get(request)
    schema_name, schema_version = api.schema_get_name_version_from_entity(entity)

    schema = await api.schema_get_by_name_version(request, schema_name, schema_version)
    types_and_values = _get_types_and_values(schema, entity)

    if type == "types_and_values":
        json_encoded = json.dumps(types_and_values, indent=4, ensure_ascii=False)
    elif type == "entity":
        json_encoded = json.dumps(entity, indent=4, ensure_ascii=False)
    elif type == "schema":
        json_encoded = json.dumps(schema, indent=4, ensure_ascii=False)
    else:
        raise HTTPException(404, detail="Not found", headers=None)

    return PlainTextResponse(json_encoded)
