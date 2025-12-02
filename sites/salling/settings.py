import typing


settings: dict[str, typing.Any] = {
    "client_name": "SallingArkivet",
    "client_url": "https://www.sallingarkivet.dk",
    "client_email": "stadsarkivet@aarhusarkivet.dk",
    "language": "da",
    "log_handlers": ["rotating_file"],
    # "cors_allow_origins": ['https://demo.openaws.dk'],
    "cookie": {
        "name": "session",
        "lifetime": 3600,  # seconds
        "httponly": True,
        "secure": True,
        "samesite": "lax",
    },
    "api_base_url": "https://api.openaws.dk/v1",
    "pages": [
        # {"name": "home_test", "title": "Hjem", "template": "pages/home.html", "url": "/"},
        {"name": "about", "title": "Om SallingArkivet", "template": "pages/about.html", "url": "/om-sallingarkivet"},
        {"name": "privatlivspolitik", "title": "Privatlivspolitik", "template": "pages/privacy.html", "url": "/privatlivspolitik"},
    ],
    "main_menu_top": [
        {"name": "search_get", "title": "Udforsk Arkivet", "type": "text"},
        {"name": "stories", "title": "Historien", "type": "text"},
        {"name": "memories", "title": "Minder", "type": "text"},
        {"name": "about", "title": "Om Arkivet", "type": "text"},
        # {"name": "search_get", "title": "Søg", "type": "icon", "icon": "search"},
    ],
    "main_menu_system": [],
    "search_base_url": "/search",
    "show_version": False,
    "allow_user_registration": False,
    "allow_user_management": False,
    "allow_save_bookmarks": False,
    "allow_save_search": False,
    "allow_online_ordering": False,
    "ignore_record_keys": ["curators", "collectors", "collection", "organisations"],
    "canonical_url": "https://www.aarhusarkivet.dk",
    # default search parameters
    "search_default_sort": "created_at",
    "search_default_view": "list",
}
