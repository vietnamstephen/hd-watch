# -*- coding: utf-8 -*-
"""
Amazon 声量榜单采集（网评分 / 畅销榜 / buzz 分析的原始数据）。

为什么以 Amazon 为主数据源
--------------------------------------------------
Home Depot 与 Lowe's 的站内商品数据（评分、评论数、畅销标识）由 Akamai 保护，
在本机网络下所有通道均被拒绝。实测过的失败通道：

  · urllib 直连 homedepot.com / lowes.com / homedepot.com.mx / homedepot.ca
    的类目页、产品页、内容页，甚至 robots.txt          → 全部 403
  · 无头 Chrome（含 --disable-blink-features=AutomationControlled
    与完整桌面 UA / 持久化 profile）                    → 403
  · 五个公开 CORS 代理（allorigins / codetabs / corsproxy / thingproxy / cors.lol）
                                                      → 403 / 522 / 429
  · r.jina.ai 文本代理                                → 403
  · Google Shopping、Bing 商品富片段                   → 页面可抓但无结构化评分字段

连 robots.txt 都返回 403，说明拦截发生在请求指纹层（TLS/JA3 + IP 段），
不是简单 UA 判断，「换 UA / 换代理」这条路已穷尽。

Amazon 的 Best Sellers / New Releases 榜单可正常抓取，且它本身就是最具代表性的
电商畅销榜，含排名 + 平均评分 + 累计评论数三个 buzz 核心字段，故以它为一手数据源。
Home Depot 与 Lowe's 改用公开渠道披露的、带来源的评分与畅销信息，见 config_buzz.py。

⚠️ 两个必须记住的坑
--------------------------------------------------
1. **URL 形式决定拿到什么榜单。** `/Best-Sellers-Patio-Lawn-Garden/zgbs/lawn-garden`
   这个形式在限流后可能返回 3.7KB 空壳，若只按长度判断重试，会静默拿到别的榜单内容
   （实测发生过：「总榜」被写成了「虫害防治」的内容）。现在改为
   `/gp/bestsellers/lawn-garden`（不带节点 = 总榜），解析后强制校验页面
   title / canonical，并做跨榜单 ASIN 重复检测，一旦异常直接记入 errors。
2. **Amazon 有速率限制。** 连续快发会返回空壳页。请求间隔 2.2s 起，指数退避重试。

本模块只负责采集与解析，不做任何结论。
"""
import os
import re
import json
import time
import ssl
import random
import urllib.request

import patio_taxonomy as TX       # 品类口径的单一事实来源（与 Walmart 采集共用）

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

UA = "Mozilla/5.0"          # 本机代理环境：请求头只能带 User-Agent
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE

HOST = "https://www.amazon.com"

# ---------------------------------------------------------------- 榜单定义
# 全部为已验证可抓的 Amazon 节点。expect_title 用于防串榜校验。
BOARDS = [
    {"key": "overall", "label_zh": "庭院与户外 总榜", "label_en": "Patio, Lawn & Garden (overall)",
     "kind": "best", "path": "/gp/bestsellers/lawn-garden",
     "expect": "Patio, Lawn & Garden"},
    {"key": "patio", "label_zh": "户外家具与配件", "label_en": "Patio Furniture & Accessories",
     "kind": "best", "path": "/gp/bestsellers/lawn-garden/553824",
     "expect": "Patio Furniture"},
    {"key": "grills", "label_zh": "烧烤与户外烹饪", "label_en": "Grills & Outdoor Cooking",
     "kind": "best", "path": "/gp/bestsellers/lawn-garden/553760",
     "expect": "Outdoor Cooking"},
    {"key": "decor", "label_zh": "户外装饰", "label_en": "Outdoor Décor",
     "kind": "best", "path": "/gp/bestsellers/lawn-garden/553788",
     "expect": "Outdoor D"},
    {"key": "heating", "label_zh": "户外取暖", "label_en": "Outdoor Heating",
     "kind": "best", "path": "/gp/bestsellers/lawn-garden/13638732011",
     "expect": "Outdoor Heating"},
    {"key": "pools", "label_zh": "泳池与按摩浴缸", "label_en": "Pools, Hot Tubs & Supplies",
     "kind": "best", "path": "/gp/bestsellers/lawn-garden/1272941011",
     "expect": "Pools"},
    {"key": "pest", "label_zh": "虫害防治", "label_en": "Pest Control",
     "kind": "best", "path": "/gp/bestsellers/lawn-garden/553844",
     "expect": "Pest Control"},
    {"key": "patio_new", "label_zh": "户外家具 新品榜", "label_en": "Patio Furniture — New Releases",
     "kind": "new", "path": "/gp/new-releases/lawn-garden/553824",
     "expect": "New Releases"},
]

