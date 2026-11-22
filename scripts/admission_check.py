#!/usr/bin/env python3
"""Package admission check (C14, T-16).

Usage: python scripts/admission_check.py <pypi|npm> <name> [version]

Prints PASS, REVIEW or FAIL with reasons. Exit code 0 = PASS, 1 = FAIL, 2 = REVIEW.

Checks, in order:
  1. Exists: the package is on the public registry. A name an AI assistant
     hallucinated (slopsquatting) fails here.
  2. Intended package: the name is not within edit distance 2 of a different
     well-known package (scripts/known_packages.txt), i.e. not a typosquat.
  3. Credible history: first release older than MIN_AGE_DAYS, at least
     MIN_RELEASES releases, a linked source repository.

Uses only the standard library so it runs before anything is installed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

MIN_AGE_DAYS = 90
MIN_RELEASES = 5
MAX_TYPO_DISTANCE = 2
# A version published less than this many days ago is flagged for review:
# most malicious releases of real packages are caught within days.
MIN_VERSION_AGE_DAYS = 14

KNOWN_PACKAGES_FILE = Path(__file__).with_name("known_packages.txt")
SOURCE_HOSTS = ("github.com", "gitlab.com", "codeberg.org", "bitbucket.org", "sr.ht")
USER_AGENT = "rubrica-admission-check/1.0"
REGISTRY_PREFIXES = ("https://pypi.org/pypi/", "https://registry.npmjs.org/")

PASS, REVIEW, FAIL = "PASS", "REVIEW", "FAIL"
EXIT_CODES = {PASS: 0, FAIL: 1, REVIEW: 2}

Fetcher = Callable[[str], dict | None]


@dataclass
class PackageInfo:
    ecosystem: str
    name: str
    summary: str = ""
    project_url: str = ""
    first_release: datetime | None = None
    latest_release: datetime | None = None
    latest_version: str = ""
    release_count: int = 0
    maintainers: list[str] = field(default_factory=list)
    source_repo: str = ""
    version_published: datetime | None = None
    version_exists: bool = True


@dataclass
class Result:
    verdict: str
    reasons: list[str]
    info: PackageInfo | None


# ---------------------------------------------------------------- registry I/O


def http_fetch(url: str) -> dict | None:
    """GET a registry JSON document. Returns None on 404."""
    if not url.startswith(REGISTRY_PREFIXES):
        raise ValueError(f"refusing non-registry URL: {url}")
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    req = urllib.request.Request(url, headers=headers)  # noqa: S310 (prefix checked above)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(value)
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _find_source_repo(urls: list[str]) -> str:
    """First URL on a known code host, trimmed to https://host/owner/repo."""
    for url in urls:
        if not url:
            continue
        url = re.sub(r"^git\+", "", url.strip())
        url = re.sub(r"^git://", "https://", url)
        url = re.sub(r"^ssh://git@", "https://", url)
        parsed = urllib.parse.urlparse(url)
        host = parsed.netloc.split("@")[-1].lower()
        host = host.removeprefix("www.")
        if host in SOURCE_HOSTS:
            parts = [p for p in parsed.path.split("/") if p][:2]
            if len(parts) == 2:
                return f"https://{host}/{parts[0]}/{parts[1].removesuffix('.git')}"
    return ""


def _split_people(*values: str | None) -> list[str]:
    """PyPI's author/maintainer fields are free text, often comma-separated."""
    people: list[str] = []
    for value in values:
        for person in re.split(r",| and ", value or ""):
            person = person.strip()
            if person and person not in people:
                people.append(person)
    return people


