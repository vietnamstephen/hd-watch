# -*- coding: utf-8 -*-
"""
buzz 分析引擎：从 Amazon 榜单原始数据里算出「明星产品」。

方法（三个分量，各自归一化到 0–1）
--------------------------------------------------
  声量 Volume   = log10(累计评分人数) 在**同一榜单内**做 min-max 归一化
                  用对数是因为评论数跨越数个数量级（77 → 164,109），线性归一化会
                  让头部商品把其余全部压成 0。
  口碑 Valence  = (平均星级 − 3.5) / 1.5，截断到 [0,1]
                  3.5 星以下记 0 分 —— 那是「有量但口碑不佳」，不该被声量抬上去。
  动能 Momentum = 1 − (名次 − 1) / (条数 − 1)
  综合分        = 0.45×V + 0.30×Q + 0.25×M

为什么必须在榜内归一化
--------------------------------------------------
不同榜单的评论量级完全不同：畅销榜中位数上万，新品榜中位数只有几百。
若跨榜比较，任何畅销榜商品都会碾压新品榜 —— 那是「上架时间」的差异，不是热度差异。
所以榜内打分，新品榜单独输出为「新星」。

输出 data/buzz_analysis.json，供看板直接消费。
"""
import os
import re
import json
import math

import config_buzz as CB
import patio_taxonomy as TX       # 品类口径的单一事实来源（与两个采集器共用）

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

W_V, W_Q, W_M = 0.45, 0.30, 0.25

# 进明星榜的品类由 patio_taxonomy 的 PATIO_KEYS 决定（off_topic / other 除外）
PATIO_CATS = set(TX.PATIO_KEYS)

# 标题里的营销噪声，用于压缩展示长度
_NOISE = re.compile(r"^(?:New |202\d (?:Upgraded|New) )", re.I)


def _short(title: str, n: int = 78) -> str:
    t = _NOISE.sub("", (title or "").strip())
    t = re.sub(r"\s*[|｜]\s*.*$", "", t)          # 去掉 | 之后的关键词堆砌
    t = re.sub(r"\s*,\s*(?:for|with|ideal|perfect).*$", "", t, flags=re.I)
    return (t[:n] + "…") if len(t) > n else t


def _norm_volumes(vals: list) -> list:
    logs = [math.log10(max(v, 1)) for v in vals]
    lo, hi = min(logs), max(logs)
    if hi - lo < 1e-9:
        return [0.5] * len(vals)
    return [(x - lo) / (hi - lo) for x in logs]


def _norm_valence(rating) -> float:
    if rating is None:
        return 0.0
    return max(0.0, min(1.0, (float(rating) - 3.5) / 1.5))


def score_board(items: list) -> list:
    """对单个榜单内的商品打分。"""
    if not items:
        return []
    n = len(items)
    vols = _norm_volumes([i["reviews"] for i in items])
    out = []
    for idx, it in enumerate(sorted(items, key=lambda x: x["rank"])):
        rank = it.get("rank") or (idx + 1)
        v = vols[idx]
        q = _norm_valence(it.get("rating"))
        m = 1.0 - (min(rank, n) - 1) / max(n - 1, 1)
        buzz = W_V * v + W_Q * q + W_M * m
        out.append({
            "asin": it.get("asin", ""), "rank": rank,
            "title": it.get("title", ""), "short": _short(it.get("title", "")),
            "rating": it.get("rating"), "reviews": it.get("reviews", 0),
            "price": it.get("price"), "cat": it.get("cat", "other"), "url": it.get("url", ""),
            "v": round(v, 4), "q": round(q, 4), "m": round(m, 4),
            "buzz": round(buzz, 4),
        })
    return out


