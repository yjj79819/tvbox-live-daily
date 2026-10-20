# 直播源优选

自动从 GitHub 上**最近更新**的 TVBox / IPTV 相关仓库抓取直播源，逐条测速剔除死链，
按延迟优选后生成可直接使用的直播配置文件。每两天自动跑一次，结果自动提交回仓库。

产出的是「已经测过速、排除掉失效源」的清单，不是原始聚合。

## 交付文件

| 文件 | 用途 |
|---|---|
| `output/live.txt` | **主用**。TVBox 的 `频道名,URL` 格式，IPv4 源，已测速优选 |
| `output/live_ipv6.txt` | IPv6 源。家庭宽带支持 IPv6 时可额外添加 |
| `output/live.m3u` | 通用 m3u，给 PotPlayer / VLC / 各类 IPTV 播放器 |
| `output/tvbox_live.json` | TVBox 的 `lives` 配置，内含直连/加速/本地三组地址 |
| `output/live_dead.txt` | 本次失效的源与失败原因，供排查 |
| `output/mirrors.md` | 所有可用访问地址（直连与各加速站） |
| `output/verify.md` | 各通道实测结果（状态、耗时、内容是否一致） |
| `output/report.md` | 本次统计报告 |

## 在 TVBox 中使用

把 `mirrors.md` 里列出的任一地址填到 TVBox 的「直播接口」。推荐顺序：

```
1. https://raw.githubusercontent.com/<你的用户名>/<仓库名>/main/output/live.txt
2. https://ghproxy.net/https://raw.githubusercontent.com/<你的用户名>/<仓库名>/main/output/live.txt
3. https://ghfast.top/https://raw.githubusercontent.com/<你的用户名>/<仓库名>/main/output/live.txt
```

也可以直接用 `tvbox_live.json`，它已经把上述通道都写进去了，
在 TVBox 里切换条目即可换通道，不用手改地址。

### 关于加速站

国内访问 raw 不畅时才需要加速。2026-10-21 实测结果：

| 通道 | 实测 | 结论 |
|---|---|---|
| 直连 raw.githubusercontent.com | 0.40s | 最快，优先用 |
| ghproxy.net | 1.05s | 可用 |
| ghfast.top | 1.42s | 可用 |
| gh-proxy.com | 2.79s | 可用 |
| jsDelivr（CDN 缓存） | 4.23s | 可用但滞后 12 小时 |
| githubraw.com、ghproxy.com、raw.kkgithub.com 等 12 个 | 超时/404 | **已失效** |

失效清单与替换项都写在 `config/mirrors.txt` 里，改那个文件即可增减通道。

> jsDelivr 缓存最长 12 小时，仓库每两天更新一次，作备用够用，别当主用。

## 首次部署

1. 在 GitHub 新建**公开**仓库（Public）
2. 推送本目录的全部文件
3. 仓库 → **Settings → Actions → General → Workflow permissions**
   → 改选 **Read and write permissions** → **Save**
   （默认是只读，不改自动提交会被拒绝）
4. 打开 **Actions** 页签确认启用，可手动点 **Run workflow** 立即跑一次
5. 把 `config/repo.txt` 改成真实的 `owner/repo`（不改也能靠 git remote 自动推断）

不需要付费账号，不需要 Personal Access Token——Actions 运行时会自动注入 `GITHUB_TOKEN`。

## 运行方式

```bash
pip install -r requirements.txt

python run.py                     # 全流程
python run.py --max-probe 300     # 只测前 300 条，本地快速验证
python run.py --no-probe          # 只抓取解析，不测速
python run.py --verify            # 跑完顺带验证各访问通道

python scripts/verify.py          # 单独验证远端/本地地址
python scripts/verify.py --no-local   # 只验远端
```

可用环境变量：`MAX_PROBE`（默认 2500）、`TIMEOUT`（默认 8 秒）、
`WORKERS`（默认 48）、`KEEP_PER_CHANNEL`（默认 3）、
`JOIN_BACKUP=0`（关闭同频道备用源合并成一行）。

## 工作流程

