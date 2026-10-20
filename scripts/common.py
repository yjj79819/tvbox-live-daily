# -*- coding: utf-8 -*-
"""公共工具：HTTP 请求、GitHub API、配置读取、日志。

所有网络请求统一走这里，便于集中控制超时、重试和镜像回退。
GitHub Actions 运行环境不支持 IPv6，本文件同时提供环境探测能力。
"""
from __future__ import annotations

import hashlib
import os
import random
import re
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse

import requests
from requests.adapters import HTTPAdapter

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
OUTPUT_DIR = ROOT / "output"
DATA_DIR = ROOT / "data"
# state/ 必须提交入库：Actions 每次都是全新环境，
# 只有靠仓库里留存的健康档案才能跨运行记住哪些源是死的。
STATE_DIR = ROOT / "state"
for _d in (DATA_DIR, OUTPUT_DIR, STATE_DIR):
    _d.mkdir(exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

# raw.githubusercontent.com 的镜像前缀（按顺序尝试）。
# 全部经过实测：2026-10 实测可用的是 ghproxy.net / ghfast.top / gh-proxy.com，
# 而网上流传的 githubraw.com、ghproxy.com、raw.kkgithub.com 当时均已失效。
RAW_MIRRORS = [
    "",
    "https://ghproxy.net/",
    "https://ghfast.top/",
    "https://gh-proxy.com/",
]

GH_TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""

# ---------------- 日志 ----------------


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def warn(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] [WARN] {msg}", file=sys.stderr, flush=True)


# ---------------- HTTP ----------------


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "*/*"})
    adapter = HTTPAdapter(pool_connections=64, pool_maxsize=64, max_retries=0)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


SESSION = _session()


def http_get(
    url: str,
    timeout: float = 20,
    headers: dict | None = None,
    retries: int = 2,
    allow_mirror: bool = False,
    quiet: bool = False,
    max_mirrors: int = 99,
) -> requests.Response | None:
    """GET 请求。失败返回 None，不打异常，便于调用方继续跑其他源。

    区分两类失败：
      - HTTP 状态码错误（404/403 等）：目标确实不可用，直接放弃，不换镜像重试
      - 网络层错误（超时、DNS、连接被重置）：换镜像重试

    这个区分很关键——回退探测会尝试大量不存在的路径，
    若每次 404 都把 4 个镜像挨个试一遍，光探测就要多花十几分钟。

    max_mirrors 控制最多换几个镜像。探测不存在路径时用 1（快速放弃），
    下载已确认存在的文件时才放开。
    """
    urls = [url]
    if allow_mirror and "raw.githubusercontent.com" in url:
        urls += [m + url for m in RAW_MIRRORS if m][:max_mirrors]

    last_err = None
    for u in urls:
        for attempt in range(retries + 1):
            try:
                r = SESSION.get(u, timeout=timeout, headers=headers, allow_redirects=True)
                if r.status_code >= 400:
                    # 目标明确不可用，无需换镜像
                    return None
                return r
            except requests.exceptions.RequestException as e:
                last_err = e
                if attempt < retries:
                    time.sleep(0.4 * (attempt + 1) + random.random() * 0.2)
                    continue
                break  # 网络层失败，换下一个镜像
        # 只有网络层失败才会走到这里；HTTP 错误已提前返回
    if last_err and not quiet:
        warn(f"GET 失败 {url[:90]} -> {type(last_err).__name__}")
    return None


def http_head(url: str, timeout: float = 10) -> requests.Response | None:
    """轻量探测用 HEAD；部分服务不支持 HEAD，调用方需准备 GET 回退。"""
    try:
        return SESSION.head(url, timeout=timeout, allow_redirects=True)
    except Exception:  # noqa: BLE001
        return None


# ---------------- GitHub API ----------------

API = "https://api.github.com"


# API 熔断：连续失败或遇到 403/429 后关闭 API 通道，
# 后续仓库改走 raw 路径猜测。无 token 时限额只有 60 次/小时，
# 跑几十个仓库就会耗尽，熔断能让主流程继续产出结果。
_API_STATE = {"fails": 0, "dead": False}
API_FAIL_LIMIT = 5


def api_available() -> bool:
    return not _API_STATE["dead"]


def kill_api(reason: str) -> None:
    if not _API_STATE["dead"]:
        _API_STATE["dead"] = True
        warn(f"GitHub API 已熔断（{reason}），后续改为 raw 路径猜测模式")


