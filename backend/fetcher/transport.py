"""Fetch public citation text using the existing web egress proxy."""

from dataclasses import dataclass
from hashlib import sha256
from html.parser import HTMLParser
from http.client import HTTPConnection, HTTPException
from socket import SHUT_RDWR, socket
from ssl import create_default_context
from threading import Timer
from time import monotonic
from urllib.parse import quote, urljoin, urlsplit

from backend.fetcher.resolver import resolve_for_fetcher
from backend.fetcher.url_policy import BlockedUrl, check_url

MAX_BYTES = 2_000_000
MAX_REDIRECTS = 3
REDIRECTS = {301, 302, 303, 307, 308}
_MEDIA_TYPES = {"text/html", "text/plain"}


@dataclass(frozen=True)
class FetchResult:
    status: str
    final_url: str | None = None
    body_hash: str | None = None
    text: str | None = None
    reason: str | None = None


class _VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.hidden: list[str] = []

    def handle_starttag(self, tag, attrs) -> None:
        if tag in {"script", "style", "noscript", "template"}:
            self.hidden.append(tag)

    def handle_endtag(self, tag) -> None:
        if self.hidden and self.hidden[-1] == tag:
            self.hidden.pop()

    def handle_data(self, data) -> None:
        if not self.hidden:
            self.parts.append(data)


def _remaining(deadline: float) -> float:
    remaining = deadline - monotonic()
    if remaining <= 0:
        raise TimeoutError
    return remaining


def _interrupt_read(connection: socket) -> None:
    try:
        connection.shutdown(SHUT_RDWR)
    except OSError:
        return


def _hop(url: str, deadline: float) -> FetchResult | str:
    host, port, addresses = check_url(url, resolve=resolve_for_fetcher)
    parsed = urlsplit(url)
    # The existing proxy only permits CONNECT to port 443. Fail closed for
    # schemes and ports that cannot use an address-pinned tunnel.
    if parsed.scheme != "https" or port != 443:
        raise BlockedUrl("proxy_transport_policy")

    target = quote(parsed.path or "/", safe="/%:@!$&'()*+,;=-._~")
    if parsed.query:
        target += "?" + quote(parsed.query, safe="/%?:@!$&'()*+,;=-._~[]")
    authority = f"[{host}]" if ":" in host else host
    proxy = HTTPConnection("web-proxy", 3128, timeout=_remaining(deadline))
    timer = None
    try:
        # CONNECT uses only the resolved numeric address. TLS still verifies
        # the original hostname, and the origin request uses that Host header.
        address = min(addresses, key=lambda value: ":" in value)
        proxy.set_tunnel(address, port)
        proxy.connect()
        assert proxy.sock is not None
        proxy.sock.settimeout(_remaining(deadline))
        proxy.sock = create_default_context().wrap_socket(proxy.sock, server_hostname=host)
        proxy.sock.settimeout(_remaining(deadline))
        timer = Timer(_remaining(deadline), _interrupt_read, args=(proxy.sock,))
        timer.daemon = True
        timer.start()
        proxy.request(
            "GET",
            target,
            headers={
                "Host": authority,
                "Accept": "text/html, text/plain",
                "Accept-Encoding": "identity",
                "Connection": "close",
            },
        )
        with proxy.getresponse() as response:
            if response.status in REDIRECTS:
                location = response.getheader("Location")
                if not location or len(location) > 2048:
                    raise BlockedUrl("invalid_redirect")
                return urljoin(url, location)
            if response.status != 200:
                return FetchResult("unavailable", final_url=url, reason="upstream_status")
            media_type = response.headers.get_content_type()
            if not response.getheader("Content-Type") or media_type not in _MEDIA_TYPES:
                raise BlockedUrl("content_type")
            if response.getheader("Content-Encoding", "identity").lower() != "identity":
                raise BlockedUrl("content_encoding")
            data = bytearray()
            while True:
                _remaining(deadline)
                chunk = response.read1(min(65536, MAX_BYTES + 1 - len(data)))
                if not chunk:
                    break
                data.extend(chunk)
                if len(data) > MAX_BYTES:
                    raise BlockedUrl("body_too_large")

            _remaining(deadline)
            encoding = response.headers.get_content_charset() or "utf-8"
            try:
                text = data.decode(encoding, errors="replace")
            except LookupError:
                text = data.decode("utf-8", errors="replace")
            if media_type == "text/html":
                page = _VisibleText()
                page.feed(text)
                page.close()
                text = " ".join(" ".join(page.parts).split())
            # PostgreSQL text does not accept NUL characters.
            return FetchResult(
                "fetched", url, sha256(data).hexdigest(), text.replace("\x00", "\ufffd")
            )
    finally:
        if timer is not None:
            timer.cancel()
        proxy.close()


def fetch_citation(url: str) -> FetchResult:
    deadline = monotonic() + 10
    try:
        for _ in range(MAX_REDIRECTS + 1):
            if len(url) > 2048:
                raise BlockedUrl("invalid_url")
            result = _hop(url, deadline)
            if isinstance(result, FetchResult):
                return result
            url = result
        return FetchResult("blocked", reason="redirect_limit")
    except BlockedUrl as exc:
        return FetchResult("blocked", reason=str(exc))
    except TimeoutError:
        return FetchResult("unavailable", reason="timeout")
    except (HTTPException, OSError, ValueError):
        reason = "timeout" if monotonic() >= deadline else "transport_failure"
        return FetchResult("unavailable", reason=reason)
