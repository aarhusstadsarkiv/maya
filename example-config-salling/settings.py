import typing


settings: dict[str, typing.Any] = {
    "client_name": "development",
    "client_url": "https://demo.openaws.dk",
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
    # "api_base_url": "http://localhost:8000/v1",
    "api_base_url": "https://dev.openaws.dk/v1",
    "main_menu_top": [
        {"name": "stories", "title": "Historier", "type": "text"},
        {"name": "memories", "title": "Erindringer", "type": "text"},
        {"name": "search_get", "title": "Søg", "type": "icon", "icon": "search"},
    ],
    "main_menu_system": [
        {"name": "auth_login_get", "title": "Log ind"},
        {"name": "auth_logout_get", "title": "Log ud"},
        {"name": "auth_register_get", "title": "Ny bruger"},
        {"name": "auth_me_get", "title": "Profil"},
        {"name": "admin_users_get", "title": "Brugere"},
        {"name": "schemas_get_list", "title": "Skemaer"},
        {"name": "entities_get_list", "title": "Entiteter"},
    ],
    "sqlite3": {
        "default": "data/database.db",
        "orders": "data/orders.db",
    },
    "search_base_url": "/search",
    "show_version": True,
    "allow_user_registration": True,
    "allow_user_management": True,
    "allow_save_bookmarks": False,
    "allow_save_search": False,
    "allow_online_ordering": False,
}