# ---------------------------------------------------------------- 品类标注
# 从标题关键词推断商品品类，用于「明星产品」的品类分布分析。
# ⚠️ 顺序即优先级，务必「先专有、后一般」：
#    · "Fire Pit Cover" 应归 cover 而非 fire → cover 必须在 fire 之前
#    · "Grill Cover" 同理         → cover 必须在 grill 之前
#    · 先用 "flameless" 排除，否则 "Flameless Candle" 会被 "flame" 误判成火炉
CATS = [
    ("cover",   ["cover", "carry bag", "storage bag", "protective", "carrying case"]),
    ("fire",    ["fire pit", "firepit", "fire bowl", "chiminea", "fireplace",
                 "fire color", "flame color", "magical flames", "fire log",
                 "fire starter", "kindling"]),
    ("grill",   ["grill", "grilling", "smoker", "bbq", "barbecue", "pellet",
                 "griddle", "meat thermometer", "skewer", "rotisserie", "pizza oven"]),
    ("heating", ["heater", "patio heater", "misting fan", "mister", "heat lamp",
                 "infrared"]),
    ("shade",   ["umbrella", "gazebo", "canopy", "pergola", "awning", "shade sail",
                 "pop up tent", "parasol", "screen house", "sun shelter"]),
    # 露营/海滩用品单独一类：它们是 Amazon 该节点下的真实商品，但不是露台家具，
    # 混进「大件家具」会误导（榜首曾被一张露营椅占据）。
    ("camp",    ["camping", "beach chair", "stadium seat", "tailgating",
                 "sleeping bag", "backpacking", "camp chair"]),
    # storage 必须早于 seating：否则 "Storage Bench" 会被 "bench" 抢走
    ("storage", ["storage box", "deck box", "storage cabinet", "storage shed",
                 "storage bench", "container", "shed", "storage rack"]),
    ("seating", ["chair", "sofa", "couch", "sectional", "loveseat", "settle",
                 "bench", "ottoman", "stool", "hammock", "rocking", "glider",
                 "lounger", "chaise", "recliner", "swing", "daybed"]),
    ("table",   ["table", "dining set", "bistro set", "conversation set", "desk",
                 "furniture set", "patio set", "seating set", "chat set"]),
    ("cooler",  ["cooler", "ice pack", "ice chest", "tumbler", "water bottle",
                 "keg", "drink", "freezer pack"]),
    ("pool",    ["pool", "hot tub", "spa ", "chlorine", "algaecide", "pool liner",
                 "pump", "water slide", "solar cover"]),
    ("pest",    ["insect", "ant ", "ant killer", "mosquito", "fly trap", "roach",
                 "rodent", "mouse", "rat ", "trap", "repellent", "bug", "wasp",
                 "termite", "zapper", "pest", "gnat"]),
    ("garden",  ["planter", "flower pot", "pot ", "soil", "seed", "hose",
                 "sprinkler", "watering", "trellis", "garden stake", "raised bed",
                 "compost", "fertilizer", "weed", "mower", "trimmer", "blower",
                 "leaf", "rake", "shovel", "garden"]),
    ("light",   ["light", "lamp", "lantern", "led", "solar", "floodlight",
                 "chandelier", "string light"]),
    ("decor",   ["statue", "ornament", "flag", "wind", "sign", "wall art",
                 "fountain", "pond", "bird", "feeder", "bath", "mat", "rug",
                 "pillow", "cushion", "spider web", "halloween", "christmas",
                 "inflatable", "candle", "tapestry", "planter stand"]),
]

