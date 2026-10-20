# 直播源优选报告

生成时间：2026-10-20 18:24:39　仓库：`yjj79819/tvbox-live-daily`　分支：`main`

## 总览

| 指标 | 数值 |
|---|---|
| 扫描仓库 | 50 |
| 命中文件 | 194 |
| 抓取条目 | 116745 |
| 冷却剔除 | 1925 |
| 重复剔除 | 50931 |
| 去重后 | 63889 |
| IPv4 探测 | 2500（跳过 60373） |
| **可用频道源** | **342** |
| 失效剔除 | 2158 |
| IPv6 源（未测速） | 1016 |
| 最终入库频道 / 源 | 177 / 297 |
| 延迟中位数 / P95 | 0.86s / 3.22s |
| 测速耗时 | 200s |

## 失效处理

| 指标 | 数值 |
|---|---|
| 档案中曾成功 | 369 |
| 冷却中 | 2140 |
| 本次新进冷却 | 1803 |
| 本次复活 | 135 |

失效源先剔除、再进冷却名单（连续失败 2/3/5/8 次分别冷却 3/7/15/45 天），到期自动放回复测。明细见 `live_dead.txt`。

## 分组分布

| 分组 | 频道源数 |
|---|---|
| 央视频道 | 62 |
| 卫视频道 | 108 |
| 体育频道 | 12 |
| 少儿频道 | 4 |
| 新闻频道 | 16 |
| 其他 | 26 |
| 北京频道 | 1 |
| 吉林频道 | 2 |
| 四川频道 | 1 |
| 地方影视 | 1 |
| 安徽频道 | 1 |
| 山东频道 | 2 |
| 广东 | 1 |
| 广东频道 | 1 |
| 广西频道 | 2 |
| 河北省 | 1 |
| 河北频道 | 3 |
| 河南地方 | 1 |
| 河南省 | 5 |
| 浙江省 | 7 |
| 浙江频道 | 28 |
| 甘肃频道 | 2 |
| 福建省 | 3 |
| 福建频道 | 2 |
| 辽宁省 | 4 |
| 辽宁频道 | 1 |

## 贡献最多的仓库

| 仓库 | 条目数 |
|---|---|
| JE668/iptv-api | 38800 |
| adminouyang/231006 | 21757 |
| cluntop/tvbox | 20342 |
| qingtingjjjjjjj/iptv-API | 6100 |
| haha130/iptv-api | 3553 |
| yinghuang-xie/yinghuangtv-pro | 3195 |
| TREEWE1/iptv-api | 3171 |
| tyxthl/iptv-api | 2939 |
| yanghanhanyingshi/iptv | 2919 |
| nihenhao988/iptv-api | 2587 |

## 历史趋势

| 日期 | 抓取 | 可用 | 入库 |
|---|---|---|---|
| 2026-10-20 | 116745 | 342 | 177 |

## 使用方式

- **TVBox 直播接口（主用）**：`https://raw.githubusercontent.com/yjj79819/tvbox-live-daily/main/output/live.txt`
- **TVBox 直播配置**：`https://raw.githubusercontent.com/yjj79819/tvbox-live-daily/main/output/tvbox_live.json`
- **IPv6 源**：`https://raw.githubusercontent.com/yjj79819/tvbox-live-daily/main/output/live_ipv6.txt`
- **通用 m3u（PotPlayer/VLC）**：`https://raw.githubusercontent.com/yjj79819/tvbox-live-daily/main/output/live.m3u`

完整通道清单见 `mirrors.md`，实测结果见 `verify.md`。

> IPv6 源在 GitHub Actions 环境无法测速，单独放 `live_ipv6.txt`。
> 家庭宽带若支持 IPv6，可在 TVBox 里额外添加该文件。
