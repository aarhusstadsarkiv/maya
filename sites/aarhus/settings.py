import typing


settings: dict[str, typing.Any] = {
    "client_name": "Aarhus Stadsarkiv",
    "client_url": "https://www.aarhusarkivet.dk",
    "client_email": "stadsarkivet@aarhusarkivet.dk",
    "language": "da",
    "log_handlers": ["rotating_file"],
    "cookie": {
        "name": "session",
        "lifetime": 3600 * 24,
        "httponly": True,
        "secure": True,
        "samesite": "lax",
    },
    "api_base_url": "https://api.openaws.dk/v1",
    "pages": [
        {"name": "home", "title": "Hjem", "template": "pages/home.html", "url": "/"},
        {"name": "page_images", "title": "Hjemmesider med billeder fra Aarhus", "template": "pages/images.html", "url": "/images"},
        {"name": "page_council", "title": "Aarhus Byråds arkiv", "template": "pages/city-council.html", "url": "/city-council"},
        # guides
        {
            "name": "page_searchguide",
            "title": "Hjælp til søgning",
            "template": "pages/guides/searchguide.html",
            "url": "/guides/searchguide",
        },
        {"name": "page_genealogy", "title": "Slægtsforskning", "template": "pages/guides/genealogy.html", "url": "/guides/genealogy"},
        {
            "name": "page_municipality_records",
            "title": "Kommunearkivet",
            "template": "pages/guides/municipality_records.html",
            "url": "/guides/municipality_records",
        },
        # about
        {"name": "page_collections", "title": "Om samlingerne", "template": "pages/about/collections.html", "url": "/about/collections"},
        {"name": "page_availability", "title": "Tilgængelighed", "template": "pages/about/availability.html", "url": "/about/availability"},
        {
            "name": "page_archival_availability",
            "title": "Arkivlovens tilgængelighedsfrister",
            "template": "pages/about/archival_availability.html",
            "url": "/about/archival_availability",
        },
        {"name": "page_usability", "title": "Brugbarhed ", "template": "pages/about/usability.html", "url": "/about/usability"},
        {"name": "page_privacy", "title": "Privatlivspolitik", "template": "pages/about/privacy.html", "url": "/about/privacy"},
    ],
    "main_menu_top": [
        {"name": "search_get", "title": "Søg", "type": "icon", "icon": "search"},
    ],
    "main_menu_system": [
        {"name": "auth_login_get", "title": "Log ind"},
        {"name": "auth_logout_get", "title": "Log ud"},
        {"name": "auth_register_get", "title": "Ny bruger"},
        {"name": "auth_me_get", "title": "Profil"},
        {"name": "orders_admin_get", "title": "Bestillinger"},
        {"name": "admin_users_get", "title": "Brugere"},
        {"name": "schemas_get_list", "title": "Skemaer"},
        {"name": "entities_get_list", "title": "Entiteter"},
    ],
    "main_menu_sections": [
        {
            "name": "guides",
            "title": "Vejledninger",
            "pages": [
                {"name": "page_searchguide", "title": "Hjælp til søgning"},
                {"name": "page_genealogy", "title": "Slægtsforskning"},
                {"name": "page_municipality_records", "title": "Kommunearkivet"},
            ],
        },
        {
            "name": "about",
            "title": "Om samlingerne",
            "pages": [
                {"name": "page_collections", "title": "Om samlingerne"},
                {"name": "page_availability", "title": "Tilgængelighed"},
                {"name": "page_archival_availability", "title": "Arkivlovens tilgængelighedsfrister"},
                {"name": "page_usability", "title": "Brugbarhed"},
                {"name": "page_privacy", "title": "Privatlivspolitik"},
            ],
        },
    ],
    "allow_user_registration": True,
    "allow_user_management": True,
    "allow_save_bookmarks": True,
    "allow_save_search": False,
    "allow_online_ordering": True,
    "sqlite3": {
        "default": "local/data/database.db",
        "orders": "local/data/orders.db",
    },
    "cron_orders": True,
    "boto3_presigned_urls": True,
}
