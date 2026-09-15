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

Two kinds of link per record:

- `downloadUrl` — the mirrored copy in this repository's `firmwares/`
  directory, served from `raw.githubusercontent.com` with CORS headers.
  **Use this in frontend code**: `fetch(downloadUrl)` returns the bytes
  as an ArrayBuffer for flashing over Web Serial, and you can verify them
  against the record's `sha256` before writing to the device.
- `url` — the original GitHub Releases asset. GitHub's release endpoints
  send no CORS headers, so this link only works as a plain `<a href>`
  navigation (browser download), never as a `fetch` target.

The `firmwares/` mirror always holds exactly the files in the current
manifest — stale files are pruned, missing ones re-downloaded, unchanged
ones left alone — so the checkout stays around 5 MB. Note that git
*history* still accumulates old firmware blobs; if the repository ever
grows uncomfortably large, squash the history once.
