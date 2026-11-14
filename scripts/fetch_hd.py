# -*- coding: utf-8 -*-
"""
HD 动态数据抓取：行情与波动指标 / SEC 监管文件 / 投资者关系财报 PDF / 新闻

三条通道互相独立，任一失败不影响其他，失败会写进 `errors` 字段并由看板展示，
绝不会用占位数字填充。
"""
import os
import re
import json
import urllib.request
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd
import yfinance as yf

import config as C

UA = "Mozilla/5.0"   # 本机网络环境限制：请求头只能带 User-Agent


# ---------------------------------------------------------------- 工具
def now_cn() -> str:
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")


def save(name: str, obj) -> str:
    os.makedirs(C.DATA_DIR, exist_ok=True)
    p = os.path.join(C.DATA_DIR, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return p


def _get(url: str, timeout: int = 40) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def _f(x):
    """转 float，NaN/None → None"""
    try:
        v = float(x)
        return None if (v != v or v in (float("inf"), float("-inf"))) else v
    except (TypeError, ValueError):
        return None


def _pct(a, b):
    if _f(a) is None or _f(b) in (None, 0):
        return None
    return round((a / b - 1.0) * 100.0, 2)


# ---------------------------------------------------------------- 行情
def _series_metrics(close: pd.Series, tag: str) -> dict:
    c = close.dropna()
    n = len(c)
    if n < 30:
        return {"key": tag, "error": "样本不足"}
    last = _f(c.iloc[-1])
    m = {
        "key": tag,
        "last": round(last, 2),
        "last_date": str(c.index[-1])[:10],
        "bars": n,
        "chg_1w": _pct(last, _f(c.iloc[-6])) if n > 6 else None,
        "chg_1m": _pct(last, _f(c.iloc[-22])) if n > 22 else None,
        "chg_3m": _pct(last, _f(c.iloc[-64])) if n > 64 else None,
        "chg_6m": _pct(last, _f(c.iloc[-127])) if n > 127 else None,
        "chg_1y": _pct(last, _f(c.iloc[-253])) if n > 253 else None,
    }
    tail = c.tail(252)
    hi, lo = _f(tail.max()), _f(tail.min())
    m.update({
        "hi52": round(hi, 2), "lo52": round(lo, 2),
        "from_hi52": _pct(last, hi), "from_lo52": _pct(last, lo),
    })
    for w in (20, 60, 120, 200):
        if n >= w:
            ma = _f(c.tail(w).mean())
            m[f"ma{w}"] = round(ma, 2)
            m[f"vs_ma{w}"] = _pct(last, ma)
    r = np.log(c / c.shift(1)).dropna()
    if len(r) >= 60:
        m["vol_1y"] = round(_f(r.tail(252).std()) * np.sqrt(252) * 100, 1)
        m["vol_60d"] = round(_f(r.tail(60).std()) * np.sqrt(252) * 100, 1)
    cum = c / c.cummax() - 1.0
    m["mdd_1y"] = round(_f(cum.tail(252).min()) * 100, 2)
    m["dates"] = [str(i)[:10] for i in c.index]
    m["close"] = [round(_f(x), 2) for x in c]
    return m


def fetch_quote() -> dict:
    out = {"asof": now_cn(), "errors": [], "ticker": C.FETCH["ticker"]}
    t = yf.Ticker(C.FETCH["ticker"])
    try:
        h = t.history(period="2y", interval="1d", auto_adjust=False)
        if h is None or h.empty:
            raise RuntimeError("history 为空")
        out["price"] = _series_metrics(h["Close"], C.FETCH["ticker"])
    except Exception as e:  # noqa: BLE001
        out["errors"].append(f"HD 行情失败：{type(e).__name__}: {e}")

    # 基准与同业（画相对强弱用）
    out["bench"] = {}
    for sym in [C.FETCH["benchmark"]] + C.FETCH["peers"]:
        if sym == C.FETCH["ticker"]:
            continue
        try:
            h = yf.Ticker(sym).history(period="2y", interval="1d", auto_adjust=False)
            if h is not None and not h.empty:
                out["bench"][sym] = _series_metrics(h["Close"], sym)
        except Exception as e:  # noqa: BLE001
            out["errors"].append(f"{sym} 行情失败：{type(e).__name__}")

    # 估值与一致预期
    try:
        info = t.info or {}
        out["fundamentals"] = {
            "market_cap": info.get("marketCap"),
            "ev": info.get("enterpriseValue"),
            "trailing_pe": _f(info.get("trailingPE")),
            "forward_pe": _f(info.get("forwardPE")),
            "dividend_yield": _f(info.get("dividendYield")),
            "payout_ratio": _f(info.get("payoutRatio")),
            "revenue_ttm": info.get("totalRevenue"),
            "revenue_growth": _f(info.get("revenueGrowth")),
            "gross_margins": _f(info.get("grossMargins")),
            "operating_margins": _f(info.get("operatingMargins")),
            "profit_margins": _f(info.get("profitMargins")),
            "roe": _f(info.get("returnOnEquity")),
            "total_debt": info.get("totalDebt"),
            "total_cash": info.get("totalCash"),
            "free_cashflow": info.get("freeCashflow"),
            "target_mean": _f(info.get("targetMeanPrice")),
            "target_high": _f(info.get("targetHighPrice")),
            "target_low": _f(info.get("targetLowPrice")),
            "analyst_count": info.get("numberOfAnalystOpinions"),
            "beta": _f(info.get("beta")),
        }
    except Exception as e:  # noqa: BLE001
        out["errors"].append(f"基本面失败：{type(e).__name__}")

    # 用一致预期算上行空间（只做算术，不做评级）
    try:
        f = out.get("fundamentals") or {}
        if f.get("target_mean") and out.get("price", {}).get("last"):
            f["upside_pct"] = _pct(f["target_mean"], out["price"]["last"])
    except Exception:  # noqa: BLE001
        pass
    return out


# ---------------------------------------------------------------- SEC 监管文件
KEY_FORMS = ("10-K", "10-Q", "8-K", "DEF 14A", "4")


def fetch_filings() -> dict:
    out = {"asof": now_cn(), "errors": [], "items": []}
    try:
        d = json.loads(_get(C.FETCH["sec_submissions"]))
        rec = d["filings"]["recent"]
        forms, dates = rec["form"], rec["filingDate"]
        acc, docs = rec["accessionNumber"], rec["primaryDocument"]
        rep = rec.get("reportDate", [""] * len(forms))
        for i, fm in enumerate(forms):
            if fm not in ("10-K", "10-Q", "8-K", "DEF 14A"):
                continue
            a = acc[i].replace("-", "")
            url = (f"https://www.sec.gov/Archives/edgar/data/"
                   f"{int(C.FETCH['sec_cik'])}/{a}/{docs[i]}") if docs[i] else ""
            out["items"].append({
                "form": fm, "filed": dates[i],
                "period": rep[i] if i < len(rep) else "",
                "url": url, "accession": acc[i],
            })
            if len(out["items"]) >= 40:
                break
        out["name"] = d.get("name")
        out["fiscal_year_end"] = d.get("fiscalYearEnd")
        out["sic"] = d.get("sicDescription")
    except Exception as e:  # noqa: BLE001
        out["errors"].append(f"SEC 失败：{type(e).__name__}: {e}")
    return out


# ---------------------------------------------------------------- IR 财报材料
# IR 页是一张 reportTable：**行 = 季度**，**列 = 材料类型**（表头即类型名）。
# 页面上的 <a> 锚文本是空的，所以类型只能从表头取、季度只能从行首单元格取。
IR_COLS = [
    ("press release", "press_release", "新闻稿", "Press Release"),
    ("10q/10k", "sec_filing", "10-Q / 10-K 报表", "10-Q / 10-K Filing"),
    ("webcast", "webcast", "电话会直播", "Earnings Webcast"),
    ("transcript", "transcript", "电话会记录", "Call Transcript"),
    ("non-gaap", "non_gaap", "非 GAAP 调节表", "Non-GAAP Reconciliation"),
    ("infographic", "infographic", "财报信息图", "Earnings Infographic"),
    ("supplemental", "supplemental", "补充材料", "Supplemental Material"),
]


def _abs_ir(u: str) -> str:
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("/"):
        return "https://ir.homedepot.com" + u
    if not u.startswith("http"):
        return "https://ir.homedepot.com/" + u.lstrip("./")
    return u


def _iso_date(s: str):
    """'August 18, 2026' → '2026-08-18'"""
    try:
        return datetime.strptime(s.strip(), "%B %d, %Y").strftime("%Y-%m-%d")
    except Exception:  # noqa: BLE001
        return None


_DOCS_DIR = None


def _pdf_cached(url: str) -> str:
    """下载 PDF 到本地缓存目录并返回路径（已存在则直接复用）。"""
    global _DOCS_DIR
    if _DOCS_DIR is None:
        _DOCS_DIR = os.path.join(C.DATA_DIR, "docs", "ir")
    os.makedirs(_DOCS_DIR, exist_ok=True)
    name = re.sub(r"[^A-Za-z0-9._-]", "_", url.rsplit("/", 1)[-1]) or "doc.pdf"
    path = os.path.join(_DOCS_DIR, name)
    if os.path.exists(path) and os.path.getsize(path) > 4000:
        return path
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        blob = r.read()
    if len(blob) < 4000:
        raise RuntimeError("下载内容过小：%d bytes" % len(blob))
    with open(path, "wb") as f:
        f.write(blob)
    return path


def _pdf_meta(url: str, kind_key: str) -> dict:
    """从 PDF 首页抽出「时间 + 主要标题」。

    · 新闻稿 —— 正文电头形如 `ATLANTA, August 18, 2026 --`，其前即为标题；
    · 电话会记录 —— 页首有形如 `EVENT DATE/TIME: August 18, 2026 / 09:00AM ET`，
      以及 `HD – Q2'26 Home Depot Earnings Call` 这样的会议名。
    ⚠️ 这两个字段页面 HTML 里都没有，只能下 PDF 解析——这正是用户抱怨
    「电话会议多个，不知道是哪段」的根因。
    """
    from pdfminer.high_level import extract_text
    path = _pdf_cached(url)
    t = extract_text(path, maxpages=1)
    t = re.sub(r"[ \t]+", " ", t or "")
    meta = {"bytes": os.path.getsize(path)}

    if kind_key == "transcript":
        first = next((l.strip() for l in t.split("\n") if l.strip()), "")
        meta["title"] = first[:160]
        m = re.search(r"EVENT DATE/TIME:\s*([A-Z][a-z]+ \d{1,2}, \d{4})"
                      r"(?:\s*/\s*([0-9:]+\s*[AP]M\s*[A-Z]{2,3}))?", t)
        if m:
            meta["dateline"] = m.group(1)
            meta["date"] = _iso_date(m.group(1))
            meta["time_et"] = (m.group(2) or "").strip()
    else:
        m = re.search(r"([A-Z][A-Za-z .,]{2,24}),\s*([A-Z][a-z]+ \d{1,2}, \d{4})\s*(?:--|–|—)", t)
        if m:
            meta["dateline"] = "%s, %s" % (m.group(1).strip(), m.group(2))
            meta["date"] = _iso_date(m.group(2))
            head = re.sub(r"\s*\n\s*", " ", t[:m.start()]).strip()
            meta["title"] = re.sub(r"\s+", " ", head)[:220]
        else:
            head = re.sub(r"\s*\n\s*", " ", t[:300]).strip()
            meta["title"] = re.sub(r"\s+", " ", head)[:220]
    return meta


def _peek_pdf(url: str) -> str:
    """从 URL 文件名猜出季度后缀，用于在标题缺失时兜底。"""
    b = url.rsplit("/", 1)[-1].lower()
    m = re.search(r"[qQ](\d)[-_]?20(\d\d)", b) or re.search(r"(\d)[qQ](\d\d)", b)
    return m.groups() if m else None


def fetch_ir_docs() -> dict:
    """解析 IR 季度财报页：按季度归组，补齐时间 / 标题 / 发布方。

    输出两套结构：
      `quarters` —— 结构化（看板主用）：每季度一组，含 date / headline / items[]
      `pdfs`     —— 扁平列表（向后兼容旧看板与小程序），字段已扩充
    """
    out = {"asof": now_cn(), "errors": [], "pdfs": [], "quarters": [],
           "publisher": "The Home Depot, Inc.", "publisher_zh": "家得宝公司（IR 官方）",
           "table_url": C.FETCH["ir_press_release_page"]}
    try:
        h = _get(C.FETCH["ir_press_release_page"])
        mt = re.search(r'<table[^>]*class="[^"]*reportTable[^"]*"(.*?)</table>', h, re.S | re.I)
        if not mt:
            raise RuntimeError("IR 页未找到 reportTable（页面结构可能已变）")
        tb = mt.group(1)
        ths = [re.sub(r"<[^>]+>", "", x).strip() for x in
               re.findall(r"<th[^>]*>(.*?)</th>", tb, re.S)]

        def col_of(idx):
            if idx < len(ths):
                low = ths[idx].lower()
                for needle, key, zh, en in IR_COLS:
                    if needle in low:
                        return key, zh, en
            return None, None, None

        tbody = re.search(r"<tbody[^>]*>(.*?)</tbody>", tb, re.S | re.I)
        body = tbody.group(1) if tbody else tb
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.S):
            tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
            if len(tds) < 3:
                continue
            qlabel = re.sub(r"<[^>]+>", "", tds[0]).strip()
            mq = re.match(r"Q([1-4])", qlabel)
            if not mq:
                continue
            qn = int(mq.group(1))
            items = []
            for ti, td in enumerate(tds[1:], 1):
                key, zh, en = col_of(ti)
                if not key:
                    continue
                href = re.search(r'href="([^"]+)"', td)
                if not href:
                    continue
                url = _abs_ir(href.group(1))
                items.append({"kind": key, "kind_zh": zh, "kind_en": en, "url": url})
            if items:
                out["quarters"].append({
                    "quarter": qn, "label": "Q%d" % qn, "items": items,
                    "date": None, "headline": None, "call_time_et": None,
                })

        # ---- 补「时间 + 主要标题」：只对新闻稿与电话会记录下 PDF（每季 2 个，很轻）
        for q in out["quarters"]:
            for it in q["items"]:
                if it["kind"] not in ("press_release", "transcript"):
                    continue
                try:
                    meta = _pdf_meta(it["url"], it["kind"])
                except Exception as e:  # noqa: BLE001
                    out["errors"].append("PDF 解析失败（%s Q%d）：%s"
                                         % (it["kind_zh"], q["quarter"], type(e).__name__))
                    continue
                it.update({k: v for k, v in meta.items() if k != "bytes"})
                if it.get("date") and not q["date"]:
                    q["date"] = it["date"]
                    q["dateline"] = it.get("dateline")
                if it["kind"] == "press_release" and it.get("title"):
                    q["headline"] = it["title"]
                if it["kind"] == "transcript":
                    q["call_time_et"] = it.get("time_et")

        # ---- 兜底：PDF 拿不到日期时，用 SEC 8-K 的申报日（财报当日发布 8-K）
        try:
            fy = json.loads(_get(C.FETCH["sec_submissions"]))
            rec = fy["filings"]["recent"]
            eights = [d for f, d in zip(rec["form"], rec["filingDate"]) if f == "8-K"]
            for q in out["quarters"]:
                if q["date"]:
                    continue
                mon = {1: (5, 6), 2: (8, 9), 3: (11, 12), 4: (2, 3)}[q["quarter"]]
                cand = [d for d in eights if int(d[5:7]) in mon]
                if cand:
                    q["date"] = sorted(cand, reverse=True)[0]
                    q["date_src"] = "SEC 8-K 申报日"
        except Exception as e:  # noqa: BLE001
            out["errors"].append("8-K 日期兜底失败：%s" % type(e).__name__)

        # ---- 兜底 2：config.FINANCIALS 里已核过的发布日（人工从财报稿抄录，最可信）
        # 优先级高于 8-K：8-K 的申报日可能比财报发布日晚 2–3 天（Q2 实测 08-21 vs 08-18），
        # 而本节要显示的是**财报发布**时间。
        try:
            rel = {int((q.get("label") or "Q0").strip()[1]): q.get("release")
                   for q in C.FINANCIALS["quarters"] if q.get("release")}
            for q in out["quarters"]:
                if rel.get(q["quarter"]) and q.get("date_src") == "SEC 8-K 申报日":
                    q["date"] = rel[q["quarter"]]
                    q["date_src"] = "config 已核对发布日"
        except Exception as e:  # noqa: BLE001
            out["errors"].append("发布日兜底失败：%s" % type(e).__name__)

        # ---- 财年：表格里只有 Q1/Q2，年份得从标题文本里解析
        for q in out["quarters"]:
            if q.get("fiscal_year"):
                continue
            for it in q["items"]:
                t = it.get("title") or ""
                m = (re.search(r"Fiscal\s+(\d{4})", t) or
                     re.search(r"[Qq]\d'?(\d{2})\b", t) or
                     re.search(r"20(\d\d)", t))
                if m:
                    g = m.group(1)
                    q["fiscal_year"] = int(g) if len(g) == 4 else 2000 + int(g)
                    break
            if not q.get("fiscal_year"):
                pk = _peek_pdf(q["items"][0]["url"]) if q["items"] else None
                if pk:
                    q["fiscal_year"] = 2000 + int(pk[1])
            q["label"] = "FY%s Q%d" % (q.get("fiscal_year") or "—", q["quarter"])
            q["label_zh"] = "%s财年 第%d季度" % (q.get("fiscal_year") or "—", q["quarter"])
            if q.get("date"):
                wd = datetime.strptime(q["date"], "%Y-%m-%d").strftime("%a")
                q["weekday"] = wd
                q["date_display"] = "%s（%s）" % (q["date"], wd)

        # ---- 扁平化，向后兼容
        for q in out["quarters"]:
            for it in q["items"]:
                out["pdfs"].append(dict(
                    it, quarter="Q%d" % q["quarter"], fiscal_year=q.get("fiscal_year"),
                    qlabel=q["label"], date=q.get("date"), weekday=q.get("weekday"),
                    headline=q.get("headline"),
                    publisher=out["publisher"], publisher_zh=out["publisher_zh"],
                ))
    except Exception as e:  # noqa: BLE001
        out["errors"].append(f"IR 页面失败：{type(e).__name__}: {e}")
    return out