# 负面词：命中则跳过该品类，避免同形词误伤（如 flameless ≠ flame）
NEG = {
    "fire": ["flameless", "flame-less"],
    "pest": ["trap house", "trap door"],
}

# 关键词一律按「词边界」匹配，并允许规则复数后缀。
# 两条血泪教训：
#   1. 直接子串匹配会让 "table" 命中 "tablets"，于是泳池氯片 (Chlorine Tablets)
#      被归成「桌类」并混进大件家具榜。
#   2. 只匹配单数会让 "Chair Covers" 漏掉 cover、被 "chair" 抢走，
#      结果椅子套出现在「大件家具」榜首。所以必须允许 s / es 后缀。
_KW_CACHE = {}


def _kw_hit(text: str, kw: str) -> bool:
    r = _KW_CACHE.get(kw)
    if r is None:
        r = re.compile(r"(?<![a-z0-9])" + re.escape(kw.strip())
                       + r"(?:s|es)?(?![a-z0-9])")
        _KW_CACHE[kw] = r
    return r.search(text) is not None

# ⚠️ 品类口径已于 2026-10-13 统一到 patio_taxonomy（用户指定按 Home Depot patio 类目）。
# 上面的 CATS / NEG / _kw_hit 保留仅供历史数据复算，**不要再改**——
# 实际归类一律走 TX.guess_cat，否则 Amazon 与 Walmart 会用两套规则，跨渠道对比失去意义。
CAT_LABEL = {k: (v["zh"], v["en"]) for k, v in TX.CATS.items()}


def guess_cat(title: str) -> str:
    """品类归类 —— 委托给 patio_taxonomy 的单一口径。"""
    return TX.guess_cat(title)


# ---------------------------------------------------------------- HTTP
def _http(url: str, tries: int = 4, base_wait: float = 2.2, timeout: int = 30) -> str:
    """带指数退避的 GET。空壳页（< 30KB 且无 gridItemRoot）视为限流，必须重试。"""
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
                body = r.read().decode("utf-8", "replace")
            if len(body) < 30000 or 'id="gridItemRoot"' not in body:
                last = f"疑似限流（仅 {len(body)}B，无榜单结构）"
                time.sleep(base_wait * (i + 1) + random.uniform(0, 0.9))
                continue
            return body
        except Exception as e:                                    # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
            time.sleep(base_wait * (i + 1) + random.uniform(0, 0.9))
    raise RuntimeError(last)


# ---------------------------------------------------------------- 解析
def _clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    # 数字实体要先解，否则标题里会残留 &#x27; &#39; 之类
    s = re.sub(r"&#x([0-9a-fA-F]+);", lambda m: chr(int(m.group(1), 16)), s)
    s = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), s)
    s = (s.replace("&amp;", "&").replace("&quot;", '"').replace("&apos;", "'")
          .replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">"))
    return re.sub(r"\s+", " ", s).strip()


def _int(s) -> int:
    try:
        return int(str(s).replace(",", "").strip())
    except (TypeError, ValueError):
        return 0


def page_title(html: str) -> str:
    m = re.search(r"<title>([^<]{0,160})", html)
    return _clean(m.group(1)) if m else ""


