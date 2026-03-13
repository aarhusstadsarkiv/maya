import typing


settings: dict[str, typing.Any] = {
    "sqlite3": {
        "default": "/tmp/database.db",
        "orders": "/tmp/orders.db",
    },
}