def gh_api(path: str, timeout: float = 25) -> dict | list | None:
    """调用 GitHub API。带 token 时限额从 60/h 提升到 5000/h。"""
    if _API_STATE["dead"]:
        return None

    headers = {"Accept": "application/vnd.github+json"}
    if GH_TOKEN:
        headers["Authorization"] = f"Bearer {GH_TOKEN}"

    try:
        r = SESSION.get(f"{API}{path}", timeout=timeout, headers=headers)
    except Exception:  # noqa: BLE001
        _API_STATE["fails"] += 1
        if _API_STATE["fails"] >= API_FAIL_LIMIT:
            kill_api("连续请求失败")
        return None

    if r.status_code in (403, 429):
        kill_api(f"HTTP{r.status_code} 限流")
        return None
    if r.status_code >= 400:
        _API_STATE["fails"] += 1
        if _API_STATE["fails"] >= API_FAIL_LIMIT:
            kill_api(f"HTTP{r.status_code} 连续失败")
        return None

    try:
        return r.json()
    except Exception:  # noqa: BLE001
        return None


def gh_remaining() -> str:
    """返回剩余 API 额度，用于报告与限流提示。"""
    r = http_get(f"{API}/rate_limit", timeout=15, headers={"Accept": "application/vnd.github+json"})
    if r is None:
        return "未知"
    try:
        core = r.json()["resources"]["core"]
        return f"{core['remaining']}/{core['limit']}"
    except Exception:  # noqa: BLE001
        return "未知"


# ---------------- 配置读取 ----------------


def read_lines(name: str) -> list[str]:
    """读取 config/<name>，跳过空行与 # 注释。"""
    p = CONFIG_DIR / name
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            out.append(s)
    return out


# ---------------- IPv6 能力探测 ----------------

_IPV6_CACHE: dict[str, bool] = {}


def ipv6_supported() -> bool:
    """探测当前环境能否发起 IPv6 连接。

    GitHub Actions（Azure）不提供 IPv6，此时 IPv6 源无法测速，
    脚本会把它们单独输出而不判定为死链。
    """
    # FORCE_IPV6=0/1 用于本地验证线上分支：GitHub Actions 无 IPv6，
    # 本机通常有，靠这个开关就能在本地复现线上走的那条路径。
    forced = os.environ.get("FORCE_IPV6")
    if forced in ("0", "1"):
        log(f"IPv6 支持: {'是' if forced == '1' else '否'}（由 FORCE_IPV6 指定）")
        _IPV6_CACHE["ok"] = forced == "1"
        return _IPV6_CACHE["ok"]

    if "ok" in _IPV6_CACHE:
        return _IPV6_CACHE["ok"]
    ok = False
    try:
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        s.settimeout(4)
        s.connect(("2400:3200::1", 53))  # 阿里公共 DNS
        s.close()
        ok = True
    except Exception:  # noqa: BLE001
        ok = False
    _IPV6_CACHE["ok"] = ok
    log(f"IPv6 支持: {'是' if ok else '否（IPv6 源将跳过测速单独输出）'}")
    return ok


# ---------------- 地址工具 ----------------

V6_RE = re.compile(r"^https?://\[[0-9a-fA-F:]+]")


def is_ipv6_url(url: str) -> bool:
    """判断是否为 IPv6 直连地址（形如 http://[2409:8087::1]:6610/...）。"""
    return bool(V6_RE.match(url.strip()))


def host_of(url: str) -> str:
    try:
        return urlparse(url).hostname or ""
    except Exception:  # noqa: BLE001
        return ""


# ---------------- URL 归一化 ----------------

# 这些参数基本都是时效性令牌或时间戳，值一变 URL 就变，
# 但它们指向的是同一路流。去重时剔除，否则会被当成两条不同源。
DROP_QUERY_KEYS = {
    "t", "ts", "timestamp", "_", "rnd", "rand",
    "token", "auth_key", "authkey", "key", "sign", "signature",
    "expires", "expire", "exp",
}


