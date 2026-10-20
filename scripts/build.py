# -*- coding: utf-8 -*-
"""阶段 4：生成交付文件。

输出（output/ 目录，全部会被 git 提交）：
  live.txt          TVBox 的 `名字,URL` 格式，IPv4 源，已测速优选
  live_ipv6.txt     IPv6 源，未经测速（家庭宽带若支持 IPv6 可加）
  live.m3u          通用 m3u，给 PotPlayer / VLC / IPTV 播放器
  live_dead.txt     本次探测失效的源与失败原因，供排查
  tvbox_live.json   TVBox 的 lives 配置，含直连/加速/本地三组地址
  mirrors.md        所有可用访问地址（直连与各加速站）
  verify.md         两套地址（远端 / 本地）的实测结果
  report.md         本次统计报告

关于「失效了怎么办」，这里有三层处理：
  1. 同一频道的多个源合并成一行（URL 用 # 连接），TVBox 播不通会自动切下一条
  2. 挑选备用源时强制跨主机，避免三条源全挂在同一个 CDN 上
  3. 失效源写入 live_dead.txt 并进入冷却名单，下轮不再浪费配额
"""
from __future__ import annotations

import json
import os
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

from common import (
    DATA_DIR,
    OUTPUT_DIR,
    host_of,
    local_base,
    log,
    mirrors,
    render_tpl,
    repo_slug,
)

KEEP_PER_CHANNEL = int(os.environ.get("KEEP_PER_CHANNEL", "3"))
# 同一频道的多个源合并成一行。TVBox 的 # 多线路支持播放失败自动切换，
# 这是客户端侧最有效的容灾手段——文件里留着备用，播不动时自己换。
JOIN_BACKUP = os.environ.get("JOIN_BACKUP", "1") != "0"
# tvbox_live.json 里放几个访问通道（含直连）
MAX_CHANNELS_IN_JSON = 3
# 失效清单最多留多少条，以及每种失败原因各留多少条
DEAD_MAX = 600
DEAD_PER_NOTE = 120
EPG = "https://epg.112114.eu.org/?ch={name}&date={date}"

EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U00002190-\U000021FF"
    "\U00002B00-\U00002BFF"
    "\U0000FE0F"
    "]+",
    flags=re.UNICODE,
)

# 交付文件 -> 说明。mirrors.md 与 verify.md 都按这个顺序输出。
FILES = (
    ("live.txt", "TVBox 直播接口（主用）"),
    ("tvbox_live.json", "TVBox 直播配置"),
    ("live_ipv6.txt", "IPv6 源"),
    ("live.m3u", "通用 m3u（PotPlayer/VLC）"),
)


def clean_group(g: str) -> str:
    g = EMOJI_RE.sub("", g or "").strip()
    g = re.sub(r"\s+", "", g)
    return g or "其他频道"


def classify(name: str, group: str) -> str:
    n = (name or "").strip()
    up = n.upper()
    if "CCTV" in up or "CGTN" in up or "央视" in n or "中央" in n:
        return "央视频道"
    if "卫视" in n or "衛視" in n:
        return "卫视频道"
    if any(k in n for k in ("体育", "足球", "篮球", "网球", "赛车")):
        return "体育频道"
    if any(k in n for k in ("电影", "影院", "院线")):
        return "影视频道"
    if any(k in n for k in ("少儿", "卡通", "动漫", "动画")):
        return "少儿频道"
    if any(k in n for k in ("新闻", "资讯")):
        return "新闻频道"
    if any(k in n for k in ("纪实", "纪录", "探索", "地理")):
        return "纪实频道"
    return clean_group(group)


def pick_best(rows: list[dict]) -> list[dict]:
    """每个频道名保留延迟最低的 KEEP_PER_CHANNEL 条，且尽量来自不同主机。

    一个频道留 3 条源，若 3 条全指向同一台 CDN，那台 CDN 一挂三条同时失效，
    备用就等于没留。所以先按主机各取一条，不够数再允许同主机补位。
    """
    by: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by[r["name"]].append(r)

    out = []
    for _name, items in by.items():
        items.sort(key=lambda x: (x.get("latency") or 999, x["url"]))

        picked: list[dict] = []
        used_hosts: set[str] = set()
        for it in items:
            h = host_of(it["url"])
            if h in used_hosts:
                continue
            used_hosts.add(h)
            picked.append(it)
            if len(picked) >= KEEP_PER_CHANNEL:
                break

        if len(picked) < KEEP_PER_CHANNEL:
            picked_ids = {id(x) for x in picked}
            for it in items:
                if id(it) in picked_ids:
                    continue
                picked.append(it)
                if len(picked) >= KEEP_PER_CHANNEL:
                    break

        picked.sort(key=lambda x: (x.get("latency") or 999, x["url"]))
        out.extend(picked)
    return out


