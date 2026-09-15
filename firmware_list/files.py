"""Mirror firmware files into the repo's firmwares/ directory.

The manifest's `downloadUrl` points at these mirrored files on
raw.githubusercontent.com (CORS-enabled), so a web frontend can fetch
the bytes directly for flashing (see ADR-0004). The directory converges
to exactly the current manifest: stale files are pruned, missing or
mismatched files are (re-)downloaded, unchanged files are never touched.
"""

import hashlib
from pathlib import Path
from typing import Any, Callable, Dict, List

from firmware_list.manifest import upstream_url

ByteDownloader = Callable[[str], bytes]


def cached_download(
    url: str,
    directory: Path,
    download: ByteDownloader,
) -> str:
    """Return the sha256 of the firmware at `url`, mirroring it on disk.

    If the file is already mirrored in `directory` (matched by the url's
    last path segment), hash the local bytes — no network. Otherwise
    download via `download(url)` and write the bytes to disk.
    """
    path = directory / url.rsplit("/", 1)[-1]
    if path.exists():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    data = download(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def prune_and_ensure(
    manifest: Dict[str, Any],
    directory: Path,
    download: ByteDownloader,
) -> None:
    """Converge `directory` to exactly the manifest's firmware files.

    Deletes files not referenced by the manifest, (re-)downloads any
    record whose file is missing or whose on-disk bytes hash to something
    other than the manifest's sha256, and leaves matching files alone.
    Downloads come from the upstream release, not the mirror.
    """
    records: List[Dict[str, Any]] = manifest["firmwares"]
    keep = {fw["filename"] for fw in records}

    if directory.exists():
        for path in directory.iterdir():
            if path.is_file() and path.name not in keep:
                path.unlink()

    for fw in records:
        path = directory / fw["filename"]
        if not path.exists() or (
            hashlib.sha256(path.read_bytes()).hexdigest() != fw["sha256"]
        ):
            data = download(upstream_url(manifest, fw))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
