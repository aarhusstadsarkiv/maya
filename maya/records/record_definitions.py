from maya.core.dynamic_settings import settings

"""
This file contains the definitions of the record fields.
The definitions are used to normalize the record data.
"""

_record_definitions = {
    "title": {"type": "string"},
    "last_updated": {"type": "date"},
    "date_normalized": {"type": "string"},
    "collectors": {"type": "link_list"},
    "locations": {"type": "link_list"},
    "series": {"type": "link_list_hierarchy"},
    "desc_data": {"type": "key_value_dicts"},
    "availability": {"type": "label_dict"},
    "contractual_status_normalized": {"type": "string"},
    "other_legal_restrictions_normalized": {"type": "string"},
    "availability_normalized": {"type": "string"},
    "registration_id": {"type": "string"},
    "date_from": {"type": "string"},
    "content_types": {"type": "link_list_hierarchy"},
    "created_by": {"type": "string"},
    "id": {"type": "string"},
    "other_legal_restrictions": {"type": "label_dict"},
    "subjects": {"type": "link_list_hierarchy"},
    "admin_tags": {"type": "key_value_dicts"},
    "admin_data": {"type": "key_value_dicts"},
    "type": {"type": "string"},
    "rights_notes": {"type": "string"},
    "admin_notes": {"type": "string"},
    "thumbnail": {"type": "url"},
    "resources": {"type": "key_value_dicts"},
    "schema": {"type": "string"},
    "curators": {"type": "link_list"},
    "copyright_status": {"type": "label_dict"},
    "copyright_status_normalized": {"type": "string_list"},
    "collection": {"type": "link_dict"},
    "last_updated_by": {"type": "string"},
    "date_to": {"type": "string"},
    "representations": {"type": "representations"},  # special type
    "collection_tags": {"type": "link_list"},
    "created": {"type": "date"},
    "summary": {"type": "paragraphs"},
    "usability": {"type": "label_dict"},
    "organisations": {"type": "link_list"},
    "people": {"type": "link_list"},
    "objects": {"type": "link_list"},
    "events": {"type": "link_list"},
    "ordering_normalized": {"type": "ordering_normalized"},  # special type
    "creators": {"type": "link_list"},
    "desc_notes": {"type": "paragraphs"},
    "heading": {"type": "string"},
}


def get_record_definitions() -> dict:
    """
    Get record definitions that are not ignored.
    """
    ignore_keys = settings["ignore_record_keys"]
    return {key: value for key, value in _record_definitions.items() if key not in ignore_keys}
