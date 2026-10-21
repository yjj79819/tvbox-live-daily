# 直播源优选报告

生成时间：2026-10-21 22:05:46　仓库：`yjj79819/tvbox-live-daily`　分支：`main`

## 总览

| 指标 | 数值 |
|---|---|
| 扫描仓库 | 32 / 计划 32 |
| 命中文件 | 254 |
| 抓取条目 | 180147 |
| 冷却剔除 | 10877 |
| 重复剔除 | 73732 |
| 去重后 | 95538 |
| IPv4 探测 | 1440（跳过 92457，预算到点放弃 160） |
| **可用频道源** | **679** |
| 失效剔除 | 761 |
| IPv6 源（未测速） | 1545 |
| 最终入库频道 / 源 | 201 / 361 |
| 延迟中位数 / P95 | 0.79s / 3.00s |
| 测速耗时 | 150s |

## 失效处理

| 指标 | 数值 |
|---|---|
| 档案中曾成功 | 710 |
| 冷却中 | 2277 |
| 本次新进冷却 | 47 |
| 本次复活 | 176 |

失效源先剔除、再进冷却名单（连续失败 2/3/5/8 次分别冷却 3/7/15/45 天），到期自动放回复测。明细见 `live_dead.txt`。

## 分组分布

| 分组 | 频道源数 |
|---|---|
| 央视频道 | 117 |
| 卫视频道 | 113 |
| 体育频道 | 11 |
| 少儿频道 | 6 |
| 新闻频道 | 15 |
| 纪实频道 | 1 |
| 其他频道 | 6 |
| 北京频道 | 1 |
| 卫视 | 1 |
| 吉林频道 | 2 |
| 四川频道 | 1 |
| 央视付费频道 | 1 |
| 安徽频道 | 1 |
| 山东频道 | 3 |
| 广东 | 1 |
| 广东频道 | 1 |
| 广西频道 | 2 |
| 河北频道 | 3 |
| 河南地方 | 1 |
| 浙江 | 2 |
| 浙江频道 | 31 |
| 港澳台 | 1 |
| 甘肃频道 | 2 |
| 电视剧频道 | 1 |
| 直播中国 | 26 |
| 福建频道 | 5 |
| 辽宁 | 2 |
| 辽宁频道 | 4 |

## 贡献最多的仓库

| 仓库 | 条目数 |
|---|---|
| JE668/iptv-api | 38753 |
| xiongjian83/TvBox | 36458 |
| yyyr-otz/iptv-api | 22776 |
| adminouyang/231006 | 21413 |
| cluntop/tvbox | 19524 |
| dushuboy/tvbox-live | 8207 |
| WilliamLuuu/iptv-api | 4155 |
| haha130/iptv-api | 3595 |
| yanghanhanyingshi/iptv | 3327 |
| TREEWE1/iptv-api | 3167 |

## 历史趋势

| 日期 | 抓取 | 可用 | 入库 |
|---|---|---|---|
| 2026-10-21 | 180147 | 679 | 201 |

## 使用方式

- **TVBox 直播接口（主用）**：`https://raw.githubusercontent.com/yjj79819/tvbox-live-daily/main/output/live.txt`
- **TVBox 直播配置**：`https://raw.githubusercontent.com/yjj79819/tvbox-live-daily/main/output/tvbox_live.json`
- **IPv6 源**：`https://raw.githubusercontent.com/yjj79819/tvbox-live-daily/main/output/live_ipv6.txt`
- **通用 m3u（PotPlayer/VLC）**：`https://raw.githubusercontent.com/yjj79819/tvbox-live-daily/main/output/live.m3u`

完整通道清单见 `mirrors.md`，实测结果见 `verify.md`。

> IPv6 源在 GitHub Actions 环境无法测速，单独放 `live_ipv6.txt`。
> 家庭宽带若支持 IPv6，可在 TVBox 里额外添加该文件。
