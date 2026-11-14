# -*- coding: utf-8 -*-
"""
Walmart 商品评论采集 —— 用户「负面评论多数论点归纳」的数据源。

为什么做这个
--------------------------------------------------
用户第 7 条需求的后半句：「对于客户的一些负面评论，有多数论点的也可以归纳分析下。」

Walmart 评论页给的东西比预想的多，一次请求能拿到四类信号：

  ① 星级分布（绝对数 + 百分比）
     ratingValueOneCount … ratingValueFiveCount / percentageOneCount …
     → 用于量化「差评集中度」，1–2 星占比是最硬的指标。
  ② 平台自带的评论维度标签 aspects[]
     [{id, name, score, snippetCount}]  —— snippetCount 是提及总数，**不含极性**。
  ③ 要点式极性摘要 bulletReviewSummary.bulletSummaryAspects[]
     [{aspectName, aspectPillText, aspectPolarity(Positive/Negative), aspectSummary}]
     ⚠️ 这里才有极性，但只给 6 条、且样本里常常全是 Positive。
  ④ 典型好评/差评 + 逐条评论正文（评论文本、星级、日期、有用票）

⚠️ 关键教训：**aspects 没有正负极性**，光靠它归纳不出「负面论点」。
   真正可靠的做法是 —— 用 `?sort=rating-asc` 直接拉「最低分优先」的第一页
   （实测返回 10 条全 1 星），再对我们自己定义的痛点词表做命中统计。
   因为只扫 1–2 星评论，像 `price` / `shipping` / `returned` 这类中性词
   落在差评语境里基本等同于投诉，误报率可控（这一点在 docstring 里立此存照）。

数据落点：__NEXT_DATA__.props.pageProps.initialData.data.reviews
⚠️ 与商品页同一套速率限制：页间隔 12s 以上，被拦时返回约 15KB 拦截页（无 __NEXT_DATA__）。
"""
import json
import os
import random
import re
import ssl
import time
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

UA = "Mozilla/5.0"
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE

PICK_PER_CAT = 2       # 每个品类挑评论数最高的 N 个商品去抓评论
# ⚠️ 这里**不能**设总数上限：7 个 patio 品类 × 2 = 14，早期写成 MAX_PRODUCTS=12
# 会把排在最后的「烧烤与火炉」整类截掉，导致该品类差评率恒为空（已踩过）。
# 0 = 不设上限。
MAX_PRODUCTS = 0
NEG_PAGES = 2          # 每商品抓「最低分优先」的前 N 页（每页 10 条）
NEG_PER_PRODUCT = 10 * NEG_PAGES

