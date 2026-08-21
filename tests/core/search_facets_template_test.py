import unittest
from pathlib import Path

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader


class TestSearchFacetsTemplate(unittest.TestCase):
    def setUp(self):
        templates_path = Path(__file__).parents[2] / "maya" / "templates"
        environment = Environment(loader=FileSystemLoader(templates_path), autoescape=True)
        environment.globals.update(
            get_setting=lambda name: "/search",
            translate=lambda value: value,
        )
        self.template = environment.from_string("""
            {% import "macros/search_macros.html" as search_macros %}
            {{ search_macros.parse_top_level_facets(facets, "facets", "search-date") }}
            """)

    def test_facet_disclosures_do_not_nest_interactive_elements(self):
        facets = {
            "content_types": {
                "type": "default",
                "label": "Material type",
                "content": [
                    {
                        "id": "images",
                        "label": "Images",
                        "count": 10,
                        "checked": False,
                        "add_link": "content_types=images",
                        "children": [
                            {
                                "id": "photos",
                                "label": "Photos",
                                "count": 5,
                                "checked": False,
                                "add_link": "content_types=photos",
                            }
                        ],
                    }
                ],
            },
            "collections": {
                "type": "resource_links",
                "label": "Collections",
                "resource_type": "collections",
                "content": [
                    {
                        "id": "group",
                        "label": "Group",
                        "children": [{"id": "item", "label": "Item"}],
                    }
                ],
            },
        }

        soup = BeautifulSoup(self.template.render(facets=facets), "html.parser")
        interactive_elements = "a, button, input, select, textarea, [tabindex]"

        self.assertFalse(any(summary.select_one(interactive_elements) for summary in soup.select("summary")))

        branch_heading = soup.select_one(".facet-branch-heading")
        expander = branch_heading.select_one(".facet-expander")
        facet_link = branch_heading.select_one('a[href="/search?content_types=images"]')

        self.assertEqual(expander["aria-expanded"], "false")
        self.assertEqual(expander["aria-label"], "Toggle subfacets: Images")
        self.assertEqual(facet_link.get_text(" ", strip=True), "Images (10)")
        self.assertEqual(len(soup.find_all(string=lambda value: value and "Images" in value)), 1)
        self.assertTrue(soup.select_one(".facet-children").has_attr("hidden"))
        self.assertIsNotNone(soup.select_one('.facet-leaf > a[href="/collections/item"]'))


if __name__ == "__main__":
    unittest.main()
