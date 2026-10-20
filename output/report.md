# 直播源优选报告

生成时间：2026-10-21 01:07:49　仓库：`OWNER/REPO`　分支：`main`

## 总览

| 指标 | 数值 |
|---|---|
| 扫描仓库 | 50 |
| 命中文件 | 144 |
| 抓取条目 | 75989 |
| 冷却剔除 | 0 |
| 重复剔除 | 43842 |
| 去重后 | 32147 |
| IPv4 探测 | 2500（跳过 28475） |
| **可用频道源** | **225** |
| 失效剔除 | 2275 |
| IPv6 源（未测速） | 1172 |
| 最终入库频道 / 源 | 142 / 215 |
| 延迟中位数 / P95 | 1.11s / 3.52s |
| 测速耗时 | 94s |

## 失效处理

| 指标 | 数值 |
|---|---|
| 档案中曾成功 | 233 |
| 冷却中 | 337 |
| 本次新进冷却 | 337 |
| 本次复活 | 16 |

失效源先剔除、再进冷却名单（连续失败 2/3/5/8 次分别冷却 3/7/15/45 天），到期自动放回复测。明细见 `live_dead.txt`。

## 分组分布

| 分组 | 频道源数 |
|---|---|
| 央视频道 | 39 |
| 卫视频道 | 78 |
| 体育频道 | 3 |
| 少儿频道 | 4 |
| 新闻频道 | 13 |
| 其他 | 30 |
| 北京频道 | 1 |
| 吉林频道 | 1 |
| 广西频道 | 2 |
| 河北省 | 1 |
| 河北频道 | 3 |
| 河南地方 | 1 |
| 浙江频道 | 27 |
| 甘肃频道 | 2 |
| 福建省 | 3 |
| 福建频道 | 1 |
| 组播线路 | 3 |
| 辽宁频道 | 1 |
| 黑龙江 | 2 |

## 贡献最多的仓库

| 仓库 | 条目数 |
|---|---|
| adminouyang/231006 | 17470 |
| cluntop/tvbox | 7224 |
| haha130/iptv-api | 2705 |
| fanmingming/live | 994 |
| a875157367/iptv-api-master | 886 |
| yanghanhanyingshi/iptv | 849 |
| willsonchan89-spec/iptv-api | 523 |
| Supprise0901/TVBox_live | 384 |
| doms9/iptv | 333 |
| JE668/iptv-api | 144 |

## 历史趋势

| 日期 | 抓取 | 可用 | 入库 |
|---|---|---|---|
| 2026-10-20 | 63439 | 148 | 144 |
| 2026-10-21 | 75989 | 225 | 142 |

## 使用方式

- **TVBox 直播接口（主用）**：`https://raw.githubusercontent.com/OWNER/REPO/main/output/live.txt`
- **TVBox 直播配置**：`https://raw.githubusercontent.com/OWNER/REPO/main/output/tvbox_live.json`
- **IPv6 源**：`https://raw.githubusercontent.com/OWNER/REPO/main/output/live_ipv6.txt`
- **通用 m3u（PotPlayer/VLC）**：`https://raw.githubusercontent.com/OWNER/REPO/main/output/live.m3u`

完整通道清单见 `mirrors.md`，实测结果见 `verify.md`。

> IPv6 源在 GitHub Actions 环境无法测速，单独放 `live_ipv6.txt`。
> 家庭宽带若支持 IPv6，可在 TVBox 里额外添加该文件。