# ── 负评痛点词表（顺序不影响结果，最终按命中数排序）──────────────────
# 匹配规则：词边界 + 可选复数，与 patio_taxonomy._kw_hit 同一套。
# ⚠️ 只用于 rating<=2 的评论，因此允许放 price / shipping 这类中性词。
THEMES = [
    ("stability", "结构不稳 / 易倒", "Sturdiness & stability",
     ["flimsy", "wobbl", "wobbly", "unstable", "sturdy", "sturdiness",
      "tipped over", "tip over", "blew over", "blew away", "collapse", "collapsed",
      "bent", "snapped", "shaky", "rickety", "fell apart", "fall apart", "falls apart",
      "not stable", "unsteady"]),
    ("durability", "材质耐久性差", "Durability & material quality",
     ["rust", "rusted", "rusty", "faded", "fading", "rot", "rotted", "rotting",
      "mold", "mildew", "cheaply made", "cheap material", "cheap plastic",
      "thin material", "low quality", "poor quality", "bad quality", "defective",
      "poorly made", "junk"]),
    ("assembly", "安装组装困难", "Hard to assemble",
     ["assemble", "assembly", "instructions", "put together", "set up", "setup",
      "missing parts", "missing pieces", "missing screws", "missing hardware",
      "missing bolt", "confusing", "no directions"]),
    ("size_fit", "尺寸与描述不符", "Size / fit mismatch",
     ["smaller than", "too small", "not as big", "wrong size", "dimensions",
      "doesn't fit", "does not fit", "didn't fit", "won't fit", "wont fit",
      "too short", "too narrow", "not as described", "misleading"]),
    ("shade", "遮阳效果不足", "Insufficient shade",
     ["shade", "sun", "coverage", "uv", "not block", "doesn't block", "does not block",
      "lets sun", "too much sun", "not enough cover"]),
    ("fabric", "面料 / 做工瑕疵", "Fabric & workmanship defects",
     ["fabric", "canvas", "tear", "tore", "torn", "ripped", "rip", "seam", "seams",
      "stitching", "hole", "holes", "pinhole", "thin fabric", "color is off",
      "color different", "wrong color", "uneven"]),
    ("damage", "到货破损 / 包装差", "Arrived damaged / poor packaging",
     ["arrived damaged", "arrived broken", "came damaged", "came broken", "damaged",
      "dented", "packaging", "package was", "box was", "shipping", "shipped",
      "broken in transit", "crushed"]),
    ("mechanism", "操作机构故障", "Mechanism & hardware failure",
     ["crank", "tilt", "button", "mechanism", "stuck", "jammed", "won't open",
      "wont open", "hard to open", "difficult to open", "won't lock", "wont lock",
      "doesn't lock", "does not lock", "won't stay", "wont stay", "hard to close",
      "won't close", "wont close", "velcro", "strap broke"]),
    ("wind", "抗风能力弱", "Poor wind resistance",
     ["wind", "windy", "gust", "gusts", "blows over", "fly away", "flew away",
      "blew", "blown"]),
    ("base", "底座 / 配重不足", "Weak base / insufficient weight",
     ["base", "weighted base", "no base", "pole", "stand", "too light", "weight",
      "counterweight", "sand", "filling with water", "water filled"]),
    ("value", "失望 / 退款退货", "Disappointment & returns",
     ["not worth", "waste of money", "overpriced", "too expensive", "refund",
      "return it", "returned", "returning", "money back", "regret", "disappointed",
      "rip off", "price"]),
    ("service", "客服与售后不佳", "Customer service & warranty",
     ["customer service", "warranty", "no response", "never responded", "replacement",
      "exchange", "policy", "no help"]),
]

def _wr(w):
    return re.compile(r"(?<![a-z0-9])" + re.escape(w) + r"(?:s|es)?(?![a-z0-9])", re.I)


_THEME_INDEX = [(k, zh, en, [_wr(w) for w in ws]) for k, zh, en, ws in THEMES]


def _http(url, tries=3, base_wait=16.0, timeout=40):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
                html = r.read().decode("utf-8", "replace")
            if "__NEXT_DATA__" in html:
                return html
            last = "拦截页或空响应 len=%d" % len(html)
        except Exception as e:
            last = "%s: %s" % (type(e).__name__, e)
        if i < tries - 1:
            time.sleep(base_wait * (i + 1) + random.random() * 3)
    raise RuntimeError("请求失败：%s" % last)


# Walmart 把评论正文里的 & ' , 等二次编码成 %26 %27 %2C，需定点还原。
# 不用 urllib.parse.unquote：正文里存在「50% off」这类百分号，全量解码会误伤。
_PCT = {"%26": "&", "%27": "'", "%2C": ",", "%3A": ":", "%2F": "/",
        "%21": "!", "%24": "$", "%28": "(", "%29": ")", "%3F": "?", "%22": '"'}


def _clean(s):
    if not s:
        return ""
    s = re.sub(r"&#x([0-9a-fA-F]+);", lambda m: chr(int(m.group(1), 16)), s)
    for a, b in (("&amp;", "&"), ("&quot;", '"'), ("&#39;", "'"), ("&apos;", "'"),
                 ("&lt;", "<"), ("&gt;", ">"), ("&nbsp;", " ")):
        s = s.replace(a, b)
    for a, b in _PCT.items():
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def _one_review(r):
    if not isinstance(r, dict):
        return None
    return {
        "rating": r.get("rating"),
        "title": _clean(str(r.get("reviewTitle") or "")),
        "text": _clean(str(r.get("reviewText") or "")),
        "date": r.get("reviewSubmissionTime") or "",
        "helpful": r.get("positiveFeedback") or 0,
    }


