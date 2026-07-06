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
                {"name": "about", "title": "Om Lydspor Aarhus"},
                {"name": "foreningen", "title": "Foreningen"},
            ],
        },
        {"name": "projects", "title": "Projekter", "type": "text", "css_class": "menu-projects"},
    ],
    "show_version": True,
    "allow_theme_toggle": True,
    "pages": [
        {"name": "home", "title": "Forside", "template": "pages/home.html", "url": "/"},
        {"name": "about", "title": "Om Lydspor Aarhus", "template": "pages/om-lydspor-aarhus.html", "url": "/about"},
        {"name": "projects", "title": "Projekter", "template": "pages/projekter.html", "url": "/projects"},
        {"name": "foreningen", "title": "Foreningen", "template": "pages/foreningen.html", "url": "/foreningen"},
    ],
    "main_menu_system": [],
}
