#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 hd-watch/data/ 下的原始数据压缩成小程序可直接 require 的数据文件。

为什么数据要内置、而不是让小程序去请求接口：
    微信要求小程序 request 的域名必须在小程序后台配置为「request 合法域名」，
    且该域名需完成 ICP 备案 + 通过文件校验（证明域名归属）。
    WorkBuddy 发布的在线看板域名不属于本用户，无法完成校验，因此走不通。
    结论：数据随包发布，每周由 build_miniprogram.py 重新生成 → 用户点一次发布。
    纯数据文件只有几十 KB，远低于小程序主包 2MB 上限。

用法：
    cd hd-watch/scripts && python build_miniprogram.py
产物：
    miniprogram/data/mini.js
"""

import json
import os
import re
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT_DIR = os.path.join(ROOT, "miniprogram", "data")
OUT = os.path.join(OUT_DIR, "mini.js")

LIMITS = {
    "stars": 15,
    "group_items": 10,
    "newcomers": 10,
    "news": 20,
    "filings": 8,
    "spark": 120,
}


def load(name, default=None):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return default if default is not None else {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# ---------- 格式化小工具（生成期就格式化好，小程序端只负责显示） ----------

def money_big(v):
    """281,196,508,672 -> $281.2B"""
    if v is None:
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    for unit, div in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(v) >= div:
            n = v / div
            return "$%.1f%s" % (n, unit) if abs(n) < 100 else "$%d%s" % (round(n), unit)
    return "$%.0f" % v


def pct(v, digits=1, sign=True):
    if v is None:
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    fmt = "%+." + str(digits) + "f%%" if sign else "%." + str(digits) + "f%%"
    return fmt % v


def num(v, digits=1):
    if v is None:
        return None
    try:
        return ("%." + str(digits) + "f") % float(v)
    except (TypeError, ValueError):
        return None


def num_plain(v):
    """整数带千分位"""
    if v is None:
        return None
    try:
        return "{:,}".format(int(round(float(v))))
    except (TypeError, ValueError):
        return None


def compact(v):
    """56344 -> 5.6万（中文）/ 56.3k（英文）—— 这里统一给中文口径，页面再决定"""
    if v is None:
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    if v >= 10000:
        return "%.1f万" % (v / 10000.0)
    if v >= 1000:
        return "{:,}".format(int(round(v)))
    return str(int(round(v)))


def pdate(s):
    """Sat, 03 Oct 2026 12:00:00 +0000 -> 10-03"""
    if not s:
        return None
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    m = re.search(r"(\d{1,2})\s+([A-Z][a-z]{2})\s+(\d{4})", s)
    if m:
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        try:
            return "%s-%02d-%02d" % (m.group(3), months.index(m.group(2)) + 1, int(m.group(1)))
        except ValueError:
            return None
    return s[:10]


def good_url(u):
    """过滤掉畸形的 IR 链接（形如 https:/~/media/... 缺域名）"""
    if not u or not isinstance(u, str):
        return False
    if not u.startswith("http"):
        return False
    if re.match(r"^https?:\s*/\s*~", u):   # https:/~/media/...
        return False
    return "://" in u and len(u.split("://", 1)[1]) > 4


# ---------- 各部分抽取 ----------

def pick_quote(q):
    p = (q.get("price") or {}).get(q.get("ticker") or "HD") or {}
    if not p:
        # 兜底：price 本身就是那条记录
        p = q.get("price") or {}
    f = q.get("fundamentals") or {}
    close = p.get("close") or []
    n = LIMITS["spark"]
    spark = [round(float(x), 2) for x in close[-n:] if x is not None]
    up = f.get("upside_pct")
    return {
        "last": num(p.get("last"), 2),
        "date": p.get("last_date"),
        "chg": {
            "w": num(p.get("chg_1w"), 2),
            "m": num(p.get("chg_1m"), 2),
            "q": num(p.get("chg_3m"), 2),
            "h": num(p.get("chg_6m"), 2),
            "y": num(p.get("chg_1y"), 2),
        },
        "hi52": num(p.get("hi52"), 2),
        "lo52": num(p.get("lo52"), 2),
        "from_hi": num(p.get("from_hi52"), 2),
        "from_lo": num(p.get("from_lo52"), 2),
        "ma": {
            "ma20": num(p.get("ma20"), 2), "vs20": num(p.get("vs_ma20"), 2),
            "ma60": num(p.get("ma60"), 2), "vs60": num(p.get("vs_ma60"), 2),
            "ma200": num(p.get("ma200"), 2), "vs200": num(p.get("vs_ma200"), 2),
        },
        "vol": num(p.get("vol_60d"), 1),
        "mdd": num(p.get("mdd_1y"), 1),
        "spark": spark,
        "spark_n": len(spark),
    }


def pick_fund(f):
    return {
        "cap": money_big(f.get("market_cap")),
        "pe": num(f.get("trailing_pe"), 1),
        "fpe": num(f.get("forward_pe"), 1),
        "dy": num(f.get("dividend_yield"), 2),
        "payout": pct((f.get("payout_ratio") or 0) * 100, 0, sign=False) if f.get("payout_ratio") is not None else None,
        "rev": money_big(f.get("revenue_ttm")),
        "revg": pct((f.get("revenue_growth") or 0) * 100, 1) if f.get("revenue_growth") is not None else None,
        "gm": pct((f.get("gross_margins") or 0) * 100, 1, sign=False) if f.get("gross_margins") is not None else None,
        "om": pct((f.get("operating_margins") or 0) * 100, 1, sign=False) if f.get("operating_margins") is not None else None,
        "pm": pct((f.get("profit_margins") or 0) * 100, 1, sign=False) if f.get("profit_margins") is not None else None,
        "roe": pct((f.get("roe") or 0) * 100, 0, sign=False) if f.get("roe") is not None else None,
        "fcf": money_big(f.get("free_cashflow")),
        "debt": money_big(f.get("total_debt")),
        "cash": money_big(f.get("total_cash")),
        "tgt": num(f.get("target_mean"), 0),
        "tgt_h": num(f.get("target_high"), 0),
        "tgt_l": num(f.get("target_low"), 0),
        "an": f.get("analyst_count"),
        "beta": num(f.get("beta"), 2),
        "upside": num(f.get("upside_pct"), 1),
    }


BENCH_NAME = {
    "SPY": ("标普 500 ETF", "大盘"),
    "LOW": ("Lowe's（LOW）", "直接竞品"),
    "XRT": ("标普零售 ETF（XRT）", "行业"),
    "RTH": ("零售指数（RTH）", "行业"),
}


def pick_bench(q):
    out = []
    hd = (q.get("price") or {}).get("HD") or {}
    bench = q.get("bench") or {}
    order = ["LOW", "SPY", "XRT", "RTH"]
    keys = [k for k in order if k in bench] + [k for k in bench if k not in order]
    for k in keys:
        b = bench.get(k)
        if not isinstance(b, dict):
            continue
        nm, tag = BENCH_NAME.get(k, (k, "对照"))
        out.append({
            "key": k,
            "name": nm,
            "tag": tag,
            "last": num(b.get("last"), 2),
            "chg": {
                "w": num(b.get("chg_1w"), 2),
                "m": num(b.get("chg_1m"), 2),
                "y": num(b.get("chg_1y"), 2),
            },
            "from_hi": num(b.get("from_hi52"), 1),
        })
    # HD 自己也放进来做对比行
    if hd:
        out.insert(0, {
            "key": "HD", "name": "Home Depot（HD）", "tag": "本标的",
            "last": num(hd.get("last"), 2),
            "chg": {"w": num(hd.get("chg_1w"), 2), "m": num(hd.get("chg_1m"), 2), "y": num(hd.get("chg_1y"), 2)},
            "from_hi": num(hd.get("from_hi52"), 1),
        })
    return out


def pick_news(n):
    out = []
    for it in (n.get("items") or [])[: LIMITS["news"]]:
        t = (it.get("title") or "").strip()
        if not t:
            continue
        out.append({
            "t": t,
            "src": it.get("publisher") or "",
            "d": pdate(it.get("published")),
            "u": it.get("url") or "",
        })
    return out


def pick_filings(fl):
    out = []
    for it in (fl.get("items") or [])[: LIMITS["filings"]]:
        out.append({
            "form": it.get("form"),
            "filed": it.get("filed"),
            "period": it.get("period"),
            "u": it.get("url") if good_url(it.get("url")) else "",
        })
    return out


def pick_ir(ir):
    """按季度输出财报材料，带时间 / 发布方 / 主要标题。

    ⚠️ 时间与标题是下载财报 PDF 后从首页正文解析出来的（新闻稿电头、电话会
    EVENT DATE/TIME），早期只输出 kind + quarter，多个季度无法分辨 —— 用户反馈过。
    """
    pub = ir.get("publisher") or "The Home Depot, Inc."
    pub_zh = ir.get("publisher_zh") or "家得宝公司（IR 官方）"
    out = []
    for q in (ir.get("quarters") or []):
        items = []
        for it in (q.get("items") or []):
            u = it.get("url")
            if not good_url(u):
                continue
            items.append({
                "kind": it.get("kind_zh") or it.get("kind") or "",
                "kz": it.get("kind_en") or "",
                "u": u,
                "t": it.get("title") or "",
                "d": it.get("date") or "",
            })
        if not items:
            continue
        out.append({
            "q": q.get("label") or "",
            "d": q.get("date") or "",
            "wd": q.get("weekday") or "",
            "call": q.get("call_time_et") or "",
            "head": q.get("headline") or "",
            "pub": pub,
            "pub_zh": pub_zh,
            "items": items,
        })
    if out:
        return out
    # 兼容兜底：旧结构
    legacy = []
    for it in (ir.get("pdfs") or []):
        u = it.get("url")
        if not good_url(u):
            continue
        legacy.append({
            "q": it.get("quarter") or "", "d": it.get("date") or "",
            "wd": it.get("weekday") or "", "call": "",
            "head": it.get("headline") or "", "pub": pub, "pub_zh": pub_zh,
            "items": [{"kind": it.get("kind") or "", "kz": "", "u": u,
                       "t": it.get("title") or "", "d": it.get("date") or ""}],
        })
    return legacy[:6]


def pick_patio_items(seq, n):
    out = []
    for i, it in enumerate((seq or [])[:n], 1):
        out.append({
            "rk": i,
            "asin": it.get("asin") or "",
            "t": it.get("short") or it.get("title") or "",
            "brand": (it.get("brand") or "").strip(),
            "rating": num(it.get("rating"), 1),
            "reviews": compact(it.get("reviews")),
            "reviews_n": it.get("reviews"),
            "price": ("$%g" % it["price"]) if it.get("price") is not None else None,
            "cat": it.get("cat_label_zh") or "",
            "buzz": num(it.get("buzz"), 3),
            "v": num(it.get("v"), 3),
            "q": num(it.get("q"), 3),
            "m": num(it.get("m"), 3),
            "board": it.get("board_zh") or "",
            "u": it.get("url") or "",
        })
    return out


def pick_patio(bz):
    m = bz.get("method") or {}
    w = m.get("weights") or {}
    groups = []
    # ⚠️ 分组名与顺序一律跟着 patio_taxonomy 走（analyze_buzz 已按 PATIO_KEYS 建表）。
    # 早期这里写死了 ("furniture","equipment","accessory") 三个旧键，品类口径重构后
    # 一个都命中不了，整块直接渲染为空。
    gsrc = bz.get("groups") or {}
    for key, g in gsrc.items():
        items = pick_patio_items(g.get("items"), LIMITS["group_items"])
        if not items:
            continue
        groups.append({
            "key": key, "name": g.get("label_zh") or key,
            "desc": g.get("label_en") or "",
            "cats": "·".join(g.get("cats") or []),
            "items": items,
        })

    notes = bz.get("notes") or {}
    return {
        "method": {
            "w_v": int(round((w.get("volume") or 0.45) * 100)),
            "w_q": int(round((w.get("valence") or 0.30) * 100)),
            "w_m": int(round((w.get("momentum") or 0.25) * 100)),
            "formula": m.get("formula_zh") or "",
            "limits": [x for x in (m.get("limits_zh") or []) if x],
        },
        "groups": groups,
        "stars": pick_patio_items(bz.get("stars"), LIMITS["stars"]),
        "newcomers": pick_patio_items(bz.get("newcomers"), LIMITS["newcomers"]),
        "notes": [
            {"t": "总榜头部为什么全是杀虫剂", "b": notes.get("consumable_zh") or ""},
            {"t": "「户外家具」节点的口径", "b": notes.get("category_zh") or ""},
        ],
        "cats": [
            {
                "n": c.get("n"), "share": num((c.get("share") or 0) * 100, 1, ),
                "label": c.get("label_zh"), "reviews": compact(c.get("reviews")),
            }
            for c in (bz.get("categories") or [])[:8]
        ],
    }


def strip_md(s):
    """去掉 `**加粗**` 标记 —— WXML 的 <text> 渲染不了行内标签，
    留着只会让用户看到字面星号。"""
    return re.sub(r"\*\*(.+?)\*\*", r"\1", s) if isinstance(s, str) else s


def strip_md_deep(o):
    if isinstance(o, dict):
        return {k: strip_md_deep(v) for k, v in o.items()}
    if isinstance(o, list):
        return [strip_md_deep(v) for v in o]
    return strip_md(o)


def pick_cats(bz):
    """「品类对标」tab 的数据：档次阶梯 / 渠道供给对照 / 品类冠军(带图) / 差评归纳。"""
    imgs = bz.get("star_images") or {}

    def img_for(pid, cat):
        v = imgs.get(str(pid)) or {}
        if not v.get("mp") and cat:
            cands = [x for x in imgs.values() if x.get("cat") == cat and x.get("mp")]
            if cands:
                v = max(cands, key=lambda x: x.get("star_score") or 0)
        return v.get("mp") or ""

    ladder = []
    for r in (bz.get("cat_ladder") or []):
        ladder.append({
            "rk": r.get("rank"),
            "cat": r.get("label_zh") or "",
            "cat_en": r.get("label_en") or "",
            "pos": ("%+.3f" % (r.get("positioning") or 0)),
            "posv": r.get("positioning") or 0,
            "wm": r.get("n_wm"),
            "amz": r.get("n_amz"),
            "rev": compact(r.get("rev_total")),
            "wrat": ("%.2f" % r["wm_weighted_rating"]) if r.get("wm_weighted_rating") is not None else "—",
            "neg": ("%.1f%%" % r["wm_neg_share"]) if r.get("wm_neg_share") is not None else "—",
            "tier": r.get("tier") or "",
            "risk": r.get("risk") or "",
            "confidence": r.get("confidence") or "",
            "themes": "、".join(t.get("zh", "") for t in (r.get("top_themes") or [])[:2]) or "—",
        })

    reading = [{
        "zh": x.get("zh") or "", "cat": x.get("label_zh") or "", "val": x.get("val") or "",
    } for x in (bz.get("cat_ladder_reading") or [])]

    cmp_ = []
    for r in (bz.get("category_compare") or []):
        a, w = r.get("amazon") or {}, r.get("walmart") or {}
        an, wn = a.get("n") or 0, w.get("n") or 0
        tot = max(an, wn, 1)
        cmp_.append({
            "cat": r.get("label_zh") or "",
            "an": an, "wn": wn,
            "amz_w": max(1, round(100.0 * an / tot)),
            "wm_w": max(1, round(100.0 * wn / tot)),
            "amz_mr": compact(a.get("median_reviews")),
            "wm_mr": compact(w.get("median_reviews")),
            "amz_rt": ("%.1f" % a["median_rating"]) if a.get("median_rating") else "—",
            "wm_rt": ("%.1f" % w["median_rating"]) if w.get("median_rating") else "—",
        })

    champs = []
    for r in (bz.get("stars_cross") or []):
        row = {"cat": r.get("label_zh") or "", "cat_en": r.get("label_en") or "", "ch": []}
        for key, nm in (("amazon", "Amazon"), ("walmart", "Walmart")):
            it = r.get(key)
            if not it:
                row["ch"].append({"ch": nm, "t": "", "img": "", "meta": ""})
                continue
            pid = it.get("id") or it.get("asin") or ""
            row["ch"].append({
                "ch": nm,
                "t": it.get("short") or it.get("title") or "",
                "img": img_for(pid, (r.get("cat") or "") if key == "walmart" else ""),
                "meta": "%s★ · %s 条" % (num(it.get("rating"), 1) or "—",
                                          compact(it.get("reviews"))),
                "u": it.get("url") or "",
            })
        champs.append(row)

    rv = bz.get("reviews") or {}
    themes = []
    mx = max([t.get("negative") or 0 for t in (rv.get("themes") or [])] or [1]) or 1
    for t in (rv.get("themes") or [])[:10]:
        themes.append({
            "t": t.get("zh") or "", "t_en": t.get("en") or "",
            "n": t.get("negative") or 0,
            "p": t.get("products") or 0,
            "w": max(2, round(100.0 * (t.get("negative") or 0) / mx)),
            "q": (t.get("quote") or "")[:200],
        })

    bycat = rv.get("by_cat") or {}
    tops = [t["key"] for t in (rv.get("themes") or [])[:6]]
    meta = {t["key"]: t for t in (rv.get("themes") or [])}
    order = [r.get("cat") for r in (bz.get("cat_ladder") or [])]
    keys = [k for k in order if k in bycat]
    matrix = {
        "cols": [meta[k]["zh"] for k in tops],
        "rows": [],
    }
    for ck in keys:
        blk = bycat[ck]
        d = {x["key"]: x["negative"] for x in (blk.get("themes") or [])}
        mxrow = max(d.values()) if d else 1
        cells = []
        for k in tops:
            v = d.get(k, 0)
            cells.append({
                # i 只给 wx:key 用 —— v 在同一行里会重复（多个痛点都是 0 或同一个数），
                # 拿 v 当 key 会让微信报 duplicate key 警告。
                "i": len(cells),
                "v": v,
                "lvl": 0 if not v else min(4, 1 + int(3.0 * v / max(mxrow, 1))),
            })
        matrix["rows"].append({
            "cat": blk.get("label_zh") or ck,
            "total": blk.get("total") or 0,
            "cells": cells,
        })

    return {
        "ladder": ladder,
        "reading": reading,
        "cmp": cmp_,
        "champs": champs,
        "themes": themes,
        "matrix": matrix,
        "n_products": rv.get("n_products") or 0,
        "n_negative": rv.get("n_negative") or 0,
        "note": ("档次对标：需求体量与口碑取自 Walmart 一手品类页与 Amazon 畅销榜；"
                 "差评主题取自 Walmart「最低分优先」评论页。定位分是这 7 类之间的相对排名，"
                 "不是绝对好坏；梯队只按排名分档，抱怨压力单独看。图片为 Walmart 公开商品图。"),
    }


def pick_channels(bz):
    """只返回能站内直抓的渠道；excluded=True 的三家只留名字，供页面写口径说明。

    返回 (live, dropped)。2026-10-15 口径收敛：Home Depot / Lowe's / Costco 已整体
    移出对标（站内不可直抓，并列进来会伪造可比性），配置仍保留在 config_buzz.CHANNELS。
    """
    live, dropped = [], []
    for c in (bz.get("channels") or []):
        if c.get("excluded"):
            dropped.append(c.get("name_zh") or c.get("name_en") or "")
            continue
        live.append({
            "key": c.get("key"),
            "name": c.get("name_zh"),
            "tier": c.get("data_tier_zh"),
            "strength": c.get("strength_zh"),
            "brand": c.get("brand_zh"),
            "access": c.get("access_zh"),
            "src": c.get("src"),
        })
    return live, dropped


def pick_brief(q, bz, ir):
    """首页概览要点（bullet 列表）。

    设计原则与看板 §一 的 highlights 一致：**每条都能追溯到某个 tab**，
    不做没有数据支撑的判断句。这里只出 6 条短句 —— 手机上一屏能扫完，
    详细展开留给对应的 tab。
    """
    out = []
    p = (q.get("price") or {}).get(q.get("ticker") or "HD") or q.get("price") or {}
    if not isinstance(p, dict):
        p = {}
    f = q.get("fundamentals") or {}

    # 1) 价格与位置
    if p.get("last") is not None:
        bits = ["股价 $%s（%s）" % (num(p.get("last"), 2), p.get("last_date") or "—")]
        if p.get("chg_1w") is not None:
            bits.append("本周 %s" % pct(p.get("chg_1w"), 2))
        if p.get("chg_1m") is not None:
            bits.append("近一月 %s" % pct(p.get("chg_1m"), 2))
        if p.get("from_hi52") is not None:
            bits.append("距 52 周高 %s" % pct(p.get("from_hi52"), 1))
        out.append("；".join(bits))

    # 2) 最近一期财报
    q2 = None
    try:
        import config as _C
        q2 = (_C.FINANCIALS.get("quarters") or [None])[0]
    except Exception:  # noqa: BLE001
        q2 = None
    if q2 and q2.get("net_sales_yoy") is not None:
        line = ("最近一期 %s 净销售 $%.1fB（同比 %s），同店 %s、美国同店 %s"
                % (q2.get("label") or "—", (q2.get("net_sales") or 0) / 1000.0,
                   pct(q2.get("net_sales_yoy"), 1), pct(q2.get("comps"), 1),
                   pct(q2.get("comps_us"), 1)))
        # 增长质量：是客流还是客单价在驱动 —— 与看板 §一 第二条对应
        if q2.get("transactions_yoy") is not None:
            line += ("；增长由客单价驱动 —— 交易量同比 %s，平均客单价 $%s（同比 %s）"
                     % (pct(q2.get("transactions_yoy"), 1), q2.get("avg_ticket"),
                        pct(q2.get("avg_ticket_yoy"), 1)))
        out.append(line)

    # 3) 估值
    if f.get("trailing_pe") and f.get("target_mean"):
        out.append(
            "估值：滚动 PE %.1f 倍，一致目标价 $%.2f（对现价 %s），%s 位分析师覆盖"
            % (f["trailing_pe"], f["target_mean"], pct(f.get("upside_pct"), 1),
               f.get("analyst_count") or "—"))

    # 4) 品类档次第一位
    lad = bz.get("cat_ladder") or []
    if lad:
        t = lad[0]
        # ⚠️ positioning 是三个 z 分加权后的**标准化得分**（量纲已消掉），
        # 不是百分比 —— 早期写成 pct(positioning*100) 会渲染成「+128%」，属误导。
        out.append(
            "Patio 档次第一位「%s」：定位分 %+.3f，Amazon %d 件 / Walmart %d 件，加权星级 %s"
            % (t.get("label_zh"), t.get("positioning") or 0, t.get("n_amz") or 0,
               t.get("n_wm") or 0, num(t.get("wm_weighted_rating"), 2) or "—"))

    # 5) 渠道供给反差（成套家具：Amazon 0 件 vs Walmart 多件）
    big = None
    for r in (bz.get("category_compare") or []):
        if ((r.get("amazon") or {}).get("n") or 0) == 0 and ((r.get("walmart") or {}).get("n") or 0) > 10:
            big = r
            break
    if big:
        out.append(
            "渠道反差：%s在 Amazon 榜单 0 件、Walmart 有 %d 件 —— 大件家具几乎不上亚马逊榜，正是 Home Depot 的主场"
            % (big.get("label_zh"), big["walmart"].get("n") or 0))

    # 6) 负评第一主题
    ths = ((bz.get("reviews") or {}).get("themes") or [])
    if ths:
        t = ths[0]
        out.append(
            "差评第一主题「%s」：命中 %d 条、覆盖 %d 款商品（共 %d 款 / %d 条差评样本）"
            % (t.get("zh"), t.get("negative") or t.get("hits") or 0,
               t.get("products") or 0,
               (bz.get("reviews") or {}).get("n_products") or 0,
               (bz.get("reviews") or {}).get("n_negative") or 0))

    # 7) 数据边界（一句话说清渠道口径）
    drop = [c.get("name_zh") for c in (bz.get("channels") or []) if c.get("excluded")]
    if drop:
        out.append(
            "渠道口径：只对标 Amazon 与 Walmart 两家站内一手直抓渠道；"
            "%s 站内不可直抓，已整体移出对比" % "、".join(drop))

    return out


def week_label():
    now = datetime.now()
    iso = now.isocalendar()
    return "%d-W%02d" % (iso[0], iso[1])


def main():
    q = load("quote.json", {})
    bz = load("buzz_analysis.json", {})
    news = load("news.json", {})
    filings = load("filings.json", {})
    ir = load("ir.json", {})

    chans, chans_drop = pick_channels(bz)

    mini = {
        "meta": {
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "week": week_label(),
            "quote_asof": q.get("asof"),
            "quote_date": (q.get("price") or {}).get("last_date"),
            "buzz_asof": bz.get("asof"),
            "ticker": q.get("ticker") or "HD",
            "company": (filings.get("name") or "HOME DEPOT, INC.").title(),
            "sic": filings.get("sic") or "",
            "fy_end": filings.get("fiscal_year_end") or "0131",
            "boards_n": len(bz.get("boards") or {}),
            "items_n": sum(len((v or {}).get("rows") or (v or {}).get("items") or [])
                           for v in (bz.get("boards") or {}).values()),
        },
        "quote": pick_quote(q),
        "brief": pick_brief(q, bz, ir),
        "fund": pick_fund(q.get("fundamentals") or {}),
        "bench": pick_bench(q),
        "news": pick_news(news),
        "filings": pick_filings(filings),
        "ir": pick_ir(ir),
        "patio": pick_patio(bz),
        "cats": pick_cats(bz),
        "channels": chans,
        "channels_excluded": chans_drop,
        "disclaimer": "本内容基于公开数据与量化分析，仅供参考，不构成投资建议。市场有风险，投资需谨慎。",
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    mini = strip_md_deep(mini)
    body = json.dumps(mini, ensure_ascii=False, separators=(",", ":"), indent=None)
    # 极小概率出现段落/行分隔符，会破坏 JS 解析
    body = body.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    js = (
        "// 自动生成，请勿手改 —— 由 scripts/build_miniprogram.py 产出\n"
        "// 数据周期：%s\n"
        "module.exports = %s\n" % (week_label(), body)
    )
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(js)

    ir_all = ir.get("pdfs") or []
    ir_bad = [p for p in ir_all if not good_url(p.get("url"))]

    kb = os.path.getsize(OUT) / 1024.0
    print("写出 %s（%.1f KB）" % (OUT, kb))
    print("  周期 %s | 行情 %s（%s）" % (mini["meta"]["week"], mini["quote"]["last"], mini["quote"]["date"]))
    print("  概览要点 %d 条" % len(mini["brief"]))
    print("  新闻 %d 条 / 表单 %d 条 / 明星榜 %d 条 / 分组 %d 层 / 对标渠道 %d 家（移出 %d 家）"
          % (len(mini["news"]), len(mini["filings"]), len(mini["patio"]["stars"]),
             len(mini["patio"]["groups"]), len(chans), len(chans_drop)))
    print("  IR 材料 %d 组（源数据 %d 条链接，拦截畸形链接 %d 条）"
          % (len(mini["ir"]), len(ir_all), len(ir_bad)))
    cc = mini["cats"]
    n_img = sum(1 for r in cc["champs"] for c in r["ch"] if c["img"])
    print("  品类对标：档次 %d 行 / 渠道对照 %d 行 / 冠军 %d 组（含图 %d 张）/ 差评主题 %d 条"
          % (len(cc["ladder"]), len(cc["cmp"]), len(cc["champs"]), n_img, len(cc["themes"])))
    # Amazon 侧设计上就无图（商品主图三路皆被封），只有 Walmart 槽位缺图才算异常
    miss_wm = [r["cat"] for r in cc["champs"]
               for c in r["ch"] if c["ch"] == "Walmart" and not c["img"]]
    if miss_wm:
        print("    ⚠️ Walmart 侧缺图：%s" % "、".join(miss_wm))
    if ir_bad:
        for p in ir_bad:
            print("    ! 畸形：%s" % p.get("url"))


if __name__ == "__main__":
    main()
