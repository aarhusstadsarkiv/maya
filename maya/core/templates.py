"""
Template Engine Initialization and Utility Functions for Jinja2 Integration

This module sets up the Jinja2 template engine for use within a Starlette-based
web application. It configures the template directories, adds custom context
processors, and registers a set of helper functions to be available within
Jinja2 templates.

Key Features:
- Dynamically discovers and loads local and module-level template directories.
- Defines a suite of utility functions for use in templates, including:
  - `pre`, `to_json`: Format variables as JSON (with optional <pre> tags).
  - `paragraphs`: Convert newline-separated text into HTML paragraphs.
  - `markdown`: Convert markdown-formatted strings to HTML.
  - `get_icon`: Retrieve and size SVG icons from designated directories.
  - `has_permission`, `key_exist_in_dict`, `sub_string`: Common logical utilities.
- Registers external utilities (e.g., `translate`, `get_setting`, `date_format`) into the template global scope.

"""

import typing
import os
from jinja2 import FileSystemLoader
from starlette.templating import Jinja2Templates
from starlette.requests import Request
from maya.core.translate import translate
from maya.core.dynamic_settings import get_setting
from maya.core.logging import get_log
from maya.core.date_format import date_format
from maya.core.paths import get_base_dir_path
import json
import re
import markdown
from markdown.extensions.toc import TocExtension

log = get_log()

"""
Get a list of template directories.
"""
template_dirs = []
local_templates_dir = get_base_dir_path("templates")
if os.path.exists(local_templates_dir):
    template_dirs.append(local_templates_dir)
    log.debug(f"Loaded local templates: {local_templates_dir}")
else:
    log.debug(f"Local templates NOT loaded: {local_templates_dir}")

# Full path to module templates
current_dir = os.path.dirname(os.path.abspath(__file__))
template_module_dirs = os.path.join(current_dir, "..", "templates")
template_dirs.append(template_module_dirs)


def _get_app_context(request: Request) -> typing.Dict[str, typing.Any]:
    return {"app": request.app}


def _to_json(variable):
    return json.dumps(variable, indent=4, ensure_ascii=False)


def _pre(value):
    """
    Output variable as JSON inside <pre> tags.

    Usage:
        {{ pre(top_level_value)|safe }}

    """
    return f"<pre>{_to_json(value)}</pre>"


def _paragraphs(value):
    """Normalize newlines, then wrap content split by newlines in <p></p>."""
    # Normalize newlines
    normalized = re.sub(r"(\r\n|\r|\n)+", "\n", value).strip()

    # Split by newline and wrap each segment in <p></p>
    segments = normalized.split("\n")
    wrapped = ["<p>{}</p>".format(segment) for segment in segments]

    string = "".join(wrapped)
    return string


def _key_exist_in_dict(keys: list, data: dict):
    """Check if a key exists in a dictionary. And if the value is not empty."""
    for key in keys:
        if key in data:
            # Check if the value is empty
            if data[key] == "":
                return False
            if data[key] == []:
                return False
            if data[key] == {}:
                return False

            return True

    return False


def _markdown(text: str, safe: bool = True):
    return markdown.markdown(text, extensions=["fenced_code", TocExtension(permalink=False)])


loader = FileSystemLoader(template_dirs)
templates = Jinja2Templates(
    directory=template_dirs,
    context_processors=[_get_app_context],
    loader=loader,
    trim_blocks=True,
    lstrip_blocks=True,
)


ICONS = {}
for template_dir in template_dirs:
    icons_dir = template_dir + "/icons"
    if os.path.exists(icons_dir):
        for icon in os.listdir(icons_dir):
            icon_as_str = icons_dir + "/" + icon
            if os.path.isfile(icon_as_str):
                icon_name = icon.split(".")[0]
                if icon_name in ICONS:
                    continue

                with open(icon_as_str, "r") as f:
                    icon_as_str = f.read()

                ICONS[icon_name] = icon_as_str


def get_icon(icon: str, size: int = 24):
    svg = ICONS.get(icon)
    if not svg:
        raise ValueError(f"Icon {icon} not found")
    if size != 24:
        # replace the width and height in the svg
        svg = svg.replace('width="24"', f'width="{size}"')
        svg = svg.replace('height="24"', f'height="{size}"')
    return svg


def has_permission(permission: str, permissions: list):
    return permission in permissions


def sub_string(value: str, length: int):
    if len(value) <= length:
        return value
    return value[:length] + "..."


async def get_template_content(template_path: str, context_values: dict) -> str:
    """
    Get template content from a jinja2 template and a dict of context values
    """

    # Get the template as string
    template = templates.get_template(template_path)
    html_content = template.render(context_values)

    return html_content


templates.env.globals.update(translate=translate)
templates.env.globals.update(get_setting=get_setting)
templates.env.globals.update(date_format=date_format)
templates.env.globals.update(to_json=_to_json)
templates.env.globals.update(pre=_pre)
templates.env.globals.update(paragraphs=_paragraphs)
templates.env.globals.update(get_icon=get_icon)
templates.env.globals.update(has_permission=has_permission)
templates.env.globals.update(markdown=_markdown)
templates.env.globals.update(key_exist_in_dict=_key_exist_in_dict)
templates.env.globals.update(sub_string=sub_string)
