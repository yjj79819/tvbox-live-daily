# -*- coding: utf-8 -*-
"""阶段 3：测速与优选。

直播流是长连接，不能整段下载。这里用流式读取前若干 KB 判断：
  - 直接流（.ts/.flv/mp4）：能看到媒体字节即判定可用
  - 播放列表（m3u8）：先取到 #EXTM3U，再下钻验证第一路子流

IPv6 源：GitHub Actions 无 IPv6 环境，无法测速，单独归类输出，
不判为死链（否则每天会误杀一半以上的 iptv-api 源）。
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

import requests

from common import (
    DATA_DIR,
    SESSION,
    UA,
    ipv6_supported,
    is_ipv6_url,
    log,
    norm_url,
    read_lines,
    warn,
)

import state as state_mod  # noqa: E402

PROBE_BYTES = 8192
M3U_SIG = "#EXTM3U"

# 可接受的 Content-Type 片段；为空则看实际内容
OK_CT = (
    "video/",
    "audio/",
    "application/vnd.apple.mpegurl",
    "application/x-mpegurl",
    "application/octet-stream",
    "application/ts",
)

_PRIORITY: list[str] | None = None


def _prio() -> list[str]:
    global _PRIORITY
    if _PRIORITY is None:
        _PRIORITY = [x.lower() for x in read_lines("priority_channels.txt")]
    return _PRIORITY


def is_priority(name: str) -> bool:
    low = (name or "").lower()
    return any(k in low for k in _prio())


def _read_stream(url: str, timeout: float) -> tuple[int, bytes, str, float]:
    """流式读取前 PROBE_BYTES 字节。返回 (status, 内容, content_type, 耗时秒)。"""
    t0 = time.time()
    try:
        r = SESSION.get(
            url,
            timeout=timeout,
            stream=True,
            headers={"User-Agent": UA, "Accept": "*/*"},
        )
    except Exception as e:  # noqa: BLE001
        return 0, b"", "", time.time() - t0

    try:
        buf = b""
        for chunk in r.iter_content(2048):
            buf += chunk
            if len(buf) >= PROBE_BYTES:
                break
        status = r.status_code
        ct = (r.headers.get("Content-Type") or "").lower()
        cost = round(time.time() - t0, 2)
        return status, buf, ct, cost
    except Exception as e:  # noqa: BLE001
        return r.status_code, b"", "", time.time() - t0
    finally:
        try:
            r.close()
        except Exception:  # noqa: BLE001
            pass


def _first_child(text: str, base: str) -> str:
    """从 m3u8 播放列表里取第一路子流地址。"""
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        return urljoin(base, s)
    return ""


def probe_one(ch: dict, timeout: float = 8.0) -> dict:
    url = ch["url"]
    out = dict(ch)
    out.update(ok=False, latency=999.0, kind="", note="")

    status, buf, ct, cost = _read_stream(url, timeout)
    if status != 200:
        out["note"] = f"HTTP{status}"
        return out

    head = buf[:64]
    # 情况 1：返回的是播放列表，需要下钻验证子流
    if head.startswith(M3U_SIG.encode()):
        child = _first_child(buf.decode("utf-8", errors="ignore"), url)
        if not child:
            out["note"] = "空播放列表"
            return out
        c_status, c_buf, c_ct, c_cost = _read_stream(child, timeout)
        if c_status != 200 or not c_buf:
            out["note"] = f"子流HTTP{c_status}"
            return out
        # 子流通常直接是 TS 分片（0x47 同步字节）
        if c_buf[:1] == b"\x47" or any(k in c_ct for k in OK_CT):
            out.update(ok=True, latency=round(cost + c_cost, 2), kind="m3u8")
        else:
            out["note"] = "子流非媒体"
        return out

    # 情况 2：直接返回媒体流
    if head[:1] == b"\x47":  # TS
        out.update(ok=True, latency=cost, kind="ts")
        return out
    if head[:4] == b"FLV\x01" or head[:3] == b"FLV":
        out.update(ok=True, latency=cost, kind="flv")
        return out
    if any(k in ct for k in OK_CT) and len(buf) > 512:
        out.update(ok=True, latency=cost, kind=ct.split(";")[0][:20])
        return out

    out["note"] = f"非媒体 ct={ct[:24]}"
    return out


# 至少留给新源的探测配额比例。
# 档案里的老源虽好，全给它们会让新发现的源永远排不上号。
NEW_SOURCE_RATIO = 0.45


def probe(
    channels: list[dict],
    max_probe: int = 2500,
    timeout: float = 8.0,
    workers: int = 48,
) -> tuple[list[dict], list[dict], list[dict], dict]:
    """返回 (可用频道, IPv6 未测速频道, 失效明细, 统计)。"""
    v6_ok = ipv6_supported()

    # 老源补种：本次没抓到、但档案里记着能用的源，拉回来复测
    kg = state_mod.load_known_good()
    known_set = set(kg.keys())
    existing = {norm_url(c["url"]) for c in channels}
    extra = state_mod.known_good_candidates(kg, existing, limit=int(max_probe * 0.3))
    if extra:
        log(f"档案补种 {len(extra)} 条本次未抓到的老源参与复测")
        channels = channels + extra

    v6_rows = [c for c in channels if is_ipv6_url(c["url"])]
    v4_rows = [c for c in channels if not is_ipv6_url(c["url"])]

    log(f"待探测：IPv4 {len(v4_rows)} 条，IPv6 {len(v6_rows)} 条")

    # 本环境有 IPv6 就把 IPv6 源也放进池子测一遍，好在输出前把死的挑掉；
    # 没有 IPv6（Actions 就是）则一条不测、单独归类，绝不误判成死链。
    # 早期版本在无 IPv6 环境之外会直接把 IPv6 源丢掉，本机一跑就少一半。
    if v6_ok:
        pool = v4_rows + v6_rows
    else:
        log(f"环境不支持 IPv6：{len(v6_rows)} 条 IPv6 源跳过测速，单独输出")
        pool = v4_rows

    # 排序：档案里的老源 > 央视/卫视高优先级频道 > 其余
    # 老源之所以优先，是因为它们被验证过能通，同样配额下命中率最高。
    scored = [
        (0 if norm_url(c["url"]) in known_set else 1, 0 if is_priority(c["name"]) else 1, c)
        for c in pool
    ]
    scored.sort(key=lambda x: (x[0], x[1]))
    known_rows = [x[2] for x in scored if x[0] == 0]
    new_rows = [x[2] for x in scored if x[0] == 1]

    # 但要给新源留出固定比例，否则老源会把配额吃光
    n_new_cap = int(max_probe * NEW_SOURCE_RATIO)
    n_known = min(len(known_rows), max(0, max_probe - n_new_cap))
    n_new = min(len(new_rows), max(0, max_probe - n_known))
    to_probe = known_rows[:n_known] + new_rows[:n_new]
    skipped = len(pool) - len(to_probe)
    if skipped > 0:
        log(
            f"超出配额，跳过 {skipped} 条（上限 {max_probe}："
            f"老源 {n_known} + 新源 {n_new}）"
        )

    results: list[dict] = []
    done = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(lambda c: probe_one(c, timeout), to_probe):
            results.append(r)
            done += 1
            if done % 300 == 0:
                log(f"  已探测 {done}/{len(to_probe)}，用时 {int(time.time()-t0)}s")

    # 按协议族拆回两组：IPv4 进主清单，IPv6 单独成册
    v6_res = [r for r in results if is_ipv6_url(r["url"])]
    v4_res = [r for r in results if not is_ipv6_url(r["url"])]

    ok_rows = [r for r in v4_res if r.get("ok")]
    fail_rows = [r for r in v4_res if not r.get("ok")]
    ok_rows.sort(key=lambda x: x["latency"])

    if v6_ok:
        ok_v6 = [r for r in v6_res if r.get("ok")]
        fail_rows += [r for r in v6_res if not r.get("ok")]
        v6_out = ok_v6
    else:
        # 没测过的原样输出，一条不扔
        for c in v6_rows:
            c.update(ok=False, latency=0.0, kind="ipv6", note="环境无IPv6(未测速)")
        v6_out = v6_rows
        ok_v6 = []

    stats = {
        "ipv4_total": len(v4_rows),
        "ipv6_total": len(v6_rows),
        "probed": len(to_probe),
        "skipped_quota": skipped,
        "ok": len(ok_rows),
        "fail": len(fail_rows),
        "v6_ok": len(ok_v6),
        "elapsed_sec": int(time.time() - t0),
    }
    log(
        f"测速完成：探测 {stats['probed']} 条 -> 可用 {stats['ok']} 条 / "
        f"失效 {stats['fail']} 条"
        + (f" / IPv6 可用 {stats['v6_ok']} 条" if v6_ok else "（IPv6 未测）")
        + f" (耗时 {stats['elapsed_sec']}s)"
    )

    (DATA_DIR / "probed.json").write_text(
        json.dumps(
            {"ok": ok_rows, "fail": fail_rows, "ipv6": v6_out},
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    return ok_rows, v6_out, fail_rows, stats
