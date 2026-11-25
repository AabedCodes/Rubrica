import socket

import pytest

from backend.fetcher.url_policy import BlockedUrl, check_url


def test_citation_preflight_rejects_mixed_dns_records(monkeypatch):
    def resolve(*_args, **_kwargs):
        return [(0, 0, 0, "", (host, 443)) for host in ("93.184.216.34", "10.0.0.1")]

    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    with pytest.raises(BlockedUrl, match="non_public_address"):
        check_url("https://example.edu/reading")


def test_citation_preflight_returns_addresses_for_pinned_transport(monkeypatch):
    def resolve(*_args, **_kwargs):
        return [(0, 0, 0, "", ("93.184.216.34", 443))]

    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    assert check_url("https://example.edu/reading") == ("example.edu", 443, ("93.184.216.34",))


@pytest.mark.parametrize(
    ("url", "reason"),
    [
        ("file:///tmp/example.txt", "scheme_or_userinfo"),
        ("https://user@example.edu", "scheme_or_userinfo"),
        ("https://example.edu:0", "port"),
        ("https://example.edu:99999", "invalid_url"),
    ],
)
def test_citation_preflight_rejects_unsupported_url_components(url, reason):
    with pytest.raises(BlockedUrl, match=reason):
        check_url(url)
