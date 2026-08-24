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
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

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


def download_and_hash(url: str, attempts: int = 3, backoff_s: int = 3) -> str:
    """Stream-download `url` and return its sha256 hex digest.

    Retries on transient network errors so one flaky CDN connection
    doesn't fail the whole run (each retry restarts the stream and the
    digest from scratch).
    """
    last_error: Optional[Exception] = None
    for attempt in range(attempts):
        if attempt:
            time.sleep(backoff_s * attempt)
        digest = hashlib.sha256()
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": USER_AGENT}
            )
            with urllib.request.urlopen(req, timeout=300) as resp:
                for chunk in iter(lambda: resp.read(CHUNK), b""):
                    digest.update(chunk)
            return digest.hexdigest()
        except (urllib.error.URLError, OSError) as exc:
            last_error = exc
    raise RuntimeError(f"failed to download {url} after {attempts} attempts") \
        from last_error


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
    previous = load_previous()
    manifest = build_manifest(
        releases,
        previous,
        download_and_hash,
        owner=OWNER,
        repo=REPO,
        refreshed_at=refreshed_at,
        keep=is_sonoff_dongle,
    )
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
