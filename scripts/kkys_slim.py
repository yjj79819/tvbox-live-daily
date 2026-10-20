# -*- coding: utf-8 -*-
"""可可追剧(kkys20) TVBox 蜘蛛 — 零依赖精简版。

由 clun.top/py/kkys.py 精简而来:
  * 去掉 lxml 依赖(纯正则解析), 安卓 Chaquopy 环境通用
  * 去掉 init 阶段的远端图片域名探测(每次开站省 1 次往返)
  * 只保留 搜索/分类/详情/播放 四条主链路
实测: 搜索《持械入宋》13 条, 第九季 200 集, 播放直出 m3u8(1.1s)
"""
import json
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request

sys.path.append('..')

try:
    from base.spider import Spider as _BaseSpider
except ImportError:
    class _BaseSpider(object):
        pass

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0 Safari/537.36')


class Spider(_BaseSpider):
    HOST = 'https://www.kkys20.com'
    PIC = 'https://vf.wkcyvs.cn'
    HAS_FETCH = hasattr(_BaseSpider, 'fetch')

    def getName(self):
        return '可可追剧'

    def init(self, extend=''):
        self.host = self.HOST
        self.headers = {'User-Agent': UA, 'Referer': self.HOST + '/'}
        self.categories = [
            {'type_id': '1', 'type_name': '电影'},
            {'type_id': '2', 'type_name': '连续剧'},
            {'type_id': '3', 'type_name': '动漫'},
            {'type_id': '4', 'type_name': '综艺'},
            {'type_id': '6', 'type_name': '短剧'},
        ]

    # ---------------- 网络层 ----------------
    def _get(self, url, timeout=12):
        if self.HAS_FETCH:
            try:
                r = self.fetch(url, headers=self.headers, timeout=timeout,
                               verify=False)
                if r is None or getattr(r, 'status_code', 0) != 200:
                    return ''
                return r.text or ''
            except Exception:
                return ''
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        op = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPSHandler(context=ctx))
        try:
            req = urllib.request.Request(url, headers=self.headers)
            return op.open(req, timeout=timeout).read().decode('utf-8', 'ignore')
        except Exception:
            return ''

    @staticmethod
    def _fix(u):
        if not u:
            return ''
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/'):
            return Spider.HOST + u
        return u

    def _pic(self, u):
        if not u:
            return ''
        if u.startswith('http') or u.startswith('//'):
            return self._fix(u)
        return self.PIC + u

    # ---------------- 解析 ----------------
    def _parse_cards(self, html):
        """列表/首页卡片: <a class="module-item ..." href="/detail/x.html">"""
        out, seen = [], set()
        for blk in re.findall(
                r'<div[^>]*class="[^"]*module-item[^"]*"[^>]*>(.*?)</div>\s*</div>',
                html, re.S):
            m = re.search(r'href="(/detail/(\d+)\.html)"', blk)
            if not m or m.group(2) in seen:
                continue
            seen.add(m.group(2))
            name = re.search(r'class="[^"]*v-item-title[^"]*"[^>]*>\s*([^<]+)', blk)
            if not name:
                continue
            pic = re.search(r'data-original="([^"]+)"', blk)
            rem = re.search(r'class="[^"]*v-item-bottom[^"]*"[^>]*>\s*([^<]*)', blk)
            out.append({'vod_id': m.group(2),
                        'vod_name': name.group(1).strip(),
                        'vod_pic': self._pic(pic.group(1) if pic else ''),
                        'vod_remarks': (rem.group(1).strip() if rem else '')})
        return out

    def _search_raw(self, key, pg='1'):
        k = urllib.parse.quote(key)
        h1 = self._get('%s/search?k=%s' % (self.host, k))
        t = (re.search(r'name="t"\s+value="([^"]+)"', h1) or [None, ''])[1]
        if not t:
            return []
        url = '%s/search?k=%s&t=%s' % (self.host, k, urllib.parse.quote(t))
        if pg and pg != '1':
            url += '&page=%s' % pg
        h2 = self._get(url)
        if not h2:
            return []
        out, seen = [], set()
        for blk in re.findall(
                r'<a href="/detail/(\d+)\.html" class="search-result-item"(.*?)</a>',
                h2, re.S):
            vid, body = blk
            if vid in seen:
                continue
            seen.add(vid)
            nm = re.search(r'alt="([^"]*)"', body) or re.search(
                r'class="[^"]*title[^"]*"[^>]*>\s*([^<]+)', body)
            pic = re.search(r'data-original="([^"]+)"', body)
            cls = re.search(r'search-result-item-header[^>]*>\s*<div>([^<]*)</div>',
                            body)
            out.append({'vod_id': vid,
                        'vod_name': (nm.group(1).strip() if nm else vid),
                        'vod_pic': self._pic(pic.group(1) if pic else ''),
                        'type_name': (cls.group(1).strip() if cls else '')})
        return out

    def _play_lines(self, html):
        """返回 [(线路名, [(集名, 播放页URL), ...]), ...]"""
        box = re.search(r'<div class="episode-list-box-main">(.*?)</div>\s*</div>\s*</div>',
                        html, re.S)
        if not box:
            return []
        body = box.group(1)
        names = [x.strip() for x in re.findall(
            r'class="source-item-label">([^<]+)<', html)]
        blocks = re.findall(r'<div class="episode-list"[^>]*>(.*?)</div>',
                            body, re.S)
        lines = []
        for blk in blocks:
            eps = re.findall(r'href="(/play/[^"]+)"[^>]*>\s*<span>([^<]*)</span>',
                             blk)
            if not eps:
                eps = [(u, '') for u in re.findall(r'href="(/play/[^"]+)"', blk)]
            if eps:
                lines.append([(n.strip(), u) for u, n in eps])
        if not lines:
            return []
        while len(names) < len(lines):
            names.append('线路%d' % (len(names) + 1))
        pairs = list(zip(names[:len(lines)], lines))
        return [(n, e) for n, e in pairs if '4k' not in n.lower()]

    # ---------------- 接口 ----------------
    def homeContent(self, filter):
        return {'class': self.categories}

    def homeVideoContent(self):
        items = self._parse_cards(self._get(self.host + '/'))
        return {'list': items}

    def categoryContent(self, tid, pg, filter, extend):
        extend = extend or {}
        pg = int(pg or 1)
        url = '%s/show/%s-%s-%s-%s-%s-%s-%d.html' % (
            self.host, tid, extend.get('type', ''), extend.get('area', ''),
            extend.get('lang', ''), extend.get('year', ''),
            extend.get('sort', 3), pg)
        html = self._get(url)
        items = self._parse_cards(html)
        more = bool(html and 'page-item-next' in html)
        return {'page': pg, 'pagecount': pg + 1 if more else pg,
                'limit': len(items), 'total': len(items), 'list': items}

    def detailContent(self, ids):
        vid = str(ids[0])
        html = self._get('%s/detail/%s.html' % (self.host, vid))
        result = {'list': []}
        if not html:
            return result
        title = (re.search(r'<title>(.*?)-', html) or [None, ''])[1].strip()
        pic = re.search(r'class="detail-pic"[^>]*>.*?data-original="([^"]+)"',
                        html, re.S)
        desc = re.search(r'class="detail-desc"[^>]*>(.*?)</div>', html, re.S)
        cont = re.sub(r'<[^>]+>', '', desc.group(1)).strip() if desc else ''
        year = (re.search(r'(19|20)\d{2}', html) or [None, ''])[1]
        lines = self._play_lines(html)
        if not lines:
            return result
        froms, urls = [], []
        for name, eps in lines:
            froms.append(name)
            urls.append('#'.join('%s$%s' % (n or '第%d集' % (i + 1), self._fix(u))
                                 for i, (n, u) in enumerate(eps)))
        vod = {
            'vod_id': vid,
            'vod_name': title or vid,
            'vod_pic': self._pic(pic.group(1)) if pic else '',
            'type_name': '',
            'vod_year': year,
            'vod_area': '',
            'vod_remarks': '共%d集' % len(lines[0][1]),
            'vod_actor': '',
            'vod_director': '',
            'vod_content': cont,
            'vod_play_from': '$$$'.join(froms),
            'vod_play_url': '$$$'.join(urls),
        }
        result['list'].append(vod)
        return result

    def _searchContent_raw(self, key, quick, pg='1'):
        items = self._search_raw(key, pg)
        return {'list': items, 'page': int(pg or 1)}

    def searchContent(self, key, quick, pg='1'):
        data = self._searchContent_raw(key, quick, pg)
        data.setdefault('pagecount', int(pg or 1))
        data.setdefault('limit', len(data['list']))
        data.setdefault('total', len(data['list']))
        return data

    def playerContent(self, flag, id, vipFlags):
        url = self._fix(id)
        html = self._get(url)
        play = ''
        if html:
            for pat in (r'playSource\s*=\s*\{[^}]*?src:\s*"([^"]+)"',
                        r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)',
                        r'(https?://[^\s"\'<>]+\.(?:mp4|flv|mkv|webm)[^\s"\'<>]*)'):
                m = re.search(pat, html)
                if m:
                    play = m.group(1)
                    break
        if not play:
            return {'parse': 1, 'url': url, 'header': json.dumps(self.headers),
                    'message': '需解析'}
        header = {'User-Agent': UA, 'Referer': self.host + '/'}
        return {'parse': 0, 'url': play, 'header': json.dumps(header)}

    def isVideoFormat(self, url):
        return '.m3u8' in url or '.mp4' in url

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None

    def destroy(self):
        return None


if __name__ == '__main__':
    s = Spider()
    s.init('')
    t0 = time.time()
    r = s.searchContent('持械入宋', False, '1')
    print('搜索 %.2fs 命中 %d' % (time.time() - t0, len(r['list'])))
    for it in r['list']:
        print('  ', it['vod_id'], it['vod_name'], it.get('type_name'))
    nine = [i for i in r['list'] if '第九季' in i['vod_name']]
    if nine:
        t1 = time.time()
        d = s.detailContent([nine[0]['vod_id']])
        v = d['list'][0]
        print('详情 %.2fs %s %s 集数=%s' % (
            time.time() - t1, v['vod_name'], v['vod_remarks'],
            len(v['vod_play_url'].split('$$$')[0].split('#'))))
        print('  线路:', v['vod_play_from'])
        last = v['vod_play_url'].split('$$$')[0].split('#')[-1].split('$')[-1]
        t2 = time.time()
        p = s.playerContent('', last, [])
        print('播放 %.2fs scheme=%s url=%s' % (
            time.time() - t2, p.get('parse'), p.get('url', '')[:110]))