def board_stats(items: list) -> dict:
    rts = sorted(i["rating"] for i in items if i["rating"])
    rvs = sorted(i["reviews"] for i in items if i["reviews"])
    if not items:
        return {}
    tot = sum(i["reviews"] for i in items)
    top3 = sum(sorted((i["reviews"] for i in items), reverse=True)[:3])
    return {
        "count": len(items),
        "median_rating": rts[len(rts) // 2] if rts else None,
        "median_reviews": rvs[len(rvs) // 2] if rvs else 0,
        "max_reviews": rvs[-1] if rvs else 0,
        "total_reviews": tot,
        "top3_share": round(top3 / tot, 4) if tot else 0,
        "rated_share": round(len(rts) / len(items), 4),
    }


def cat_mix(items: list) -> list:
    """（内部保留）按品类汇总，标签由调用方注入。"""
    from collections import Counter
    c = Counter(i.get("cat", "other") for i in items)
    tot = sum(c.values()) or 1
    return [{"cat": k, "n": v, "share": round(v / tot, 4)} for k, v in c.most_common()]


# ---------------------------------------------------------------- 渠道统计
def _med(a):
    a = sorted(a)
    return a[len(a) // 2] if a else None


def _cat_stats(rows):
    """一个渠道（或渠道内某品类）的统计口径，保证两个渠道算法一致。"""
    rs = [r["rating"] for r in rows if r.get("rating") is not None]
    rv = [r["reviews"] for r in rows if r.get("reviews")]
    pr = [r["price"] for r in rows if r.get("price")]
    return {
        "n": len(rows),
        "rated": len(rs),
        "median_rating": (round(_med(rs), 2) if rs else None),
        "median_reviews": _med(rv),
        "max_reviews": (max(rv) if rv else None),
        "total_reviews": sum(rv),
        "median_price": _med(pr),
    }


def score_walmart_page(rows):
    """对单个 Walmart 品类页打分（只保留 patio 品类）。

    动能分量用**页面展示序位**——Walmart 不公布销量排名，页内顺序是站内推荐排序，
    只能作为动能的代理指标（看板中已注明该限制）。另两个分量与 Amazon 完全同口径：
    声量 = log10(评论数) 在页内归一化，口碑 = (评分 − 3.5) / 1.5。
    """
    pool = [r for r in rows if r["cat"] in PATIO_CATS]
    if not pool:
        return []
    n = len(pool)
    vols = _norm_volumes([r.get("reviews") or 1 for r in pool])
    out = []
    for i, r in enumerate(pool):
        v, q = vols[i], _norm_valence(r.get("rating"))
        m = 1.0 - i / max(n - 1, 1)
        out.append(dict(r, v=round(v, 4), q=round(q, 4), m=round(m, 4),
                        buzz=round(W_V * v + W_Q * q + W_M * m, 4),
                        cat_label_zh=TX.label(r["cat"]),
                        cat_label_en=TX.label(r["cat"], "en")))
    return out


def build_channel_summary(amz_rows, wm_rows):
    return [
        {"channel": "Amazon", "access": "first_party",
         "scope_zh": "8 个畅销榜 / 新品榜", "scope_en": "8 best-seller / new-release boards",
         **_cat_stats(amz_rows)},
        {"channel": "Walmart", "access": "first_party",
         "scope_zh": "7 个 patio 品类页", "scope_en": "7 patio category pages",
         **_cat_stats(wm_rows)},
    ]


def build_channel_compare(amz_rows, wm_rows):
    """按 patio 品类做 Amazon × Walmart 逐类对比。"""
    out = []
    for ck in TX.PATIO_KEYS:
        out.append({
            "cat": ck, "label_zh": TX.label(ck), "label_en": TX.label(ck, "en"),
            "amazon": _cat_stats([r for r in amz_rows if r["cat"] == ck]),
            "walmart": _cat_stats([r for r in wm_rows if r["cat"] == ck]),
        })
    return out


def build_stars_cross(amz_best, wm_rows):
    """每个 patio 品类的「渠道冠军」并列展示（内含明星配图键）。

    ⚠️ 两渠道的 buzz 分是**各自榜内归一化**的，数值不可直接比较，
    所以这里只做「同渠道内排名」，跨渠道只并列、不排序。
    """
    from collections import defaultdict
    awm = defaultdict(list)
    for r in wm_rows:
        awm[r["cat"]].append(r)
    aam = defaultdict(list)
    for r in amz_best:
        aam[r["cat"]].append(r)

    out = []
    for ck in TX.PATIO_KEYS:
        a = sorted(aam.get(ck) or [], key=lambda x: -x["buzz"])
        w = sorted(awm.get(ck) or [], key=lambda x: -x["buzz"])
        out.append({
            "cat": ck, "label_zh": TX.label(ck), "label_en": TX.label(ck, "en"),
            "amazon": a[0] if a else None,
            "walmart": w[0] if w else None,
            "amazon_top": a[:3], "walmart_top": w[:3],
        })
    return out


def build_cat_ladder(amz_rows, wm_rows, wm_cat_stats):
    """品类「档次」阶梯 —— 回答「HD 主流 category 在目前品类里是什么档次」。

    三个观测轴，各自在 7 类之间做 z-score 后加权：
      需求体量 0.40 = z(log10(两渠道累计评论数))  —— 用「评论总量」而不是「在架件数」
      口碑     0.35 = z(加权星级 − 3.5)          —— 评论数加权，反映真实体验
      抗差评   0.25 = z(− 1–2 星占比)            —— 抱怨越少越稳

    ⚠️ 为什么体量轴不用「在架件数」：件数反映的是**沃尔玛的招商策略**，不是品类本身的
    需求规模。早期版本用了件数，结果「成套家具」被压到末位并打成「机会/利基」——
    而它恰恰是 Home Depot 的门面品类，这个结论明显是口径artifact 造成的误导。

    tier 只按排名分档（第几梯队），**不暗示谁该做谁不该做**；抱怨压力单独成列，
    因为「规模大」和「抱怨多」可以同时成立（成套家具正是如此）。
    """
    stats = {c["cat"]: c for c in (wm_cat_stats or [])}
    rows = []
    for ck in TX.PATIO_KEYS:
        s = stats.get(ck) or {}
        a = [r for r in amz_rows if r["cat"] == ck]
        w = [r for r in wm_rows if r["cat"] == ck]
        rev_a = sum(r["reviews"] for r in a if r.get("reviews"))
        rev_w = sum(r["reviews"] for r in w if r.get("reviews"))
        rows.append({
            "cat": ck, "label_zh": TX.label(ck), "label_en": TX.label(ck, "en"),
            "n_amz": len(a), "n_wm": len(w),
            "rev_amz": rev_a, "rev_wm": rev_w, "rev_total": rev_a + rev_w,
            "amz_median_reviews": _med([r["reviews"] for r in a if r.get("reviews")]),
            "amz_max_reviews": (max([r["reviews"] for r in a]) if a else 0),
            "wm_weighted_rating": s.get("weighted_rating"),
            "wm_median_rating": s.get("median_rating"),
            "wm_neg_share": s.get("neg_share"),
            "wm_pct_1star": s.get("pct_1star"),
            "sampled": s.get("sampled", 0),
            "sample_reviews": s.get("sample_reviews", 0),
            "top_themes": s.get("top_themes") or [],
            "confidence": "high" if (s.get("sample_reviews") or 0) >= 1000 else "low",
        })

    def z(vals):
        vs = [v for v in vals if v is not None]
        if len(vs) < 2:
            return [0.0] * len(vals)
        m = sum(vs) / len(vs)
        sd = (sum((v - m) ** 2 for v in vs) / len(vs)) ** 0.5
        if sd < 1e-9:
            return [0.0] * len(vals)
        return [0.0 if v is None else (v - m) / sd for v in vals]

    zs = z([math.log10(r["rev_total"] + 1) for r in rows])
    zq = z([(r["wm_weighted_rating"] - 3.5) if r["wm_weighted_rating"] else None for r in rows])
    zn = z([-(r["wm_neg_share"] or 0) for r in rows])
    for i, r in enumerate(rows):
        r["z_scale"], r["z_quality"], r["z_anti_neg"] = (round(zs[i], 3), round(zq[i], 3),
                                                         round(zn[i], 3))
        r["positioning"] = round(0.40 * zs[i] + 0.35 * zq[i] + 0.25 * zn[i], 4)

    rows.sort(key=lambda x: -x["positioning"])
    for i, r in enumerate(rows):
        r["rank"] = i + 1
        r["tier"] = ("第一梯队" if i < 2 else "第二梯队" if i < 4 else "第三梯队")
        ns = r["wm_neg_share"]
        r["risk"] = ("低" if ns is None else
                     "低" if ns < 6 else "中" if ns < 12 else "高")

    # 自动解读：把三条最值得说的事实点出来（避免读者自己在表里找）
    reading = []
    if rows:
        by_scale = max(rows, key=lambda x: x["rev_total"])
        ok = [r for r in rows if r["wm_weighted_rating"]]
        by_q = max(ok, key=lambda x: x["wm_weighted_rating"]) if ok else None
        risky = [r for r in rows if r["wm_neg_share"] is not None]
        by_r = max(risky, key=lambda x: x["wm_neg_share"]) if risky else None
        reading.append({
            "k": "scale", "zh": "需求体量最大", "en": "Largest demand mass",
            "cat": by_scale["cat"], "label_zh": by_scale["label_zh"],
            "label_en": by_scale["label_en"],
            "val": "累计 %s 条评论" % f"{by_scale['rev_total']:,}",
            "val_en": "%s cumulative ratings" % f"{by_scale['rev_total']:,}",
        })
        if by_q:
            reading.append({
                "k": "quality", "zh": "口碑最稳", "en": "Most stable sentiment",
                "cat": by_q["cat"], "label_zh": by_q["label_zh"],
                "label_en": by_q["label_en"],
                "val": "加权 %.2f 星" % by_q["wm_weighted_rating"],
                "val_en": "weighted %.2f★" % by_q["wm_weighted_rating"],
            })
        if by_r:
            reading.append({
                "k": "risk", "zh": "抱怨最集中", "en": "Most concentrated complaints",
                "cat": by_r["cat"], "label_zh": by_r["label_zh"],
                "label_en": by_r["label_en"],
                "val": "1–2 星占 %.1f%%" % by_r["wm_neg_share"],
                "val_en": "%.1f%% one- and two-star" % by_r["wm_neg_share"],
            })
    return rows, reading


def analyze(verbose: bool = True) -> dict:
    src = os.path.join(DATA_DIR, "buzz.json")
    if not os.path.exists(src):
        raise SystemExit("缺少 data/buzz.json，请先运行 fetch_buzz.py")
    raw = json.load(open(src, encoding="utf-8"))

    # 品类标签从 fetch_buzz 取，保持单一事实来源
    import fetch_buzz as FB
    cat_label = FB.CAT_LABEL

    doc = {
        "asof": raw.get("asof"), "source": raw.get("source"), "source_zh": raw.get("source_zh"),
        "captured_at": CB.CAPTURED_AT,
        "method": CB.METHOD, "notes": CB.NOTES,
        "boards": {}, "errors": raw.get("errors", []),
    }

    all_scored, star_pool = {}, {}
    for key, b in raw["boards"].items():
        items = b.get("items") or []
        # 品类一律按 patio_taxonomy 现算：落盘时的 cat 可能是旧口径，
        # 以规则为准意味着改规则后只要重跑本脚本即可，不必重新抓取。
        scored = []
        for s in score_board(items):
            s["cat"] = TX.guess_cat(s["title"])
            s["cat_label_zh"] = TX.label(s["cat"])
            s["cat_label_en"] = TX.label(s["cat"], "en")
            scored.append(s)
        st = board_stats(items)
        mix = []
        from collections import Counter
        cc = Counter(TX.guess_cat(i.get("title", "")) for i in items)
        tot = sum(cc.values()) or 1
        for k, v in cc.most_common():
            mix.append({"cat": k, "n": v, "share": round(v / tot, 4),
                        "label_zh": TX.label(k), "label_en": TX.label(k, "en")})
        top = sorted(scored, key=lambda x: -x["buzz"])[:8]
        doc["boards"][key] = {
            "label_zh": b["label_zh"], "label_en": b["label_en"], "kind": b["kind"],
            "url": b["url"], "page_title": b.get("page_title", ""),
            "stats": st, "cat_mix": mix,
            "top_buzz": top,
            "rows": sorted(scored, key=lambda x: x["rank"]),
        }
        all_scored[key] = scored
        for s in scored:
            # 只把 patio 相关品类放进跨榜候选池，按 ASIN 取最高分
            if s["cat"] in PATIO_CATS:
                cur = star_pool.get(s["asin"])
                if cur is None or s["buzz"] > cur["buzz"]:
                    star_pool[s["asin"]] = dict(s, board=key, board_zh=b["label_zh"],
                                                board_en=b["label_en"])
        if verbose:
            print(f"  ✅ {b['label_zh']:<16} {st['count']:>3} 条"
                  f"｜中位评分 {st['median_rating']}｜中位评论 {st['median_reviews']:,}"
                  f"｜Top3 占声量 {st['top3_share']*100:.0f}%")

    # 长销明星：畅销榜（kind=best）里 buzz 分最高的
    best_pool = [v for v in star_pool.values() if v["board"] != "patio_new"]
    doc["stars"] = sorted(best_pool, key=lambda x: -x["buzz"])[:20]

    # 分组 = 用户指定的 HD patio 品类（patio_taxonomy.PATIO_KEYS），每类单独出一张榜。
    # 必须分类展示：配件的评论量天然高于大件（低单价、高频、易复购），
    # 混排会把配件永久顶到最前，读者会以为「露台就是卖坐垫罩的」。
    doc["groups"] = {}
    for ck in TX.PATIO_KEYS:
        pool = [v for v in best_pool if v["cat"] == ck]
        doc["groups"][ck] = {
            "label_zh": TX.label(ck), "label_en": TX.label(ck, "en"),
            "cats": [ck],
            "items": sorted(pool, key=lambda x: -x["buzz"])[:10],
        }

    # 高口碑长销：评论数 ≥ 5000 且评分 ≥ 4.5（过市场检验且口碑好）
    proven = [v for v in best_pool if v["reviews"] >= 5000 and (v["rating"] or 0) >= 4.5]
    doc["proven"] = sorted(proven, key=lambda x: -x["reviews"])[:15]

    # 新星：新品榜
    newpool = [v for v in star_pool.values() if v["board"] == "patio_new"]
    doc["newcomers"] = sorted(newpool, key=lambda x: -x["buzz"])[:15]

    # 声量王：纯按评论数（客观事实排序，不做加权）
    doc["most_reviewed"] = sorted(best_pool, key=lambda x: -x["reviews"])[:15]

    # 全品类汇总（跨所有榜单）
    from collections import Counter
    cc, tot = Counter(), 0
    cat_reviews = Counter()
    for key, scored in all_scored.items():
        for s in scored:
            cc[s["cat"]] += 1
            cat_reviews[s["cat"]] += s["reviews"]
            tot += 1
    mix = []
    for k, v in sorted(cc.items(), key=lambda x: TX.order_of(x[0])):
        mix.append({"cat": k, "n": v, "share": round(v / tot, 4),
                    "label_zh": TX.label(k), "label_en": TX.label(k, "en"),
                    "reviews": cat_reviews[k]})
    doc["categories"] = mix

    # 三渠道公开数据
    doc["channels"] = CB.CHANNELS
    doc["hd_items"] = [dict(x, src_name=CB.HD_SRC[x["src"]]["name"],
                            src_url=CB.HD_SRC[x["src"]]["url"],
                            src_tier=CB.HD_SRC[x["src"]]["tier"],
                            src_tier_zh=_TIER_ZH[CB.HD_SRC[x["src"]]["tier"]])
                       for x in CB.HD_ITEMS]
    doc["low_items"] = [dict(x, src_name=CB.LOW_SRC[x["src"]]["name"],
                             src_url=CB.LOW_SRC[x["src"]]["url"],
                             src_tier=CB.LOW_SRC[x["src"]]["tier"],
                             src_tier_zh=_TIER_ZH[CB.LOW_SRC[x["src"]]["tier"]])
                        for x in CB.LOW_ITEMS]
    doc["sources"] = {
        "hd": [dict(v, key=k) for k, v in CB.HD_SRC.items()],
        "low": [dict(v, key=k) for k, v in CB.LOW_SRC.items()],
    }

    # ------------------------------------------------------------ 双渠道对比
    amz_rows = []
    for key, scored in all_scored.items():
        for s in scored:
            amz_rows.append({
                "id": s["asin"], "title": s["title"], "short": s["short"],
                "rating": s["rating"], "reviews": s["reviews"], "price": s["price"],
                "image": "", "url": s["url"], "cat": s["cat"], "channel": "Amazon",
                "page": key, "v": s["v"], "q": s["q"], "m": s["m"], "buzz": s["buzz"],
                "cat_label_zh": TX.label(s["cat"]), "cat_label_en": TX.label(s["cat"], "en"),
            })

    wm_rows, wm_pages, wm_meta = [], {}, {}
    wm_path = os.path.join(DATA_DIR, "walmart.json")
    if os.path.exists(wm_path):
        raw_wm = json.load(open(wm_path, encoding="utf-8"))
        wm_meta = {"source": raw_wm.get("source"), "captured_at": raw_wm.get("captured_at"),
                   "listed_at": raw_wm.get("listed_at"),
                   "errors": raw_wm.get("errors", [])}
        by_page = {}
        for it in raw_wm.get("items") or []:
            by_page.setdefault(it.get("page", ""), []).append({
                "id": it.get("id", ""), "title": it.get("title", ""),
                "short": _short(it.get("title", "")), "brand": it.get("brand", ""),
                "rating": it.get("rating"), "reviews": it.get("reviews") or 0,
                "price": it.get("price"), "image": it.get("image", ""),
                "url": it.get("url", ""), "channel": "Walmart",
                "cat": TX.guess_cat(it.get("title", "")),
            })
        for pk, rows in by_page.items():
            meta = raw_wm.get("pages", {}).get(pk) or {}
            scored = score_walmart_page(rows)
            cc = Counter(r["cat"] for r in rows)
            wm_pages[pk] = {
                "label_zh": meta.get("label_zh", pk), "label_en": meta.get("label_en", pk),
                "url": meta.get("url", ""), "title": meta.get("title", ""),
                "raw_count": meta.get("count", len(rows)),
                "stats": _cat_stats(rows),
                "cat_mix": [{"cat": k, "n": v, "share": round(v / max(len(rows), 1), 4),
                             "label_zh": TX.label(k), "label_en": TX.label(k, "en")}
                            for k, v in sorted(cc.items(), key=lambda x: TX.order_of(x[0]))],
                "top_buzz": sorted(scored, key=lambda x: -x["buzz"])[:8],
                "rows": scored,
            }
            wm_rows.extend(scored)
    else:
        wm_meta = {"errors": [{"page": "-", "error": "缺少 data/walmart.json，请先运行 fetch_walmart.py"}]}

    doc["walmart"] = dict(wm_meta, pages=wm_pages, total=len(wm_rows))
    doc["channel_summary"] = build_channel_summary(amz_rows, wm_rows)
    doc["category_compare"] = build_channel_compare(amz_rows, wm_rows)

    # ------------------------------------------------- 明星产品配图（Walmart 图 CDN）
    star_img = {}
    si_path = os.path.join(DATA_DIR, "star_images.json")
    if os.path.exists(si_path):
        try:
            si = json.load(open(si_path, encoding="utf-8"))
            star_img = si.get("items") or {}
            doc["star_images_meta"] = {
                "source": si.get("source"), "source_zh": si.get("source_zh"),
                "captured_at": si.get("captured_at"), "note": si.get("note"),
                "size": si.get("size"), "count": len(star_img),
            }
        except Exception as e:
            doc["star_images_meta"] = {"error": str(e)}
    doc["star_images"] = star_img

    # ------------------------------------------------- 跨渠道品类冠军
    doc["stars_cross"] = build_stars_cross(best_pool, wm_rows)

    # ------------------------------------------------- 差评归纳（Walmart 评论）
    rv_path = os.path.join(DATA_DIR, "walmart_reviews.json")
    wm_cat_stats = []
    if os.path.exists(rv_path):
        try:
            rv = json.load(open(rv_path, encoding="utf-8"))
            wm_cat_stats = rv.get("cat_stats") or []
            doc["reviews"] = {
                "source": rv.get("source"), "captured_at": rv.get("captured_at"),
                "note": rv.get("note"),
                "n_products": len(rv.get("products") or []),
                "n_negative": sum(len(p.get("neg_samples") or [])
                                  for p in (rv.get("products") or [])),
                "themes": rv.get("themes") or [],
                "by_cat": rv.get("by_cat") or {},
                "cat_stats": wm_cat_stats,
                # 每个抽样商品的口碑卡片（含星级分布，不含差评正文，避免体积膨胀）
                "products": [{k: v for k, v in p.items() if k != "neg_samples"}
                             for p in (rv.get("products") or [])],
                "errors": rv.get("errors") or [],
            }
        except Exception as e:
            doc["reviews"] = {"error": str(e)}
    else:
        doc["reviews"] = {"error": "缺少 data/walmart_reviews.json，请先运行 fetch_walmart_reviews.py"}

    doc["cat_ladder"], doc["cat_ladder_reading"] = build_cat_ladder(
        amz_rows, wm_rows, wm_cat_stats)

    out = os.path.join(DATA_DIR, "buzz_analysis.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    if verbose:
        print(f"  明星 {len(doc['stars'])} / 高口碑长销 {len(doc['proven'])} / "
              f"新星 {len(doc['newcomers'])} / 渠道 {len(doc['channels'])}"
              f" / Walmart {doc['walmart'].get('total', 0)} 件 → {out}")
        if doc["stars"]:
            print("\n  ── 各品类 Top 3（Amazon）──")
            for gk in TX.PATIO_KEYS:
                g = doc["groups"].get(gk) or {}
                items = g.get("items") or []
                print(f"  【{g.get('label_zh', gk)}】{len(items)} 条")
                for s in items[:3]:
                    print(f"    {s['buzz']:.3f}  {s['rating']}★ {s['reviews']:>7,} 条"
                          f"  {s['short'][:48]}")
        if doc["category_compare"]:
            print("\n  ── 渠道 × 品类（件数 / 中位评论）──")
            for row in doc["category_compare"]:
                a, w = row["amazon"], row["walmart"]
                print(f"  {row['label_zh']:<7} Amazon {a['n']:>3} 件 /"
                      f" {str(a['median_reviews'] or '-'):>7} ｜"
                      f" Walmart {w['n']:>3} 件 / {str(w['median_reviews'] or '-'):>7}")
        rvs = doc.get("reviews") or {}
        if rvs.get("themes"):
            print(f"\n  ── 差评归纳（{rvs.get('n_products')} 款商品 /"
                  f" {rvs.get('n_negative')} 条差评）──")
            for t in rvs["themes"][:6]:
                print(f"    {t['zh']:<14} 命中 {t['negative']:>3} ｜ 覆盖 {t['products']:>2} 款")
        if doc.get("cat_ladder"):
            print("\n  ── 品类档次阶梯 ──")
            for r in doc["cat_ladder"]:
                print(f"  #{r['rank']} {r['label_zh']:<7} 定位 {r['positioning']:+.3f}"
                      f" ｜ WM {r['n_wm']:>3} 件 ｜ 加权星 {r['wm_weighted_rating']}"
                      f" ｜ 差评率 {r['wm_neg_share']}% ｜ {r['tier']}")
    return out


_TIER_ZH = {"index": "搜索索引快照（零售商页面原文）",
            "media_cited": "媒体引用零售商网站",
            "brand_site": "品牌官方站点"}


if __name__ == "__main__":
    analyze()
