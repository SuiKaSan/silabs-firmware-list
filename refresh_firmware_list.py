"""Regenerate firmwares.json from the latest release of
Nerivec/silabs-firmware-builder.

Design decisions live in the upstream research repo:
- data source & caching  -> ADR-0001 (hourly pull of releases/latest)
- deployment             -> ADR-0002 (standalone repo, GitHub Actions, raw URL)
- sha256 incrementality  -> ADR-0003 (reuse hash when url+size unchanged)

On any failure this script exits non-zero WITHOUT touching firmwares.json,
so the previously committed manifest is preserved (ADR-0001 failure policy).

GITHUB_TOKEN is optional; when set (as in CI) it lifts the GitHub API rate
limit from 60/h to 1000/h.
"""

import datetime as dt
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

from firmware_list.manifest import build_manifest

API_URL = (
    "https://api.github.com/repos/Nerivec/silabs-firmware-builder"
    "/releases/latest"
)
OWNER = "Nerivec"
REPO = "silabs-firmware-builder"
OUTPUT = Path(__file__).resolve().parent / "firmwares.json"
CHUNK = 1 << 16
USER_AGENT = "silabs-firmware-list-sync"


def api_headers() -> Dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def http_get_json(url: str) -> Any:
    req = urllib.request.Request(url, headers=api_headers())
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def sha256_of(url: str) -> str:
    """Stream-download `url` and return its sha256 hex digest."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    digest = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=300) as resp:
        for chunk in iter(lambda: resp.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_previous() -> Optional[Dict[str, Any]]:
    if OUTPUT.exists():
        previous: Dict[str, Any] = json.loads(
            OUTPUT.read_text(encoding="utf-8")
        )
        return previous
    return None


def main() -> int:
    release = http_get_json(API_URL)
    refreshed_at = dt.datetime.now(dt.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    manifest = build_manifest(
        release,
        load_previous(),
        sha256_of,
        owner=OWNER,
        repo=REPO,
        refreshed_at=refreshed_at,
    )
    OUTPUT.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {manifest['count']} firmwares from {manifest['releaseTag']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