def norm_url(u: str) -> str:
    """把 URL 归一成去重键。

    处理：协议/主机小写、去掉 80/443 默认端口、去掉末尾斜杠、
    query 参数排序并剔除时效参数。

    同一个 CDN 上的同一路流，在不同聚合仓库里常被写成
    `http://a.com:80/x/?t=1` 和 `https://A.com/x`，
    不做归一化就会留下两条，白占一个备用名额。
    """
    u = (u or "").strip()
    if not u:
        return ""
    try:
        p = urlparse(u)
    except Exception:  # noqa: BLE001
        return u.lower()
    if not p.scheme:
        return u.lower()

    scheme = p.scheme.lower()
    host = (p.hostname or "").lower()
    port = None
    try:
        port = p.port
    except ValueError:
        port = None
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        port = None

    path = p.path or "/"
    if len(path) > 1:
        path = path.rstrip("/")

    q = ""
    if p.query:
        pairs = [
            (k, v)
            for k, v in parse_qsl(p.query, keep_blank_values=True)
            if k.lower() not in DROP_QUERY_KEYS
        ]
        if pairs:
            q = urlencode(sorted(pairs))

    netloc = f"[{host}]" if ":" in host else host
    if port:
        netloc = f"{netloc}:{port}"
    out = f"{scheme}://{netloc}{path}"
    if q:
        out = f"{out}?{q}"
    return out


def short_hash(text: str, n: int = 12) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()[:n]


# ---------------- 仓库定位与镜像 ----------------


def repo_slug() -> tuple[str, str]:
    """返回 (owner/repo, 分支)。

    优先级：config/repo.txt（本地没有 git 远端时可用它固定）
           > Actions 环境变量 GITHUB_REPOSITORY / GITHUB_REF
           > git remote 推断
    """
    slug, branch = "", ""

    p = CONFIG_DIR / "repo.txt"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s and not s.startswith("#"):
                parts = s.split()
                if "/" in parts[0]:
                    slug = parts[0]
                    if len(parts) > 1:
                        branch = parts[1]
                break

    if not slug:
        env = os.environ.get("GITHUB_REPOSITORY")
        if env and "/" in env:
            slug = env

    if not branch:
        ref = os.environ.get("GITHUB_REF") or ""
        if ref.startswith("refs/heads/"):
            branch = ref[len("refs/heads/"):]

    if not slug:
        try:
            url = subprocess.check_output(
                ["git", "config", "--get", "remote.origin.url"], text=True, timeout=10
            ).strip()
            m = re.search(r"github\.com[:/]([^/]+/[^/\s]+?)(\.git)?$", url)
            if m:
                slug = m.group(1)
        except Exception:  # noqa: BLE001
            pass

    return slug or "OWNER/REPO", branch or "main"


def raw_base(slug: str, branch: str) -> str:
    return f"https://raw.githubusercontent.com/{slug}/{branch}"


def render_tpl(tpl: str, slug: str, branch: str, path: str) -> str:
    """渲染地址模板。支持 {slug} {branch} {path} {u} 四种占位符。"""
    u = f"{raw_base(slug, branch)}/{path}"
    return (
        tpl.replace("{u}", u)
        .replace("{slug}", slug)
        .replace("{branch}", branch)
        .replace("{path}", path)
    )


DEFAULT_MIRRORS = [
    ("直连", "https://raw.githubusercontent.com/{slug}/{branch}/{path}"),
    ("ghproxy.net", "https://ghproxy.net/{u}"),
    ("ghfast.top", "https://ghfast.top/{u}"),
    ("gh-proxy.com", "https://gh-proxy.com/{u}"),
    ("jsDelivr", "https://cdn.jsdelivr.net/gh/{slug}@{branch}/{path}"),
]


def mirrors() -> list[tuple[str, str]]:
    """返回 [(名称, 模板)]。优先读 config/mirrors.txt，缺失时用内置实测清单。"""
    out: list[tuple[str, str]] = []
    for line in read_lines("mirrors.txt"):
        if "|" not in line:
            continue
        name, tpl = line.split("|", 1)
        name, tpl = name.strip(), tpl.strip()
        if not name or not tpl.startswith("http"):
            continue
        if tpl in {t for _, t in out}:
            continue
        out.append((name, tpl))
    return out or DEFAULT_MIRRORS


def local_base() -> str:
    """本地源基地址，如 http://192.168.1.13:9978/file/。未配置返回空串。"""
    for line in read_lines("local_base.txt"):
        s = line.strip()
        if s.startswith("http"):
            return s.rstrip("/") + "/"
    return ""
