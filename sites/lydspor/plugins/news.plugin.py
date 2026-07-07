import re
import unicodedata
from pathlib import Path

from maya.core.context import get_context
from maya.core.templates import templates
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.routing import Route

base_dir = Path(__file__).resolve().parent
news_dir = base_dir / "nyheder"


def get_routes() -> list:
    return [
        Route("/nyheder", endpoint=news_index_endpoint, name="news_index", methods=["GET"]),
        Route("/nyheder/{slug:str}", endpoint=news_article_endpoint, name="news_article", methods=["GET"]),
    ]


async def news_index_endpoint(request: Request):
    articles = get_articles()
    context_values = {"title": "Nyheder", "articles": articles}
    context = await get_context(request, context_values=context_values)
    return templates.TemplateResponse(request, "pages/news.html", context)


async def news_article_endpoint(request: Request):
    slug = request.path_params["slug"]

    for article in get_articles():
        if article["slug"] != slug:
            continue

        context_values = {
            "title": article["title"],
            "article": article,
        }
        context = await get_context(request, context_values=context_values)
        return templates.TemplateResponse(request, "pages/news.html", context)

    raise HTTPException(404, detail="News article not found", headers=None)


def get_articles() -> list[dict[str, str]]:
    articles = []

    for file_path in sorted(news_dir.glob("*.md")):
        article = get_article(file_path)
        articles.append(article)

    return articles


def get_article(file_path: Path) -> dict[str, str]:
    content = file_path.read_text(encoding="utf-8")
    meta, body = parse_front_matter(content)
    title = meta.get("title") or file_path.stem

    return {
        "title": title,
        "date": meta.get("date", ""),
        "author": meta.get("author", ""),
        "body": body,
        "slug": slugify(title),
        "path": f"/nyheder/{slugify(title)}",
        "file": file_path.name,
    }


def parse_front_matter(content: str) -> tuple[dict[str, str], str]:
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) != 3:
        return {}, content

    meta = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()

    return meta, parts[2].lstrip()


def slugify(value: str) -> str:
    value = value.lower()
    value = value.replace("æ", "ae").replace("ø", "oe").replace("å", "aa")
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "nyhed"
