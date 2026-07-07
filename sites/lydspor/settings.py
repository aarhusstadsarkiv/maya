import typing

settings: dict[str, typing.Any] = {
    "client_name": "development",
    "client_url": "https://www.lydsporaarhus.dk",
    "client_email": "stadsarkivet@aarhusarkivet.dk",
    "language": "da",
    "log_handlers": ["rotating_file"],
    "api_base_url": "https://api.openaws.dk/v1",
    "canonical_url": "https://www.aarhusarkivet.dk",
    "main_menu_top": [
        {"name": "search_get", "title": "Søg i Arkivet", "type": "text"},
        {
            "title": "Om Lydspor Aarhus",
            "type": "dropdown",
            "css_class": "menu-about",
            "items": [
                {"name": "vision", "title": "Vision"},
                {"name": "bestyrelsen", "title": "Betyrelsen"},
                {"name": "vedtægter", "title": "Vedtægter"},
                {"name": "news_index", "title": "Nyheder"},
            ],
        },
        {"name": "projekter", "title": "Projekter", "type": "text", "css_class": "menu-projects"},
    ],
    "show_version": True,
    "allow_theme_toggle": True,
    "pages": [
        {"name": "home", "title": "Forside", "template": "pages/home.html", "url": "/"},
        {"name": "vision", "title": "Om Lydspor Aarhus", "template": "pages/vision.html", "url": "/vision"},
        {"name": "projekter", "title": "Projekter", "template": "pages/projekter.html", "url": "/projekter"},
        {"name": "bestyrelsen", "title": "Betyrelsen", "template": "pages/bestyrelsen.html", "url": "/bestyrelsen"},
        {"name": "vedtægter", "title": "Vedtægter", "template": "pages/vedtægter.html", "url": "/vedtægter"},
    ],
    "main_menu_system": [],
}
