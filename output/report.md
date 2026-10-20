# 直播源优选报告

生成时间：2026-10-21 04:05:01　仓库：`yjj79819/tvbox-live-daily`　分支：`main`

## 总览

| 指标 | 数值 |
|---|---|
| 扫描仓库 | 17 / 计划 17 |
| 命中文件 | 157 |
| 抓取条目 | 81118 |
| 冷却剔除 | 5205 |
| 重复剔除 | 33251 |
| 去重后 | 42662 |
| IPv4 探测 | 1600（跳过 41065） |
| **可用频道源** | **220** |
| 失效剔除 | 1380 |
| IPv6 源（未测速） | 0 |
| 最终入库频道 / 源 | 147 / 211 |
| 延迟中位数 / P95 | 0.35s / 2.57s |
| 测速耗时 | 144s |

## 失效处理

| 指标 | 数值 |
|---|---|
| 档案中曾成功 | 408 |
| 冷却中 | 2235 |
| 本次新进冷却 | 61 |
| 本次复活 | 10 |

失效源先剔除、再进冷却名单（连续失败 2/3/5/8 次分别冷却 3/7/15/45 天），到期自动放回复测。明细见 `live_dead.txt`。

## 分组分布

| 分组 | 频道源数 |
|---|---|
| 央视频道 | 48 |
| 卫视频道 | 75 |
| 体育频道 | 2 |
| 少儿频道 | 4 |
| 新闻频道 | 11 |
| 上海频道 | 1 |
| 其他 | 25 |
| 内蒙频道 | 1 |
| 北京频道 | 1 |
| 吉林频道 | 1 |
| 央视付费频道 | 1 |
| 山东频道 | 1 |
| 广西频道 | 1 |
| 河北频道 | 3 |
| 河南地方 | 1 |
| 浙江频道 | 23 |
| 甘肃频道 | 2 |
| 直播中国 | 4 |
| 福建频道 | 3 |
| 辽宁频道 | 1 |
| 黑龙江 | 2 |

## 贡献最多的仓库

| 仓库 | 条目数 |
|---|---|
| adminouyang/231006 | 21757 |
| cluntop/tvbox | 20342 |
| yangxiaoge/tvbox_cust | 17151 |
| CCSH/IPTV | 11019 |
| lubin776/tvbox-api-backup | 4300 |
| haha130/iptv-api | 3553 |
| yjj79819/tvbox-live-daily | 1417 |
| fanmingming/live | 1065 |
| Supprise0901/TVBox_live | 389 |
| JinRudy/tvbox-more | 125 |

## 历史趋势

| 日期 | 抓取 | 可用 | 入库 |
|---|---|---|---|
| 2026-10-20 | 63439 | 148 | 144 |
| 2026-10-21 | 81118 | 220 | 147 |

## 使用方式

- **TVBox 直播接口（主用）**：`https://raw.githubusercontent.com/yjj79819/tvbox-live-daily/main/output/live.txt`
- **TVBox 直播配置**：`https://raw.githubusercontent.com/yjj79819/tvbox-live-daily/main/output/tvbox_live.json`
- **IPv6 源**：`https://raw.githubusercontent.com/yjj79819/tvbox-live-daily/main/output/live_ipv6.txt`
- **通用 m3u（PotPlayer/VLC）**：`https://raw.githubusercontent.com/yjj79819/tvbox-live-daily/main/output/live.m3u`

完整通道清单见 `mirrors.md`，实测结果见 `verify.md`。

> IPv6 源在 GitHub Actions 环境无法测速，单独放 `live_ipv6.txt`。
> 家庭宽带若支持 IPv6，可在 TVBox 里额外添加该文件。
