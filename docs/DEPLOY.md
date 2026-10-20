# 部署到 GitHub

## 一、需要你提供的东西

| # | 需要提供 | 说明 | 是否必须 |
|---|---|---|---|
| 1 | GitHub 账号 | 免费账号即可，不需要付费、不需要实名 | 必须 |
| 2 | 仓库名 | 比如 `tvbox-live`。必须**公开（Public）**，私有仓库 raw 地址带 token 时效，TVBox 读不了 | 必须 |
| 3 | Workflow 读写权限 | Settings → Actions → General → Workflow permissions → 改选 Read and write | 必须（否则提交被拒） |

**不需要**的东西：
- 不需要 Personal Access Token（Actions 自动注入 `GITHUB_TOKEN`）
- 不需要服务器、域名、对象存储
- 不需要 Actions 额度付费（公开仓库 Actions 免费，本项目每两天跑约 10 分钟，远低于限额）

**空间够不够**：单次产出约 250KB，健康档案约 300KB。
按每两天提交一次算，一年增量约 50MB，远低于 GitHub 单仓库 1GB 的软上限。

## 二、推送步骤

下面的命令在你**本机**（Windows，Git Bash 或 PowerShell 都行）执行。
把 `你的用户名` 和 `tvbox-live` 换成实际值。

```bash
cd "C:/Users/yjj/WorkBuddy/2026-10-20-19-35-23/tvbox-live-daily"

# 1. 初始化并首次推送（仓库先在 GitHub 网页上建好，空的，别勾 README）
git init
git branch -M main
git remote add origin https://github.com/你的用户名/tvbox-live.git
git add -A
git commit -m "feat: 直播源优选（每两天自动更新）"
git push -u origin main
```

推上去之后：

```bash
# 2. 把仓库地址写进配置，这样生成的 URL 才是真实可访问的
#    编辑 config/repo.txt，内容改成：
#    你的用户名/tvbox-live main
```

然后到 GitHub 网页操作（这一步必须在网页上点，命令行做不了）：

> 仓库 → **Settings** → **Actions** → **General** → 拖到最下面
> **Workflow permissions** → 选 **Read and write permissions** → **Save**

最后手动跑一次看效果：

> 仓库 → **Actions** → 左侧选「直播源优选（每两天）」→ **Run workflow**

跑完约 10 分钟，`output/` 下会出现文件，README 首页会显示报告。

## 三、推完自检

```bash
# 本地验证各通道是否真能拿到文件
cd "C:/Users/yjj/WorkBuddy/2026-10-20-19-35-23/tvbox-live-daily"
python scripts/verify.py
```

看 `output/verify.md` 里的「通道排名」。如果直连和各加速站都是「可用」，就通了。

## 四、加速站实测清单

2026-10-21 从本机逐个 curl 实测（`https://raw.githubusercontent.com/github/gitignore/main/README.md`，5847 字节）：

| 通道 | 实测耗时 | 结论 |
|---|---|---|
| 直连 raw.githubusercontent.com | 0.40s | 可用，最快 |
| https://ghproxy.net/ | 1.05s | 可用 |
| https://ghfast.top/ | 1.42s | 可用 |
| https://gh-proxy.com/ | 2.79s | 可用 |
| https://gcore.jsdelivr.net/gh/ | 2.38s | 可用（CDN 缓存） |
| https://cdn.jsdelivr.net/gh/ | 4.23s | 可用（CDN 缓存） |
| https://ghproxy.com/ | 超时 15s | **已失效** |
| https://githubraw.com/ | 404 / 超时 | **已失效** |
| https://raw.kkgithub.com/ | 超时 | **已失效** |
| https://raw.gitmirror.com/ | 域名无解析 | **已失效** |
| https://gh.llkk.cc/ | 超时 | **已失效** |
| https://gh-proxy.linqi.dev/ | 超时 | **已失效** |
| https://gh.api.99988866.xyz/ | 超时 | **已失效** |
| https://mirror.ghproxy.com/ | 超时 | **已失效** |
| https://gh.idc.ooo/ | 连接被重置 | **已失效** |
| https://gh-proxy.ygxz.in/ | 超时 | **已失效** |
| https://gh.flyinbug.top/ | HTTP 502 | **已失效** |
| https://gh-proxy.0z.me/ | 域名无解析 | **已失效** |
| https://fastly.jsdelivr.net/gh/ | 超时 | **已失效** |
| https://gh.con.sh/ | 200 但内容只有 48 字节 | **假可用** |

第三方的加速站生死很频繁，今天能用的下个月可能就挂了。
所以脚本每次跑完会把各通道实测一遍写进 `verify.md`，
挂了直接从 `config/mirrors.txt` 里注掉那行即可。

## 五、两套地址怎么用

**远端（GitHub）**：TVBox 填 `output/live.txt` 的地址，断网时用不了。

**本地（局域网）**：把 `output/live.txt` 放到能本机访问的位置，
比如 TVBox 自带的 9978 文件服务（`http://192.168.1.13:9978/file/live.txt`），
然后在 `config/local_base.txt` 里填上基地址：

```
http://192.168.1.13:9978/file/
```

填了之后 `tvbox_live.json` 会多出一组「优选直播·本地」，
`mirrors.md` 和 `verify.md` 里也会带上本地通道的实测结果。

两套并存的意义：GitHub 那套自动更新、不用管；
本地那套在 GitHub 抽风、家里断外网时仍能看。

## 六、更新频率

Workflow 定时：`0 19 */2 * *`，即 UTC 19:00（北京 03:00），逢单日运行。
选凌晨是因为 GitHub 调度在高峰期会排队延迟，深夜最准，
且此时源站负载低，测速结果更接近真实体验。

想改成每天：把 `daily.yml` 里的 cron 改成 `0 19 * * *`。

## 七、常见故障

| 现象 | 原因 | 处理 |
|---|---|---|
| Actions 报 `Permission denied` | Workflow permissions 没改读写 | 按第二节改 |
| Actions 跑完没提交 | 内容无变化 | 正常，脚本会跳过空提交 |
| verify.md 全是旧内容 | 手动在本地跑，文件还没推上去 | 正常，推上去后再验 |
| 加速站全部不可用 | 第三方站挂了 | 换 `config/mirrors.txt` 里的其他站 |
| 仓库越来越大 | 健康档案累积 | 调小 `scripts/state.py` 里的 `KNOWN_GOOD_MAX` / `COOLDOWN_MAX` |
