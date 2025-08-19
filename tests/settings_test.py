import typing


settings: dict[str, typing.Any] = {
    "client_name": "test",
    "client_url": "https://demo.openaws.dk",
    "log_handlers": ["stream"],
    "api_base_url": "https://staging.openaws.dk/v1",
    "sqlite3": {
        "default": "/tmp/database.db",
        "orders": "/tmp/orders.db",
    },
    "send_mail_disabled": True,
}
