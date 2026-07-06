import unittest
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from maya.core.context import _generate_menu_urls


class RequestStub:
    def url_for(self, name, **params):
        suffix = f"/{params['identifier']}" if "identifier" in params else ""
        return f"https://example.test/{name}{suffix}"


class TestMenuDropdown(unittest.TestCase):
    def test_generates_urls_for_nested_items(self):
        menu_items = [
            {
                "title": "About",
                "type": "dropdown",
                "items": [
                    {"name": "about", "title": "About"},
                    {"name": "page", "title": "Page", "params": {"identifier": "one"}},
                ],
            }
        ]

        result = _generate_menu_urls(RequestStub(), menu_items, "")

        self.assertNotIn("url", result[0])
        self.assertEqual(result[0]["items"][0]["url"], "https://example.test/about")
        self.assertEqual(result[0]["items"][1]["url"], "https://example.test/page/one")

    def test_renders_accessible_desktop_and_mobile_dropdowns(self):
        template_directory = Path(__file__).parents[2] / "maya" / "templates"
        environment = Environment(loader=FileSystemLoader(template_directory))
        environment.globals.update(
            get_icon=lambda _name: "",
            get_setting=lambda _name: False,
            translate=lambda value: value,
            url_for=lambda _name: "/",
        )
        template = environment.get_template("includes/navigation.html")

        rendered = template.render(
            main_menu_system=[],
            main_menu_sections=[],
            main_menu_top=[
                {
                    "title": "About",
                    "type": "dropdown",
                    "items": [{"title": "Organisation", "url": "/organisation"}],
                }
            ],
        )

        self.assertIn('class="menu-dropdown-toggle"', rendered)
        self.assertIn('aria-expanded="false"', rendered)
        self.assertIn('class="menu-dropdown-list"', rendered)
        self.assertIn('href="/organisation"', rendered)
        self.assertIn('class="menu-dropdown-overlay"', rendered)


if __name__ == "__main__":
    unittest.main()
