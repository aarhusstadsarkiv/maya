import typing

settings: dict[str, typing.Any] = {
    "session_secret": "test-only-session-secret-do-not-use-in-production",
    "client_name": "test",
    "client_url": "https://demo.openaws.dk",
    "log_handlers": ["stream"],
    "api_base_url": "https://dev.openaws.dk/v1",
    "send_mail_disabled": True,
}