# ---------------------------------------------------------------- 新闻
def fetch_news(limit: int = 24) -> dict:
    out = {"asof": now_cn(), "errors": [], "items": []}
    # 通道 1：yfinance
    try:
        raw = yf.Ticker(C.FETCH["ticker"]).news or []
        for it in raw:
            c = it.get("content", it)
            title = c.get("title") or it.get("title")
            if not title:
                continue
            out["items"].append({
                "title": title,
                "publisher": ((c.get("provider") or {}).get("displayName")
                              if isinstance(c.get("provider"), dict) else c.get("publisher")),
                "published": c.get("pubDate") or c.get("providerPublishTime"),
                "url": ((c.get("canonicalUrl") or {}).get("url")
                        if isinstance(c.get("canonicalUrl"), dict) else c.get("link")),
                "src": "yfinance",
            })
    except Exception as e:  # noqa: BLE001
        out["errors"].append(f"yfinance 新闻失败：{type(e).__name__}")

    # 通道 2：Yahoo 财经 RSS
    try:
        x = _get("https://feeds.finance.yahoo.com/rss/2.0/headline?s=HD&region=US&lang=en-US")
        for m in re.finditer(r"<item>(.*?)</item>", x, re.S):
            blk = m.group(1)
            ti = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", blk, re.S)
            li = re.search(r"<link>(.*?)</link>", blk, re.S)
            pd_ = re.search(r"<pubDate>(.*?)</pubDate>", blk, re.S)
            if ti:
                out["items"].append({
                    "title": ti.group(1).strip(),
                    "publisher": "Yahoo Finance",
                    "published": pd_.group(1).strip() if pd_ else None,
                    "url": li.group(1).strip() if li else None,
                    "src": "yahoo-rss",
                })
    except Exception as e:  # noqa: BLE001
        out["errors"].append(f"Yahoo RSS 失败：{type(e).__name__}")

    # 去重（按标题前 60 字）
    seen, uniq = set(), []
    for it in out["items"]:
        k = (it["title"] or "")[:60].lower().strip()
        if k and k not in seen:
            seen.add(k)
            uniq.append(it)
    out["items"] = uniq[:limit]
    out["count"] = len(out["items"])
    return out


# ---------------------------------------------------------------- 编排
def run() -> dict:
    res = {}
    for name, fn in (("quote", fetch_quote), ("filings", fetch_filings),
                     ("ir", fetch_ir_docs), ("news", fetch_news)):
        try:
            r = fn()
            res[name] = r
            errs = r.get("errors") or []
            print(f"  {name:<8} 完成" + (f"（{len(errs)} 个错误）" if errs else " ✅"))
            for e in errs:
                print(f"      ⚠️ {e}")
        except Exception as e:  # noqa: BLE001
            res[name] = {"errors": [f"{type(e).__name__}: {e}"]}
            print(f"  {name:<8} ❌ {type(e).__name__}: {e}")
    for k, v in res.items():
        save(f"{k}.json", v)
    return res


if __name__ == "__main__":
    print(f"[{now_cn()}] 抓取 HD 数据…")
    r = run()
    p = r.get("quote", {}).get("price") or {}
    if p.get("last"):
        print(f"\nHD {p['last']} @ {p['last_date']}｜1年 {p.get('chg_1y')}%｜"
              f"距52周高 {p.get('from_hi52')}%｜距52周低 {p.get('from_lo52')}%")
