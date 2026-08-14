from firmware_list.manifest import build_manifest

RELEASE = {
    "tag_name": "v2025.6.2-update1",
    "published_at": "2026-08-01T12:00:00Z",
    "assets": [
        {
            "name": "sonoff_dongle-pmg24_zigbee_ncp_8.2.2.0_460800_sw_flow.gbl",
            "browser_download_url": (
                "https://github.com/Nerivec/silabs-firmware-builder/"
                "releases/download/v2025.6.2-update1/"
                "sonoff_dongle-pmg24_zigbee_ncp_8.2.2.0_460800_sw_flow.gbl"
            ),
            "size": 245760,
        },
        {
            "name": "nabucasa_skyconnect_bootloader_3.1.2.gbl",
            "browser_download_url": (
                "https://github.com/Nerivec/silabs-firmware-builder/"
                "releases/download/v2025.6.2-update1/"
                "nabucasa_skyconnect_bootloader_3.1.2.gbl"
            ),
            "size": 231456,
        },
    ],
}


def make_fetcher(spy: list) -> "callable":
    def fetch(url: str) -> str:
        spy.append(url)
        return f"hash-of-{url}"

    return fetch


def test_builds_manifest_for_new_release():
    fetched: list = []
    manifest = build_manifest(
        RELEASE,
        None,
        make_fetcher(fetched),
        owner="Nerivec",
        repo="silabs-firmware-builder",
        refreshed_at="2026-08-14T07:07:00Z",
    )
    assert manifest["owner"] == "Nerivec"
    assert manifest["repo"] == "silabs-firmware-builder"
    assert manifest["releaseTag"] == "v2025.6.2-update1"
    assert manifest["releasePublishedAt"] == "2026-08-01T12:00:00Z"
    assert manifest["refreshedAt"] == "2026-08-14T07:07:00Z"
    assert manifest["count"] == 2

    first = manifest["firmwares"][0]
    assert first["brand"] == "sonoff"
    assert first["model"] == "dongle-pmg24"
    assert first["type"] == "zigbee_ncp"
    assert first["version"] == "8.2.2.0"
    assert first["baudRate"] == 460800
    assert first["flowControl"] == "sw_flow"
    assert first["filename"] == RELEASE["assets"][0]["name"]
    assert first["url"] == RELEASE["assets"][0]["browser_download_url"]
    assert first["size"] == 245760
    assert first["sha256"] == f"hash-of-{first['url']}"

    # new release, no previous manifest: every firmware must be hashed
    assert len(fetched) == 2


def test_reuses_sha256_when_url_and_size_unchanged():
    previous = build_manifest(
        RELEASE,
        None,
        lambda url: "stale-hash",
        owner="Nerivec",
        repo="silabs-firmware-builder",
        refreshed_at="2026-08-14T06:07:00Z",
    )
    fetched: list = []
    manifest = build_manifest(
        RELEASE,
        previous,
        make_fetcher(fetched),
        owner="Nerivec",
        repo="silabs-firmware-builder",
        refreshed_at="2026-08-14T07:07:00Z",
    )
    # hourly rerun against the same release: nothing downloaded
    assert fetched == []
    assert all(fw["sha256"] == "stale-hash" for fw in manifest["firmwares"])
    assert manifest["refreshedAt"] == "2026-08-14T07:07:00Z"


def test_rehashes_when_size_changes():
    import copy

    previous = build_manifest(
        RELEASE,
        None,
        lambda url: "stale-hash",
        owner="Nerivec",
        repo="silabs-firmware-builder",
        refreshed_at="2026-08-14T06:07:00Z",
    )
    # upstream replaced the asset under the same url with a different size
    rerelease = copy.deepcopy(RELEASE)
    rerelease["assets"][0]["size"] = 999999

    fetched: list = []
    manifest = build_manifest(
        rerelease,
        previous,
        make_fetcher(fetched),
        owner="Nerivec",
        repo="silabs-firmware-builder",
        refreshed_at="2026-08-14T07:07:00Z",
    )
    changed = manifest["firmwares"][0]
    unchanged = manifest["firmwares"][1]
    assert changed["size"] == 999999
    assert changed["sha256"] == f"hash-of-{changed['url']}"
    assert unchanged["sha256"] == "stale-hash"
    assert len(fetched) == 1


def test_refuses_empty_manifest_when_gbl_assets_exist():
    import copy
    import pytest

    broken = copy.deepcopy(RELEASE)
    for asset in broken["assets"]:
        asset["name"] = "totally_unknown_convention.gbl"
    with pytest.raises(ValueError):
        build_manifest(
            broken,
            None,
            lambda url: "hash",
            owner="Nerivec",
            repo="silabs-firmware-builder",
            refreshed_at="2026-08-14T07:07:00Z",
        )