def parse_reviews(html):
    m = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise RuntimeError("无 __NEXT_DATA__")
    nd = json.loads(m.group(1))
    rv = ((nd.get("props") or {}).get("pageProps") or {}).get("initialData", {}) \
        .get("data", {}).get("reviews") or {}
    if not rv:
        raise RuntimeError("页面无 reviews 数据")

    aspects = []
    for a in (rv.get("aspects") or []):
        if not isinstance(a, dict):
            continue
        nm = _clean(str(a.get("name") or ""))
        if nm:
            aspects.append({"name": nm, "mentions": a.get("snippetCount") or 0})

    bullets = []
    bsum = rv.get("bulletReviewSummary") or {}
    for b in (bsum.get("bulletSummaryAspects") or []):
        if not isinstance(b, dict):
            continue
        bullets.append({
            "polarity": b.get("aspectPolarity") or "",
            "pill": _clean(str(b.get("aspectPillText") or "")),
            "aspect": _clean(str(b.get("aspectName") or "")),
            "summary": _clean(str(b.get("aspectSummary") or "")),
        })

    dist_n = {str(i): rv.get("ratingValue%sCount" % w) or 0 for i, w in
              ((1, "One"), (2, "Two"), (3, "Three"), (4, "Four"), (5, "Five"))}
    dist_pct = {str(i): rv.get("percentage%sCount" % w) or 0 for i, w in
                ((1, "One"), (2, "Two"), (3, "Three"), (4, "Four"), (5, "Five"))}

    samples = [x for x in (_one_review(r) for r in (rv.get("customerReviews") or [])) if x]

    return {
        "avg_rating": rv.get("averageOverallRating"),
        "total_reviews": rv.get("totalReviewCount") or 0,
        "with_text": rv.get("reviewsWithTextCount") or 0,
        "recommended_pct": rv.get("recommendedPercentage"),
        "dist_n": dist_n,
        "dist_pct": dist_pct,
        "aspects": aspects,
        "bullets": bullets,
        "top_negative": _one_review(rv.get("topNegativeReview")),
        "top_positive": _one_review(rv.get("topPositiveReview")),
        "samples": samples,
    }


def count_themes(text):
    """返回命中的痛点 key 列表（同一 key 只记一次，避免长文刷量）。"""
    hits = []
    low = text or ""
    for key, _zh, _en, pats in _THEME_INDEX:
        for p in pats:
            if p.search(low):
                hits.append(key)
                break
    return hits


def _dedupe_key(title):
    """前 3 个词做近似去重键：Blackstone Griddle 28in / 36in 视为同一款。"""
    return " ".join(re.findall(r"[A-Za-z0-9]+", (title or "").lower())[:3])


def pick_products(wm):
    """每个品类挑评论数最高的 N 个商品（保证每个品类都有样本、且款不重复）。"""
    from collections import defaultdict
    import patio_taxonomy as TX
    by = defaultdict(list)
    for it in wm.get("items") or []:
        cat = TX.guess_cat(it.get("title", ""))
        if cat in TX.PATIO_KEYS and (it.get("reviews") or 0) > 0:
            by[cat].append(it)
    picked = []
    for cat in TX.PATIO_KEYS:
        rows = sorted(by.get(cat) or [], key=lambda x: -(x.get("reviews") or 0))
        seen, chosen = set(), []
        for r in rows:
            k = _dedupe_key(r.get("title"))
            if k in seen:
                continue
            seen.add(k)
            chosen.append(r)
            if len(chosen) >= PICK_PER_CAT:
                break
        picked.extend(chosen)
    return picked[:MAX_PRODUCTS] if MAX_PRODUCTS else picked


