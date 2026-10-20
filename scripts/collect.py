# -*- coding: utf-8 -*-
"""阶段 2：抓取直播源文件并解析为统一频道列表。

支持两类主流格式：
  - M3U ：#EXTINF 行 + 紧随其后的 URL 行
  - TXT ："分组名,#genre#" + "频道名,URL"（TVBox 常用）

产出 data/raw_channels.json，每个条目形如：
  {name, url, group, repo, file}
"""
from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from common import (
    DATA_DIR,
    cache_flush,
    cache_stat,
    gh_api,
    http_get,
    http_get_cached,
    ipv6_supported,
    is_ipv6_url,
    log,
    norm_url,
    read_lines,
    warn,
)

import state as state_mod  # noqa: E402

# 候选文件名关键词
NAME_HINTS = ("live", "iptv", "channel", "tv", "直播", "频道")
# 允许的扩展名
GOOD_EXT = (".txt", ".m3u", ".m3u8")
# 文件大小区间（字节）：太小是空壳，太大可能是别的资源
MIN_SIZE = 800
MAX_SIZE = 8 * 1024 * 1024

EXTINF_RE = re.compile(r"#EXTINF\s*:\s*([^,]*)(?:,(.*))?$")
TVG_NAME_RE = re.compile(r'tvg-name="([^"]*)"')
GROUP_RE = re.compile(r'group-title="([^"]*)"')


# ---------------- 文件发现 ----------------


def _candidate_files(repo: dict) -> list[dict]:
    """列出仓库中疑似直播源的文件。"""
    full = repo["full_name"]
    branch = repo.get("default_branch") or "main"
    data = gh_api(f"/repos/{full}/git/trees/{branch}?recursive=1")
    if not isinstance(data, dict) or "tree" not in data:
        return []

    cands = []
    for item in data["tree"]:
        if item.get("type") != "blob":
            continue
        path = item.get("path", "")
        low = path.lower()
        if not low.endswith(GOOD_EXT):
            continue
        size = item.get("size") or 0
        if not (MIN_SIZE <= size <= MAX_SIZE):
            continue
        # 文件名或路径需含直播相关词，避免抓到 README、依赖清单
        base = low.rsplit("/", 1)[-1]
        if not any(h in base or h in low for h in NAME_HINTS):
            continue
        cands.append({"path": path, "size": size, "branch": branch})
    return cands


# ---------------- 解析 ----------------


# 多路源用 # 串接（如 http://a.m3u8#rtsp://b），且聚合仓库里常见未还原的
# HTML 实体（&amp;）。这类串接在 TVBox 上解析不稳定，只保留第一段。
MULTI_SRC_RE = re.compile(r"#(?:https?|rtsp|rtmp|rtp)://", re.I)


def clean_url(u: str) -> str:
    u = (u or "").split("$")[0].strip()  # $ 后是线路备注
    u = u.replace("&amp;", "&").replace("&quot;", '"')
    if MULTI_SRC_RE.search(u):
        u = MULTI_SRC_RE.split(u)[0]
    return u.strip()


def _clean_name(n: str) -> str:
    n = (n or "").strip()
    n = re.sub(r"\s+", "", n)
    return n


def parse_m3u(text: str) -> list[tuple[str, str, str]]:
    """返回 [(name, url, group)]。"""
    out: list[tuple[str, str, str]] = []
    pending: tuple[str, str] | None = None  # (name, group)

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#EXTINF"):
            m = EXTINF_RE.match(line)
            if m:
                attrs, disp = m.group(1), (m.group(2) or "").strip()
                g = GROUP_RE.search(attrs)
                t = TVG_NAME_RE.search(attrs)
                group = (g.group(1) if g else "").strip()
                name = _clean_name(disp or (t.group(1) if t else ""))
                pending = (name, group)
            continue
        if line.startswith("#"):
            continue
        if line.startswith(("http://", "https://")):
            if pending:
                out.append((pending[0], line, pending[1]))
                pending = None
            else:
                out.append(("", line, ""))
    return out


def parse_txt(text: str) -> list[tuple[str, str, str]]:
    """解析 TVBox 的 `名字,URL` 格式，支持 #genre# 分组头。"""
    out: list[tuple[str, str, str]] = []
    group = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#!"):
            continue
        if "#genre#" in line:
            group = _clean_name(line.split(",")[0])
            continue
        if "," not in line:
            continue
        parts = line.split(",")
        name = _clean_name(parts[0])
        # 取最后一个看起来像 URL 的字段，兼容 `名字,URL$备注` 的写法
        url = ""
        for p in reversed(parts[1:]):
            p = p.strip()
            if p.startswith(("http://", "https://")):
                url = p.split("$")[0].strip()
                break
        if name and url:
            out.append((name, url, group))
    return out


