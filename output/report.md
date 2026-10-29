# 直播源优选报告

生成时间：2026-10-29 23:06:10　仓库：`yjj79819/tvbox-live-daily`　分支：`main`

## 总览

| 指标 | 数值 |
|---|---|
| 扫描仓库 | 32 / 计划 32 |
| 命中文件 | 246 |
| 抓取条目 | 171553 |
| 冷却剔除 | 1061 |
| 重复剔除 | 76266 |
| 去重后 | 94226 |
| IPv4 探测 | 1344（跳过 91261，预算到点放弃 256） |
| **可用频道源** | **807** |
| 失效剔除 | 537 |
| IPv6 源（未测速） | 1543 |
| 最终入库频道 / 源 | 194 / 339 |
| 延迟中位数 / P95 | 0.75s / 2.58s |
| 测速耗时 | 152s |

## 失效处理

| 指标 | 数值 |
|---|---|
| 档案中曾成功 | 943 |
| 冷却中 | 375 |
| 本次新进冷却 | 75 |
| 本次复活 | 79 |

失效源先剔除、再进冷却名单（连续失败 2/3/5/8 次分别冷却 3/7/15/45 天），到期自动放回复测。明细见 `live_dead.txt`。

## 分组分布

| 分组 | 频道源数 |
|---|---|
| 央视频道 | 113 |
| 卫视频道 | 111 |
| 体育频道 | 4 |
| 影视频道 | 1 |
| 少儿频道 | 7 |
| 新闻频道 | 15 |
| 其他频道 | 6 |
| 卫视 | 1 |
| 吉林频道 | 2 |
| 四川频道 | 1 |
| 地方频道 | 1 |
| 大陆 | 1 |
| 安徽频道 | 1 |
| 小地方 | 4 |
| 少儿动画 | 1 |
| 山东频道 | 2 |
| 广东 | 1 |
| 广东频道 | 1 |
| 广西频道 | 2 |
| 河北综合 | 1 |
| 河北频道 | 3 |
| 浙江 | 1 |
| 浙江频道 | 18 |
| 甘肃频道 | 2 |
| 电视剧频道 | 1 |
| 直播中国 | 28 |
| 福建频道 | 4 |
| 辽宁 | 1 |
| 辽宁频道 | 5 |

## 贡献最多的仓库

| 仓库 | 条目数 |
|---|---|
| JE668/iptv-api | 38692 |
| xiongjian83/TvBox | 36458 |
| yyyr-otz/iptv-api | 22727 |
| adminouyang/231006 | 21224 |
| cluntop/tvbox | 14552 |
| dushuboy/tvbox-live | 9736 |
| WilliamLuuu/iptv-api | 4133 |
| haha130/iptv-api | 3615 |
| yanghanhanyingshi/iptv | 3543 |
| jn950/live | 3158 |

## 历史趋势

| 日期 | 抓取 | 可用 | 入库 |
|---|---|---|---|
| 2026-10-21 | 180147 | 679 | 201 |
| 2026-10-23 | 178678 | 700 | 200 |
| 2026-10-25 | 177768 | 824 | 200 |
| 2026-10-27 | 166986 | 794 | 194 |
| 2026-10-29 | 171553 | 807 | 194 |

## 使用方式

- **TVBox 直播接口（主用）**：`https://raw.githubusercontent.com/yjj79819/tvbox-live-daily/main/output/live.txt`
- **TVBox 直播配置**：`https://raw.githubusercontent.com/yjj79819/tvbox-live-daily/main/output/tvbox_live.json`
- **IPv6 源**：`https://raw.githubusercontent.com/yjj79819/tvbox-live-daily/main/output/live_ipv6.txt`
- **通用 m3u（PotPlayer/VLC）**：`https://raw.githubusercontent.com/yjj79819/tvbox-live-daily/main/output/live.m3u`

完整通道清单见 `mirrors.md`，实测结果见 `verify.md`。

> IPv6 源在 GitHub Actions 环境无法测速，单独放 `live_ipv6.txt`。
> 家庭宽带若支持 IPv6，可在 TVBox 里额外添加该文件。
