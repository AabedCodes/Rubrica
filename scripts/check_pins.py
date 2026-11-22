#!/usr/bin/env python3
"""Pinning gate (C16, T-17).

Usage: python scripts/check_pins.py [repo_root]

Fails (exit 1) when any of these is unpinned:
  - a GitHub Actions `uses:` that is not a 40-hex commit SHA
    (local `./` actions are allowed; `docker://` images need @sha256)
  - a Compose `image:` without @sha256:<64 hex>
  - a Dockerfile `FROM` without @sha256:<64 hex> (a FROM that names an
    earlier build stage, or `scratch`, is allowed)
  - a lockfile is missing: backend/uv.lock, and frontend/package-lock.json
    once frontend/package.json exists

Standard library only, line-based so it needs no YAML parser.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

SHA40 = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"@sha256:[0-9a-f]{64}$")
USES = re.compile(r"^\s*-?\s*uses:\s*['\"]?([^'\"\s#]+)")
IMAGE = re.compile(r"^\s*image:\s*['\"]?([^'\"\s#]+)")
FROM = re.compile(r"^\s*FROM\s+(?:--platform=\S+\s+)?(\S+)(?:\s+AS\s+(\S+))?", re.IGNORECASE)

SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", "dist", ".pytest_cache"}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.message}"


def _files(root: Path, pattern: str) -> list[Path]:
    return sorted(p for p in root.rglob(pattern) if p.is_file() and not (set(p.parts) & SKIP_DIRS))


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def check_workflow(root: Path, path: Path) -> list[Finding]:
    findings = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        m = USES.match(line)
        if not m:
            continue
        ref = m.group(1)
        if ref.startswith("./"):
            continue
        if ref.startswith("docker://"):
            if not DIGEST.search(ref):
                findings.append(
                    Finding(
                        _rel(root, path),
                        n,
                        f"docker action not pinned by digest: {ref}",
                    )
                )
            continue
        _, _, version = ref.partition("@")
        if not SHA40.match(version):
            findings.append(
                Finding(
                    _rel(root, path),
                    n,
                    f"action not pinned to a full commit SHA: {ref}",
                )
            )
    return findings


def check_compose(root: Path, path: Path) -> list[Finding]:
    findings = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        m = IMAGE.match(line)
        if m and not DIGEST.search(m.group(1)):
            findings.append(
                Finding(_rel(root, path), n, f"image not pinned by digest: {m.group(1)}")
            )
    return findings


def check_dockerfile(root: Path, path: Path) -> list[Finding]:
    findings = []
    stages: set[str] = set()
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        m = FROM.match(line)
        if not m:
            continue
        image, alias = m.group(1), m.group(2)
        if image.lower() == "scratch" or image.lower() in stages:
            pass
        elif not DIGEST.search(image):
            findings.append(Finding(_rel(root, path), n, f"FROM not pinned by digest: {image}"))
        if alias:
            stages.add(alias.lower())
    # COPY --from=<image> pulls an image too.
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        m = re.match(r"^\s*COPY\s+.*--from=(\S+)", line, re.IGNORECASE)
        if not m:
            continue
        src = m.group(1)
        if src.lower() in stages or src.isdigit() or DIGEST.search(src):
            continue
        msg = f"COPY --from image not pinned by digest: {src}"
        findings.append(Finding(_rel(root, path), n, msg))
    return findings


def check_lockfiles(root: Path) -> list[Finding]:
    findings = []
    if (root / "backend" / "pyproject.toml").exists() and not (
        root / "backend" / "uv.lock"
    ).exists():
        findings.append(Finding("backend/uv.lock", 0, "lockfile missing"))
    if (root / "frontend" / "package.json").exists() and not (
        root / "frontend" / "package-lock.json"
    ).exists():
        findings.append(Finding("frontend/package-lock.json", 0, "lockfile missing"))
    return findings


def check(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    wf_dir = root / ".github" / "workflows"
    if wf_dir.is_dir():
        for p in sorted(wf_dir.glob("*.y*ml")):
            findings += check_workflow(root, p)
    for pattern in ("docker-compose*.y*ml", "compose*.y*ml"):
        for p in _files(root, pattern):
            findings += check_compose(root, p)
    for pattern in ("Dockerfile", "*.Dockerfile", "Dockerfile.*"):
        for p in _files(root, pattern):
            findings += check_dockerfile(root, p)
    findings += check_lockfiles(root)
    return findings


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0] if argv else ".").resolve()
    findings = check(root)
    for f in findings:
        print(f"UNPINNED {f}")
    if findings:
        print(f"check_pins: FAIL ({len(findings)} finding(s))")
        return 1
    print("check_pins: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
