from email.message import Message
from unittest.mock import MagicMock

from backend.fetcher import transport


def test_https_tunnel_uses_resolved_ip_but_tls_and_host_use_origin(monkeypatch):
    connection = MagicMock()
    response = connection.getresponse.return_value.__enter__.return_value
    response.status = 200
    response.headers = Message()
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    response.getheader.side_effect = response.headers.get
    response.read1.side_effect = [b"<p>Course text.</p><script>synthetic marker</script>", b""]
    ssl_context = MagicMock()
    checked = MagicMock(return_value=("example.edu", 443, ("93.184.216.34",)))
    monkeypatch.setattr(transport, "HTTPConnection", MagicMock(return_value=connection))
    monkeypatch.setattr(transport, "create_default_context", lambda: ssl_context)
    monkeypatch.setattr(transport, "check_url", checked)

    result = transport.fetch_citation("https://example.edu/read?p=1")

    assert result.status == "fetched"
    assert result.text == "Course text."
    connection.set_tunnel.assert_called_once_with("93.184.216.34", 443)
    assert ssl_context.wrap_socket.call_args.kwargs["server_hostname"] == "example.edu"
    assert connection.request.call_args.args == ("GET", "/read?p=1")
    assert connection.request.call_args.kwargs["headers"]["Host"] == "example.edu"


def test_redirect_hop_is_validated_before_a_second_connection(monkeypatch):
    connection = MagicMock()
    response = connection.getresponse.return_value.__enter__.return_value
    response.status = 302
    response.getheader.return_value = "https://secondary.example.edu/"
    checked = MagicMock(
        side_effect=[
            ("example.edu", 443, ("93.184.216.34",)),
            transport.BlockedUrl("non_public_address"),
        ]
    )
    proxy = MagicMock(return_value=connection)
    monkeypatch.setattr(transport, "HTTPConnection", proxy)
    monkeypatch.setattr(transport, "create_default_context", MagicMock())
    monkeypatch.setattr(transport, "check_url", checked)

    result = transport.fetch_citation("https://example.edu/")

    assert result.status == "blocked"
    assert result.reason == "non_public_address"
    assert checked.call_count == 2
    proxy.assert_called_once()


def test_http_is_blocked_with_current_proxy_policy(monkeypatch):
    proxy = MagicMock()
    monkeypatch.setattr(transport, "HTTPConnection", proxy)
    monkeypatch.setattr(
        transport, "check_url", lambda _, **__: ("example.edu", 80, ("93.184.216.34",))
    )

    result = transport.fetch_citation("http://example.edu/")

    assert result.reason == "proxy_transport_policy"
    proxy.assert_not_called()


def test_size_limit_works_without_content_length(monkeypatch):
    connection = MagicMock()
    response = connection.getresponse.return_value.__enter__.return_value
    response.status = 200
    response.headers = Message()
    response.headers["Content-Type"] = "text/plain"
    response.getheader.side_effect = response.headers.get
    response.read1.return_value = b"123456"
    monkeypatch.setattr(transport, "MAX_BYTES", 5)
    monkeypatch.setattr(transport, "HTTPConnection", MagicMock(return_value=connection))
    monkeypatch.setattr(transport, "create_default_context", MagicMock())
    monkeypatch.setattr(
        transport, "check_url", lambda _, **__: ("example.edu", 443, ("93.184.216.34",))
    )

    result = transport.fetch_citation("https://example.edu/")

    assert result.reason == "body_too_large"