```
阶段1 发现   ├─ 种子仓库 config/seed_repos.txt（人工验证，保底）
             └─ GitHub 搜索 API，按 updated 倒序发现新的活跃仓库
                     ↓
阶段2 抓取   列出仓库文件树 → 按文件名/大小筛出直播源文件
             → 下载 → 解析 M3U 与 TXT → 黑名单过滤
             → 冷却名单剔除 → 归一化去重
                     ↓
阶段3 测速   流式读取前 8KB 判断（直播流不能整段下载）：
             ├─ m3u8：先取播放列表，再下钻验证第一路子流
             ├─ TS/FLV：检查同步字节
             ├─ 老源优先 + 新源保底 45% 配额
             └─ IPv6：无 IPv6 环境则单独归类，不判死链
                     ↓
阶段4 生成   按延迟排序，每个频道跨主机留 3 条并合并成一行（# 连接）
             → 分组 → 输出；同时把结果写回健康档案
                     ↓
阶段5 验证   逐个真实请求各通道，输出 verify.md
```

## 三个关键设计

**失效了怎么办——四层处理**

1. 探测失败的源不进清单，同时记入 `live_dead.txt`
2. 连续失败进冷却名单：失败 2/3/5/8 次分别冷却 3/7/15/45 天，
   冷却期内不抓不测，省下的配额留给新源
3. 冷却到期自动放回复测，活过来就回档案——不会永久误杀
4. 客户端侧：同一频道的多个源合并成一行，TVBox 播不通自动切下一条；
   且挑选时强制跨主机，避免三条备用源全挂在同一个 CDN 上

**为什么按归一化 URL 去重？**
同一路流在不同仓库常被写成 `http://a.com:80/x/?t=1` 和 `https://A.com/x`。
不做归一化就是两条，白占一个备用名额。去重时统一小写主机、去掉默认端口、
去掉末尾斜杠、排序 query 并剔除 `token`/`t`/`expire` 这类时效参数。

**为什么不整段下载来测速？**
直播流没有结尾，整段下载会一直挂住。脚本用流式读取前 8KB 判断：
拿到 TS 同步字节（0x47）或 FLV 头，或拿到 m3u8 播放列表后成功下钻子流，才算可用。

## 目录结构

```
├── run.py                     主入口
├── requirements.txt
├── config/
│   ├── seed_repos.txt         种子仓库（想加源改这里）
│   ├── discover_keywords.txt  搜索关键词（想换发现方向改这里）
│   ├── blacklist.txt          黑名单关键词（过滤违规/无效频道）
│   ├── priority_channels.txt  高优先级频道（配额紧张时优先保障）
│   ├── mirrors.txt            加速站模板（实测结论也记在这里）
│   ├── local_base.txt         本地/局域网源基地址
│   └── repo.txt               本仓库地址（用于生成 URL）
├── scripts/
│   ├── common.py              HTTP / GitHub API / 归一化 / 镜像
│   ├── discover.py            阶段1 发现仓库
│   ├── collect.py             阶段2 抓取解析去重
│   ├── probe.py               阶段3 测速优选
│   ├── build.py               阶段4 生成输出
│   ├── verify.py              阶段5 地址验证
│   └── state.py               URL 健康档案与冷却名单
├── state/                     健康档案（必须入库，跨运行留存）
├── data/                      中间数据（已 gitignore）
└── output/                    交付文件（自动提交）
```

## 常见问题

**Actions 跑了但没更新？**
先看 Actions 日志。若报 `remote: Permission denied`，
就是第 3 步的 Workflow permissions 没改成读写。

**想多加/去掉某个源？**
编辑 `config/seed_repos.txt`，加一行 `owner/repo`，下次运行生效。

**报告里「失效剔除」特别多？**
正常。直播源本身寿命短，聚合仓库里混杂大量历史失效条目。
引入冷却名单后，第二批开始这个数会明显下降——死链不再反复探测。

**verify.md 里全是「落后」？**
Actions 中 verify 在 push 后 30 秒才跑，是给 raw 留同步时间。
手动在本地跑 `python scripts/verify.py` 时，本地文件尚未推上去，
显示落后是正常的，说明远端还是上一版内容。

**搜索 API 被限流？**
未认证搜索限额 10 次/分钟，脚本每个关键词间已留 2.5 秒。
带 token 时为 30 次/分钟，通常不会触发。真被限流会自动熔断，
改走 raw 路径猜测，主流程照常产出。
