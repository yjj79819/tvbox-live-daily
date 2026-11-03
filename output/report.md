# 直播源优选报告

生成时间：2026-11-03 23:52:53　仓库：`yjj79819/tvbox-live-daily`　分支：`main`

## 总览

| 指标 | 数值 |
|---|---|
| 扫描仓库 | 32 / 计划 32 |
| 命中文件 | 262 |
| 抓取条目 | 194695 |
| 冷却剔除 | 8 |
| 重复剔除 | 78526 |
| 去重后 | 116161 |
| IPv4 探测 | 1056（跳过 113230，预算到点放弃 544） |
| **可用频道源** | **752** |
| 失效剔除 | 304 |
| IPv6 源（未测速） | 1573 |
| 最终入库频道 / 源 | 203 / 373 |
| 延迟中位数 / P95 | 0.64s / 3.46s |
| 测速耗时 | 188s |

## 失效处理

| 指标 | 数值 |
|---|---|
| 档案中曾成功 | 977 |
| 冷却中 | 39 |
| 本次新进冷却 | 25 |
| 本次复活 | 78 |

失效源先剔除、再进冷却名单（连续失败 2/3/5/8 次分别冷却 3/7/15/45 天），到期自动放回复测。明细见 `live_dead.txt`。

## 分组分布

| 分组 | 频道源数 |
|---|---|
| 央视频道 | 128 |
| 卫视频道 | 111 |
| 体育频道 | 10 |
| 影视频道 | 1 |
| 少儿频道 | 8 |
| 新闻频道 | 22 |
| 其他频道 | 6 |
| 北京频道 | 1 |
| 卫视 | 1 |
| 吉林频道 | 2 |
| 地方频道 | 6 |
| 大陆 | 27 |
| 安徽频道 | 1 |
| 小地方 | 2 |
| 少儿动画 | 1 |
| 山东频道 | 3 |
| 广东 | 1 |
| 广东频道 | 1 |
| 广西频道 | 2 |
| 河北频道 | 3 |
| 浙江 | 1 |
| 浙江频道 | 23 |
| 甘肃频道 | 2 |
| 电视剧频道 | 1 |
| 福建频道 | 3 |
| 辽宁 | 1 |
| 辽宁频道 | 5 |

## 贡献最多的仓库

| 仓库 | 条目数 |
|---|---|
| JE668/iptv-api | 38653 |
| xiongjian83/TvBox | 36458 |
| niuinyang/niuin-s-iptv | 29002 |
| yyyr-otz/iptv-api | 22710 |
| adminouyang/231006 | 20901 |
| cluntop/tvbox | 14994 |
| abusaeeidx/IPTV-Scraper-Zilla | 8062 |
| haha130/iptv-api | 3593 |
| yanghanhanyingshi/iptv | 3403 |
| TREEWE1/iptv-api | 3157 |

## 历史趋势

| 日期 | 抓取 | 可用 | 入库 |
|---|---|---|---|
| 2026-10-21 | 180147 | 679 | 201 |
| 2026-10-23 | 178678 | 700 | 200 |
| 2026-10-25 | 177768 | 824 | 200 |
| 2026-10-27 | 166986 | 794 | 194 |
| 2026-10-29 | 171553 | 807 | 194 |
| 2026-10-31 | 169561 | 772 | 191 |
| 2026-11-03 | 194695 | 752 | 203 |

## 使用方式

- **TVBox 直播接口（主用）**：`https://raw.githubusercontent.com/yjj79819/tvbox-live-daily/main/output/live.txt`
- **TVBox 直播配置**：`https://raw.githubusercontent.com/yjj79819/tvbox-live-daily/main/output/tvbox_live.json`
- **IPv6 源**：`https://raw.githubusercontent.com/yjj79819/tvbox-live-daily/main/output/live_ipv6.txt`
- **通用 m3u（PotPlayer/VLC）**：`https://raw.githubusercontent.com/yjj79819/tvbox-live-daily/main/output/live.m3u`

完整通道清单见 `mirrors.md`，实测结果见 `verify.md`。

> IPv6 源在 GitHub Actions 环境无法测速，单独放 `live_ipv6.txt`。
> 家庭宽带若支持 IPv6，可在 TVBox 里额外添加该文件。
