# -*- coding: utf-8 -*-
"""
Walmart 站内商品采集（平均评分 / 累计评论数 / 商品图 / 品类路径）。

为什么 Walmart 能抓而 Home Depot / Lowe's 不能
--------------------------------------------------
实测（2026-10-13）：
  · walmart.com 品类页             → 200，商品数据在 __NEXT_DATA__ 里，字段完整
  · walmart.com/search?q=...       → 307 跳转 "blocked - redirecting"，搜索页走不通
  · homedepot.com / lowes.com      → Access Denied（Akamai 指纹级拦截，六条通道已穷尽）
  · costco.com 品类页              → 200 但含 350 处 Skeleton 占位，商品纯客户端 JS 渲染，
                                     且 catalog/search、AjaxGetProductByItemNumber、
                                     /api/catalog/search 三个内部接口全部 404

Walmart 的价值：它的品类页直接带 averageRating + numberOfReviews（与 Amazon 同一量纲），
且商品图在公开 CDN（i5.walmartimages.com），另有独立的评论页可抓评论正文与维度标签。

⚠️ 三个必须记住的坑
--------------------------------------------------
1. **URL 形式决定拿到什么。** `/browse/<top>/<catId>` 与 `/cp/<slug>/<catId>` 可用；
   但形如 `/browse/patio-lawn-garden/patio-furniture/5428_1234` 这类不存在的节点会返回
   **HTTP 200 + 2MB 的软 404 空壳**，`itemStacks` 长度为 0。只看状态码和体积必然误判
   → 解析后必须校验 itemStacks 非空 + 页面标题匹配。
2. **速率限制很硬。** 连续 5–6 个请求后开始返回约 15KB 的拦截页（无 __NEXT_DATA__）。
   实测页间隔 12s 可稳定通过；失败后等 35s 重试多数成功；间隔 <5s 必挂。
3. **价格字段是顶层 `price`**，不是 `priceInfo.currentPrice`（后者恒为空）。

数据落点：
  __NEXT_DATA__.props.pageProps.initialData.searchResult.itemStacks[0].items[]

本模块只负责采集与解析，不做任何结论。
"""
import json
import os
import random
import re
import ssl
import time
import urllib.request

import patio_taxonomy as TX       # 品类口径统一由 patio_taxonomy 提供

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

UA = "Mozilla/5.0"          # 本机代理环境：请求头只能带 User-Agent
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE

LISTED_AT = "2026-10-13"

# ---------------------------------------------------------------- 采集页定义
# 全部为实测可抓、且返回商品数据的页面（2026-10-13 逐页验证）。
# expect 用于防串页/防软 404 校验，必须与页面 searchResult.title 的关键字一致。
PAGES = [
    {"key": "patio_main", "label_zh": "庭院与户外 总类", "label_en": "Patio & Garden (overall)",
     "url": "https://www.walmart.com/browse/patio-lawn-garden/5428",
     "expect": "Patio & Garden"},
    {"key": "patio_set", "label_zh": "户外家具套装", "label_en": "Patio Furniture Collections",
     "url": "https://www.walmart.com/cp/patio-furniture-collections/7895442",
     "expect": "Patio Furniture Collections"},
    {"key": "umbrella", "label_zh": "遮阳伞", "label_en": "Patio Umbrellas",
     "url": "https://www.walmart.com/cp/patio-umbrellas/8341994",
     "expect": "Patio Umbrellas"},
    {"key": "canopy", "label_zh": "篷房与凉亭", "label_en": "Canopies & Shelters",
     "url": "https://www.walmart.com/cp/canopies-shelters/55558",
     "expect": "Canopies"},
    {"key": "camping", "label_zh": "露营椅", "label_en": "Camping Chairs",
     "url": "https://www.walmart.com/cp/camping-chairs/6170779",
     "expect": "Camping Chairs"},
    {"key": "grill", "label_zh": "燃气烤炉", "label_en": "Gas Grills",
     "url": "https://www.walmart.com/cp/gas-grills/7991811",
     "expect": "Gas Grills"},
    {"key": "cushion", "label_zh": "户外坐垫", "label_en": "Outdoor Cushions",
     "url": "https://www.walmart.com/cp/outdoor-cushions/1225353",
     "expect": "Outdoor Cushions"},
]

