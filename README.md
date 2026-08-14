# silabs-firmware-list

每小时从 [`Nerivec/silabs-firmware-builder`](https://github.com/Nerivec/silabs-firmware-builder)
的最新 Release 拉取固件资产，解析 `.gbl` 文件名，计算 sha256（增量），
生成 `firmwares.json` 提交回本仓库。网站跨域 fetch 它的 raw URL 渲染固件列表。

## 数据流

```
GitHub Actions (cron "7 * * * *")
  └─ refresh_firmware_list.py
       ├─ GET api.github.com/repos/Nerivec/silabs-firmware-builder/releases/latest
       ├─ 解析全部 .gbl 文件名 → brand/model/type/version/baudRate/flowControl
       ├─ sha256：url+size 与上次相同则复用，否则流式下载重算（ADR-0003）
       └─ 写 firmwares.json（任何失败都不写，保留旧清单）
  └─ 有变化则 git commit + push
```

## 网页怎么消费

```js
// 清单：raw.githubusercontent.com 自带 Access-Control-Allow-Origin: *
const data = await fetch(
  "https://raw.githubusercontent.com/<你的用户名>/silabs-firmware-list/main/firmwares.json"
).then((r) => r.json());
```

```html
<!-- 下载按钮：必须用 <a href>（导航下载不受 CORS 限制），
     不要用 fetch 拉 .gbl（会被 CORS 挡） -->
<a href="https://github.com/Nerivec/silabs-firmware-builder/releases/download/<tag>/<file>.gbl"
   download>下载</a>
```

每条固件记录的字段：
`brand, model, type, version, baudRate, flowControl, filename, url, size, sha256`

注意：
- `type` ∈ `zigbee_ncp | zigbee_router | openthread_rcp | bootloader`
- `version` 可能含下划线后缀（如 OpenThread 的 `2.7.2.0_GitHub-fb0446f53`），原样字符串
- `flowControl` 值为上游原样 `sw_flow | hw_flow`
- **bootloader 记录没有 `baudRate` / `flowControl` 字段**（上游文件名就没有这两段），网页按可选字段处理

顶层 meta：`owner, repo, releaseTag, releasePublishedAt, refreshedAt, count`

sha256 供用户下载后校验（如 `certutil -hashfile file.gbl SHA256` /
`shasum -a 256 file.gbl`）。它校验"下载传输无损"，不是上游签名。

## 一次性部署

1. 把本目录推到你 GitHub 账号下的新仓库（如 `silabs-firmware-list`）。
2. 仓库 Settings → Actions → General → Workflow permissions 选
   **Read and write permissions**（workflow 已声明 `permissions: contents: write`，
   默认设置通常也允许，若 push 失败检查这里）。
3. Actions 页手动触发一次 `refresh-firmware-list`（workflow_dispatch）验证，
   确认 `firmwares.json` 生成并提交。
4. 之后每小时自动刷新。

## 本地开发

```bash
python -m venv .venv
.venv/Scripts/python -m pip install pytest mypy   # Windows；macOS/Linux 用 .venv/bin/python
.venv/Scripts/python -m pytest                    # 测试（接缝：parse / manifest）
.venv/Scripts/python -m mypy firmware_list refresh_firmware_list.py
python refresh_firmware_list.py                   # 手动生成 firmwares.json（无 token 时受 60/h 限额）
```

设计决策记录（ADR）与领域术语表见上游调研仓库的 `docs/adr/` 与 `CONTEXT.md`：
- ADR-0001 数据来源与缓存策略（定时拉 releases/latest，失败保留旧清单）
- ADR-0002 部署架构（独立仓库 + Actions + raw URL 分发）
- ADR-0003 sha256 增量计算（url+size 不变即复用）
