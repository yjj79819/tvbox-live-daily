# -*- coding: utf-8 -*-
"""主入口：发现 -> 抓取 -> 测速优选 -> 生成交付文件。

用法：
    python run.py                      # 全流程
    python run.py --max-probe 800      # 限制探测条数（本地快速试跑）
    python run.py --no-probe           # 只抓取不测速（调试解析用）

可用环境变量：
    MAX_PROBE        最大探测条数，默认 2500
    REPO_LIMIT       最多处理几个仓库，默认 40
    TIMEOUT          单条探测超时秒，默认 8
    WORKERS          探测并发数，默认 48
    FETCH_WORKERS    抓取并发数，默认 16
    FETCH_BUDGET     抓取阶段时间预算秒，默认 200
    PROBE_BUDGET     测速阶段时间预算秒，默认 240
    KEEP_PER_CHANNEL 每个频道保留几条备用源，默认 3
    GH_TOKEN         GitHub API 令牌（可选，Actions 中自动注入）

各阶段都有硬时间预算：宁可少抓少测，也不能让 Actions 跑到超时白跑一场。
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

import build as build_mod  # noqa: E402
import collect as collect_mod  # noqa: E402
import discover as discover_mod  # noqa: E402
import probe as probe_mod  # noqa: E402
import state as state_mod  # noqa: E402
from common import gh_remaining, log  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-probe", type=int, default=int(os.environ.get("MAX_PROBE", "2500")))
    ap.add_argument("--repo-limit", type=int, default=int(os.environ.get("REPO_LIMIT", "40")))
    ap.add_argument("--timeout", type=float, default=float(os.environ.get("TIMEOUT", "7")))
    ap.add_argument("--workers", type=int, default=int(os.environ.get("WORKERS", "32")))
    ap.add_argument(
        "--fetch-workers", type=int, default=int(os.environ.get("FETCH_WORKERS", "16"))
    )
    ap.add_argument(
        "--fetch-budget", type=float, default=float(os.environ.get("FETCH_BUDGET", "200"))
    )
    ap.add_argument(
        "--probe-budget", type=float, default=float(os.environ.get("PROBE_BUDGET", "240"))
    )
    ap.add_argument("--no-probe", action="store_true", help="跳过测速，仅抓取解析")
    ap.add_argument("--verify", action="store_true", help="结束后顺带验证各访问通道")
    args = ap.parse_args()

    t0 = time.time()
    log("=" * 60)
    log("直播源每日优选 启动")
    log(f"GitHub API 剩余额度: {gh_remaining()}")
    log("=" * 60)

    # 阶段 1：发现仓库
    repos = discover_mod.discover(max_repos=args.repo_limit)
    if not repos:
        log("未发现任何仓库，退出")
        return 1

    # 阶段 2：抓取解析
    channels, cstats = collect_mod.collect(
        repos, workers=args.fetch_workers, budget=args.fetch_budget
    )
    if not channels:
        log("未抓到任何频道，退出")
        return 1

    # 阶段 3：测速优选
    if args.no_probe:
        log("--no-probe：跳过测速，直接按抓取顺序输出")
        ok_rows = channels
        v6_rows = []
        fail_rows = []
        pstats = {
            "ipv4_total": len(channels),
            "ipv6_total": 0,
            "probed": 0,
            "skipped_quota": 0,
            "ok": len(channels),
            "fail": 0,
            "elapsed_sec": 0,
        }
        sstats = {}
    else:
        ok_rows, v6_rows, fail_rows, pstats = probe_mod.probe(
            channels,
            max_probe=args.max_probe,
            timeout=args.timeout,
            workers=args.workers,
            budget=args.probe_budget,
        )
        # 把本次结果记进健康档案：活过的留档，死掉的进冷却
        sstats = state_mod.update(ok_rows + fail_rows)
        log(
            f"健康档案：曾成功 {sstats['known_good']} / 冷却中 {sstats['cooldown']} / "
            f"本次新进冷却 {sstats['cooled_new']} / 复活 {sstats['revived']}"
        )

    # 阶段 4：生成文件
    b = build_mod.build(ok_rows, v6_rows, fail_rows, cstats, pstats, repos, sstats)

    # 可选：验证各访问通道是否真能拿到文件
    if args.verify:
        import verify as verify_mod

        verify_mod.main([])

    log("=" * 60)
    log(
        f"全部完成：仓库 {cstats['repos']} / 抓取 {cstats['raw']} / "
        f"可用 {pstats['ok']} / 入库 {b['channels']} 频道 {b['txt']} 源，"
        f"耗时 {int(time.time()-t0)}s"
    )
    log("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
