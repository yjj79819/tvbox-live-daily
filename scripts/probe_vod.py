"""实测 vod 接口：能否连通 + 能否真的搜到内容。"""
import concurrent.futures as cf
import json
import sys
import time
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def norm(u: str) -> str:
    u = u.strip().rstrip("/")
    # 丢掉各种采集参数尾巴，只留到 provide/vod
    i = u.find("/provide/vod")
    if i > 0:
        u = u[: i + len("/provide/vod")]
    i = u.find("/seaxml/vod")
    if i > 0:
        u = u[: i + len("/seaxml/vod")]
    return u + "/"


def check(base: str, timeout: int = 12):
    """返回 (可用, 延迟, 列表条数, 搜索条数, 备注)"""
    t0 = time.time()
    try:
        # 1. 先测列表
        req = urllib.request.Request(base + "?ac=list", headers={"User-Agent": UA})
        with op.open(req, timeout=timeout) as r:
            body = r.read()
            code = r.status
        el = time.time() - t0
        # 苹果CMS 返回 xml 或 json
        txt = body.decode("utf-8", "ignore")
        if "<list" in txt or 'vodrows' in txt or 'total' in txt:
            n = txt.count("<video>") or txt.count('"vod_id"')
            n = max(n, 1) if ("<video>" in txt or "vod_id" in txt) else 0
        else:
            n = 0
        if n == 0:
            return False, el, 0, 0, f"列表空/异常(code={code})"

        # 2. 再测搜索能力
        t1 = time.time()
        su = base + "?wd=" + urllib.parse.quote("电影")
        req = urllib.request.Request(su, headers={"User-Agent": UA})
        with op.open(req, timeout=timeout) as r:
            b2 = r.read()
        t2 = b2.decode("utf-8", "ignore")
        s = t2.count("<video>") or t2.count('"vod_id"')
        return True, el, n, s, "OK" if s > 0 else "列表有但搜索无果"
    except Exception as e:  # noqa: BLE001
        el = time.time() - t0
        return False, el, 0, 0, type(e).__name__ + ":" + str(e)[:30]


def main():
    d = json.load(open("_hebing_all.json", encoding="utf-8"))
    sites = d.get("sites") or []

    def strv(v):
        return v if isinstance(v, str) else (json.dumps(v, ensure_ascii=False) if v else "")

    urls = set()
    for s in sites:
        for k in ("api", "jar", "ext"):
            u = strv(s.get(k))
            if "/provide/vod" in u or "/seaxml/vod" in u:
                urls.add(norm(u))
    urls = sorted(urls)
    print(f"去重后 vod 接口：{len(urls)} 个，开始并发实测...\n")

    res = []
    with cf.ThreadPoolExecutor(max_workers=24) as ex:
        futs = {ex.submit(check, u): u for u in urls}
        for f in cf.as_completed(futs):
            u = futs[f]
            try:
                ok, el, n, s, note = f.result()
            except Exception as e:  # noqa: BLE001
                ok, el, n, s, note = False, 99, 0, 0, "err"
            res.append((ok, el, n, s, note, u))

    good = [r for r in res if r[0] and r[3] > 0]
    good.sort(key=lambda x: x[1])
    print(f"{'状态':<4}{'延迟':>7}{'列表':>7}{'搜索':>7}  {'接口'}")
    print("-" * 100)
    for ok, el, n, s, note, u in good[:24]:
        print(f"{'✓':<4}{el:>6.2f}s{n:>7}{s:>7}  {u[:72]}")
    bad = [r for r in res if not r[0]]
    print(f"\n失效/搜索无果的：{len(bad)} 个（可用 {len(good)} 个）")
    for ok, el, n, s, note, u in res:
        if ok and s == 0:
            print(f"  列表有搜索无: {u[:70]}  ({note})")
    json.dump(
        [{"url": u, "latency": round(el, 2), "list": n, "search": s} for ok, el, n, s, _n, u in good],
        open("_vod_ok.json", "w", encoding="utf-8"),
        ensure_ascii=False,
        indent=1,
    )
    print(f"\n结果已存 _vod_ok.json（{len(good)} 条）")


main()