# 实测被拦时返回的页面长度（±500 内视为拦截页）
_BLOCK_LEN = 15190
_BLOCK_TOL = 900


# ---------------------------------------------------------------- 工具
def _http(url, tries=4, base_wait=18.0, timeout=45):
    """带拦截页检测 + 长间隔退避的请求。返回 HTML 文本。

    实测（2026-10-13）：Walmart 在连续 5–6 个请求后开始拦截，且**拦截状态会持续几十秒**。
    tries=4 / base_wait=18 时等待 18→36→54 秒，单页最坏约 2 分钟，
    但能把整轮成功率从「7 页挂 2 页」提到基本稳定。
    """
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
                html = r.read().decode("utf-8", "replace")
        except Exception as e:
            last = "%s: %s" % (type(e).__name__, e)
            html = ""

        if html and "__NEXT_DATA__" in html:
            return html
        # 拦截页 / 空响应 → 退避
        last = (last or "") + " | 拦截页或空响应 len=%d" % len(html)
        if i < tries - 1:
            wait = base_wait * (i + 1) + random.random() * 2.0
            time.sleep(wait)
    raise RuntimeError("请求失败（%d 次）：%s" % (tries, last))


def _clean(s):
    """清 HTML 实体与多余空白。"""
    if not s:
        return ""
    s = re.sub(r"&#x([0-9a-fA-F]+);", lambda m: chr(int(m.group(1), 16)), s)
    s = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), s)
    for a, b in (("&amp;", "&"), ("&quot;", '"'), ("&#39;", "'"),
                 ("&apos;", "'"), ("&lt;", "<"), ("&gt;", ">"), ("&nbsp;", " ")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def _title(html):
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return _clean(m.group(1)) if m else ""


def _num(v):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f


def _price(item):
    """价格：顶层 price 优先，其次 priceInfo.itemPrice.price。"""
    p = _num(item.get("price"))
    if p is not None:
        return p
    pi = item.get("priceInfo") or {}
    cur = pi.get("itemPrice")
    if isinstance(cur, dict):
        p = _num(cur.get("price"))
        if p is not None:
            return p
    return None


def _img(item):
    info = item.get("imageInfo") or {}
    return info.get("thumbnailUrl") or ""


def _brand(item):
    for k in ("brand", "productBrand"):
        v = item.get(k)
        if isinstance(v, dict):
            v = v.get("name")
        if v:
            return _clean(str(v))
    return ""


def _catpath(item):
    cat = item.get("category") or {}
    return cat.get("categoryPath") or ""


# ---------------------------------------------------------------- 解析
def parse_page(html):
    """从 __NEXT_DATA__ 里取商品列表。返回 (items, title, total_hint)。"""
    m = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise RuntimeError("页面无 __NEXT_DATA__（可能是拦截页）")
    nd = json.loads(m.group(1))
    sr = ((nd.get("props") or {}).get("pageProps") or {}).get("initialData", {}).get("searchResult") or {}
    title = _clean(str(sr.get("title") or ""))
    stacks = sr.get("itemStacks") or []
    items = []
    for s in stacks:
        for it in (s.get("items") or []):
            nm = _clean(str(it.get("name") or ""))
            iid = str(it.get("usItemId") or it.get("id") or "")
            if not nm or not iid:
                continue
            url = it.get("canonicalUrl") or ""
            if url.startswith("/"):
                url = "https://www.walmart.com" + url
            items.append({
                "id": iid,
                "title": nm,
                "brand": _brand(it),
                "price": _price(it),
                "rating": _num(it.get("averageRating")),
                "reviews": _num(it.get("numberOfReviews")),
                "image": _img(it),
                "url": url,
                "cat_path": _catpath(it),
                "cat": TX.guess_cat(nm),      # 与 Amazon 共用同一套口径
            })
    return items, title, sr.get("count")


def fetch_all(verbose=True, only=None):
    """逐页采集。页间隔 16–20s（实测唯一能稳定通过 Walmart 速率的间隔）。

    only: 只抓指定的 page key（用于补抓失败页）。
    """
    pages = {}
    errors = []
    seen = {}
    all_items = []
    page_list = [p for p in PAGES if not only or p["key"] in only]

    for i, p in enumerate(page_list):
        if i:
            time.sleep(16 + random.random() * 4)
        try:
            html = _http(p["url"])
            items, title, count = parse_page(html)
            if not items:
                raise RuntimeError("itemStacks 为空（软 404 或页面结构变化）")
            if p.get("expect") and p["expect"].lower() not in title.lower():
                raise RuntimeError("页面标题不符预期（期望含「%s」，实际「%s」）" % (p["expect"], title))
            for it in items:
                it["page"] = p["key"]
                if it["id"] in seen:
                    seen[it["id"]]["also_in"].append(p["key"])
                    continue
                it["also_in"] = []
                seen[it["id"]] = it
                all_items.append(it)
            pages[p["key"]] = {
                "label_zh": p["label_zh"], "label_en": p["label_en"],
                "url": p["url"], "title": title, "count": len(items),
                "raw_count": count,
                "with_rating": sum(1 for x in items if x["rating"] is not None),
                "with_image": sum(1 for x in items if x["image"]),
            }
            if verbose:
                print("  ✅ %-11s %3d 件（含评分 %2d / 含图 %2d）  %s"
                      % (p["key"], len(items),
                         pages[p["key"]]["with_rating"], pages[p["key"]]["with_image"], title[:40]))
        except Exception as e:
            errors.append({"page": p["key"], "url": p["url"], "error": str(e)})
            if verbose:
                print("  ❌ %-11s %s" % (p["key"], e))

    return {"pages": pages, "items": all_items, "errors": errors}


def run(verbose=True, only=None):
    """only: 只补抓指定 page key，并与已有 walmart.json 合并（未请求的页保留旧数据）。"""
    path = os.path.join(DATA_DIR, "walmart.json")
    prev = None
    if only and os.path.exists(path):
        try:
            prev = json.load(open(path, encoding="utf-8"))
        except Exception:
            prev = None

    if verbose:
        if only:
            print("补抓 Walmart 品类页：%s" % ", ".join(only))
        else:
            print("抓取 Walmart 品类页（%d 页）…" % len(PAGES))

    res = fetch_all(verbose=verbose, only=only)

    pages = dict((prev or {}).get("pages") or {})
    pages.update(res["pages"])

    items = list(res["items"])
    if prev:
        have = {x["id"] for x in items}
        for x in (prev.get("items") or []):
            if x.get("page") not in res["pages"] and x["id"] not in have:
                items.append(x)
                have.add(x["id"])

    asked = {p["key"] for p in PAGES if not only or p["key"] in only}
    errors = [e for e in ((prev or {}).get("errors") or []) if e.get("page") not in asked]
    errors += res["errors"]

    out = {
        "source": "walmart.com",
        "listed_at": LISTED_AT,
        "captured_at": time.strftime("%Y-%m-%d"),
        "pages": pages,
        "items": items,
        "errors": errors,
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    n = len(out["items"])
    wr = sum(1 for x in out["items"] if x["rating"] is not None)
    wi = sum(1 for x in out["items"] if x["image"])
    if verbose:
        print("-" * 62)
        print("  落盘 %s" % path)
        print("  去重后 %d 件 | 含评分 %d | 含图 %d | 错误 %d" % (n, wr, wi, len(out["errors"])))
        for e in out["errors"]:
            print("    ⚠️ %s: %s" % (e["page"], e["error"][:80]))
    return out


if __name__ == "__main__":
    import sys
    _only = None
    if "--only" in sys.argv:
        _i = sys.argv.index("--only")
        _only = [x for x in sys.argv[_i + 1].split(",") if x]
    run(only=_only)
