""" "
Used to add special links to a record.
Only link so far is a link to the 'serie' in the 'collection'
"""


def record_add_links(record: dict) -> dict:
    """
    Add links to record
    """
    if "collection" in record:
        collection = record["collection"]

        collection_id = collection.get("id", None)
        if collection_id:
            record["collection_link"] = {
                "label": "Collection",
                "url": f"/collections/{collection_id}",
                "id": collection_id,
                "search_query": f"/collections/{collection_id}",
            }

    return record
