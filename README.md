# silabs-firmware-list

Automatically tracks SONOFF dongle firmware (Dongle-E / -L / -M / -PMG24)
published by
[silabs-firmware-builder](https://github.com/Nerivec/silabs-firmware-builder),
turns it into a list with download links and sha256 checksums, and mirrors
the firmware files themselves into `firmwares/` so a web frontend can
fetch the bytes directly (CORS-enabled) for flashing over Web Serial.

The list refreshes automatically once an hour, staying in sync with the
latest upstream release.

## Where the data is

The list lives in `firmwares.json` at the root of this repository. Fetch it
at (replace `<your-username>` with the actual repository owner):

```
https://raw.githubusercontent.com/<your-username>/silabs-firmware-list/main/firmwares.json
```

Each firmware record contains: brand, model, firmware type, version,
baud rate, flow control, filename, download link, file size, sha256, the
release tag it came from, and a `prerelease` flag (`true` for pre-release
firmware).

The `url` field points at the mirrored copy in this repository's
`firmwares/` directory, served from `raw.githubusercontent.com` with
CORS headers. In frontend code, `fetch(url)` returns the firmware bytes
as an ArrayBuffer — ready for flashing over Web Serial — and you can
verify them against the record's `sha256` before writing to the device.
The same link also works as a plain `<a href>` download. (GitHub's own
release-download URLs send no CORS headers, which is why the mirror
exists; see ADR-0004.)

The `firmwares/` mirror always holds exactly the files in the current
manifest — stale files are pruned, missing ones re-downloaded, unchanged
ones left alone — so the checkout stays around 5 MB. Note that git
*history* still accumulates old firmware blobs; if the repository ever
grows uncomfortably large, squash the history once.
