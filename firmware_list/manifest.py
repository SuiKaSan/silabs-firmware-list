"""Assemble the firmwares.json manifest from a GitHub release payload."""

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
    skipped rather than failing the whole run.
    """
    prev_by_url: Dict[str, Dict[str, Any]] = {
        fw["url"]: fw for fw in (previous or {}).get("firmwares", [])
    }

    gbl_count = 0
    firmwares: List[Dict[str, Any]] = []
    for asset in release.get("assets", []):
        name = asset.get("name", "")
        if not name.endswith(".gbl"):
            continue
        gbl_count += 1
        try:
            fields = parse_gbl_filename(name)
        except ValueError:
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

    if gbl_count and not firmwares:
        # All assets failed to parse: almost certainly a filename-convention
        # break, not an actually empty release. Refuse to clobber the
        # previous manifest with an empty list (ADR-0001 failure policy).
        raise ValueError(
            f"release has {gbl_count} .gbl assets but none parsed"
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
