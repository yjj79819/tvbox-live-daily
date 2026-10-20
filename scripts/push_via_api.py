# -*- coding: utf-8 -*-
"""git push 走不通时的兜底：用 GitHub Git Data API 直接提交。

什么时候用：github.com:443 连不上（CONNECT 失败 / 超时），但 api.github.com 通。
原理：把本地 HEAD 相对 origin/main 的变更文件逐个建 blob，
以 main 的当前 commit 为 parent 建 tree → commit → 移动 refs/heads/main。

用法：
    python scripts/push_via_api.py            # 提交 HEAD 相对 origin/main 的改动
    python scripts/push_via_api.py --dry-run # 只看会提交哪些文件
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
BRANCH = "main"


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=str(ROOT)).decode().strip()


def api(method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "push-via-api",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")
    except Exception as e:  # noqa: BLE001
        return 0, {"message": repr(e)[:200]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not TOKEN:
        tok_file = ROOT.parent / "_gh_tok.tmp"
        if tok_file.exists():
            globals()["TOKEN"] = tok_file.read_text().strip()
    if not TOKEN:
        print("需要 GH_TOKEN 环境变量（或上级目录 _gh_tok.tmp）")
        return 1

    remote = _git("config", "--get", "remote.origin.url")  # https://github.com/o/r.git
    slug = remote.replace("https://github.com/", "").replace(".git", "")
    print(f"仓库 {slug} 分支 {BRANCH}")

    base = _git("rev-parse", f"origin/{BRANCH}")
    head = _git("rev-parse", "HEAD")
    print(f"origin/{BRANCH}={base[:10]}  HEAD={head[:10]}")

    changed = _git("diff", "--name-only", f"origin/{BRANCH}", "HEAD").split()
    if not changed:
        print("没有需要提交的文件")
        return 0
    print(f"待提交 {len(changed)} 个文件：")
    for f in changed:
        print("   ", f)
    if args.dry_run:
        return 0

    tree = []
    for f in changed:
        p = ROOT / f
        if not p.exists():
            print(f"跳过（已删除，API 方式未实现删除）: {f}")
            continue
        raw = p.read_bytes()
        st, res = api(
            "POST",
            f"/repos/{slug}/git/blobs",
            {"content": base64.b64encode(raw).decode(), "encoding": "base64"},
        )
        if st >= 300:
            print(f"blob 失败 {f}: {st} {res.get('message')}")
            return 1
        tree.append({"path": f.replace("\\", "/"), "mode": "100644", "type": "blob", "sha": res["sha"]})
        print(f"   blob {f} ({len(raw)}B)")

    st, res = api("POST", f"/repos/{slug}/git/trees", {"base_tree": base, "tree": tree})
    if st >= 300:
        print(f"tree 失败: {st} {res.get('message')}")
        return 1
    tree_sha = res["sha"]

    msg = _git("log", "-1", "--pretty=%s")
    st, res = api(
        "POST",
        f"/repos/{slug}/git/commits",
        {"message": msg, "tree": tree_sha, "parents": [base]},
    )
    if st >= 300:
        print(f"commit 失败: {st} {res.get('message')}")
        return 1
    commit_sha = res["sha"]
    print(f"commit {commit_sha[:10]}  {msg}")

    st, res = api("PATCH", f"/repos/{slug}/git/refs/heads/{BRANCH}", {"sha": commit_sha})
    if st >= 300:
        print(f"更新 ref 失败: {st} {res.get('message')}")
        return 1
    print(f"完成：{BRANCH} -> {commit_sha[:10]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
