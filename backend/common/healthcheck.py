"""Container healthcheck: exit 0 when healthy, 1 otherwise.

HTTP services: GET http://127.0.0.1:$PORT/healthz must return 200.
Services without a network (RUBRICA_NO_NETWORK=1, the parser): the heartbeat
file must have been touched in the last 30 seconds.
"""

from __future__ import annotations

import os
import sys
import time
import urllib.request
from pathlib import Path

MAX_HEARTBEAT_AGE_S = 30


def main() -> int:
    if os.environ.get("RUBRICA_NO_NETWORK") == "1":
        path = Path(os.environ.get("RUBRICA_HEARTBEAT_FILE", "/tmp/heartbeat"))  # noqa: S108
        try:
            return 0 if time.time() - path.stat().st_mtime < MAX_HEARTBEAT_AGE_S else 1
        except OSError:
            return 1
    url = f"http://127.0.0.1:{os.environ.get('PORT', '8000')}/healthz"
    # Bypass any HTTPS_PROXY/HTTP_PROXY set for the service's egress.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url, timeout=2) as resp:
            return 0 if resp.status == 200 else 1
    except OSError:
        return 1


if __name__ == "__main__":
    sys.exit(main())
