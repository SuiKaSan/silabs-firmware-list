import copy

import pytest

from firmware_list.manifest import build_manifest, manifest_changed

RELEASE = {
    "tag_name": "v2025.6.2-update1",
    "published_at": "2026-08-01T12:00:00Z",
    "prerelease": False,
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

PRE_RELEASE = {
    "tag_name": "v2026.6.1-pre1",
    "published_at": "2026-08-10T12:00:00Z",
    "prerelease": True,
    "assets": [
        {
            "name": "sonoff_dongle-pmg24_zigbee_ncp_8.2.2.1_460800_sw_flow.gbl",
            "browser_download_url": (
                "https://github.com/Nerivec/silabs-firmware-builder/"
                "releases/download/v2026.6.1-pre1/"
                "sonoff_dongle-pmg24_zigbee_ncp_8.2.2.1_460800_sw_flow.gbl"
            ),
            "size": 245999,
        },
    ],
}


class Recorder:
    """Fake hash fetcher that records which urls it was asked to hash."""

    def __init__(self) -> None:
        self.fetched: list = []

    def __call__(self, url: str) -> str:
        self.fetched.append(url)
        return f"hash-of-{url}"


def build(releases=None, previous=None, recorder=None, **overrides):
    kwargs = dict(
        owner="Nerivec",
        repo="silabs-firmware-builder",
        refreshed_at="2026-08-14T07:07:00Z",
    )
    kwargs.update(overrides)
    return build_manifest(
        releases if releases is not None else [RELEASE],
        previous,
        recorder or Recorder(),
        **kwargs,
    )


def stale_previous():
    return build(recorder=Recorder(), refreshed_at="2026-08-14T06:07:00Z")


def test_builds_manifest_for_new_release():
    recorder = Recorder()
    manifest = build(recorder=recorder)
    assert manifest["owner"] == "Nerivec"
    assert manifest["repo"] == "silabs-firmware-builder"
    assert manifest["refreshedAt"] == "2026-08-14T07:07:00Z"
    assert manifest["count"] == 2
    assert manifest["releases"] == [
        {
            "tag": "v2025.6.2-update1",
            "publishedAt": "2026-08-01T12:00:00Z",
            "prerelease": False,
        }
    ]

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
    assert len(recorder.fetched) == 2


def test_reuses_sha256_when_url_and_size_unchanged():
    previous = stale_previous()
    old_hashes = {fw["url"]: fw["sha256"] for fw in previous["firmwares"]}
    recorder = Recorder()
    manifest = build(previous=previous, recorder=recorder)
    # hourly rerun against the same release: nothing downloaded
    assert recorder.fetched == []
    assert all(
        fw["sha256"] == old_hashes[fw["url"]] for fw in manifest["firmwares"]
    )
    assert manifest["refreshedAt"] == "2026-08-14T07:07:00Z"


def test_rehashes_when_size_changes():
    rerelease = copy.deepcopy(RELEASE)
    rerelease["assets"][0]["size"] = 999999  # asset replaced under same url

    recorder = Recorder()
    manifest = build(releases=[rerelease], previous=stale_previous(),
                     recorder=recorder)
    changed = manifest["firmwares"][0]
    unchanged = manifest["firmwares"][1]
    assert changed["size"] == 999999
    assert changed["sha256"] == f"hash-of-{changed['url']}"
    assert len(recorder.fetched) == 1


def test_refuses_when_no_asset_parses():
    broken = copy.deepcopy(RELEASE)
    for asset in broken["assets"]:
        asset["name"] = "totally_unknown_convention.gbl"
    with pytest.raises(ValueError):
        build(releases=[broken])


def test_refuses_when_release_has_no_assets():
    with pytest.raises(ValueError):
        build(releases=[{"tag_name": "t", "published_at": "p",
                         "assets": []}])


def test_partial_failure_keeps_good_assets_and_warns(capsys):
    mixed = copy.deepcopy(RELEASE)
    mixed["assets"][1]["name"] = "totally_unknown_convention.gbl"
    manifest = build(releases=[mixed])
    assert manifest["count"] == 1
    assert manifest["firmwares"][0]["type"] == "zigbee_ncp"
    assert "warning" in capsys.readouterr().err


def test_keep_filter_restricts_manifest_and_reuses_hashes():
    from refresh_firmware_list import is_sonoff_dongle

    recorder = Recorder()
    manifest = build(previous=stale_previous(), recorder=recorder,
                     keep=is_sonoff_dongle)
    # only the sonoff dongle record survives; bootloader (nabucasa) is out
    assert manifest["count"] == 1
    assert manifest["firmwares"][0]["brand"] == "sonoff"
    assert manifest["firmwares"][0]["model"] == "dongle-pmg24"
    # and its hash was still reused from the previous manifest
    assert recorder.fetched == []


def test_keep_filter_rejects_manifest_when_everything_filtered_out():
    def keep_nothing(fw):
        return False

    with pytest.raises(ValueError):
        build(keep=keep_nothing)


def test_includes_latest_pre_release_flagged_on_records():
    recorder = Recorder()
    manifest = build(releases=[RELEASE, PRE_RELEASE], recorder=recorder)
    assert manifest["count"] == 3
    assert manifest["releases"] == [
        {
            "tag": "v2025.6.2-update1",
            "publishedAt": "2026-08-01T12:00:00Z",
            "prerelease": False,
        },
        {
            "tag": "v2026.6.1-pre1",
            "publishedAt": "2026-08-10T12:00:00Z",
            "prerelease": True,
        },
    ]
    stable = manifest["firmwares"][0]
    pre = manifest["firmwares"][2]
    assert stable["prerelease"] is False
    assert stable["releaseTag"] == "v2025.6.2-update1"
    assert pre["prerelease"] is True
    assert pre["releaseTag"] == "v2026.6.1-pre1"
    assert pre["version"] == "8.2.2.1"
    # both releases' firmwares were hashed (different urls)
    assert len(recorder.fetched) == 3


def test_pre_release_assets_share_no_hash_with_stable():
    # same url+size across releases reuses the hash (url is the key)
    same_asset = copy.deepcopy(PRE_RELEASE)
    same_asset["assets"][0]["browser_download_url"] = (
        RELEASE["assets"][0]["browser_download_url"]
    )
    same_asset["assets"][0]["size"] = RELEASE["assets"][0]["size"]
    previous = build(releases=[RELEASE])  # hashes it as stable
    recorder = Recorder()
    manifest = build(releases=[RELEASE, same_asset], previous=previous,
                     recorder=recorder)
    assert recorder.fetched == []  # reused
    assert manifest["firmwares"][2]["prerelease"] is True


def test_sonoff_dongle_filter_accepts_zbdongle_e_spelling():
    from refresh_firmware_list import is_sonoff_dongle

    assert is_sonoff_dongle({"brand": "sonoff", "model": "zbdongle-e"})
    assert is_sonoff_dongle({"brand": "sonoff", "model": "dongle-pmg24"})
    assert not is_sonoff_dongle({"brand": "nabucasa", "model": "skyconnect"})
    assert not is_sonoff_dongle({"brand": "sonoff", "model": "other-model"})


def test_manifest_changed_ignores_refreshed_at_only():
    manifest = build()
    same = dict(manifest, refreshedAt="2099-01-01T00:00:00Z")
    assert not manifest_changed(manifest, same)


def test_manifest_changed_detects_real_changes():
    manifest = build()
    assert manifest_changed(None, manifest)
    trimmed = dict(manifest, count=manifest["count"] - 1)
    assert manifest_changed(manifest, trimmed)
