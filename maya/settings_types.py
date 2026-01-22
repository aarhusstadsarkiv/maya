# maya/settings_types.py
from __future__ import annotations
from typing import Literal, TypedDict
from typing import NotRequired


class CookieSettings(TypedDict, total=False):
    name: str
    lifetime: int  # seconds
    httponly: bool
    secure: bool
    samesite: Literal["lax", "strict", "none"]


class PageSettings(TypedDict, total=False):
    name: str
    title: str
    template: str
    url: str


class MenuItemSettings(TypedDict, total=False):
    name: str
    title: str
    type: NotRequired[Literal["icon"]]
    icon: NotRequired[str]


class SectionPageRef(TypedDict, total=False):
    name: str
    title: str


class MenuSectionSettings(TypedDict, total=False):
    name: str
    title: str
    pages: list[SectionPageRef]


class Sqlite3Settings(TypedDict, total=False):
    default: str
    orders: str
    errors: str


class Settings(TypedDict, total=True):
    api_key: str
    session_secret: str
    environment: str

    client_name: str
    client_url: str
    client_email: NotRequired[str]
    client_email_orders_reply_to: NotRequired[str]

    debug: bool
    version: str
    show_version: bool
    language: str

    log_level: int  # logging.DEBUG/INFO/etc. are ints
    log_handlers: list[Literal["stream", "rotating_file"]]
    log_api_calls: bool

    cookie: CookieSettings
    custom_error: str

    api_base_url: str

    pages: list[PageSettings]
    main_menu_top: list[MenuItemSettings]
    main_menu_system: list[MenuItemSettings]
    main_menu_sections: list[MenuSectionSettings]

    search_base_url: str
    search_keep_results: bool

    facets_enabled: list[str]
    cors_allow_origins: list[str]

    allow_user_registration: bool
    allow_user_management: bool
    allow_online_ordering: bool
    allow_save_bookmarks: bool
    allow_save_search: NotRequired[bool]

    ignore_record_keys: list[str]

    sqlite3: NotRequired[Sqlite3Settings]
    cron_orders: NotRequired[bool]
    boto3_presigned_urls: NotRequired[bool]
