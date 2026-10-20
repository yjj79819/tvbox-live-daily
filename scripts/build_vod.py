"""构建加强版点播配置：红果短剧加强（含 zhenguojian 那套）+ 影视搜索。

来源说明：
  短剧全部用设备本地 py 文件（/sdcard/dj2/），它们与 clun.top 的 py 是同一份
  （shortfilm.py 742143 字节、hongguo.py 221954 字节，逐字节一致），
  用本地的不但不用下载，还避开了 TVBox 相对路径解析的问题。
  影视站用轻量 vod 接口，不加载 jar。
"""
import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SRC = "duanju_v3_full.json"
OUT = "duanju_final.json"

BASE = "http://127.0.0.1:9978/file/dj2"
SPIDER = "http://127.0.0.1:9978/file/dj/xs.jar"

# 本地短剧源：从原配置继承对象（保证 jar/type 一致）
KEEP_PY = [
    "🔴红果·真源[35源]",
    "🟡聚合短剧·红果黄豆黄果黄剧",   # = zhenguojian 那套（742KB shortfilm.py）
    "🦛河马短剧",
    "🍩甜圈短剧[62类]",
]

# 实测最快的影视 vod 接口（不加载 jar）
VOD = [
    ("猫眼影视", "https://api.maoyanapi.top/api.php/provide/vod"),
    ("非凡影视", "http://cj.ffzyapi.com/api.php/provide/vod"),
    ("量子影视", "https://cj.lziapi.com/api.php/provide/vod"),
    ("急速影视", "https://jszyapi.com/api.php/provide/vod"),
    ("暴风影视", "https://bfzyapi.com/api.php/provide/vod"),
]

d = json.load(open(SRC, encoding="utf-8"))
old_sites = d.get("sites") or []

py_sites = [s for s in old_sites if s.get("name") in KEEP_PY]
py_sites.sort(key=lambda s: KEEP_PY.index(s["name"]) if s["name"] in KEEP_PY else 99)

# clun 的 js 短剧源（远程，type=3，走本地 xs.jar 引擎）
CLUN_JS = [
    {
        "key": "clun_duanshipin",
        "name": "🎭聚合短剧[js]",
        "type": 3,
        "api": "https://clun.top/js/聚合短剧.js",
        "searchable": 1,
        "quickSearch": 1,
        "filterable": 1,
    },
]

vod_sites = []
for i, (name, api) in enumerate(VOD):
    vod_sites.append(
        {
            "key": f"vod_{i}",
            "name": f"🎬{name}",
            "type": 1,
            "api": api,
            "searchable": 1,
            "quickSearch": 1,
            "filterable": 1,
            "playerType": 2,
        }
    )

sites = py_sites + CLUN_JS + vod_sites

out = {
    "spider": SPIDER,
    "wallpaper": d.get("wallpaper"),
    "sites": sites,
    "parses": d.get("parses"),
    "flags": d.get("flags"),
    "lives": d.get("lives"),
}

json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print(f"生成 {OUT}")
print(f"  站点总数 {len(sites)} = 短剧PY {len(py_sites)} + clun-JS {len(CLUN_JS)} + 影视vod {len(vod_sites)}")
print(f"  需下载远程 jar 的站点：0 个（全部用本地/无jar）")
print()
for s in sites:
    kind = "本地PY" if "9978" in (s.get("api") or "") else ("clunJS" if "clun.top" in (s.get("api") or "") else "vod轻")
    print(f"  {kind:<7} {s['name'][:26]:<28} {s.get('api','')[:58]}")
