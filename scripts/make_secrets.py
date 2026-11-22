#!/usr/bin/env python3
"""Create random Docker secrets under secrets/ (git-ignored). Never overwrites.

One file per secret, as listed in docs/plan/E-platform-devsecops-engineer.md (E2):
one database password per role, one X-Service-Auth secret per internal caller,
the token-hashing pepper and the TOTP encryption key. The provider API key is
created empty: paste the real key in by hand when it arrives (never commit it).
"""

from __future__ import annotations

import base64
import contextlib
import os
import secrets
import sys
from pathlib import Path

DB_ROLES = ["owner", "web", "ingest", "grading", "mcp", "release", "fetch"]
# Internal callers that send X-Service-Auth: web -> agents and release;
# grading-agent -> fetcher.
SERVICE_CALLERS = ["web", "grading_agent"]

GENERATED = (
    [f"db_{role}_password" for role in DB_ROLES]
    + [f"service_auth_{caller}" for caller in SERVICE_CALLERS]
    + ["token_pepper", "session_secret"]
)
EMPTY = ["llm_api_key"]  # filled by hand when provider keys arrive


def fernet_key() -> str:
    # 32 random bytes, urlsafe base64: the format `cryptography.Fernet` expects.
    return base64.urlsafe_b64encode(os.urandom(32)).decode()


def main() -> int:
    root = Path(__file__).resolve().parent.parent / "secrets"
    root.mkdir(exist_ok=True)
    with contextlib.suppress(OSError):  # chmod is a no-op on Windows
        root.chmod(0o700)  # only the host user can list or open the directory
    created = []
    values = {name: secrets.token_urlsafe(32) for name in GENERATED}
    values["totp_encryption_key"] = fernet_key()
    values.update({name: "" for name in EMPTY})
    for name, value in values.items():
        path = root / name
        if path.exists():
            continue
        path.write_text(value, encoding="utf-8")
        # Compose bind-mounts each file into /run/secrets with host permissions,
        # and the containers run as non-root users with other UIDs, so the file
        # must be world-readable. The 0700 directory keeps other host users out.
        with contextlib.suppress(OSError):
            path.chmod(0o644)
        created.append(name)
    print(f"secrets/: created {len(created)}, kept {len(values) - len(created)} existing")
    for name in created:
        print(f"  + {name}")  # names only, never values
    return 0


if __name__ == "__main__":
    sys.exit(main())
