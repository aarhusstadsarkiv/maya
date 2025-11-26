import typing


settings: dict[str, typing.Any] = {
    # test
    "client_name": "teaterarkivet",
    "client_url": "https://teater.openaws.dk",
    "client_email": "stadsarkivet@aarhusarkivet.dk",
    "language": "da",
    "log_handlers": ["rotating_file"],
    "canonical_url": "https://www.aarhusarkivet.dk",
    #
    # cookie settings
    #
    "cookie": {
        "name": "session",
        "lifetime": 3600,  # seconds
        "httponly": True,
        "secure": True,
        "samesite": "lax",
    },
    "api_base_url": "https://api.openaws.dk/v1",
    # Top menu items. These are the default items. You may remove or add more.
    "main_menu_top": [{"name": "search_get", "title": "Søg", "type": "icon", "icon": "search"}],
    #
    # Main menu containing built-in endpoints, but you may remove these and generate your own menu.
    # You may also add other "menus", e.g. "footer_items" or something similar.
    #
    "main_menu_system": [
        # {"name": "auth_login_get", "title": "Log ind"},
        {"name": "auth_logout_get", "title": "Log ud"},
        # {"name": "auth_register_get", "title": "Ny bruger"},
        # {"name": "auth_me_get", "title": "Profil"},
        # {"name": "admin_users_get", "title": "Brugere"},
        # {"name": "schemas_get_list", "title": "Skemaer"},
        # {"name": "entities_get_list", "title": "Entiteter"},
        # {"name": "search_get", "title": "Søg", "type": "icon", "icon": "search"},
    ],
    "search_base_url": "/search",
    "search_keep_results": False,
    #
    # Allow robots
    #
    "show_version": True,
    "facets_enabled": ["events"],
    "allow_user_registration": False,
    "allow_user_management": True,
    "allow_online_ordering": False,
    "allow_save_bookmarks": False,
    "ignore_record_keys": ["curators"],
}

# Custom pages
#
# "name" is the route name.
# "title" is the page title.
# "template" if the page you will use. It is also the content of the page.
# "url" is the path to the page
# "type" is the type of menu item. It can be "top" or "dropdown". If it is not set, it will not be displayed in the menu.
#
pages: list = [
    {"name": "home", "title": "Forside", "template": "pages/home.html", "url": "/"},
]

pages_guides: list = [
    {"name": "how_to_search", "title": "Søgevejledning", "template": "pages/how-to-search.html", "url": "/how-to-search"},
    {"name": "about_aarhus_teater", "title": "Samling", "template": "pages/about.html", "url": "/about"},
    {"name": "history", "title": "Historie", "template": "pages/history.html", "url": "/history"},
    {"name": "architecture", "title": "Arkitektur", "template": "pages/architecture.html", "url": "/architecture"},
    {"name": "scenes", "title": "Scener", "template": "pages/scenes.html", "url": "/scenes"},
    {"name": "contact", "title": "Kontakt", "template": "pages/contact.html", "url": "/contact"},
]

settings["pages"] = pages + pages_guides

settings["main_menu_sections"] = [
    {"name": "guides", "title": "", "pages": pages_guides},
]
