"""Assemble the firmwares.json manifest from GitHub release payloads."""

import sys
from typing import Any, Callable, Dict, List, Optional, Sequence

from firmware_list.parse import parse_gbl_filename

HashFetcher = Callable[[str], str]
KeepFilter = Callable[[Dict[str, Any]], bool]


def manifest_changed(
    old: Optional[Dict[str, Any]],
    new: Dict[str, Any],
) -> bool:
    """True when the manifest's substance changed.

    `refreshedAt` is a per-run timestamp and is ignored: when nothing else
    moved, callers should keep the committed file (and its history) as is.
    """
    if old is None:
        return True
    keys = (set(old) | set(new)) - {"refreshedAt"}
    return any(old.get(k) != new.get(k) for k in keys)


def pick_latest_releases(
    releases: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """From a `/releases` listing (newest first), keep the latest stable
    release and the latest pre-release, stable first."""
    stable = next((r for r in releases if not r.get("prerelease")), None)
    pre = next((r for r in releases if r.get("prerelease")), None)
    return [r for r in (stable, pre) if r is not None]


def build_manifest(
    releases: Sequence[Dict[str, Any]],
    previous: Optional[Dict[str, Any]],
    fetch_sha256: HashFetcher,
    owner: str,
    repo: str,
    refreshed_at: str,
    keep: Optional[KeepFilter] = None,
) -> Dict[str, Any]:
    """Build a manifest dict for the given releases.

    Each release contributes its (filtered) firmwares; every record carries
    the `releaseTag` it came from and a `prerelease` flag. `fetch_sha256(url)`
    is called only for firmwares whose url+size do not match a record in
    `previous` (see ADR-0003: unchanged url and size mean the file content
    is unchanged, so the previous sha256 is reused). `keep(firmware)`, when
    given, restricts the manifest to firmwares it accepts (applied after
    parsing, before hashing). Assets that are not `.gbl` or whose filename
    cannot be parsed are skipped with a warning. If nothing survives —
    empty releases (assets may still be uploading), a filename-convention
    break, or the filter rejecting everything — raises ValueError so the
    caller leaves the previous manifest untouched (ADR-0001).
    """
    prev_by_url: Dict[str, Dict[str, Any]] = {
        fw["url"]: fw for fw in (previous or {}).get("firmwares", [])
    }

    firmwares: List[Dict[str, Any]] = []
    releases_meta: List[Dict[str, Any]] = []
    for release in releases:
        releases_meta.append({
            "tag": release["tag_name"],
            "publishedAt": release["published_at"],
            "prerelease": bool(release.get("prerelease")),
        })
        for asset in release.get("assets", []):
            name = asset.get("name", "")
            try:
                fields = parse_gbl_filename(name)
            except ValueError as exc:
                print(f"warning: skipping asset {name!r}: {exc}",
                      file=sys.stderr)
                continue
            url = asset["browser_download_url"]
            size = asset["size"]
            firmware: Dict[str, Any] = {
                **fields,
                "filename": name,
                "url": url,
                "size": size,
                "releaseTag": release["tag_name"],
                "prerelease": bool(release.get("prerelease")),
            }
            if keep is not None and not keep(firmware):
                continue
            prev = prev_by_url.get(url)
            if prev and prev.get("size") == size and prev.get("sha256"):
                sha256 = prev["sha256"]
            else:
                sha256 = fetch_sha256(url)
            firmware["sha256"] = sha256
            firmwares.append(firmware)

    if not firmwares:
        raise ValueError(
            "no firmware records survived — refusing to write an empty "
            "manifest (releases may still be uploading, the filename "
            "convention changed, or the keep filter rejected everything)"
        )

    return {
        "owner": owner,
        "repo": repo,
        "releases": releases_meta,
        "refreshedAt": refreshed_at,
        "count": len(firmwares),
        "firmwares": firmwares,
    }