def pypi_info(name: str, version: str | None, fetch: Fetcher) -> PackageInfo | None:
    data = fetch(f"https://pypi.org/pypi/{urllib.parse.quote(name)}/json")
    if data is None:
        return None
    info = data.get("info", {})
    releases = data.get("releases", {})
    upload_times: dict[str, datetime] = {}
    for ver, files in releases.items():
        times = [_parse_time(f.get("upload_time_iso_8601")) for f in files]
        times = [t for t in times if t]
        if times:
            upload_times[ver] = min(times)
    urls_by_label = info.get("project_urls") or {}
    preferred = ("source", "source code", "repository", "code", "github", "homepage")
    project_urls = sorted(
        urls_by_label.values(),
        key=lambda u: next(
            (
                i
                for i, lbl in enumerate(preferred)
                for k, v in urls_by_label.items()
                if v == u and k.lower() == lbl
            ),
            len(preferred),
        ),
    )
    # PyPI's JSON API doesn't expose account maintainers; author/maintainer text
    # is the best available signal, so the report labels it as such.
    maintainers = _split_people(info.get("author"), info.get("maintainer"))
    pkg = PackageInfo(
        ecosystem="pypi",
        name=info.get("name", name),
        summary=info.get("summary") or "",
        project_url=info.get("project_url") or f"https://pypi.org/project/{name}/",
        first_release=min(upload_times.values(), default=None),
        latest_release=max(upload_times.values(), default=None),
        latest_version=info.get("version", ""),
        release_count=len(upload_times),
        maintainers=maintainers,
        source_repo=_find_source_repo(project_urls + [info.get("home_page") or ""]),
    )
    if version:
        pkg.version_exists = version in upload_times
        pkg.version_published = upload_times.get(version)
    return pkg


def npm_info(name: str, version: str | None, fetch: Fetcher) -> PackageInfo | None:
    # Scoped names keep the @ but encode the slash.
    data = fetch("https://registry.npmjs.org/" + urllib.parse.quote(name, safe="@"))
    if data is None:
        return None
    times = {k: _parse_time(v) for k, v in (data.get("time") or {}).items()}
    version_times = {k: v for k, v in times.items() if k not in ("created", "modified") and v}
    repo = data.get("repository") or {}
    repo_url = repo.get("url", "") if isinstance(repo, dict) else str(repo)
    latest = (data.get("dist-tags") or {}).get("latest", "")
    pkg = PackageInfo(
        ecosystem="npm",
        name=data.get("name", name),
        summary=data.get("description") or "",
        project_url=f"https://www.npmjs.com/package/{name}",
        first_release=times.get("created") or min(version_times.values(), default=None),
        latest_release=max(version_times.values(), default=None),
        latest_version=latest,
        release_count=len(data.get("versions") or {}),
        maintainers=[
            m.get("name", "") for m in data.get("maintainers") or [] if isinstance(m, dict)
        ],
        source_repo=_find_source_repo([repo_url, data.get("homepage") or ""]),
    )
    if version:
        pkg.version_exists = version in (data.get("versions") or {})
        pkg.version_published = version_times.get(version)
    return pkg


# ---------------------------------------------------------------- name checks


def normalise(ecosystem: str, name: str) -> str:
    name = name.strip().lower()
    if ecosystem == "pypi":
        name = re.sub(r"[-_.]+", "-", name)  # PEP 503
    return name


def edit_distance(a: str, b: str) -> int:
    """Damerau-Levenshtein (optimal string alignment) distance."""
    prev2: list[int] = []
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if i > 1 and j > 1 and ca == b[j - 2] and a[i - 2] == cb:
                cur[j] = min(cur[j], prev2[j - 2] + 1)
        prev2, prev = prev, cur
    return prev[-1]


def load_known(ecosystem: str, path: Path = KNOWN_PACKAGES_FILE) -> set[str]:
    known: set[str] = set()
    if not path.exists():
        return known
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        eco, _, pkg = line.partition(" ")
        if eco == ecosystem and pkg.strip():
            known.add(normalise(ecosystem, pkg.strip()))
    return known


def lookalikes(ecosystem: str, name: str, known: set[str]) -> list[str]:
    target = normalise(ecosystem, name)
    if target in known:
        return []
    close = [k for k in known if edit_distance(target, k) <= MAX_TYPO_DISTANCE]
    # Very short names collide with everything; only flag them on distance 1.
    if len(target) <= 4:
        close = [k for k in close if edit_distance(target, k) <= 1]
    return sorted(close)


