"""
Helpers for generating sitemap XML files from paginated proxy record ids.
Fetches all record ids using the /proxies/view/ids endpoint and generates sitemap XML files in the
static/sitemap directory.
"""

import asyncio
from pathlib import Path
from urllib.parse import parse_qsl
from xml.sax.saxutils import escape

from maya.core.api import proxies_view_ids_from_list
from maya.core.dynamic_settings import settings
from maya.core.paths import get_base_dir_path
from maya.core.logging import get_custom_log

cron_log = get_custom_log("cron_sitemap")

MAX_PAGE_SIZE = 10000
MAX_URLS_PER_SITEMAP = 50000


def _parse_items(query: str | None = None) -> list[tuple[str, str]]:
    query_string = query.lstrip("?") if query else ""
    items = [(key, value) for key, value in parse_qsl(query_string, keep_blank_values=True) if key]
    items = [(key, value) for key, value in items if key not in {"cursor", "view", "size"}]
    items.append(("view", "ids"))
    items.append(("size", str(MAX_PAGE_SIZE)))
    return items


async def _fetch_all_ids(items: list[tuple[str, str]]) -> list[str]:
    ids = []
    next_cursor = None
    page_number = 0

    while True:
        page_items = list(items)
        if next_cursor:
            page_items.append(("cursor", next_cursor))

        payload = await proxies_view_ids_from_list(page_items)
        page_ids = payload.get("result", [])
        if not isinstance(page_ids, list):
            raise ValueError("Expected 'result' to be a list in proxy response.")

        page_number += 1
        ids.extend(page_ids)
        cron_log.info(f"Fetched page {page_number}: {len(page_ids)} ids")

        next_cursor = payload.get("next_cursor")
        if not next_cursor or not page_ids:
            break

    return ids


def _build_sitemap(host: str, ids: list[str]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    for record_id in ids:
        loc = escape(f"{host}/records/{record_id}")
        lines.append("  <url>")
        lines.append(f"    <loc>{loc}</loc>")
        lines.append("    <changefreq>yearly</changefreq>")
        lines.append("  </url>")

    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def _build_sitemap_index(host: str, sitemap_names: list[str]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    for sitemap_name in sitemap_names:
        loc = escape(f"{host}/{sitemap_name}")
        lines.append("  <sitemap>")
        lines.append(f"    <loc>{loc}</loc>")
        lines.append("  </sitemap>")

    lines.append("</sitemapindex>")
    return "\n".join(lines) + "\n"


def _write_output(output_path: Path, content: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def _clear_existing_sitemaps(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in output_dir.glob("sitemap*.xml"):
        path.unlink()


def _chunk_ids(ids: list[str], chunk_size: int) -> list[list[str]]:
    return [ids[i : i + chunk_size] for i in range(0, len(ids), chunk_size)]


def _write_sitemaps(host: str, ids: list[str], output_dir: Path) -> None:
    _clear_existing_sitemaps(output_dir)
    chunks = _chunk_ids(ids, MAX_URLS_PER_SITEMAP)
    index_path = output_dir / "sitemap.xml"

    if len(chunks) <= 1:
        _write_output(index_path, _build_sitemap(host, ids))
        cron_log.info(f"Wrote sitemap with {len(ids)} URLs to {index_path}")
        return

    sitemap_names = []
    for index, chunk in enumerate(chunks, start=1):
        sitemap_name = f"sitemap-{index:04d}.xml"
        sitemap_names.append(sitemap_name)
        sitemap_path = output_dir / sitemap_name
        _write_output(sitemap_path, _build_sitemap(host, chunk))
        cron_log.info(f"Wrote sitemap {sitemap_name} with {len(chunk)} URLs")

    _write_output(index_path, _build_sitemap_index(host, sitemap_names))
    cron_log.info(f"Wrote sitemap index with {len(sitemap_names)} sitemap files to {index_path}")


def generate_sitemap(query: str | None = None) -> None:
    try:
        output_dir = Path(get_base_dir_path("data", "sitemap"))
        sitemap_path = output_dir / "sitemap.xml"
        items = _parse_items(query=query)
        host = settings["client_url"]
        ids = asyncio.run(_fetch_all_ids(items))
        _write_sitemaps(host, ids, output_dir)
        cron_log.info(f"Sitemap written to {sitemap_path}")
    except Exception:
        cron_log.exception("Failed to generate sitemap")
