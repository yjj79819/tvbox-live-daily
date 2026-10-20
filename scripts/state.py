# -*- coding: utf-8 -*-
"""URL 健康档案：记住哪些源活过、哪些死过，别把配额浪费在死链上。

直播源寿命短，聚合仓库里混着大量历史失效条目。如果不做记忆，
每两天跑一次就要把同一批死链重新探测一遍——1500 条探测配额里
大半会被它们吃掉，真正的新源反而排不上号。

这里维护两份状态（放在 state/ 目录，会被 git 提交，跨运行保留）：

  known_good.json  曾经探测成功的源  key -> [name, 成功次数, 最后成功日期, 延迟, 原始URL]
  cooldown.json    连续失败的源      key -> [失败次数, 解禁日期]

两份状态都以「归一化 URL」为键。聚合仓库里同一路流常被写成
`http://a.com/x?t=1` 和 `http://a.com/x?t=2`，若按原始 URL 存，
每次抓到的是不同字符串，冷却名单就永远命中不了。

失效/恢复的闭环：
  本次失败 -> 失败次数 +1 -> 达到阈值进入冷却，冷却期内不再探测
  冷却到期 -> 自动放回复测 -> 若活过来，清除冷却并写回 known_good

冷却期随失败次数递增：偶尔抖动不该被长期打入冷宫，
但反复失败的源确实该压后，把配额让给新源。
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from common import STATE_DIR, log, norm_url

KNOWN_GOOD = STATE_DIR / "known_good.json"
COOLDOWN = STATE_DIR / "cooldown.json"

# 状态文件上限。URL 一条约 90 字节，3000 条约 270KB。
# 每两天提交一次，一年增量约 50MB，仓库体积可控。
KNOWN_GOOD_MAX = 3000
COOLDOWN_MAX = 3000

# 连续失败次数 -> 冷却天数
COOLDOWN_RULES = ((8, 45), (5, 15), (3, 7), (2, 3))
# known_good 里超过这个天数没再成功的，视为自然淘汰
KNOWN_GOOD_TTL_DAYS = 21


def today() -> str:
    return time.strftime("%Y-%m-%d")


def _day_offset(days: int) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(time.time() + days * 86400))


def _days_between(a: str, b: str) -> int:
    """a 比 b 晚多少天（b 为基准）。日期解析失败时返回 0。"""
    try:
        ta = time.mktime(time.strptime(a, "%Y-%m-%d"))
        tb = time.mktime(time.strptime(b, "%Y-%m-%d"))
        return int((ta - tb) // 86400)
    except Exception:  # noqa: BLE001
        return 0


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _save(path: Path, data: dict) -> None:
    STATE_DIR.mkdir(exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )


def load_known_good() -> dict:
    return _load(KNOWN_GOOD)


def load_cooldown() -> dict:
    """加载冷却名单，顺手清掉已到期的。

    注意别把"还没判冷却、只在累计次数"的条目一并清掉——
    它们 until 是空串，看着像到期，删了就永远攒不到阈值。
    """
    d = _load(COOLDOWN)
    now = today()
    alive = {}
    released = 0
    for u, v in d.items():
        until = v[1] if isinstance(v, list) and len(v) > 1 else ""
        if until and until <= now:
            released += 1
            continue
        alive[u] = v
    if released:
        frozen = sum(1 for v in alive.values() if _is_frozen(v, now))
        log(f"冷却名单到期释放 {released} 条，仍在冷却 {frozen} 条")
    return alive


def _is_frozen(v, now: str) -> bool:
    """是否仍在冷却期内。兼容旧格式的 dict 与新格式的 list。"""
    until = v[1] if isinstance(v, list) else (v or {}).get("until", "")
    return bool(until) and until > now


def cooldown_days(fails: int) -> int:
    for threshold, days in COOLDOWN_RULES:
        if fails >= threshold:
            return days
    return 0


def is_cooled(cd: dict, url: str) -> bool:
    v = cd.get(url)
    return bool(v) and _is_frozen(v, today())


def update(results: list[dict]) -> dict:
    """用本次探测结果更新两份状态。

    results 为 probe 阶段输出的全部条目，含 ok 与 note 字段。
    返回统计信息，供报告展示。
    """
    kg = load_known_good()
    cd = load_cooldown()
    now = today()

    cooled_new = 0
    revived = 0

    for r in results:
        url = r.get("url") or ""
        if not url:
            continue
        # 本环境测不了的 IPv6 源，不参与健康判定，否则会被误杀
        if r.get("kind") == "ipv6" or r.get("note") == "环境无IPv6(未测速)":
            continue

        key = norm_url(url)

        if r.get("ok"):
            old = kg.get(key)
            hits = (old[1] if isinstance(old, list) and len(old) > 1 else 0) + 1
            kg[key] = [
                r.get("name") or "",
                hits,
                now,
                round(float(r.get("latency") or 0), 2),
                url,
            ]
            if key in cd:
                revived += 1
                cd.pop(key, None)
        else:
            old = cd.get(key)
            fails = (old[0] if isinstance(old, list) else 0) + 1
            days = cooldown_days(fails)
            if days:
                if not _is_frozen(old, now):
                    cooled_new += 1
                cd[key] = [fails, _day_offset(days)]
            else:
                # 未达冷却阈值：只累计次数，暂不冻结
                cd[key] = [fails, ""]
            # 死透的源不配留在好人名单里
            if fails >= 3:
                kg.pop(key, None)

    # 自然淘汰：太久没成功的移除，避免名单无限膨胀
    if kg:
        keep = {}
        for k, v in kg.items():
            last_ok = v[2] if isinstance(v, list) and len(v) > 2 else ""
            if last_ok and _days_between(now, last_ok) > KNOWN_GOOD_TTL_DAYS:
                continue
            keep[k] = v
        kg = keep

    kg = _trim(kg, KNOWN_GOOD_MAX, key=lambda kv: (kv[1][1] if isinstance(kv[1], list) else 0))
    cd = _trim(cd, COOLDOWN_MAX, key=lambda kv: (kv[1][0] if isinstance(kv[1], list) else 0))

    _save(KNOWN_GOOD, kg)
    _save(COOLDOWN, cd)

    return {
        "known_good": len(kg),
        "cooldown": sum(1 for v in cd.values() if _is_frozen(v, now)),
        "cooled_new": cooled_new,
        "revived": revived,
    }


def _trim(d: dict, limit: int, key) -> dict:
    if len(d) <= limit:
        return d
    items = sorted(d.items(), key=key, reverse=True)
    return dict(items[:limit])


def known_good_candidates(kg: dict, existing: set[str], limit: int = 500) -> list[dict]:
    """把档案里本次没抓到的老源补回候选队列。

    聚合仓库更新时经常删掉旧条目，但这些源可能还活着。
    补回来让它们有机会被复测，复活了就是白捡。
    existing 传的是本次已抓到的归一化 URL 集合。
    """
    out = []
    for key, v in kg.items():
        if key in existing:
            continue
        if not isinstance(v, list) or not v:
            continue
        name = v[0]
        if not name:
            continue
        # 优先用带完整参数的原始 URL，缺了就用归一化后的
        url = v[4] if len(v) > 4 and v[4] else key
        out.append(
            {
                "name": name,
                "url": url,
                "group": "",
                "repo": "state:known_good",
                "file": "",
                "from_archive": True,
            }
        )
        if len(out) >= limit:
            break
    return out