def summarize_themes(products):
    """把差评正文汇总成「痛点主题」，并给出品类 × 痛点二维视图。

    引语选取：优先「有用票多、且同时命中的主题数少」的评论——因为一段差评常常
    一次吐槽 4、5 个点，若只按有用票挑，同一段话会同时出现在多个主题下，看着很假。
    这里用 helpful*100 - 共同命中主题数*10 打分，让每条主题拿到最「专属」的那段。
    """
    import patio_taxonomy as TX
    agg, by_cat, docs = {}, {}, []
    for p in products:
        cat = p.get("cat") or "other"
        for r in p.get("neg_samples") or []:
            text = (r.get("title") or "") + " " + (r.get("text") or "")
            hits = count_themes(text)
            if not hits:
                continue
            docs.append((cat, r, hits))
            for k in hits:
                cur = agg.setdefault(k, {"key": k, "negative": 0, "products": 0,
                                         "cats": {}, "quote": "", "_best": -1e9})
                cur["negative"] += 1
                cur["cats"][cat] = cur["cats"].get(cat, 0) + 1
                by_cat.setdefault(cat, {}).setdefault(k, 0)
                by_cat[cat][k] += 1

    # 引语：越「专属」越好
    for k, v in agg.items():
        best = None
        for cat, r, hits in docs:
            if k not in hits:
                continue
            t = (r.get("text") or "").strip()
            if len(t) < 40:
                continue
            sc = (r.get("helpful") or 0) * 100 - (len(hits) - 1) * 10 - abs(len(t) - 200) * 0.05
            if sc > v["_best"]:
                v["_best"] = sc
                best = t
        if best:
            v["quote"] = best[:240]

    # 产品级去重覆盖数
    for p in products:
        seen = set()
        for r in p.get("neg_samples") or []:
            seen.update(count_themes((r.get("title") or "") + " " + (r.get("text") or "")))
        for k in seen:
            if k in agg:
                agg[k]["products"] += 1

    meta = {k: (zh, en) for k, zh, en, _ in THEMES}
    rows = []
    for k, v in agg.items():
        zh, en = meta.get(k, (k, k))
        rows.append({"key": k, "zh": zh, "en": en, "negative": v["negative"],
                     "products": v["products"], "cats": v["cats"], "quote": v["quote"]})
    rows.sort(key=lambda x: (-x["negative"], -x["products"]))

    cat_rows = {}
    for cat, d in by_cat.items():
        lst = [{"key": k, "zh": meta.get(k, (k, k))[0], "en": meta.get(k, (k, k))[1],
                "negative": n} for k, n in d.items()]
        lst.sort(key=lambda x: -x["negative"])
        cat_rows[cat] = {"label_zh": TX.label(cat), "label_en": TX.label(cat, "en"),
                         "themes": lst, "total": sum(x["negative"] for x in lst)}
    return rows, cat_rows


