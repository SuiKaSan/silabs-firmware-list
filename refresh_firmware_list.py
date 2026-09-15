"""Regenerate firmwares.json and mirror firmware files from the latest
stable + pre-release of Nerivec/silabs-firmware-builder.

Design decisions live in the upstream research repo:
- data source & caching  -> ADR-0001 (hourly pull, failure keeps old state)
- deployment             -> ADR-0002 (standalone repo, GitHub Actions, raw URL)
- sha256 incrementality  -> ADR-0003 (reuse hash when url+size unchanged)
- firmware mirroring     -> ADR-0004 (files in firmwares/, downloadUrl on raw)

On any failure this script exits non-zero WITHOUT touching firmwares.json
or firmwares/, so the previously committed state is preserved (ADR-0001
failure policy).

GITHUB_TOKEN is optional; when set (as in CI) it lifts the GitHub API rate
limit from 60/h to 1000/h.
"""

import datetime as dt
import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

from firmware_list.files import cached_download, prune_and_ensure
from firmware_list.manifest import (
    build_manifest,
    manifest_changed,
    pick_latest_releases,
)

API_URL = (
    "https://api.github.com/repos/Nerivec/silabs-firmware-builder"
    "/releases?per_page=30"
)
OWNER = "Nerivec"
REPO = "silabs-firmware-builder"
ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "firmwares.json"
FIRMWARES_DIR = ROOT / "firmwares"
# This repository, "owner/name" — CI sets GITHUB_REPOSITORY automatically.
HOST_REPO = os.environ.get("GITHUB_REPOSITORY", "SuiKaSan/silabs-firmware-list")
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


def fetch_bytes(
    url: str, attempts: int = 3, backoff_s: int = 3
) -> bytes:
    """Download `url` fully, retrying transient network errors."""
    last_error: Optional[Exception] = None
    for attempt in range(attempts):
        if attempt:
            time.sleep(backoff_s * attempt)
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": USER_AGENT}
            )
            with urllib.request.urlopen(req, timeout=300) as resp:
                data: bytes = resp.read()
                return data
        except (urllib.error.URLError, OSError) as exc:
            last_error = exc
    raise RuntimeError(
        f"failed to download {url} after {attempts} attempts"
    ) from last_error


def load_previous() -> Optional[Dict[str, Any]]:
    if OUTPUT.exists():
        previous: Dict[str, Any] = json.loads(
            OUTPUT.read_text(encoding="utf-8")
        )
        return previous
    return None


def is_sonoff_dongle(firmware: Dict[str, Any]) -> bool:
    """Keep filter: only SONOFF dongle series.

    Covers both model spellings: `dongle-*` (Dongle-L/M/PMG24) and the
    older `zbdongle-*` (Dongle-E, named after the ZBDongle product line).
    """
    model = str(firmware.get("model", ""))
    return firmware.get("brand") == "sonoff" and (
        model.startswith("dongle") or model.startswith("zbdongle")
    )


def main() -> int:
    listing = http_get_json(API_URL)
    releases = pick_latest_releases(listing)
    if not releases:
        print("error: no releases found upstream", file=sys.stderr)
        return 1
    refreshed_at = dt.datetime.now(dt.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    manifest = build_manifest(
        releases,
        load_previous(),
        lambda url: cached_download(url, FIRMWARES_DIR, fetch_bytes),
        owner=OWNER,
        repo=REPO,
        host_repo=HOST_REPO,
        refreshed_at=refreshed_at,
        keep=is_sonoff_dongle,
    )
    # converge the mirror: prune stale, replace mismatched, add missing
    prune_and_ensure(manifest, FIRMWARES_DIR, fetch_bytes)

    previous = load_previous()
    if not manifest_changed(previous, manifest):
        tags = ", ".join(r["tag"] for r in manifest["releases"])
        print(f"no change (except refreshedAt) — keeping {tags}")
        return 0
    OUTPUT.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    tags = ", ".join(r["tag"] for r in manifest["releases"])
    print(f"wrote {manifest['count']} firmwares from {tags}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