def group_sort(rows: list[dict]) -> list[tuple[str, list[dict]]]:
    g: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        g[classify(r["name"], r.get("group", ""))].append(r)

    order = [
        "央视频道",
        "卫视频道",
        "体育频道",
        "影视频道",
        "少儿频道",
        "新闻频道",
        "纪实频道",
    ]
    keys = [k for k in order if k in g] + sorted(k for k in g if k not in order)
    result = []
    for k in keys:
        items = sorted(g[k], key=lambda x: (x["name"], x.get("latency") or 999))
        result.append((k, items))
    return result


def write_txt(path: Path, grouped: list[tuple[str, list[dict]]]) -> tuple[int, int]:
    """写 TVBox 的 txt 格式。

    返回 (频道数, 源条数)。合并模式下同一频道的多个源写在同一行，
    TVBox 播放失败会自动尝试 # 后面的下一路。
    """
    lines = []
    n_ch = 0
    n_url = 0
    for gname, items in grouped:
        lines.append(f"{gname},#genre#")
        if JOIN_BACKUP:
            merged: dict[str, list[str]] = {}
            for it in items:
                merged.setdefault(it["name"], []).append(it["url"])
            for name, urls in merged.items():
                lines.append(f"{name}," + "#".join(urls))
                n_ch += 1
                n_url += len(urls)
        else:
            for it in items:
                lines.append(f"{it['name']},{it['url']}")
                n_ch += 1
                n_url += 1
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return n_ch, n_url


def write_m3u(path: Path, grouped: list[tuple[str, list[dict]]]) -> int:
    """m3u 只保留每个频道最快的一条。

    VLC / PotPlayer 不认 # 多线路，塞进去只会显示一堆重复频道。
    """
    lines = ["#EXTM3U"]
    n = 0
    for gname, items in grouped:
        seen: set[str] = set()
        for it in items:
            if it["name"] in seen:
                continue
            seen.add(it["name"])
            lines.append(
                f'#EXTINF:-1 tvg-name="{it["name"]}" group-title="{gname}",{it["name"]}'
            )
            lines.append(it["url"])
            n += 1
    path.write_text("\n".join(lines), encoding="utf-8")
    return n


def write_dead(path: Path, fail_rows: list[dict]) -> int:
    """输出本次失效清单：名字,URL,失败原因,来源仓库。

    失效条目动辄两三千条，全写进去文件会有 300KB，
    每两天提交一次仓库涨得太快。按失败原因归类后每种留一部分即可，
    排查时看原因分布比看几千行 URL 有用得多。
    """
    rows = sorted(fail_rows, key=lambda x: (x.get("note") or "", x.get("name") or ""))

    by_note: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_note[r.get("note") or "未知"].append(r)

    lines = [
        "# 本次探测失效的源",
        "# 格式：频道名,URL,失败原因,来源仓库",
        f"# 本次共失效 {len(rows)} 条，下面按失败原因归类，"
        f"每种最多列 {DEAD_PER_NOTE} 条，合计 {min(len(rows), DEAD_MAX)} 条。",
        "# 连续失败会进入冷却名单，到期自动放回复测；这里只作排查留档。",
        "",
    ]

    n = 0
    for note in sorted(by_note, key=lambda k: -len(by_note[k])):
        items = by_note[note]
        lines.append(f"# —— {note}：{len(items)} 条 ——")
        for r in items[:DEAD_PER_NOTE]:
            if n >= DEAD_MAX:
                break
            lines.append(
                f'{r.get("name") or "未命名"},{r.get("url") or ""},'
                f'{note},{r.get("repo") or ""}'
            )
            n += 1
        if n >= DEAD_MAX:
            break

    path.write_text("\n".join(lines), encoding="utf-8")
    return len(rows)


def all_urls(slug: str, branch: str) -> list[tuple[str, str, str]]:
    """返回 [(通道名, 文件, 完整URL)]，按 mirrors 配置顺序展开。"""
    out = []
    for fname, _desc in FILES:
        for mname, tpl in mirrors():
            out.append((mname, fname, render_tpl(tpl, slug, branch, f"output/{fname}")))
    lb = local_base()
    if lb:
        for fname, _desc in FILES:
            out.append(("本地", fname, f"{lb}{fname}"))
    return out


