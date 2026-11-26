"""Preflight validation for one citation URL or redirect hop (C06)."""

import socket
from collections.abc import Callable
from ipaddress import IPv6Address, IPv6Network, ip_address
from urllib.parse import urlsplit

_NAT64 = IPv6Network("64:ff9b::/96")


class BlockedUrl(ValueError):
    """A fixed reason safe to record without echoing the URL."""


def _resolve_locally(host: str, port: int) -> tuple[str, ...]:
    records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    return tuple(record[4][0] for record in records)


def check_url(
    url: str, *, resolve: Callable[[str, int], tuple[str, ...]] = _resolve_locally
) -> tuple[str, int, tuple[str, ...]]:
    if not url or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in url):
        raise BlockedUrl("invalid_url")

    try:
        address = urlsplit(url)
        host = address.hostname
        port = address.port
    except ValueError as exc:
        raise BlockedUrl("invalid_url") from exc

    if (
        address.scheme not in {"http", "https"}
        or not host
        or address.username is not None
        or address.password is not None
        or "%" in host
        or "\\" in address.netloc
    ):
        raise BlockedUrl("scheme_or_userinfo")

    if port is None:
        port = 443 if address.scheme == "https" else 80
    if port not in {80, 443}:
        raise BlockedUrl("port")

    try:
        host = host.encode("idna").decode("ascii")
        records = resolve(host, port)
    except (UnicodeError, OSError) as exc:
        raise BlockedUrl("dns_failure") from exc

    if not records:
        raise BlockedUrl("dns_failure")

    checked = set()
    for record in records:
        value = ip_address(record)
        if (
            not value.is_global
            or value.is_multicast
            or value.is_reserved
            or (
                isinstance(value, IPv6Address)
                and (value.ipv4_mapped is not None or value in _NAT64)
            )
        ):
            raise BlockedUrl("non_public_address")
        checked.add(str(value))

    return host, port, tuple(sorted(checked))
