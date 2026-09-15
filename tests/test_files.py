import hashlib

from firmware_list.files import cached_download, prune_and_ensure

URL = "https://github.com/o/r/releases/download/t/foo_zigbee_ncp_1.0_115200_sw_flow.gbl"
FILENAME = URL.rsplit("/", 1)[-1]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_cached_download_writes_file_and_returns_hash(tmp_path):
    data = b"firmware-bytes"
    downloads = []

    def fake_download(url: str) -> bytes:
        downloads.append(url)
        return data

    digest = cached_download(URL, tmp_path, fake_download)
    assert digest == sha256_bytes(data)
    assert (tmp_path / FILENAME).read_bytes() == data
    assert downloads == [URL]


def test_cached_download_hits_disk_on_second_call(tmp_path):
    downloads = []

    def fake_download(url: str) -> bytes:
        downloads.append(url)
        return b"firmware-bytes"

    first = cached_download(URL, tmp_path, fake_download)
    second = cached_download(URL, tmp_path, fake_download)
    assert first == second
    assert len(downloads) == 1  # second call served from disk


def test_prune_and_ensure_removes_stale_and_downloads_missing(tmp_path):
    keep_file = tmp_path / FILENAME
    keep_file.write_bytes(b"current")
    stale = tmp_path / "old_brand_zigbee_ncp_0.1_115200_sw_flow.gbl"
    stale.write_bytes(b"obsolete")

    manifest = {
        "owner": "Nerivec",
        "repo": "silabs-firmware-builder",
        "firmwares": [
            {
                "filename": FILENAME,
                "releaseTag": "v2025.6.2-update1",
                "sha256": sha256_bytes(b"current"),
            },
            {
                "filename": "bar_bootloader_2.0.gbl",
                "releaseTag": "v2026.6.1-pre2",
                "sha256": sha256_bytes(b"bl-bytes"),
            },
        ],
    }
    downloaded = []

    def fake_download(url: str) -> bytes:
        downloaded.append(url)
        return b"bl-bytes"

    prune_and_ensure(manifest, tmp_path, fake_download)
    assert not stale.exists()
    assert keep_file.read_bytes() == b"current"
    assert (tmp_path / "bar_bootloader_2.0.gbl").read_bytes() == b"bl-bytes"
    # downloads go to the UPSTREAM release, rebuilt from tag+filename —
    # the manifest's own url field points at the mirror, not the source
    assert downloaded == [
        "https://github.com/Nerivec/silabs-firmware-builder"
        "/releases/download/v2026.6.1-pre2/bar_bootloader_2.0.gbl"
    ]


def test_prune_and_ensure_replaces_mismatched_file(tmp_path):
    (tmp_path / FILENAME).write_bytes(b"tampered-or-outdated")
    manifest = {
        "owner": "Nerivec",
        "repo": "silabs-firmware-builder",
        "firmwares": [
            {
                "filename": FILENAME,
                "releaseTag": "v2025.6.2-update1",
                "sha256": sha256_bytes(b"current"),
            }
        ],
    }
    prune_and_ensure(manifest, tmp_path, lambda url: b"current")
    assert (tmp_path / FILENAME).read_bytes() == b"current"


def test_prune_and_ensure_noop_when_in_sync(tmp_path):
    (tmp_path / FILENAME).write_bytes(b"current")
    manifest = {
        "owner": "Nerivec",
        "repo": "silabs-firmware-builder",
        "firmwares": [
            {
                "filename": FILENAME,
                "releaseTag": "v2025.6.2-update1",
                "sha256": sha256_bytes(b"current"),
            }
        ],
    }
    prune_and_ensure(manifest, tmp_path, lambda url: (_ for _ in ()).throw(
        AssertionError("should not download when in sync")))
    assert (tmp_path / FILENAME).read_bytes() == b"current"