def parse_board(html: str, kind: str = "best") -> list:
    """解析一个 Amazon 榜单页（2026-10 实测结构）。

      <div id="gridItemRoot"> … <span class="zg-bdg-text">#1</span> …
        <div id="p13n-asin-index-0" data-asin="B0C3FTCYZL">
        … aria-label="4.8 out of 5 stars, 37,580 ratings"
    """
    items = []
    for idx, c in enumerate(html.split('id="gridItemRoot"')[1:60]):
        rank_m = re.search(r'class="zg-bdg-text"[^>]*>\s*#?([\d,]+)', c)
        rank = _int(rank_m.group(1)) if rank_m else idx + 1

        asin_m = re.search(r'data-asin="([A-Z0-9]{10})"', c)
        asin = asin_m.group(1) if asin_m else ""

        title = ""
        alt_m = re.search(r'<img[^>]+alt="([^"]{8,240})"', c)
        if alt_m:
            title = _clean(alt_m.group(1))
        if not title:
            t_m = re.search(r'_cDEzb_p13n-sc-css-line-clamp-\d+_[^"]*">([^<]{8,260})<', c)
            if t_m:
                title = _clean(t_m.group(1))
        if not title:
            continue

        rt = re.search(r'aria-label="([\d.]+) out of 5 stars, ([\d,]+) ratings?"', c)
        rating = float(rt.group(1)) if rt else None
        reviews = _int(rt.group(2)) if rt else 0
        if rating is None:
            rt2 = re.search(r"([\d.]+) out of 5 stars", c)
            if rt2:
                rating = float(rt2.group(1))

        price = None
        for pp in (r"_cDEzb_p13n-sc-price[^>]*>\s*\$([\d,]+\.\d\d)",
                   r'class="a-price-whole">([\d,]+)',
                   r"a-color-price[^>]*>\s*\$([\d,]+\.\d\d)"):
            pm = re.search(pp, c)
            if pm:
                price = float(pm.group(1).replace(",", ""))
                break

        items.append({
            "rank": rank, "asin": asin, "title": title,
            "url": f"{HOST}/dp/{asin}" if asin else "",
            "rating": rating, "reviews": reviews, "price": price,
            "cat": guess_cat(title),
        })

    seen, out = set(), []
    for it in sorted(items, key=lambda x: x["rank"]):
        if it["asin"] and it["asin"] in seen:
            continue
        if it["asin"]:
            seen.add(it["asin"])
        out.append(it)
    return out


# ---------------------------------------------------------------- 主流程
def fetch_all(verbose: bool = True) -> dict:
    doc = {
        "asof": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "Amazon Best Sellers / New Releases（amazon.com，免密钥直抓）",
        "source_zh": "亚马逊畅销榜与新品榜（官方榜单页直抓，含排名、平均评分、累计评论数）",
        "host": HOST,
        "boards": {},
        "errors": [],
    }
    fingerprints = {}
    for b in BOARDS:
        url = HOST + b["path"]
        try:
            html = _http(url)
            ttl = page_title(html)
            # 防串榜：页面标题必须包含预期关键词
            if b.get("expect") and b["expect"].lower() not in ttl.lower():
                raise RuntimeError(f"页面标题不符预期（期望含「{b['expect']}」，实际「{ttl}」）")
            items = parse_board(html, kind=b["kind"])
            if len(items) < 10:
                raise RuntimeError(f"仅解析到 {len(items)} 条，榜单页结构可能已变")
            key_sig = tuple(sorted(i["asin"] for i in items if i["asin"])[:30])
            for other_key, other_sig in fingerprints.items():
                if key_sig and key_sig == other_sig:
                    raise RuntimeError(f"内容与「{other_key}」榜单完全重复，判定为串榜")
            fingerprints[b["key"]] = key_sig
            doc["boards"][b["key"]] = {
                "label_zh": b["label_zh"], "label_en": b["label_en"],
                "kind": b["kind"], "url": url, "page_title": ttl, "items": items,
            }
            if verbose:
                rts = sorted(i["rating"] for i in items if i["rating"])
                print(f"  ✅ {b['label_zh']:<16} {len(items):>3} 条"
                      f"｜中位评分 {rts[len(rts)//2] if rts else '—'}")
        except Exception as e:                                    # noqa: BLE001
            doc["errors"].append({"board": b["key"], "label": b["label_zh"],
                                  "error": str(e)[:220]})
            if verbose:
                print(f"  ❌ {b['label_zh']:<16} {str(e)[:100]}")
        time.sleep(2.2)
    return doc


def run(verbose: bool = True) -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    doc = fetch_all(verbose=verbose)
    p = os.path.join(DATA_DIR, "buzz.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    n_b = len(doc["boards"])
    n_i = sum(len(v["items"]) for v in doc["boards"].values())
    n_r = sum(1 for v in doc["boards"].values() for i in v["items"] if i["rating"])
    if verbose:
        print(f"  合计 {n_b} 个榜单 / {n_i} 条商品 / {n_r} 条含评分"
              f"｜错误 {len(doc['errors'])} 条 → {p}")
    return p


if __name__ == "__main__":
    run()
