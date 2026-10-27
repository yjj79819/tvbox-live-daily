# 地址可用性验证

生成时间：2026-10-27 22:50:17　仓库：`yjj79819/tvbox-live-daily`　分支：`main`

## 结论

- **最快可用通道：ghfast.top**，平均 0.17s
- 可用通道 5 / 5

## 通道排名

| 通道 | 可用文件 | 平均耗时 | 覆盖率 |
|---|---|---|---|
| ghfast.top | 4/4 | 0.17s | 100% |
| gh-proxy.com | 4/4 | 0.23s | 100% |
| 直连 | 4/4 | 0.36s | 100% |
| ghproxy.net | 4/4 | 0.5s | 100% |
| jsDelivr | 4/4 | 0.56s | 100% |

## live.txt

本地文件：27218 字节，sha256 前 12 位 `cae0b0056b89`

| 通道 | 结论 | 状态码 | 耗时 | 大小 | 内容与本地 | 备注 |
|---|---|---|---|---|---|---|
| 直连 | 可用 | 200 | 0.46s | 27218B | 一致 |  |
| ghproxy.net | 可用 | 200 | 0.73s | 27218B | 一致 |  |
| ghfast.top | 可用 | 200 | 0.23s | 27218B | 一致 |  |
| gh-proxy.com | 可用 | 200 | 0.15s | 27218B | 一致 |  |
| jsDelivr | 可用 | 200 | 0.97s | 27218B | 一致 |  |

## tvbox_live.json

本地文件：1046 字节，sha256 前 12 位 `0b5f11c4c1ab`

| 通道 | 结论 | 状态码 | 耗时 | 大小 | 内容与本地 | 备注 |
|---|---|---|---|---|---|---|
| 直连 | 可用 | 200 | 0.31s | 1046B | 一致 |  |
| ghproxy.net | 可用 | 200 | 0.51s | 1046B | 一致 |  |
| ghfast.top | 可用 | 200 | 0.11s | 1046B | 一致 |  |
| gh-proxy.com | 可用 | 200 | 0.16s | 1046B | 一致 |  |
| jsDelivr | 可用 | 200 | 0.47s | 1046B | 一致 |  |

## live_ipv6.txt

本地文件：119287 字节，sha256 前 12 位 `bc38e7b2687f`

| 通道 | 结论 | 状态码 | 耗时 | 大小 | 内容与本地 | 备注 |
|---|---|---|---|---|---|---|
| 直连 | 可用 | 200 | 0.32s | 119287B | 一致 |  |
| ghproxy.net | 可用 | 200 | 0.44s | 119287B | 一致 |  |
| ghfast.top | 可用 | 200 | 0.15s | 119287B | 一致 |  |
| gh-proxy.com | 可用 | 200 | 0.37s | 119287B | 一致 |  |
| jsDelivr | 可用 | 200 | 0.4s | 119287B | 一致 |  |

## live.m3u

本地文件：29671 字节，sha256 前 12 位 `7991c2a54133`

| 通道 | 结论 | 状态码 | 耗时 | 大小 | 内容与本地 | 备注 |
|---|---|---|---|---|---|---|
| 直连 | 可用 | 200 | 0.33s | 29671B | 一致 |  |
| ghproxy.net | 可用 | 200 | 0.31s | 29671B | 一致 |  |
| ghfast.top | 可用 | 200 | 0.17s | 29671B | 一致 |  |
| gh-proxy.com | 可用 | 200 | 0.23s | 29671B | 一致 |  |
| jsDelivr | 可用 | 200 | 0.41s | 29671B | 一致 |  |

## TVBox 该填哪个地址

- live.txt：`https://ghfast.top/https://raw.githubusercontent.com/yjj79819/tvbox-live-daily/main/output/live.txt`
- tvbox_live.json：`https://ghfast.top/https://raw.githubusercontent.com/yjj79819/tvbox-live-daily/main/output/tvbox_live.json`

> 「假可用」指返回 200 但内容不对（拿到了 HTML 错误页），不能算能用。
