# silabs-firmware-list

自动跟踪 [silabs-firmware-builder](https://github.com/Nerivec/silabs-firmware-builder)
发布的 SONOFF dongle 系列固件（Dongle-E / -L / -M / -PMG24），整理成一份
带下载链接和 sha256 校验值的清单，供网站展示和下载使用。

清单每小时自动刷新一次，与上游最新 Release 保持同步。

## 数据在哪

清单文件是仓库根目录的 `firmwares.json`，通过下面的地址获取（把
`<你的用户名>` 换成实际仓库归属）：

```
https://raw.githubusercontent.com/<你的用户名>/silabs-firmware-list/main/firmwares.json
```

每条固件记录包含：品牌、型号、固件类型、版本、波特率、流控方式、
文件名、下载链接、文件大小和 sha256。下载链接直接指向 GitHub Releases
上的原始固件文件，点击即下载。