def parse_content(text: str, path: str) -> list[tuple[str, str, str]]:
    if path.lower().endswith((".m3u", ".m3u8")) or text.lstrip().startswith("#EXTM3U"):
        return parse_m3u(text)
    return parse_txt(text)


# ---------------- 黑名单 ----------------

_BAD: list[str] | None = None


def _bad_list() -> list[str]:
    global _BAD
    if _BAD is None:
        _BAD = [x.lower() for x in read_lines("blacklist.txt")]
    return _BAD


def is_blocked(name: str, url: str) -> bool:
    blob = f"{name} {url}".lower()
    for kw in _bad_list():
        if kw and kw in blob:
            return True
    return False


# 聚合仓库常把"更新时间""版本号"之类塞成一条伪频道，
# 这些不是真正的频道，混进去会污染分组和统计。
DATE_NAME_RE = re.compile(r"^\d{4}[-/年]\d{1,2}[-/月]\d{1,2}")
FAKE_HINTS = ("更新时间", "更新于", "最后更新", "数据更新", "版本", "共", "条频道")


def is_fake_channel(name: str) -> bool:
    n = (name or "").strip()
    if not n:
        return True
    if DATE_NAME_RE.match(n):
        return True
    return any(h in n for h in FAKE_HINTS)


# ---------------- 主流程 ----------------


# 仓库名里出现这些词才值得猜路径。搜索 API 会带回大量无关仓库
# （比如名叫 market-live、loot-lab 的项目），逐个探测纯属浪费。
REPO_HINTS = ("iptv", "tvbox", "tv-box", "live", "m3u", "直播", "tv")

# 常见直播源文件路径。来自对主流仓库的实际观察，覆盖 iptv-api 系、
# TVBox 系、fanmingming/live 系三类布局。
GUESS_PATHS = (
    "live.txt",
    "lives/live.txt",
    "output/result.m3u",
    "output/ipv4/result.m3u",
    "output/user_result.m3u",
    "iptv.txt",
    "tv.txt",
    "live.m3u",
    "py/TV/output/ipv4/result.m3u",
)


def _looks_like_live_repo(full_name: str) -> bool:
    low = full_name.lower()
    return any(h in low for h in REPO_HINTS)


def _guess_files(repo: dict, max_hits: int = 3) -> list[dict]:
    """API 不可用时的回退：直接按常见路径猜。

    对每个候选路径发一次 raw 请求，404 会立刻返回，代价很低。
    命中 max_hits 个就停，避免在一个仓库上耗太久。
    """
    full = repo["full_name"]
    if not _looks_like_live_repo(full):
        return []

    br = repo.get("default_branch") or "main"
    branches = [br] + [b for b in ("main", "master") if b != br]

    out: list[dict] = []
    for b in branches:
        for p in GUESS_PATHS:
            url = f"https://raw.githubusercontent.com/{full}/{b}/{p}"
            # 探测阶段允许 1 个镜像即可：命中率低，不值得为它逐个镜像重试
            r = http_get(
                url, timeout=10, retries=0, allow_mirror=True, quiet=True, max_mirrors=1
            )
            if r is None:
                continue
            size = len(r.content)
            if MIN_SIZE <= size <= MAX_SIZE:
                out.append({"path": p, "size": size, "branch": b, "prefetched": r})
            if len(out) >= max_hits:
                return out
        if out:
            break
    return out


