"""Request-local context made available to log formatters."""

from contextvars import ContextVar, Token

_client_ip: ContextVar[str | None] = ContextVar("client_ip", default=None)


def get_client_ip() -> str | None:
    return _client_ip.get()


def set_client_ip(client_ip: str) -> Token:
    return _client_ip.set(client_ip)


def reset_client_ip(token: Token) -> None:
    _client_ip.reset(token)
