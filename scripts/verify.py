# -*- coding: utf-8 -*-
"""地址可用性验证：把每个通道都真实拉一遍，看看到底哪个能用。

两套东西一起验：
  - 远端：直连与各加速站，逐个真实请求
  - 本地：config/local_base.txt 配的局域网地址

只看 HTTP 状态码会被骗。实测中就遇到过返回 200 但内容只有 48 字节 HTML 的
加速站——状态码好看，文件根本没拿到。所以这里同时做内容校验：
txt 必须有 #genre#、m3u 必须有 #EXTM3U、json 必须有 lives 字段。

用法：
    python scripts/verify.py                 # 验证全部
    python scripts/verify.py --files live.txt # 只验指定文件
    python scripts/verify.py --no-local      # 跳过本地通道
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    OUTPUT_DIR,
    SESSION,
    UA,
    local_base,
    log,
    mirrors,
    repo_slug,
    short_hash,
)

TIMEOUT = float(os.environ.get("VERIFY_TIMEOUT", "15"))

# 每个文件的合法性指纹：内容里必须含有这个串，否则视为拿到了错误页
SIGNATURES = {
    "live.txt": "#genre#",
    "live_ipv6.txt": "#genre#",
    "live.m3u": "#EXTM3U",
    "tvbox_live.json": '"lives"',
}


def fetch(url: str, timeout: float = TIMEOUT) -> tuple[int, bytes, float]:
    """返回 (状态码, 内容, 耗时秒)。网络层失败状态码记为 0。"""
    t0 = time.time()
    try:
        r = SESSION.get(url, timeout=timeout, headers={"User-Agent": UA})
        return r.status_code, r.content, round(time.time() - t0, 2)
    except Exception:  # noqa: BLE001
        return 0, b"", round(time.time() - t0, 2)


def judge(fname: str, status: int, body: bytes) -> tuple[str, str]:
    """判定结果。返回 (结论, 备注)。"""
    if status == 0:
        return "不可达", "连接超时/被重置"
    if status >= 400:
        return "不可达", f"HTTP{status}"
    if status >= 300:
        return "存疑", f"HTTP{status} 重定向"
    sig = SIGNATURES.get(fname)
    if sig and sig.encode() not in body:
        head = body[:40].decode("utf-8", errors="ignore").replace("\n", " ")
        return "假可用", f"200 但内容异常：{head[:36]}"
    return "可用", ""


def main(argv: list[str] | None = None) -> int:
    # argv 显式传入，被 run.py 调用时才不会去解析主程序的参数
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", nargs="*", default=None, help="只验指定文件")
    ap.add_argument("--no-local", action="store_true", help="跳过本地通道")
    ap.add_argument("--no-remote", action="store_true", help="跳过远端通道")
    args = ap.parse_args(argv)

    slug, branch = repo_slug()
    files = args.files or ["live.txt", "tvbox_live.json", "live_ipv6.txt", "live.m3u"]

    ms = mirrors()
    lb = "" if args.no_local else local_base()

    log(f"验证目标：{slug}（{branch}），通道 {len(ms)} 个 + 本地 {'有' if lb else '无'}")

    # 先把本地文件内容读出来，用于后续比对
    local_hash: dict[str, str] = {}
    local_size: dict[str, int] = {}
    for f in files:
        p = OUTPUT_DIR / f
        if p.exists():
            b = p.read_bytes()
            local_hash[f] = short_hash(b.decode("utf-8", errors="ignore"))
            local_size[f] = len(b)

    results: list[dict] = []
    for f in files:
        if not args.no_remote:
            for mname, tpl in ms:
                url = f"https://raw.githubusercontent.com/{slug}/{branch}/output/{f}"
                url = tpl.replace("{u}", url).replace("{slug}", slug)
                url = url.replace("{branch}", branch).replace("{path}", f"output/{f}")
                status, body, cost = fetch(url)
                verdict, note = judge(f, status, body)
                rh = short_hash(body.decode("utf-8", errors="ignore"))
                results.append(
                    {
                        "file": f,
                        "ch": mname,
                        "kind": "远端",
                        "url": url,
                        "status": status,
                        "cost": cost,
                        "size": len(body),
                        "verdict": verdict,
                        "note": note,
                        "remote_hash": rh,
                    }
                )
                log(f"  [{verdict}] {f} <- {mname} {status} {cost}s {len(body)}B")
        if lb:
            url = f"{lb}{f}"
            status, body, cost = fetch(url, timeout=6)
            verdict, note = judge(f, status, body)
            rh = short_hash(body.decode("utf-8", errors="ignore"))
            results.append(
                {
                    "file": f,
                    "ch": "本地",
                    "kind": "本地",
                    "url": url,
                    "status": status,
                    "cost": cost,
                    "size": len(body),
                    "verdict": verdict,
                    "note": note,
                    "remote_hash": rh,
                }
            )
            log(f"  [{verdict}] {f} <- 本地 {status} {cost}s {len(body)}B")

    # 一致性：远端内容与本地文件比对
    for r in results:
        f = r["file"]
        if f not in local_hash:
            r["sync"] = "本地无此文件"
        elif r["verdict"] != "可用":
            r["sync"] = "-"
        elif r["remote_hash"] == local_hash[f]:
            r["sync"] = "一致"
        else:
            r["sync"] = f"落后(本地 {local_hash[f]})"

    # 通道层面汇总：取每个通道在所有文件上的表现
    chs: dict[str, list[dict]] = {}
    for r in results:
        chs.setdefault(r["ch"], []).append(r)

    rank = []
    for ch, rs in chs.items():
        ok = [x for x in rs if x["verdict"] == "可用"]
        if not ok:
            rank.append((ch, 0, 0.0, len(rs)))
            continue
        avg = sum(x["cost"] for x in ok) / len(ok)
        rank.append((ch, len(ok), round(avg, 2), len(rs)))
    rank.sort(key=lambda x: (-x[1], x[2]))

    best = rank[0] if rank else ("", 0, 0.0, 0)

    L = []
    L.append("# 地址可用性验证")
    L.append("")
    L.append(
        f"生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}　"
        f"仓库：`{slug}`　分支：`{branch}`"
    )
    L.append("")
    L.append("## 结论")
    L.append("")
    if best[1]:
        L.append(f"- **最快可用通道：{best[0]}**，平均 {best[2]}s")
    else:
        L.append("- **没有任何通道可用**，检查仓库地址与分支是否正确")
    ok_ch = [x for x in rank if x[1] > 0]
    L.append(f"- 可用通道 {len(ok_ch)} / {len(rank)}")
    if lb:
        local_rows = [r for r in results if r["kind"] == "本地"]
        local_ok = [r for r in local_rows if r["verdict"] == "可用"]
        if local_rows:
            L.append(
                f"- 本地通道：{'可用' if local_ok else '不可达'}（{len(local_ok)}/{len(local_rows)} 个文件）"
            )
        else:
            L.append("- 本地通道：未配置")
    L.append("")

    L.append("## 通道排名")
    L.append("")
    L.append("| 通道 | 可用文件 | 平均耗时 | 覆盖率 |")
    L.append("|---|---|---|---|")
    for ch, n_ok, avg, total in rank:
        L.append(f"| {ch} | {n_ok}/{total} | {avg}s | {int(n_ok / total * 100) if total else 0}% |")
    L.append("")

    for f in files:
        rows = [r for r in results if r["file"] == f]
        if not rows:
            continue
        L.append(f"## {f}")
        L.append("")
        if f in local_hash:
            L.append(f"本地文件：{local_size[f]} 字节，sha256 前 12 位 `{local_hash[f]}`")
            L.append("")
        L.append("| 通道 | 结论 | 状态码 | 耗时 | 大小 | 内容与本地 | 备注 |")
        L.append("|---|---|---|---|---|---|---|")
        for r in rows:
            L.append(
                f"| {r['ch']} | {r['verdict']} | {r['status']} | {r['cost']}s | "
                f"{r['size']}B | {r['sync']} | {r['note']} |"
            )
        L.append("")

    L.append("## TVBox 该填哪个地址")
    L.append("")
    if best[1]:
        for f in ("live.txt", "tvbox_live.json"):
            rows = [
                r
                for r in results
                if r["file"] == f and r["ch"] == best[0] and r["verdict"] == "可用"
            ]
            if rows:
                L.append(f"- {f}：`{rows[0]['url']}`")
    else:
        L.append("- 暂无可用地址")
    L.append("")
    L.append("> 「假可用」指返回 200 但内容不对（拿到了 HTML 错误页），不能算能用。")
    L.append("")

    (OUTPUT_DIR / "verify.md").write_text("\n".join(L), encoding="utf-8")
    log(f"验证完成，结果写入 {OUTPUT_DIR / 'verify.md'}")

    if best[1] == 0:
        log("没有任何可用通道")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
