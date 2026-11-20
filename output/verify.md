# 地址可用性验证

生成时间：2026-11-20 01:01:44　仓库：`yjj79819/tvbox-live-daily`　分支：`main`

## 结论

- **最快可用通道：ghfast.top**，平均 0.13s
- 可用通道 5 / 5

## 通道排名

| 通道 | 可用文件 | 平均耗时 | 覆盖率 |
|---|---|---|---|
| ghfast.top | 4/4 | 0.13s | 100% |
| 直连 | 4/4 | 0.14s | 100% |
| gh-proxy.com | 4/4 | 0.21s | 100% |
| jsDelivr | 4/4 | 0.35s | 100% |
| ghproxy.net | 4/4 | 0.45s | 100% |

## live.txt

本地文件：36164 字节，sha256 前 12 位 `ebff46053607`

| 通道 | 结论 | 状态码 | 耗时 | 大小 | 内容与本地 | 备注 |
|---|---|---|---|---|---|---|
| 直连 | 可用 | 200 | 0.18s | 36164B | 一致 |  |
| ghproxy.net | 可用 | 200 | 0.62s | 36164B | 一致 |  |
| ghfast.top | 可用 | 200 | 0.17s | 36164B | 一致 |  |
| gh-proxy.com | 可用 | 200 | 0.21s | 36164B | 一致 |  |
| jsDelivr | 可用 | 200 | 0.37s | 36164B | 一致 |  |

## tvbox_live.json

本地文件：1046 字节，sha256 前 12 位 `0b5f11c4c1ab`

| 通道 | 结论 | 状态码 | 耗时 | 大小 | 内容与本地 | 备注 |
|---|---|---|---|---|---|---|
| 直连 | 可用 | 200 | 0.13s | 1046B | 一致 |  |
| ghproxy.net | 可用 | 200 | 0.29s | 1046B | 一致 |  |
| ghfast.top | 可用 | 200 | 0.11s | 1046B | 一致 |  |
| gh-proxy.com | 可用 | 200 | 0.11s | 1046B | 一致 |  |
| jsDelivr | 可用 | 200 | 0.31s | 1046B | 一致 |  |

## live_ipv6.txt

本地文件：114174 字节，sha256 前 12 位 `3fd617970d8e`

| 通道 | 结论 | 状态码 | 耗时 | 大小 | 内容与本地 | 备注 |
|---|---|---|---|---|---|---|
| 直连 | 可用 | 200 | 0.13s | 114174B | 一致 |  |
| ghproxy.net | 可用 | 200 | 0.55s | 114174B | 一致 |  |
| ghfast.top | 可用 | 200 | 0.14s | 114174B | 一致 |  |
| gh-proxy.com | 可用 | 200 | 0.23s | 114174B | 一致 |  |
| jsDelivr | 可用 | 200 | 0.37s | 114174B | 一致 |  |

## live.m3u

本地文件：42403 字节，sha256 前 12 位 `9d8bf37695bd`

| 通道 | 结论 | 状态码 | 耗时 | 大小 | 内容与本地 | 备注 |
|---|---|---|---|---|---|---|
| 直连 | 可用 | 200 | 0.13s | 42403B | 一致 |  |
| ghproxy.net | 可用 | 200 | 0.34s | 42403B | 一致 |  |
| ghfast.top | 可用 | 200 | 0.11s | 42403B | 一致 |  |
| gh-proxy.com | 可用 | 200 | 0.29s | 42403B | 一致 |  |
| jsDelivr | 可用 | 200 | 0.35s | 42403B | 一致 |  |

## TVBox 该填哪个地址

- live.txt：`https://ghfast.top/https://raw.githubusercontent.com/yjj79819/tvbox-live-daily/main/output/live.txt`
- tvbox_live.json：`https://ghfast.top/https://raw.githubusercontent.com/yjj79819/tvbox-live-daily/main/output/tvbox_live.json`

> 「假可用」指返回 200 但内容不对（拿到了 HTML 错误页），不能算能用。
