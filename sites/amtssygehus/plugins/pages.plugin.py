from starlette.routing import Route
from starlette.requests import Request

from starlette.exceptions import HTTPException
from maya.core.templates import templates
from maya.core.context import get_context
import os
from maya.core.logging import get_log
import json
import random

log = get_log()
current_path = os.path.abspath(__file__)
base_dir = os.path.dirname(os.path.abspath(__file__))


def _load_stories_sync():
    stories_dir = os.path.join(base_dir, "..", "data-imported", "stories")
    stories = []

    filenames = sorted([f for f in os.listdir(stories_dir) if f.endswith(".json")], key=lambda f: int(f.split("-")[0]))

    for filename in filenames:
        with open(os.path.join(stories_dir, filename), "r") as f:
            story = json.load(f)
            stories.append(story)

    return stories


def _load_memories_sync():
    memories_dir = os.path.join(base_dir, "..", "data-imported", "memories")
    memories = []

    filenames = sorted([f for f in os.listdir(memories_dir) if f.endswith(".json")], key=lambda f: int(f.split("-")[0]))

    for filename in filenames:
        with open(os.path.join(memories_dir, filename), "r") as f:
            story = json.load(f)
            memories.append(story)

    return memories


STORIES = _load_stories_sync()
MEMORIES = _load_memories_sync()


async def stories_index(request: Request):
    """
    Index of stories
    """

    # Get all main stories. Main stories is the first story in each section
    main_stories = []
    for story in STORIES:
        main_stories.append(story[0])

    # The first story is special
    story_first = main_stories.pop(0)
    title = story_first.get("heading")

    context = await get_context(
        request,
        context_values={
            "title": title,
            # "stories": stories,
            "story_first": story_first,
            "main_stories": main_stories,
        },
    )
    return templates.TemplateResponse(request, "pages/stories.html", context)


async def memories_index(request: Request):
    """
    Index of memories
    """
    memories = MEMORIES.copy()

    context = await get_context(
        request,
        context_values={
            "title": "Udvalgte minder",
            "memories": memories,
        },
    )
    return templates.TemplateResponse(request, "pages/memories.html", context)


async def story_exists(stories: list, path: str) -> dict:
    found_story = {}
    for story in stories:
        if story[0]["path"] == path:
            found_story = story
            break

    return found_story


async def story_display(request: Request):
    """
    A story is a list of dicts where each dict is sub-story or section of a story
    """
    stories = STORIES.copy()
    path = request.path_params["page"]

    found_story = await story_exists(stories, path)
    if not found_story:
        raise HTTPException(404, detail="Page not found", headers=None)

    sections = found_story.copy()

    # Get data of the story
    first_section = sections.pop(0)
    title = first_section["heading"]
    data = {
        "title": title,
        "sections": sections,
        "first_section": first_section,
    }

    context = await get_context(
        request,
        context_values=data,
    )
    return templates.TemplateResponse(request, "pages/story.html", context)


async def story_by_index(index: list = []) -> list:
    stories = STORIES.copy()

    if index:
        stories = [stories[i] for i in index]
    else:
        stories = stories

    stories_data = []

    for story in stories:
        # extract data
        sections = story.copy()
        first_section = sections.pop(0)
        title = first_section["heading"]
        data = {
            "title": title,
            "sections": sections,
            "first_section": first_section,
        }
        stories_data.append(data)
    return stories_data


async def memory_display(request: Request):
    # get path
    path = request.path_params["page"]

    memories = MEMORIES.copy()

    # Iterate over all stories and find the one with the correct path
    found_memory = None
    for memory in memories:
        if memory["path"] == path:
            found_memory = True
            break

    if not found_memory:
        raise HTTPException(404, detail="Page not found", headers=None)

    memory_images = []
    images = memory.get("urls", [])
    images_texts = memory.get("summary", [])
    records = memory.get("recordIds", [])
    for url, text, record in zip(images, images_texts, records):
        image = {
            "url": url,
            "text": text,
            "record": record,
        }
        memory_images.append(image)

    if not memory_images:
        first_image = None
    else:
        first_image = memory_images.pop(0)

    context = await get_context(
        request,
        context_values={
            "title": memory["heading"],
            "memory": memory,
            "first_image": first_image,
            "images": memory_images,
        },
    )
    return templates.TemplateResponse(request, "pages/memory.html", context)


async def home_page(request: Request):

    memories = MEMORIES.copy()
    stories = STORIES.copy()

    # get two random memories
    random_memories = random.sample(range(len(memories)), 2)
    memories = [memories[i] for i in random_memories]

    stories = await story_by_index(index=[])

    story_sections = []
    for story in stories:
        story_sections.append(story["first_section"])

    # remove the first story_section from the list
    story_sections.pop(0)

    context = await get_context(
        request,
        context_values={
            "title": "Forside",
            "stories": story_sections,
            "memories": memories,
        },
    )
    return templates.TemplateResponse(request, "pages/home.html", context)


def get_routes() -> list:

    routes = [
        Route("/historier", endpoint=stories_index, name="stories", methods=["GET"]),
        Route("/historier/{page:str}", endpoint=story_display, name="story_display", methods=["GET"]),
        Route("/erindringer", endpoint=memories_index, name="memories", methods=["GET"]),
        Route("/erindringer/{page:str}", endpoint=memory_display, name="memory_display", methods=["GET"]),
        Route("/", endpoint=home_page, name="home", methods=["GET"]),
    ]

    return routes
