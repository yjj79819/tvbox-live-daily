# 地址可用性验证

生成时间：2026-11-03 23:53:21　仓库：`yjj79819/tvbox-live-daily`　分支：`main`

## 结论

- **最快可用通道：ghfast.top**，平均 0.13s
- 可用通道 5 / 5

## 通道排名

| 通道 | 可用文件 | 平均耗时 | 覆盖率 |
|---|---|---|---|
| ghfast.top | 4/4 | 0.13s | 100% |
| 直连 | 4/4 | 0.14s | 100% |
| gh-proxy.com | 4/4 | 0.16s | 100% |
| ghproxy.net | 4/4 | 0.46s | 100% |
| jsDelivr | 4/4 | 0.48s | 100% |

## live.txt

本地文件：28222 字节，sha256 前 12 位 `876e7e85fd66`

| 通道 | 结论 | 状态码 | 耗时 | 大小 | 内容与本地 | 备注 |
|---|---|---|---|---|---|---|
| 直连 | 可用 | 200 | 0.15s | 28222B | 一致 |  |
| ghproxy.net | 可用 | 200 | 0.69s | 28222B | 一致 |  |
| ghfast.top | 可用 | 200 | 0.22s | 28222B | 一致 |  |
| gh-proxy.com | 可用 | 200 | 0.2s | 28222B | 一致 |  |
| jsDelivr | 可用 | 200 | 0.47s | 28222B | 一致 |  |

## tvbox_live.json

本地文件：1046 字节，sha256 前 12 位 `0b5f11c4c1ab`

| 通道 | 结论 | 状态码 | 耗时 | 大小 | 内容与本地 | 备注 |
|---|---|---|---|---|---|---|
| 直连 | 可用 | 200 | 0.13s | 1046B | 一致 |  |
| ghproxy.net | 可用 | 200 | 0.35s | 1046B | 一致 |  |
| ghfast.top | 可用 | 200 | 0.1s | 1046B | 一致 |  |
| gh-proxy.com | 可用 | 200 | 0.05s | 1046B | 一致 |  |
| jsDelivr | 可用 | 200 | 0.45s | 1046B | 一致 |  |

## live_ipv6.txt

本地文件：119351 字节，sha256 前 12 位 `5b9432996ff5`

| 通道 | 结论 | 状态码 | 耗时 | 大小 | 内容与本地 | 备注 |
|---|---|---|---|---|---|---|
| 直连 | 可用 | 200 | 0.15s | 119351B | 一致 |  |
| ghproxy.net | 可用 | 200 | 0.45s | 119351B | 一致 |  |
| ghfast.top | 可用 | 200 | 0.11s | 119351B | 一致 |  |
| gh-proxy.com | 可用 | 200 | 0.2s | 119351B | 一致 |  |
| jsDelivr | 可用 | 200 | 0.51s | 119351B | 一致 |  |

## live.m3u

本地文件：30581 字节，sha256 前 12 位 `7020738cb939`

| 通道 | 结论 | 状态码 | 耗时 | 大小 | 内容与本地 | 备注 |
|---|---|---|---|---|---|---|
| 直连 | 可用 | 200 | 0.13s | 30581B | 一致 |  |
| ghproxy.net | 可用 | 200 | 0.37s | 30581B | 一致 |  |
| ghfast.top | 可用 | 200 | 0.1s | 30581B | 一致 |  |
| gh-proxy.com | 可用 | 200 | 0.2s | 30581B | 一致 |  |
| jsDelivr | 可用 | 200 | 0.49s | 30581B | 一致 |  |

## TVBox 该填哪个地址

- live.txt：`https://ghfast.top/https://raw.githubusercontent.com/yjj79819/tvbox-live-daily/main/output/live.txt`
- tvbox_live.json：`https://ghfast.top/https://raw.githubusercontent.com/yjj79819/tvbox-live-daily/main/output/tvbox_live.json`

> 「假可用」指返回 200 但内容不对（拿到了 HTML 错误页），不能算能用。
