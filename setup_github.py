#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
登录 GitHub 之后，一条命令把项目推上去、开好 Actions 权限、并跑第一次。

    python setup_github.py
    python setup_github.py --name 我的仓库名
    python setup_github.py --no-run          # 推完不触发 Actions

做了什么：
  1. 取 GitHub 用户名，配好 git 身份
  2. git init / add / commit
  3. gh repo create --public --source=. --push   （仓库必须是公开的，TVBox 才读得到 raw 地址）
  4. 打开 Workflow 读写权限（不然 Actions 没法把结果提交回来）
  5. 触发一次 Actions，让它当场产出 output/

前置：先跑 gh auth login 完成浏览器授权（只需做一次）。
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_NAME = "tvbox-live-daily"


def run(args, *, check=True, capture=True, timeout=300):
    return subprocess.run(
        args, cwd=str(ROOT), capture_output=capture, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
    )


def sh(args, timeout=300):
    r = run(args, check=False, timeout=timeout)
    out = (r.stdout or "") + (r.stderr or "")
    return r.returncode, out.strip()


def has_gh() -> bool:
    code, out = sh(["gh", "--version"])
    if code != 0:
        return False
    print(f"  gh {out.splitlines()[0] if out else ''}")
    return True


def gh_api(path):
    code, out = sh(["gh", "api", path])
    if code != 0:
        return None
    try:
        return json.loads(out)
    except Exception:  # noqa: BLE001
        return None


def whoami():
    """拿登录名。

    优先问 API：gh 的 keyring 在某些机器上存不住 token（Windows 凭据管理器读出来报
    invalid），但 GITHUB_TOKEN 环境变量这条路一直是通的，所以不依赖 gh auth status。
    """
    u = gh_api("user")
    if u and u.get("login"):
        return u["login"], u
    code, out = sh(["gh", "auth", "status"])
    if code == 0:
        m = re.search(r"account\s+(\S+)", out)
        if m:
            return m.group(1), {}
    return None, {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default=DEFAULT_NAME, help=f"仓库名（默认 {DEFAULT_NAME}）")
    ap.add_argument("--no-run", action="store_true", help="推完不触发 Actions")
    args = ap.parse_args()

    print("① 检查 gh")
    if not has_gh():
        print("  没找到 gh。先装 GitHub CLI，再跑 gh auth login 完成授权。")
        return 1

    login, u = whoami()
    if not login:
        print("  还没认证。设 GITHUB_TOKEN 环境变量，或先跑 gh auth login。")
        return 1
    print(f"  已认证：{login}")

    # 走代理才能连上 GitHub 时，把代理配给 git（gh 自己读环境变量）。
    # 大写优先：小写那套常被别的程序占着（比如本机 54682 是 WorkBuddy 自己的代理，
    # 不是全流量的，GitHub 的请求过不去）。
    proxy = (
        os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        or os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    )
    if proxy:
        sh(["git", "config", "http.proxy", proxy])
        sh(["git", "config", "https.proxy", proxy])
        print(f"  git 代理：{proxy}")

    u = u or gh_api("user") or {}
    email = u.get("email") or f"{u.get('id', login)}+{login}@users.noreply.github.com"
    gname = u.get("name") or login

    print("② 配 git 身份")
    sh(["git", "config", "user.name", gname])
    sh(["git", "config", "user.email", email])
    print(f"  {gname} <{email}>")

    print("③ 初始化仓库并提交")
    if not (ROOT / ".git").exists():
        code, out = sh(["git", "init"])
        if code != 0:
            print(f"  git init 失败：{out}")
            return 1
        sh(["git", "branch", "-M", "main"])
    sh(["git", "add", "-A"])
    code, out = sh([
        "git", "commit", "-m", "feat: 直播源优选（每两天自动更新）"
    ])
    if code != 0 and "nothing to commit" not in out.lower():
        print(f"  commit 失败：{out}")
        return 1
    print("  已提交")

    print(f"④ 创建公开仓库 {login}/{args.name} 并推送")
    code, out = sh([
        "gh", "repo", "create", args.name,
        "--public", "--source=.", "--remote=origin", "--push",
    ], timeout=600)
    if code != 0:
        # 仓库可能已经存在（比如网页上先建了），那就只推
        if "already exists" in out.lower() or "name already exists" in out.lower():
            print("  仓库已存在，改为直接推送")
            sh(["git", "remote", "remove", "origin"])
            sh(["git", "remote", "add", "origin",
                f"https://github.com/{login}/{args.name}.git"])
            code, out = sh(["git", "push", "-u", "origin", "main"], timeout=600)
            if code != 0:
                print(f"  推送失败：{out}")
                return 1
        else:
            print(f"  创建失败：{out}")
            return 1
    print("  已推送")

    print("⑤ 开 Actions 读写权限")
    code, out = sh(["gh", "api", "-X", "PUT",
                    f"repos/{login}/{args.name}/actions/permissions/workflow",
                    "-f", "default_workflow_permissions=write",
                    "-f", "can_approve_pull_request_reviews=true"])
    if code == 0:
        print("  已设为 Read and write")
    else:
        print(f"  API 设置没成功（可网页手动改）：{out[:200]}")

    if not args.no_run:
        print("⑥ 触发第一次 Actions")
        code, out = sh(["gh", "workflow", "run", "daily.yml"])
        if code == 0:
            print("  已触发，约 5-10 分钟后产出 output/")
        else:
            print(f"  触发失败（可网页 Actions 里手动 Run workflow）：{out[:200]}")

    print()
    print("=" * 62)
    print(f"仓库：https://github.com/{login}/{args.name}")
    print(f"源地址（TVBox 用这个）：")
    print(f"  https://raw.githubusercontent.com/{login}/{args.name}/main/output/tvbox_live.json")
    print("  国内若慢，换：")
    print(f"  https://ghfast.top/https://raw.githubusercontent.com/{login}/{args.name}/main/output/tvbox_live.json")
    print(f"  https://ghproxy.net/https://raw.githubusercontent.com/{login}/{args.name}/main/output/tvbox_live.json")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    sys.exit(main())
