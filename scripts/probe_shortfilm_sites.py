# -*- coding: utf-8 -*-
"""聚合短剧(shortfilm) 站点实测探针 v2。

判定口径（贴合用户要求: 必须有《持械入宋》最新第九季、更新快、有片源）:
  1. 搜索结果里必须有标题精确包含剧名的条目(模糊分词命中不算)
  2. 其中必须存在"第九季/第9季/9"标记, 或总集数 >= 800
  3. 播放地址必须能取到(并可实测出流)

用法:
  python probe_sites.py 持械入宋 search
  python probe_sites.py 持械入宋 deep [key,key,...]
"""
import importlib.util
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'shortfilm_orig.py')
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0 Safari/537.36')


def load(src=SRC):
    spec = importlib.util.spec_from_file_location('sfmod', src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules['sfmod'] = mod
    spec.loader.exec_module(mod)
    return mod


def compact(text):
    return ''.join(str(text or '').split())


def exact_hits(items, wd):
    target = compact(wd)
    out = []
    for it in items or []:
        if target in compact(it.get('vod_name')):
            out.append(it)
    return out


def episodes_of(d):
    """三种详情结构自适应: list / episodes / sources。"""
    if not isinstance(d, dict):
        return []
    if isinstance(d.get('episodes'), list):
        return d['episodes']
    if isinstance(d.get('sources'), list) and d['sources']:
        s = d['sources'][0]
        if isinstance(s, dict) and isinstance(s.get('episodes'), list):
            return s['episodes']
    lst = d.get('list') or []
    if lst and isinstance(lst[0], dict):
        urls = str(lst[0].get('vod_play_url') or '')
        if urls:
            return [{'url': x} for x in urls.split('$$$')[0].split('#') if x]
    return []


def ep_url(ep):
    if isinstance(ep, dict):
        return str(ep.get('url') or '')
    return str(ep)


def season_mark(name):
    n = str(name or '')
    return ('第九季' in n or '第9季' in n or '9季' in n or '九季' in n)


def head_ok(url, referer=''):
    """实测播放地址是否出流(前 200 字节)。"""
    import ssl
    import urllib.request
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                     urllib.request.HTTPSHandler(context=ctx))
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': referer or url})
    t = time.time()
    try:
        r = op.open(req, timeout=12)
        d = r.read(200)
        ms = int((time.time() - t) * 1000)
        r.close()
        if r.status == 200 and not d[:20].lstrip().lower().startswith(b'<'):
            return True, ms, r.status
        return False, ms, r.status
    except Exception as exc:
        return False, int((time.time() - t) * 1000), repr(exc)[:60]


def one(site, key, wd, deep):
    row = {'key': key, 'name': str(getattr(site, 'name', key) or key),
           'search_ms': 0, 'hits': 0, 'exact': 0, 's9': False,
           'eps': 0, 'play_ms': 0, 'play_url': '', 'stream': False,
           'total_ms': 0, 'err': ''}
    t0 = time.time()
    try:
        items = site.search(wd, 1) or []
    except Exception as exc:
        row['err'] = 'search:%s' % repr(exc)[:60]
        row['total_ms'] = int((time.time() - t0) * 1000)
        return row
    row['search_ms'] = int((time.time() - t0) * 1000)
    row['hits'] = len(items)
    ex = exact_hits(items, wd)
    row['exact'] = len(ex)
    if not ex or not deep:
        row['total_ms'] = int((time.time() - t0) * 1000)
        return row
    # 第九季优先, 其次取标题含剧名且顺序靠前的
    picks = [i for i in ex if season_mark(i.get('vod_name'))] or ex
    best = None
    for cand in picks[:4]:
        vid = str(cand.get('vod_id') or '')
        if not vid:
            continue
        t = time.time()
        try:
            d = site.detail(vid) or {}
        except Exception as exc:
            row['err'] = 'detail:%s' % repr(exc)[:60]
            continue
        dt = int((time.time() - t) * 1000)
        eps = episodes_of(d)
        if eps and (best is None or len(eps) > best[1]):
            best = (eps, len(eps), cand, dt, d)
    if not best:
        row['total_ms'] = int((time.time() - t0) * 1000)
        return row
    eps, cnt, cand, dt, d = best
    row['eps'] = cnt
    row['detail_ms'] = dt
    row['s9'] = season_mark(cand.get('vod_name')) or cnt >= 800
    row['title'] = str(cand.get('vod_name') or '')[:40]
    # 播放: 取最后一集
    t = time.time()
    try:
        p = site.play(ep_url(eps[-1])) or {}
    except Exception as exc:
        row['err'] = 'play:%s' % repr(exc)[:60]
        row['total_ms'] = int((time.time() - t0) * 1000)
        return row
    url = str(p.get('url') or '')
    row['play_ms'] = int((time.time() - t) * 1000)
    row['play_url'] = url[:120]
    if url:
        row['stream'], ms, st = head_ok(url)
        row['stream_ms'] = ms
        row['stream_status'] = st
    row['total_ms'] = int((time.time() - t0) * 1000)
    return row


def main():
    wd = sys.argv[1] if len(sys.argv) > 1 else '持械入宋'
    deep = (sys.argv[2] if len(sys.argv) > 2 else 'search') == 'deep'
    only = [x for x in (sys.argv[3].split(',') if len(sys.argv) > 3 else []) if x]
    mod = load()
    router = mod.SiteRouter()
    keys = [k for k in router.order if (not only or k in only)]
    print('站点 %d, 关键字 %s, deep=%s' % (len(keys), wd, deep), flush=True)

    def run(key):
        return one(router.sites[key], key, wd, deep)

    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(run, keys))
    rows.sort(key=lambda r: (not r.get('s9'), -r['exact'], r['search_ms']))
    hdr = ('key', 'name', '搜索ms', '命中', '精确', '集数', '九季', '播放ms',
           '出流', '总计')
    print('%-11s %-8s %6s %4s %4s %5s %4s %6s %4s %6s' % hdr)
    for r in rows:
        print('%-11s %-8s %6d %4d %4d %5d %4s %6d %4s %6d  %s' % (
            r['key'], r['name'], r['search_ms'], r['hits'], r['exact'],
            r.get('eps', 0), 'YES' if r.get('s9') else '-',
            r['play_ms'], 'OK' if r.get('stream') else ('x' if r.get('play_url') else '-'),
            r['total_ms'], (r.get('title') or r.get('err') or '')[:32]))
    with open(os.path.join(HERE, 'probe_result.json'), 'w', encoding='utf-8') as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
