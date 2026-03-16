"""
File contains functions for altering resources,
e.g. set sources_normalized, set outer years, etc.
"""

from maya.core.logging import get_log
from maya.resources import normalize_resource

log = get_log()


def resource_alter(resource: dict):
    schema = resource["schema"]

    resource_orginal = resource.copy()

    relations = resource.get("relations")
    search_result = resource.get("search_result")

    resource = normalize_resource.set_created_decommissioned(resource)
    resource = normalize_resource.set_collectors_link_list(resource, schema)
    resource = normalize_resource.set_creators_link_list(resource, schema)
    resource = normalize_resource.set_persons_link_list(resource, schema)
    resource = normalize_resource.set_sources_normalized(resource)
    resource = normalize_resource.set_outer_years(resource)
    resource = normalize_resource.set_latitude_longitude(resource)
    resource = normalize_resource.alter_portrait_hightlights(resource)
    resource = normalize_resource.normalize_curators_collectors(resource)
    resource = normalize_resource.get_resource_and_types(resource)

    resource["relations"] = relations
    resource["search_result"] = search_result
    resource["resource_orginal"] = resource_orginal
    return resource
