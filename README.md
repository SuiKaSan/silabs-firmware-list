# silabs-firmware-list

Automatically tracks SONOFF dongle firmware (Dongle-E / -L / -M / -PMG24)
published by
[silabs-firmware-builder](https://github.com/Nerivec/silabs-firmware-builder),
and turns it into a list with download links and sha256 checksums for a
website to display and serve.

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
firmware). Download links point straight at the original firmware files
on GitHub Releases — click to download.