def summarize_cats(wm, products):
    """品类级口碑：全量商品的加权星级 + 抽样商品的 1/2 星占比、TOP 痛点。

    加权星级 = Σ(评分×评论数)/Σ评论数 —— 用评论数当权重，等价于「把该品类所有
    评论揉在一起算平均分」，比简单平均中位数更能反映真实口碑（老品评论多、权重大）。
    """
    import patio_taxonomy as TX
    from collections import defaultdict
    allby = defaultdict(list)
    for it in wm.get("items") or []:
        c = TX.guess_cat(it.get("title", ""))
        if c in TX.PATIO_KEYS:
            allby[c].append(it)

    samp = defaultdict(list)
    for p in products:
        samp[p.get("cat")].append(p)

    rows = []
    for c in TX.PATIO_KEYS:
        items = allby.get(c) or []
        num = sum((x.get("rating") or 0) * (x.get("reviews") or 0) for x in items)
        den = sum((x.get("reviews") or 0) for x in items if x.get("rating"))
        wavg = round(num / den, 2) if den else None
        rs = sorted([x["rating"] for x in items if x.get("rating")])
        med = rs[len(rs) // 2] if rs else None

        ps = samp.get(c) or []
        tr = sum(p.get("total_reviews") or 0 for p in ps)
        n1 = sum((p["dist_n"].get("1") or 0) for p in ps)
        n2 = sum((p["dist_n"].get("2") or 0) for p in ps)
        themes = {}
        for p in ps:
            for r in p.get("neg_samples") or []:
                for k in count_themes((r.get("title") or "") + " " + (r.get("text") or "")):
                    themes[k] = themes.get(k, 0) + 1
        top = sorted(themes.items(), key=lambda x: -x[1])[:3]
        meta = {k: (zh, en) for k, zh, en, _ in THEMES}
        rows.append({
            "cat": c, "label_zh": TX.label(c), "label_en": TX.label(c, "en"),
            "n_items": len(items), "median_rating": med, "weighted_rating": wavg,
            "total_reviews": int(den),
            "sampled": len(ps), "sample_reviews": int(tr),
            "pct_1star": round(100.0 * n1 / tr, 1) if tr else None,
            "pct_2star": round(100.0 * n2 / tr, 1) if tr else None,
            "neg_share": round(100.0 * (n1 + n2) / tr, 1) if tr else None,
            "top_themes": [{"key": k, "zh": meta.get(k, (k, k))[0],
                            "en": meta.get(k, (k, k))[1], "hits": v} for k, v in top],
        })
    return rows


def run(verbose=True):
    import patio_taxonomy as TX
    wm_path = os.path.join(DATA_DIR, "walmart.json")
    if not os.path.exists(wm_path):
        raise SystemExit("缺少 data/walmart.json，请先运行 fetch_walmart.py")
    wm = json.load(open(wm_path, encoding="utf-8"))
    picked = pick_products(wm)

    if verbose:
        print("抓取 Walmart 评论（%d 个商品：每品类挑评论量最高的 %d 个）…"
              % (len(picked), PICK_PER_CAT))

    products, errors = [], []
    for i, it in enumerate(picked):
        if i:
            time.sleep(12 + random.random() * 3)
        try:
            base = parse_reviews(_http(
                "https://www.walmart.com/reviews/product/%s?sort=rating-asc&page=1" % it["id"]))
            neg = [r for r in base["samples"] if (r.get("rating") or 5) <= 2]
            # 再抓低分页 2..N，凑厚样本（每页 10 条）
            for pg in range(2, NEG_PAGES + 1):
                time.sleep(12 + random.random() * 3)
                try:
                    more = parse_reviews(_http(
                        "https://www.walmart.com/reviews/product/%s?sort=rating-asc&page=%d"
                        % (it["id"], pg)))
                    neg += [r for r in more["samples"] if (r.get("rating") or 5) <= 2]
                except Exception:
                    pass  # 单页失败不影响整体
            # 去重（同一条评论标题+日期唯一）
            seen, uniq = set(), []
            for r in neg:
                k = (r.get("date"), (r.get("title") or "")[:40], (r.get("text") or "")[:60])
                if k in seen:
                    continue
                seen.add(k)
                uniq.append(r)
            if not uniq and base.get("top_negative"):
                uniq = [base["top_negative"]]
            base["neg_samples"] = uniq[:NEG_PER_PRODUCT]
            base.pop("samples", None)
            cat = TX.guess_cat(it.get("title", ""))
            base.update({
                "id": it["id"], "title": it["title"], "short": it["title"][:78],
                "rating": it.get("rating"), "reviews": it.get("reviews"),
                "image": it.get("image", ""),
                "cat": cat, "cat_label_zh": TX.label(cat), "cat_label_en": TX.label(cat, "en"),
                "url": it.get("url", ""),
            })
            products.append(base)
            if verbose:
                print("  ✅ %-24s 评 %5d 星%s ｜ 1星%2d%% 2星%2d%% ｜ 差评样本 %d"
                      % (it["title"][:24], base["total_reviews"], base["avg_rating"],
                         base["dist_pct"].get("1") or 0, base["dist_pct"].get("2") or 0,
                         len(base["neg_samples"])))
        except Exception as e:
            errors.append({"id": it["id"], "title": it["title"][:60], "error": str(e)})
            if verbose:
                print("  ❌ %-24s %s" % (it["title"][:24], str(e)[:60]))

    themes, by_cat = summarize_themes(products)
    cat_stats = summarize_cats(wm, products)

    out = {
        "source": "walmart.com/reviews?sort=rating-asc",
        "captured_at": time.strftime("%Y-%m-%d"),
        "note": "差评样本取自每个商品「最低分优先」前 %d 页；痛点主题由关键词表对 1–2 星"
                "正文命中统计，仅供定性参考。" % NEG_PAGES,
        "products": products,
        "themes": themes,
        "by_cat": by_cat,
        "cat_stats": cat_stats,
        "errors": errors,
    }
    path = os.path.join(DATA_DIR, "walmart_reviews.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    if verbose:
        print("-" * 70)
        print("  落盘 %s（%d 个商品 / 错误 %d）" % (path, len(products), len(errors)))
        print("\n  痛点主题 Top 10（命中差评条数 / 覆盖商品数）：")
        for t in themes[:10]:
            print("    %-16s 命中 %3d ｜ 覆盖 %2d 款 ｜ %s"
                  % (t["zh"][:16], t["negative"], t["products"], t["quote"][:40]))
        print("\n  品类口碑（全量加权星级 ｜ 抽样差评率 ｜ TOP 痛点）：")
        for c in cat_stats:
            tt = "、".join(x["zh"] for x in c["top_themes"])
            print("    %-12s 加权 %.2f ｜ 1星%.1f%% 2星%.1f%% ｜ %s"
                  % (c["label_zh"], c["weighted_rating"] or 0, c["pct_1star"] or 0,
                     c["pct_2star"] or 0, tt))
    return out


if __name__ == "__main__":
    run()
