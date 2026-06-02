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
        {"name": "about", "title": "Om Lydspor Aarhus", "type": "text"},
    ],
    "show_version": True,
    "pages": [
        {"name": "home", "title": "Forside", "template": "pages/home.html", "url": "/"},
        {"name": "about", "title": "Om Lydspor Aarhus", "template": "pages/about.html", "url": "/about"},
    ],
}
