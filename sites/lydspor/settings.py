import typing


settings: dict[str, typing.Any] = {
    "client_name": "development",
    "client_url": "https://www.lydsporaarhus.dk",
    "client_email": "stadsarkivet@aarhusarkivet.dk",
    "language": "da",
    "log_handlers": ["rotating_file"],
    "api_base_url": "https://api.openaws.dk/v1",
    "main_menu_top": [
        {"name": "search_get", "title": "Søg", "type": "icon", "icon": "search"},
    ],
    "main_menu_system": [
        {"name": "about", "title": "About"},
    ],
    "show_version": True,
}