def write_mirrors_md(path: Path, slug: str, branch: str) -> None:
    lb = local_base()
    L = [
        "# 可用地址清单",
        "",
        f"仓库：`{slug}`　分支：`{branch}`　生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "直连走不通时，往下换一个通道即可，文件内容完全一致。",
        "",
    ]
    for fname, desc in FILES:
        L.append(f"## {fname}　{desc}")
        L.append("")
        L.append("| 通道 | 地址 |")
        L.append("|---|---|")
        for mname, tpl in mirrors():
            url = render_tpl(tpl, slug, branch, f"output/{fname}")
            L.append(f"| {mname} | `{url}` |")
        if lb:
            L.append(f"| 本地 | `{lb}{fname}` |")
        L.append("")

    L.append("## 说明")
    L.append("")
    L.append("- **直连**最快，但部分地区访问 raw.githubusercontent.com 不畅。")
    L.append("- **加速站**是把完整 raw 地址交给第三方代理中转，内容与直连一致。")
    L.append("- **jsDelivr** 走 CDN 缓存，对分支内容最长滞后 12 小时，仅作备用。")
    L.append("- 想增删通道改 `config/mirrors.txt`；想开启本地通道改 `config/local_base.txt`。")
    L.append("")
    path.write_text("\n".join(L), encoding="utf-8")


def write_tvbox_json(path: Path, slug: str, branch: str) -> int:
    """生成 TVBox 的 lives 配置，含多个访问通道与本地地址。"""
    ms = mirrors()
    primary = ms[0]
    lives = []

    def entry(name: str, mname: str, tpl: str, fname: str) -> dict:
        return {
            "name": name,
            "type": 0,
            "url": render_tpl(tpl, slug, branch, f"output/{fname}"),
            "epg": EPG,
        }

    # 第一组：直连，日常主用
    lives.append(entry("优选直播", primary[0], primary[1], "live.txt"))

    # 备用组：各加速通道，直连抽风时切过去
    for mname, tpl in ms[1:MAX_CHANNELS_IN_JSON]:
        lives.append(entry(f"优选直播·{mname}", mname, tpl, "live.txt"))

    lb = local_base()
    if lb:
        lives.append(
            {"name": "优选直播·本地", "type": 0, "url": f"{lb}live.txt", "epg": EPG}
        )

    lives.append(entry("直播·IPv6", primary[0], primary[1], "live_ipv6.txt"))
    lives.append(
        {
            "name": "通用M3U",
            "type": 0,
            "url": render_tpl(primary[1], slug, branch, "output/live.m3u"),
        }
    )

    cfg = {"lives": lives}
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(lives)


