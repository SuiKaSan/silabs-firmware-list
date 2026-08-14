"""Assemble the firmwares.json manifest from a GitHub release payload."""

import sys
from typing import Any, Callable, Dict, List, Optional

from firmware_list.parse import parse_gbl_filename

HashFetcher = Callable[[str], str]


def build_manifest(
    release: Dict[str, Any],
    previous: Optional[Dict[str, Any]],
    fetch_sha256: HashFetcher,
    owner: str,
    repo: str,
    refreshed_at: str,
) -> Dict[str, Any]:
    """Build a manifest dict for `release`.

    `fetch_sha256(url)` is called only for firmwares whose url+size do not
    match a record in `previous` (see ADR-0003: unchanged url and size mean
    the file content is unchanged, so the previous sha256 is reused).
    Assets that are not `.gbl` or whose filename cannot be parsed are
    skipped with a warning. If nothing parses — empty release (assets may
    still be uploading) or a filename-convention break — raises ValueError
    so the caller leaves the previous manifest untouched (ADR-0001).
    """
    prev_by_url: Dict[str, Dict[str, Any]] = {
        fw["url"]: fw for fw in (previous or {}).get("firmwares", [])
    }

    firmwares: List[Dict[str, Any]] = []
    for asset in release.get("assets", []):
        name = asset.get("name", "")
        try:
            fields = parse_gbl_filename(name)
        except ValueError as exc:
            print(f"warning: skipping asset {name!r}: {exc}", file=sys.stderr)
            continue
        url = asset["browser_download_url"]
        size = asset["size"]
        prev = prev_by_url.get(url)
        if prev and prev.get("size") == size and prev.get("sha256"):
            sha256 = prev["sha256"]
        else:
            sha256 = fetch_sha256(url)
        firmwares.append({**fields, "filename": name, "url": url,
                          "size": size, "sha256": sha256})

    if not firmwares:
        raise ValueError(
            "no parseable .gbl assets in this release — refusing to write "
            "an empty manifest (release may still be uploading, or the "
            "filename convention changed)"
        )

    return {
        "owner": owner,
        "repo": repo,
        "releaseTag": release["tag_name"],
        "releasePublishedAt": release["published_at"],
        "refreshedAt": refreshed_at,
        "count": len(firmwares),
        "firmwares": firmwares,
    }