def _fetch_one(repo: dict, f: dict) -> list[dict]:
    full = repo["full_name"]
    prefetched = f.get("prefetched")
    if prefetched is not None:
        # 路径猜测阶段已经下过一次，直接复用，不再重复请求
        r = prefetched
    else:
        raw = f"https://raw.githubusercontent.com/{full}/{f['branch']}/{f['path']}"
        # 优先条件请求：文件没变就回 304，直接用本地缓存正文，省掉整份下载。
        # 缓存里没有（首次运行）或直连不通时才回退到镜像通道。
        r = http_get_cached(raw, timeout=45)
        if r is None:
            r = http_get(raw, timeout=45, allow_mirror=True, max_mirrors=2)
    if r is None:
        return []
    try:
        text = r.content.decode("utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return []

    rows = parse_content(text, f["path"])
    if not rows:
        return []

    got = []
    for name, url, group in rows:
        if not url.startswith(("http://", "https://")):
            continue
        url = clean_url(url)
        if not url:
            continue
        if is_blocked(name, url):
            continue
        if is_fake_channel(name):
            continue
        got.append(
            {
                "name": name,
                "url": url,
                "group": group,
                "repo": full,
                "file": f["path"],
            }
        )
    return got


def _process_repo(repo: dict) -> tuple[list[dict], int, int, str]:
    """返回 (频道列表, 文件数, 条目数, 取文件方式)。"""
    files = _candidate_files(repo)
    how = "api" if files else ""
    if not files:
        files = _guess_files(repo)
        how = "guess" if files else ""
    if not files:
        return [], 0, 0, ""

    out: list[dict] = []
    for f in files:
        out.extend(_fetch_one(repo, f))
    return out, len(files), len(out), how


def collect(
    repos: list[dict], workers: int = 16, budget: float = 200
) -> tuple[list[dict], dict]:
    """并发抓取，返回 (频道列表, 统计信息)。

    budget：抓取阶段的时间预算（秒）。到点就取消还没跑完的仓库，
    用已抓到的部分继续往下走 —— 宁可少抓几个仓库，也不能让 Actions 超时白跑。
    """
    stats = {
        "repos": len(repos),
        "repos_done": 0,
        "files": 0,
        "raw": 0,
        "by_repo": {},
        "via_api": 0,
        "via_guess": 0,
    }
    all_rows: list[dict] = []
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=workers) as ex:
        fu_map = {ex.submit(_process_repo, r): r for r in repos}
        pending = set(fu_map)
        for fu in as_completed(fu_map):
            pending.discard(fu)
            repo = fu_map[fu]
            try:
                rows, nfiles, nrows, how = fu.result(timeout=300)
            except Exception as e:  # noqa: BLE001
                warn(f"处理失败 {repo['full_name']}: {type(e).__name__}")
                stats["repos"] -= 1
                continue
            stats["repos_done"] += 1
            stats["files"] += nfiles
            stats["raw"] += nrows
            if how == "api":
                stats["via_api"] += 1
            elif how == "guess":
                stats["via_guess"] += 1
            if nrows:
                stats["by_repo"][repo["full_name"]] = nrows
                log(f"  ✓ {repo['full_name']:<42} {nfiles} 文件 / {nrows} 条 [{how}]")
            all_rows.extend(rows)

            if time.time() - t0 > budget and pending:
                for f in pending:
                    f.cancel()
                log(
                    f"抓取预算 {int(budget)}s 用尽：已处理 {stats['repos_done']} 个仓库，"
                    f"放弃剩余 {len(pending)} 个"
                )
                break

    cache_flush()
    log(f"取文件方式：API 列目录 {stats['via_api']} 个仓库，路径猜测 {stats['via_guess']} 个仓库")
    log(f"HTTP 缓存：{cache_stat()}")

    # 丢弃已知失效的源，再做归一化去重
    cd = state_mod.load_cooldown()
    seen: dict[str, dict] = {}
    n_cooled = 0
    n_dup = 0

    for r in all_rows:
        nk = norm_url(r["url"])
        if not nk:
            continue
        # 冷却期内的源不进候选，省下来的配额留给新源
        if state_mod.is_cooled(cd, nk):
            n_cooled += 1
            continue

        old = seen.get(nk)
        if old is None:
            seen[nk] = r
            continue

        n_dup += 1
        # 同一路流在不同仓库里写法不同，留更短的那个（通常没被塞时效参数），
        # 但把已经拿到的名字/分组补过去。
        if len(r["url"]) < len(old["url"]):
            name = old.get("name") or r.get("name")
            group = old.get("group") or r.get("group")
            seen[nk] = r
            seen[nk]["name"] = name
            seen[nk]["group"] = group
        else:
            if not old.get("group") and r.get("group"):
                old["group"] = r["group"]
            if not old.get("name") and r.get("name"):
                old["name"] = r["name"]

    unique = list(seen.values())
    stats["unique"] = len(unique)
    stats["dup"] = n_dup
    stats["cooled"] = n_cooled
    stats["cooldown_size"] = len(cd)

    # 空名字用 URL 短形式兜底
    for r in unique:
        if not r["name"]:
            r["name"] = r["url"].rsplit("/", 1)[:24] or "未命名"

    (DATA_DIR / "raw_channels.json").write_text(
        json.dumps(unique, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    log(
        f"抓取完成：{stats['files']} 文件 / {stats['raw']} 条 -> "
        f"冷却剔除 {n_cooled} -> 重复剔除 {n_dup} -> 净剩 {len(unique)} 条"
    )
    return unique, stats


if __name__ == "__main__":
    repos = json.loads((DATA_DIR / "discovered_repos.json").read_text(encoding="utf-8"))
    rows, st = collect(repos)
    v6 = sum(1 for r in rows if is_ipv6_url(r["url"]))
    log(f"其中 IPv6 直连源 {v6} 条；当前环境 IPv6={ipv6_supported()}")