def write_report(
    path: Path,
    collect_stats: dict,
    probe_stats: dict,
    grouped: list[tuple[str, list[dict]]],
    v6_count: int,
    repos: list[dict],
    history: list[dict],
    state_stats: dict,
    slug: str,
    branch: str,
    n_channels: int,
) -> None:
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    lat = [it.get("latency") or 0 for _, items in grouped for it in items]
    lat.sort()
    p50 = lat[len(lat) // 2] if lat else 0
    p95 = lat[int(len(lat) * 0.95)] if lat else 0

    L = []
    L.append("# 直播源优选报告")
    L.append("")
    L.append(f"生成时间：{now}　仓库：`{slug}`　分支：`{branch}`")
    L.append("")
    L.append("## 总览")
    L.append("")
    L.append("| 指标 | 数值 |")
    L.append("|---|---|")
    L.append(
        f"| 扫描仓库 | {collect_stats.get('repos_done', 0)} / 计划 {collect_stats.get('repos', 0)} |"
    )
    L.append(f"| 命中文件 | {collect_stats.get('files', 0)} |")
    L.append(f"| 抓取条目 | {collect_stats.get('raw', 0)} |")
    L.append(f"| 冷却剔除 | {collect_stats.get('cooled', 0)} |")
    L.append(f"| 重复剔除 | {collect_stats.get('dup', 0)} |")
    L.append(f"| 去重后 | {collect_stats.get('unique', 0)} |")
    _ab = probe_stats.get("abandoned", 0)
    L.append(
        f"| IPv4 探测 | {probe_stats.get('probed', 0)}"
        f"（跳过 {probe_stats.get('skipped_quota', 0)}"
        + (f"，预算到点放弃 {_ab}" if _ab else "")
        + "） |"
    )
    L.append(f"| **可用频道源** | **{probe_stats.get('ok', 0)}** |")
    L.append(f"| 失效剔除 | {probe_stats.get('fail', 0)} |")
    L.append(f"| IPv6 源（未测速） | {v6_count} |")
    L.append(f"| 最终入库频道 / 源 | {n_channels} / {probe_stats.get('urls', 0)} |")
    L.append(f"| 延迟中位数 / P95 | {p50:.2f}s / {p95:.2f}s |")
    L.append(f"| 测速耗时 | {probe_stats.get('elapsed_sec', 0)}s |")
    L.append("")

    L.append("## 失效处理")
    L.append("")
    L.append("| 指标 | 数值 |")
    L.append("|---|---|")
    L.append(f"| 档案中曾成功 | {state_stats.get('known_good', 0)} |")
    L.append(f"| 冷却中 | {state_stats.get('cooldown', 0)} |")
    L.append(f"| 本次新进冷却 | {state_stats.get('cooled_new', 0)} |")
    L.append(f"| 本次复活 | {state_stats.get('revived', 0)} |")
    L.append("")
    L.append(
        "失效源先剔除、再进冷却名单（连续失败 2/3/5/8 次分别冷却 3/7/15/45 天），"
        "到期自动放回复测。明细见 `live_dead.txt`。"
    )
    L.append("")

    L.append("## 分组分布")
    L.append("")
    L.append("| 分组 | 频道源数 |")
    L.append("|---|---|")
    for gname, items in grouped:
        L.append(f"| {gname} | {len(items)} |")
    L.append("")

    top = Counter(collect_stats.get("by_repo", {})).most_common(10)
    if top:
        L.append("## 贡献最多的仓库")
        L.append("")
        L.append("| 仓库 | 条目数 |")
        L.append("|---|---|")
        for name, c in top:
            L.append(f"| {name} | {c} |")
        L.append("")

    if history:
        L.append("## 历史趋势")
        L.append("")
        L.append("| 日期 | 抓取 | 可用 | 入库 |")
        L.append("|---|---|---|---|")
        for h in history[-14:]:
            L.append(
                f"| {h['date']} | {h.get('raw', 0)} | {h.get('ok', 0)} | {h.get('channels', 0)} |"
            )
        L.append("")

    L.append("## 使用方式")
    L.append("")
    for fname, desc in FILES:
        mname, tpl = mirrors()[0]
        url = render_tpl(tpl, slug, branch, f"output/{fname}")
        L.append(f"- **{desc}**：`{url}`")
    lb = local_base()
    if lb:
        L.append(f"- **本地通道**：`{lb}live.txt`")
    L.append("")
    L.append("完整通道清单见 `mirrors.md`，实测结果见 `verify.md`。")
    L.append("")
    L.append("> IPv6 源在 GitHub Actions 环境无法测速，单独放 `live_ipv6.txt`。")
    L.append("> 家庭宽带若支持 IPv6，可在 TVBox 里额外添加该文件。")
    L.append("")

    path.write_text("\n".join(L), encoding="utf-8")


def build(
    ok_rows: list[dict],
    v6_rows: list[dict],
    fail_rows: list[dict],
    collect_stats: dict,
    probe_stats: dict,
    repos: list[dict],
    state_stats: dict,
) -> dict:
    slug, branch = repo_slug()

    best = pick_best(ok_rows)
    grouped = group_sort(best)

    n_ch, n_url = write_txt(OUTPUT_DIR / "live.txt", grouped)
    probe_stats["urls"] = n_url

    n_v6 = 0
    if v6_rows:
        n_v6, _ = write_txt(OUTPUT_DIR / "live_ipv6.txt", group_sort(pick_best(v6_rows)))
    else:
        # 抓不到 IPv6 源时也要覆盖旧文件，否则会一直留着上一版内容，
        # 而那批源可能早就失效了。
        (OUTPUT_DIR / "live_ipv6.txt").write_text(
            "# 本次未抓到 IPv6 源\n"
            "# Actions 运行环境没有 IPv6，这类源不参与测速，单独归类\n",
            encoding="utf-8",
        )

    n_m3u = write_m3u(OUTPUT_DIR / "live.m3u", grouped)
    n_dead = write_dead(OUTPUT_DIR / "live_dead.txt", fail_rows)
    n_lives = write_tvbox_json(OUTPUT_DIR / "tvbox_live.json", slug, branch)
    write_mirrors_md(OUTPUT_DIR / "mirrors.md", slug, branch)

    # 历史记录
    hist_path = DATA_DIR / "history.json"
    history: list[dict] = []
    if hist_path.exists():
        try:
            history = json.loads(hist_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            history = []
    today = time.strftime("%Y-%m-%d")
    rec = {
        "date": today,
        "raw": collect_stats.get("raw", 0),
        "ok": probe_stats.get("ok", 0),
        "channels": n_ch,
    }
    history = [h for h in history if h.get("date") != today]
    history.append(rec)
    history = history[-60:]
    hist_path.write_text(json.dumps(history, ensure_ascii=False, indent=1), encoding="utf-8")

    write_report(
        OUTPUT_DIR / "report.md",
        collect_stats,
        probe_stats,
        grouped,
        len(v6_rows),
        repos,
        history,
        state_stats,
        slug,
        branch,
        n_ch,
    )

    log(
        f"输出完成：live.txt {n_ch} 频道/{n_url} 源 / live.m3u {n_m3u} 条 / "
        f"IPv6 {n_v6} 条 / 失效 {n_dead} 条 / 通道 {n_lives} 组"
    )
    return {"txt": n_url, "channels": n_ch, "m3u": n_m3u, "ipv6": n_v6, "groups": len(grouped)}


if __name__ == "__main__":
    log("build 模块需由 run.py 调用")