# ---------------------------------------------------------------- the check


def check(
    ecosystem: str,
    name: str,
    version: str | None = None,
    *,
    fetch: Fetcher = http_fetch,
    known: set[str] | None = None,
    now: datetime | None = None,
) -> Result:
    if ecosystem not in ("pypi", "npm"):
        return Result(FAIL, [f"unknown ecosystem {ecosystem!r} (use pypi or npm)"], None)
    now = now or datetime.now(UTC)
    known = load_known(ecosystem) if known is None else known

    getter = pypi_info if ecosystem == "pypi" else npm_info
    try:
        info = getter(name, version, fetch)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return Result(
            REVIEW,
            [f"could not reach the registry ({type(exc).__name__}); retry"],
            None,
        )

    if info is None:
        reasons = [f"does not exist on {ecosystem}: possibly a hallucinated or mistyped name"]
        similar = lookalikes(ecosystem, name, known)
        if similar:
            reasons.append("did you mean: " + ", ".join(similar) + "?")
        return Result(FAIL, reasons, None)

    reasons: list[str] = []
    verdict = PASS

    def review(msg: str) -> None:
        nonlocal verdict
        verdict = REVIEW if verdict == PASS else verdict
        reasons.append(msg)

    if version and not info.version_exists:
        return Result(FAIL, [f"version {version} does not exist"], info)

    similar = lookalikes(ecosystem, name, known)
    if similar:
        review("name is close to well-known package(s): " + ", ".join(similar) + " (typosquat?)")

    if info.first_release is None:
        review("no release dates published")
    else:
        age = (now - info.first_release).days
        if age < MIN_AGE_DAYS:
            review(f"first release only {age} days ago (< {MIN_AGE_DAYS})")
    if info.release_count < MIN_RELEASES:
        review(f"only {info.release_count} release(s) (< {MIN_RELEASES})")
    if not info.source_repo:
        review("no linked source repository")
    if version and info.version_published:
        vage = (now - info.version_published).days
        if vage < MIN_VERSION_AGE_DAYS:
            review(f"version {version} published only {vage} days ago (< {MIN_VERSION_AGE_DAYS})")

    if verdict == PASS:
        reasons.append("exists, not a lookalike, credible release history, source linked")
    return Result(verdict, reasons, info)


def _fmt_date(dt: datetime | None) -> str:
    return dt.date().isoformat() if dt else "unknown"


def report(ecosystem: str, name: str, version: str | None, result: Result) -> str:
    lines = [f"admission_check {ecosystem} {name}" + (f" {version}" if version else "")]
    lines.append(f"RESULT: {result.verdict}")
    lines += [f"  - {r}" for r in result.reasons]
    info = result.info
    if info:
        people = "authors:    " if info.ecosystem == "pypi" else "maintainers:"
        people_list = ", ".join(info.maintainers) or "not listed"
        lines += [
            f"  summary:         {info.summary or '(none)'}",
            f"  project:         {info.project_url}",
            f"  source repo:     {info.source_repo or '(none)'}",
            f"  first release:   {_fmt_date(info.first_release)}",
            f"  latest release:  {info.latest_version} on {_fmt_date(info.latest_release)}",
            f"  releases:        {info.release_count}",
            f"  {people}     {len(info.maintainers)} ({people_list})",
        ]
        if version:
            lines.append(f"  version date:    {_fmt_date(info.version_published)}")
    lines.append(f"  checked at:      {datetime.now(UTC).isoformat(timespec='seconds')}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ecosystem", choices=["pypi", "npm"])
    parser.add_argument("name")
    parser.add_argument("version", nargs="?")
    args = parser.parse_args(argv)
    result = check(args.ecosystem, args.name, args.version)
    print(report(args.ecosystem, args.name, args.version, result))
    return EXIT_CODES[result.verdict]


if __name__ == "__main__":
    sys.exit(main())
