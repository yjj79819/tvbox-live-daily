# -*- coding: utf-8 -*-
"""阶段 1：发现仓库。

两个来源：
  1. 种子清单 config/seed_repos.txt —— 人工验证过，保底
  2. GitHub 搜索 API —— 按 updated desc 发现最新活跃仓库，负责"新"
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from common import DATA_DIR, gh_api, log, read_lines, warn


def _load_seeds() -> list[dict]:
    seeds = []
    for line in read_lines("seed_repos.txt"):
        if "/" in line:
            seeds.append(
                {"full_name": line, "stars": -1, "pushed_at": "", "source": "seed"}
            )
    return seeds


def _search(keyword: str, per_page: int) -> list[dict]:
    """按关键词搜索最近更新的仓库。

    未认证搜索限额 10 次/分钟，带 token 30 次/分钟；关键词逐个串行请求即可，
    不追求并发，避免触发 403。
    """
    path = (
        f"/search/repositories?q={keyword}&sort=updated&order=desc"
        f"&per_page={per_page}"
    )
    data = gh_api(path)
    if data is None:
        warn(f"搜索失败: {keyword}")
        return []
    if isinstance(data, dict) and "items" not in data:
        warn(f"搜索被限流或出错: {keyword} -> {str(data)[:80]}")
        return []

    out = []
    for r in data.get("items", []):
        out.append(
            {
                "full_name": r.get("full_name", ""),
                "stars": r.get("stargazers_count", 0),
                "pushed_at": (r.get("pushed_at") or "")[:10],
                "default_branch": r.get("default_branch") or "main",
                "source": f"search:{keyword}",
            }
        )
    return out


def discover(
    max_per_keyword: int = 12,
    max_repos: int = 50,
    cache_days: float = 7,
    kw_limit: int = 0,
) -> list[dict]:
    """返回去重后的仓库列表。

    排序规则：种子仓库优先（人工验证过，必须抓），
    其余按星数降序——星数是唯一能低成本筛掉噪声仓库的信号。

    仓库清单在 7 天内复用缓存、只跑 1 个关键词做增量补充：
    搜索 API 限额最紧（带 token 也才 30 次/分钟），两天跑一次时
    仓库集合几乎不变，没必要每次把关键词全刷一遍。
    """
    repos: dict[str, dict] = {}

    for s in _load_seeds():
        repos[s["full_name"]] = s
    log(f"种子仓库 {len(repos)} 个")

    cache_file = DATA_DIR / "discovered_repos.json"
    age_days = None
    if cache_file.exists():
        age_days = (time.time() - cache_file.stat().st_mtime) / 86400
        if age_days < cache_days:
            try:
                cached = json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                cached = []
            for r in cached:
                if r.get("full_name") and r["full_name"] not in repos:
                    repos[r["full_name"]] = r
            log(f"复用 {age_days:.1f} 天前的仓库缓存 {len(cached)} 个，本次只做增量搜索")

    kws = read_lines("discover_keywords.txt")
    if kw_limit:
        kws = kws[:kw_limit]
    elif age_days is not None and age_days < cache_days and kws:
        # 缓存新鲜：只跑 1 个关键词补新仓库，且按「年内第几天」轮换，
        # 免得每次都搜同一个词、新仓库永远只在第一个词的圈子里打转。
        pick = kws[int(time.strftime("%j")) % len(kws)]
        kws = [pick]
        log(f"增量搜索轮换关键词：{pick}")
    for kw in kws:
        got = _search(kw, max_per_keyword)
        for r in got:
            name = r["full_name"]
            # 搜索结果补充默认分支；种子仓库沿用 API 查询结果
            if name not in repos:
                repos[name] = r
        log(f"搜索 [{kw}] 命中 {len(got)} 个，累计 {len(repos)}")
        time.sleep(2.5)  # 搜索 API 限流保护

    result = list(repos.values())
    result.sort(key=lambda x: (0 if x["source"] == "seed" else 1, -(x.get("stars") or 0)))
    # 缓存必须写「未截断」的全量：否则下次运行复用的是被 max_repos 削过的
    # 清单，仓库池只会越跑越小。
    (DATA_DIR / "discovered_repos.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    if len(result) > max_repos:
        result = result[:max_repos]
    log(f"发现阶段完成，取前 {len(result)} 个仓库（清单缓存已存全量 {len(repos)} 个）")
    return result


if __name__ == "__main__":
    r = discover()
    for x in r[:20]:
        print(f"{x['stars']:>6}* {x['full_name']:<45} {x['pushed_at']}  {x['source']}")
