#!/usr/bin/env bash
# Egress and isolation smoke test for the running Compose stack (E2 "done when",
# first half of the T-15 verification test). Run after `make up`.
# Exits non-zero on the first check that does not behave as designed.
set -uo pipefail

COMPOSE=(docker compose -f deploy/docker-compose.yml)
fail=0
PY=$(command -v python3 >/dev/null 2>&1 && python3 -c "" 2>/dev/null && echo python3 || echo python)

py() {  # py <service> <python code>
  "${COMPOSE[@]}" exec -T "$1" python -c "$2"
}

expect_fail() {  # expect_fail <label> <service> <python code>
  if py "$2" "$3" >/dev/null 2>&1; then
    echo "FAIL  $1 (request succeeded, should have been blocked)"; fail=1
  else
    echo "ok    $1 (blocked)"
  fi
}

expect_ok() {  # expect_ok <label> <service> <python code>
  if py "$2" "$3" >/dev/null 2>&1; then
    echo "ok    $1"
  else
    echo "FAIL  $1 (should have succeeded)"; fail=1
  fi
}

DIRECT='import urllib.request as u; u.build_opener(u.ProxyHandler({})).open("https://example.com", timeout=5)'
VIA_ENV_PROXY='import urllib.request as u; u.urlopen("https://example.com", timeout=10)'
tcp() { printf 'import socket; socket.create_connection(("%s", %s), timeout=3)' "$1" "$2"; }

echo "== agents: no direct internet, llm-proxy denies non-provider hosts"
for svc in grading-agent chat-agent instructor-agent; do
  expect_fail "$svc direct https://example.com" "$svc" "$DIRECT"
  expect_fail "$svc via llm-proxy https://example.com" "$svc" "$VIA_ENV_PROXY"
done

echo "== internal-only services: no route out"
for svc in mcp-server ingestion release web; do
  expect_fail "$svc direct https://example.com" "$svc" "$DIRECT"
done

echo "== fetcher: public web through web-proxy only, internal ranges denied"
expect_fail "fetcher direct https://example.com" fetcher "$DIRECT"
expect_ok   "fetcher via web-proxy https://example.com" fetcher "$VIA_ENV_PROXY"
# Force the proxy (NO_PROXY lists db) so these test the proxy's own deny rules.
via_web_proxy() {
  printf 'import urllib.request as u; p="http://web-proxy:3128"; '
  printf 'u.build_opener(u.ProxyHandler({"http": p, "https": p})).open("%s", timeout=5)' "$1"
}
expect_ok   "fetcher forced via web-proxy https://example.com" fetcher \
  "$(via_web_proxy https://example.com)"
expect_fail "fetcher via web-proxy http://db:5432" fetcher "$(via_web_proxy http://db:5432/)"
expect_fail "fetcher via web-proxy http://169.254.169.254/" fetcher \
  "$(via_web_proxy http://169.254.169.254/latest/meta-data/)"
expect_fail "fetcher via web-proxy http://127.0.0.1:3128/" fetcher \
  "$(via_web_proxy http://127.0.0.1:3128/)"

echo "== mailpit: internal network only, no outbound route"
# Plain HTTP so a TLS failure in busybox wget can't pass for a block.
if "${COMPOSE[@]}" exec -T mailpit wget -q -T 5 -O /dev/null http://example.com >/dev/null 2>&1; then
  echo "FAIL  mailpit direct http://example.com (should have been blocked)"; fail=1
else
  echo "ok    mailpit direct http://example.com (blocked)"
fi

echo "== edge: only published container; no route out on Linux"
if "${COMPOSE[@]}" exec -T edge bash -c 'exec 3<>/dev/tcp/example.com/80' >/dev/null 2>&1; then
  if docker info --format '{{.OperatingSystem}}' 2>/dev/null | grep -q 'Docker Desktop'; then
    echo "WARN  edge can reach the internet (Docker Desktop ignores no-NAT; edge holds no secrets)"
  else
    echo "FAIL  edge direct example.com:80 (should have been blocked)"; fail=1
  fi
else
  echo "ok    edge direct example.com:80 (blocked)"
fi

echo "== published ports reachable from the host"
for url in "http://127.0.0.1:8080/healthz" "http://127.0.0.1:8025/readyz"; do
  if "$PY" -c "import urllib.request as u; u.urlopen('$url', timeout=5)" >/dev/null 2>&1; then
    echo "ok    $url"
  else
    echo "FAIL  $url not reachable from the host"; fail=1
  fi
done

# edge must never act as a forward proxy: an absolute URL still lands on web.
if "$PY" -c "
import urllib.request as u
o = u.build_opener(u.ProxyHandler({'http': 'http://127.0.0.1:8080'}))
try:
    body = o.open('http://example.com/', timeout=5).read()
except Exception:
    raise SystemExit(1)
raise SystemExit(0 if b'Example Domain' in body else 1)
" >/dev/null 2>&1; then
  echo "FAIL  edge forwarded a request to example.com (open proxy)"; fail=1
else
  echo "ok    edge refuses forward proxying"
fi

echo "== parser: no network, no secrets (T-15)"
expect_fail "parser tcp db:5432" parser "$(tcp db 5432)"
expect_fail "parser tcp 1.1.1.1:443" parser "$(tcp 1.1.1.1 443)"
if "${COMPOSE[@]}" exec -T parser sh -c 'ls -A /run/secrets 2>/dev/null | grep -q .'; then
  echo "FAIL  parser has files in /run/secrets"; fail=1
else
  echo "ok    parser has no secrets mounted"
fi
# GPG_KEY is set by the official python image: the ID of CPython's public
# release-signing key, not a secret. Print names only, never values.
suspicious=$("${COMPOSE[@]}" exec -T parser env | cut -d= -f1   | grep -Ei '(password|secret|token|key|credential)' | grep -vx 'GPG_KEY')
if [ -n "$suspicious" ]; then
  echo "FAIL  parser environment has credential-looking variables: $suspicious"; fail=1
else
  echo "ok    parser environment has no credential-looking variables"
fi

echo "== hardening: every service runs as non-root"
for svc in $("${COMPOSE[@]}" ps --services); do
  uid=$("${COMPOSE[@]}" exec -T "$svc" sh -c 'id -u' 2>/dev/null || echo "?")
  if [ "$uid" = "0" ]; then echo "FAIL  $svc runs as root"; fail=1; else echo "ok    $svc uid=$uid"; fi
done

exit $fail
