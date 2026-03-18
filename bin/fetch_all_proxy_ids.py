#!/usr/bin/env python
"""
Fetch all paginated `view=ids` proxy results, store each page as JSON, and
concatenate them into a single JSON file.

Examples:
    export BASE_DIR=sites/aarhus
    python bin/fetch_all_proxy_ids.py \
        --query "content_types=100&size=10000" \
        --output ids.json \
        --pages-dir tmp/proxy-pages

    python bin/fetch_all_proxy_ids.py \
        --url "http://localhost:5555/search?content_types=100&view=ids&size=5000" \
        --output ids.json \
        --pages-dir tmp/proxy-pages
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

sys.path.append(".")


MAX_PAGE_SIZE = 10000


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch all paginated proxy ids and combine them into a single JSON file.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--query",
        help="Raw search query string, e.g. 'content_types=100&size=10000'.",
    )
    source.add_argument(
        "--url",
        help="Full search URL or path, e.g. 'http://localhost:5555/search?content_types=100&view=ids'.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to the combined JSON output file.",
    )
    parser.add_argument(
        "--pages-dir",
        required=True,
        help="Directory where each fetched page JSON file will be written.",
    )
    return parser.parse_args()


def _parse_items(args: argparse.Namespace) -> list[tuple[str, str]]:
    if args.query:
        query = args.query.lstrip("?")
    else:
        parsed = urlparse(args.url)
        query = parsed.query or args.url.lstrip("?")

    items = [(key, value) for key, value in parse_qsl(query, keep_blank_values=True) if key]

    filtered_items = [(key, value) for key, value in items if key not in {"cursor", "view", "size"}]
    filtered_items.append(("view", "ids"))
    filtered_items.append(("size", str(MAX_PAGE_SIZE)))
    return filtered_items


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


async def _fetch_all(items: list[tuple[str, str]], fetch_page, pages_dir: Path) -> dict:
    next_cursor = None
    pages_fetched = 0

    while True:
        page_items = list(items)
        if next_cursor:
            page_items.append(("cursor", next_cursor))

        payload = await fetch_page(page_items)
        page_result = payload.get("result", [])

        if not isinstance(page_result, list):
            raise ValueError("Expected 'result' to be a list in proxy response.")

        page_number = pages_fetched + 1
        page_path = pages_dir / f"page_{page_number:05d}.json"
        _write_json(page_path, payload)
        print(f"Fetched page {page_number}: wrote {page_path}")
        pages_fetched += 1
        next_cursor = payload.get("next_cursor")

        if not next_cursor:
            break

    return {
        "pages_fetched": pages_fetched,
        "next_cursor": None,
        "status_code": 0,
    }


def _concatenate_pages(pages_dir: Path) -> dict:
    result = []
    page_files = sorted(pages_dir.glob("page_*.json"))

    for page_file in page_files:
        payload = json.loads(page_file.read_text(encoding="utf-8"))
        page_result = payload.get("result", [])

        if not isinstance(page_result, list):
            raise ValueError(f"Expected 'result' to be a list in {page_file}.")

        result.extend(page_result)

    return {
        "result": result,
        "count": len(result),
        "pages_fetched": len(page_files),
        "next_cursor": None,
        "status_code": 0,
    }


def _write_output(output_path: str, payload: dict) -> None:
    _write_json(Path(output_path), payload)


def main() -> int:
    args = _parse_args()
    if "BASE_DIR" not in os.environ:
        print("Environment variable BASE_DIR is not set. E.g. set it like this:")
        print("export BASE_DIR=sites/aarhus")
        return 1

    from maya.core.api import proxies_view_ids_from_list

    items = _parse_items(args)
    pages_dir = Path(args.pages_dir)
    asyncio.run(_fetch_all(items, proxies_view_ids_from_list, pages_dir))
    payload = _concatenate_pages(pages_dir)
    _write_output(args.output, payload)
    print(f"Wrote {payload['count']} ids from {payload['pages_fetched']} page(s) to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
