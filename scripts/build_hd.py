# -*- coding: utf-8 -*-
"""
HD 专项研究看板生成器 —— 输出自包含单文件 HTML（ECharts 内联，零外部请求）

章节：结论摘要 / 股价与市场表现 / 季度财报归纳 / 管理层与治理 /
      扩店与 Pro 生态 / 中美贸易与关税 / 战略与长期目标 / 风险清单 / 市场反馈与数据来源
（2026-11-15 起：Patio/渠道对标等子项目章节已整体移除，聚焦公司运营、股价、
  关税影响与市场反馈。）

两个可切换维度
--------------
* 语言  中 / EN  —— 静态文案走 `.i18n[data-zh|data-en]`，图表文案走 payload 的 `L`
* 主题  浅 / 深  —— CSS 变量两套，图表颜色在重绘时从 CSS 变量读取，保证与页面一致

选择结果写入 localStorage（键 hd-lang / hd-theme），下次打开自动沿用；
读取失败（如被沙箱 iframe 限制）时静默降级为默认值，不影响页面。
"""
import os
import re
import json
import html
import datetime

import config as C
import i18n as I

_VENDOR_ECHARTS = os.path.join(C.DASHBOARD_DIR, "vendor", "echarts.min.js")


# ---------------------------------------------------------------- 小工具
def load(name: str, default=None):
    p = os.path.join(C.DATA_DIR, name)
    if not os.path.exists(p):
        return default
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return default


def _n(v, nd=2, dash="—"):
    if v is None:
        return dash
    try:
        return f"{float(v):,.{nd}f}"
    except (TypeError, ValueError):
        return dash


def _pct(v, nd=2, dash="—", sign=True):
    if v is None:
        return dash
    try:
        f = float(v)
    except (TypeError, ValueError):
        return dash
    return f"{f:+.{nd}f}%" if sign else f"{f:.{nd}f}%"


def _cls(v):
    """涨红跌绿（中文语境）"""
    if v is None:
        return "neu"
    return "up" if v > 0 else ("down" if v < 0 else "neu")


def _usd_b(v):
    if v is None:
        return "—"
    return f"${v/1e9:,.2f}B"


def _esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def S(key, tag="span"):
    """固定文案：<span class="i18n" data-zh data-en>中文</span>"""
    return I.S(key, tag)


def bi(zh, en, tag="span"):
    """动态句子的中英对照（含数值的句子用这个）。"""
    return I.bi(zh, en, tag)


def _echarts_head() -> str:
    try:
        with open(_VENDOR_ECHARTS, encoding="utf-8") as f:
            js = f.read()
        if "</script" in js.lower():
            raise ValueError("vendor 含 </script>")
        return "<script>/* ECharts 5 · 内联自 dashboard/vendor/echarts.min.js */\n" + js + "\n</script>"
    except Exception as e:  # noqa: BLE001
        return ('<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js">'
                f'</script><!-- 内联失败，回退 CDN：{type(e).__name__} -->')


# ---------------------------------------------------------------- 结论引擎
def verdict(q: dict) -> dict:
    """基于实际数据生成结论；不引入任何主观评级。返回 (tag_key, zh, en, cls)。"""
    p = q.get("price") or {}
    f = q.get("fundamentals") or {}
    q2 = C.FINANCIALS["quarters"][0]
    points = []

    if p.get("from_hi52") is not None:
        points.append((
            "vtag.market", "warn" if (p.get("from_lo52") or 9) < C.THRESHOLDS["near_low_pct"] else "neu",
            "距 52 周高点 " + _pct(p["from_hi52"]) + "，距 52 周低点仅 " + _pct(p["from_lo52"]) + "，处于区间底部",
            _pct(p["from_hi52"]) + " from the 52-week high and only " + _pct(p["from_lo52"]) +
            " off the 52-week low — at the bottom of the range"))
    if p.get("chg_1y") is not None:
        spy = ((q.get("bench") or {}).get("SPY") or {}).get("chg_1y")
        if spy is not None:
            gap = p["chg_1y"] - spy
            points.append((
                "vtag.market", "down" if gap < 0 else "up",
                "近一年 " + _pct(p["chg_1y"]) + " vs 标普500 " + _pct(spy) + "，超额收益 " + _pct(gap),
                "1-year return " + _pct(p["chg_1y"]) + " vs the S&P 500's " + _pct(spy) +
                " — excess return " + _pct(gap)))
    points.append((
        "vtag.quality", "warn",
        "Q3 净销售 " + f"{q2['net_sales']:,}" + " 百万美元（" + _pct(q2["net_sales_yoy"]) +
        "），可比销售 " + _pct(q2["comps"]) + "、调整后 EPS $" + f"{q2['eps_adjusted']}" +
        "（+" + f"{round((q2['eps_adjusted']/q2['prev']['eps_adjusted']-1)*100,1)}" + "%）",
        "Q3 net sales of US$" + f"{q2['net_sales']:,}" + " million (" + _pct(q2["net_sales_yoy"]) +
        "); comps " + _pct(q2["comps"]) + " and adjusted EPS of $" + f"{q2['eps_adjusted']}" +
        " (+" + f"{round((q2['eps_adjusted']/q2['prev']['eps_adjusted']-1)*100,1)}" + "% y/y)"))
    points.append((
        "vtag.pv", "warn",
        "平均客单价 " + _pct(q2["avg_ticket_yoy"]) + " 而交易量 " + _pct(q2["transactions_yoy"]) +
        "——当季增长由价格而非客流驱动",
        "Average ticket " + _pct(q2["avg_ticket_yoy"]) + " while transactions " + _pct(q2["transactions_yoy"]) +
        " — growth this quarter was price-driven, not traffic-driven"))
    points.append((
        "vtag.growth", "up",
        "16 个商品部门中 13 个正 comp，线上连续第六个季度双位数增长（Q3 约 +13%）；"
        "大额交易（>$1,000）+4.5%",
        "13 of 16 merchandising departments posted positive comps and online grew double-digits for a "
        "sixth straight quarter (about +13% in Q3); big-ticket transactions above US$1,000 were +4.5%"))
    points.append((
        "vtag.gov", "up",
        "CEO Ted Decker 已结束病休归队；2026-11-23 起 Richard McPhail 接任 CEO、Ann-Marie Campbell 任总裁兼 COO，"
        "Decker 留任董事长，Jordan Broggi 接任 CFO —— 继任路径已明确",
        "CEO Ted Decker has returned from medical leave; effective 2026-11-23 Richard McPhail becomes CEO, "
        "Ann-Marie Campbell becomes President & COO, Decker stays on as Chair and Jordan Broggi becomes CFO "
        "— the succession path is now settled"))
    if f.get("upside_pct") is not None:
        points.append((
            "vtag.val", "up" if f["upside_pct"] > 0 else "down",
            "静态 PE " + _n(f.get("trailing_pe")) + "、前瞻 PE " + _n(f.get("forward_pe")) +
            "，股息率 " + _n(f.get("dividend_yield")) + "%；" + str(f.get("analyst_count")) +
            " 位分析师目标均价 $" + _n(f.get("target_mean")) + "（较现价 " + _pct(f["upside_pct"]) + "）",
            "Trailing P/E " + _n(f.get("trailing_pe")) + ", forward P/E " + _n(f.get("forward_pe")) +
            ", dividend yield " + _n(f.get("dividend_yield")) + "%; the mean target of " +
            str(f.get("analyst_count")) + " analysts is $" + _n(f.get("target_mean")) + " (" +
            _pct(f["upside_pct"]) + " vs the current price)"))
    points.append((
        "vtag.cycle", "neu",
        "管理层将住房环境定性为「冻结」：成屋周转率连续四年处于多年低位，抵押利率高企压制大型项目；"
        "市场复苏情景下销售可回到 +5%~6%",
        "Management describes housing as \"frozen\": existing-home turnover has been at multi-year lows for "
        "four years and elevated mortgage rates are suppressing large projects; in the Market Recovery Case "
        "sales could return to +5%–6%"))
    return {"points": points, "asof": q.get("asof")}


# ---------------------------------------------------------------- HTML 片段
def _kpi_cards(q: dict) -> str:
    p = q.get("price") or {}
    f = q.get("fundamentals") or {}
    q2 = C.FINANCIALS["quarters"][0]
    items = [
        ("kpi.price", f"${_n(p.get('last'))}", _esc(p.get("last_date")),
         S("kpi.week") if p.get("chg_1d") else S("kpi.week"), _cls(p.get("chg_1y"))),
        ("kpi.ret1y", _pct(p.get("chg_1y")),
         S("kpi.spx") + " " + _pct(((q.get('bench') or {}).get('SPY') or {}).get("chg_1y")),
         S("kpi.excess"), _cls(p.get("chg_1y"))),
        ("kpi.netsales", f"${q2['net_sales']/1000:,.1f}B", S("kpi.yoy") + " " + _pct(q2["net_sales_yoy"]),
         "FY2026 Q3", "up"),
        ("kpi.eps", f"${_n(q2['eps_adjusted'])}", "GAAP $" + _n(q2["eps_diluted"]),
         S("kpi.ly") + " $" + _n(q2["prev"]["eps_adjusted"]), "up"),
        ("kpi.comps", _pct(q2["comps"]), S("kpi.us") + " " + _pct(q2["comps_us"]),
         S("kpi.ticket_pos"), _cls(q2["comps"])),
        ("kpi.tx", _pct(q2["transactions_yoy"]), "", S("kpi.divergence"), _cls(q2["transactions_yoy"])),
        ("kpi.pe", _n(f.get("trailing_pe")) + "x", S("kpi.fwd") + " " + _n(f.get("forward_pe")) + "x",
         S("kpi.yield") + " " + _n(f.get("dividend_yield")) + "%", "neu"),
        ("kpi.target", f"${_n(f.get('target_mean'))}", S("kpi.vs_price") + " " + _pct(f.get("upside_pct")),
         str(f.get("analyst_count")) + S("kpi.cover"), "up"),
    ]
    # 交易量卡片的副标需要「客单价 +2.8%」，单独替换为双语拼装
    ticket_sub = bi("客单价 " + _pct(q2["avg_ticket_yoy"]), "Ticket " + _pct(q2["avg_ticket_yoy"]))
    out = []
    for name, big, sub, foot, cls in items:
        if name == "kpi.tx":
            sub = ticket_sub
        out.append(
            '<div class="kpi"><div class="k-name">' + S(name) + '</div>'
            '<div class="k-big ' + cls + '">' + big + '</div>'
            '<div class="k-sub">' + sub + '</div><div class="k-foot">' + foot + '</div></div>')
    return "".join(out)


def _upcoming_html() -> str:
    """下一份财报排期横幅：只展示已官宣信息，不写数字预期。"""
    up = getattr(C, "UPCOMING_EARNINGS", None) or {}
    if not up:
        return "<p class='muted'>" + S("c.upcoming.none") + "</p>"
    out = ["<div class='box warn-box'><b>" + S("c.upcoming") + "：" + _esc(up.get("qlabel") or "")
           + " · " + _esc(up.get("call") or "") + "</b>"
           "<p class='note' style='margin:6px 0 0'>" + bi(up.get("note", ""), I.FACT_UPCOMING["note"])]
    if up.get("webcast"):
        out.append(" <a href='" + _esc(up["webcast"]) + "' target='_blank' rel='noopener'>"
                   + S("irq.call") + " webcast →</a>")
    out.append("<div class='src'>" + I.src_bi(up.get("src", "")) + "</div></p></div>")
    return "".join(out)


def _quarter_table() -> str:
    qs = C.FINANCIALS["quarters"]
    rows = [
        ("qt.net", lambda q: f"{q['net_sales']:,}", lambda q: _pct(q["net_sales_yoy"]), True),
        ("qt.gross", lambda q: f"{q['gross_profit']:,}", lambda q: "", False),
        ("qt.op", lambda q: f"{q['operating_income']:,}", lambda q: "", False),
        ("qt.earn", lambda q: f"{q['net_earnings']:,}", lambda q: _pct(q.get("net_earnings_yoy")), True),
        ("qt.gm", lambda q: _pct(q["gross_margin"], sign=False), lambda q: "", False),
        ("qt.om", lambda q: _pct(q["operating_margin"], sign=False), lambda q: "", False),
        ("qt.eps", lambda q: f"${_n(q['eps_diluted'])}",
         lambda q: S("qt.ly") + " $" + _n(q["prev"]["eps_diluted"]), False),
        ("qt.eps_adj", lambda q: f"${_n(q['eps_adjusted'])}",
         lambda q: S("qt.ly") + " $" + _n(q["prev"]["eps_adjusted"]), False),
        ("qt.comps", lambda q: _pct(q["comps"]),
         lambda q: S("qt.ly") + " " + _pct(q["prev"]["comps"]), False),
        ("qt.comps_us", lambda q: _pct(q["comps_us"]), lambda q: "", False),
        ("qt.tx", lambda q: _n(q["transactions_m"], 1), lambda q: _pct(q["transactions_yoy"]), False),
        ("qt.ticket", lambda q: f"${_n(q['avg_ticket'])}", lambda q: _pct(q["avg_ticket_yoy"]), False),
    ]
    head = "".join("<th>" + _esc(q["label"]) + "<span class='th-sub'>" + _esc(q["end"]) + "</span></th>"
                   for q in qs)
    body = []
    for key, getter, sub, highlight in rows:
        tds = []
        for q in qs:
            v = getter(q)
            s = sub(q) or ""
            cls = _cls(q["net_sales_yoy"]) if highlight else ""
            tds.append("<td class='" + cls + "'>" + v + "<span class='td-sub'>" + s + "</span></td>")
        body.append("<tr><th class='row-h'>" + S(key) + "</th>" + "".join(tds) + "</tr>")
    return ("<table class='tbl'><thead><tr><th class='row-h'>" + S("qtable.h1") + "</th>" + head +
            "</tr></thead><tbody>" + "".join(body) + "</tbody></table>")


def _leadership_html() -> str:
    out = ["<p class='note'>" + bi(C.LEADERSHIP["note"], I.FACT_LEADERSHIP["note"]) + "</p>", "<div class='ppl'>"]
    for i, p in enumerate(C.LEADERSHIP["people"]):
        en = I.FACT_LEADERSHIP["people"][i] if i < len(I.FACT_LEADERSHIP["people"]) else {}
        st = p.get("status", "")
        cls = "warn" if ("休假" in st or "病休" in st or "代理" in st) else "ok"
        out.append(
            "<div class='person'><div class='p-head'><b>" + _esc(p["name"]) + "</b>"
            "<span class='p-title'>" + bi(p["title"], en.get("title", p["title"])) + "</span></div>"
            "<div class='p-status " + cls + "'>" +
            bi(p["status"], en.get("status", p["status"])) + "</div>"
            "<div class='p-note'>" + bi(p.get("note", ""), en.get("note", "")) + "</div></div>")
    out.append("</div>")

    # 重大变动时间线
    chs = C.LEADERSHIP.get("changes") or []
    en_chs = I.FACT_LEADERSHIP.get("changes") or []
    if chs:
        out.append("<h3 style='margin-top:16px'>" + S("c.leadchanges") + "</h3><ul class='list quote'>")
        for i, ch in enumerate(chs):
            e = en_chs[i] if i < len(en_chs) else {}
            out.append(
                "<li><b>" + _esc(ch.get("date") or "") + " · " +
                bi(ch.get("title", ""), e.get("title", ch.get("title", ""))) + "</b>"
                "<span class='muted small'> " + S("lead.filed") + "：" + _esc(ch.get("filed") or "—") +
                "</span><br><span class='qtext'>" +
                bi(ch.get("detail", ""), e.get("detail", "")) + "</span>"
                "<div class='src'>" + I.src_bi(ch.get("src", "")) + "</div></li>")
        out.append("</ul>")
    return "".join(out)


def _pb_html() -> str:
    """第九章：自有品牌。来源分级 A=官方披露 / B=第三方估计或本项目归纳。"""
    pb = C.PRIVATE_BRANDS
    en = I.FACT_PRIVATE_BRANDS

    def grade_badge(g: str) -> str:
        if g == "A":
            return "<span class='badge'>来源 A · 官方披露</span>"
        return "<span class='badge w'>来源 B · 第三方/项目归纳</span>"

    out = ["<p class='note'>" + bi(pb["note"], en["note"]) + "</p>"]

    # ① 10-K 商标
    tm = pb["trademark"]
    out.append("<div class='card'><h3>" + S("pb.trademark") + " " + grade_badge(tm["grade"]) + "</h3>")
    out.append("<div class='badges'>" + "".join("<span class='badge'>" + _esc(b) + "</span>" for b in tm["brands"]) + "</div>")
    out.append("<p class='note'>" + bi(tm["desc"], en["trademark"]["desc"]) + "</p>")
    out.append("<p class='src'>" + I.src_bi("来源：" + tm["src"]) +
               " · <a href='" + tm["url"] + "' target='_blank'>10-K 原文</a></p></div>")

    # ② 独家授权
    li = pb["licensed"]
    out.append("<div class='card'><h3>" + S("pb.licensed") + " " + grade_badge(li["grade"]) + "</h3>")
    out.append("<table><tbody>")
    en_li = en["licensed"]["items"]
    for i, b in enumerate(li["brands"]):
        e = en_li[i] if i < len(en_li) else {}
        out.append("<tr><th class='row-h'>" + _esc(b["name"]) + "</th><td>" +
                   bi(b["desc"], e.get("desc", b["desc"])) + "</td></tr>")
    out.append("</tbody></table>")
    out.append("<p class='note'>" + bi(li["desc"], en["licensed"]["desc"]) + "</p>")
    out.append("<p class='src'>" + I.src_bi("来源：" + li["src"]) + "</p></div>")

    # ③ 户外矩阵
    om = pb["outdoor_matrix"]
    out.append("<div class='card'><h3>" + S("pb.outdoor") + " " + grade_badge(om["grade"]) + "</h3>")
    out.append("<table><thead><tr><th>品牌</th><th>" + bi("定位", "Positioning") + "</th></tr></thead><tbody>")
    for i, it in enumerate(om["items"]):
        pos_en = en["outdoor_matrix"]["pos"][i] if i < len(en["outdoor_matrix"].get("pos", [])) else it["pos"]
        out.append("<tr><td><b>" + _esc(it["name"]) + "</b></td><td>" +
                   bi(it["pos"], pos_en) + "</td></tr>")
    out.append("</tbody></table>")
    out.append("<p class='note'>" + bi(om["desc"], en["outdoor_matrix"]["desc"]) + "</p>")
    out.append("<p class='src'>" + I.src_bi("来源：" + om["src"]) + "</p></div>")

    # ④ Bastek 信号
    bk = pb["bastek"]
    out.append("<div class='card'><h3>" + S("pb.bastek") + " " + grade_badge(bk["grade"]) + "</h3>")
    out.append("<p class='note' style='font-size:13.4px'>" + bi(bk["desc"], en["bastek"]["desc"]) + "</p>")
    out.append("<p class='src'>" + I.src_bi("来源：" + bk["src"]) + "</p></div>")

    # ⑤ 第三方估计
    out.append("<div class='card'><h3>" + S("pb.est") + "</h3><ul class='list quote'>")
    for t in pb["third_party"]:
        src_html = ("<a href='" + t["url"] + "' target='_blank'>" + _esc(t["src"]) + "</a>"
                    if t.get("url") else _esc(t["src"]))
        out.append("<li><span class='badge w'>B</span> " + _esc(t["fact"]) +
                   "<div class='src'>" + I.src_bi("来源：") + src_html + "</div></li>")
    out.append("</ul></div>")
    return "".join(out)


def _tariff_table() -> str:
    facts = C.TARIFF["facts"]
    en_facts = I.FACT_TARIFF["facts"]
    rows = []
    for i, f in enumerate(facts):
        e = en_facts[i] if i < len(en_facts) else {}
        rows.append("<tr><th class='row-h'>" + bi(f["k"], e.get("k", f["k"])) + "</th>"
                    "<td>" + bi(f["v"], e.get("v", f["v"])) + "</td>"
                    "<td class='src'>" + I.src_bi(f.get("src", "")) + "</td></tr>")
    tl = []
    en_tl = I.FACT_TARIFF["policy_timeline"]
    for i, t in enumerate(C.TARIFF["policy_timeline"]):
        e = en_tl[i] if i < len(en_tl) else {}
        tl.append("<li><b>" + _esc(t["date"]) + "</b> " +
                  bi(t["event"], e.get("event", t["event"])) + "</li>")
    mv = []
    en_mv = I.FACT_TARIFF["management_view"]
    for i, x in enumerate(C.TARIFF["management_view"]):
        e = en_mv[i] if i < len(en_mv) else x
        mv.append("<li>" + bi(x, e) + "</li>")
    return ("<table class='tbl compact'><thead><tr><th class='row-h'>" + S("tar.h1") + "</th>"
            "<th>" + S("tar.h2") + "</th><th>" + S("tar.h3") + "</th></tr></thead><tbody>" +
            "".join(rows) + "</tbody></table>"
            "<h4>" + S("tar.timeline") + "</h4><ul class='list'>" + "".join(tl) + "</ul>"
            "<h4>" + S("tar.quotes") + "</h4><ul class='list quote'>" + "".join(mv) + "</ul>")


def _strategy_html() -> str:
    out = []
    en_p = I.FACT_STRATEGY_PILLARS
    for i, p in enumerate(C.STRATEGY["pillars"]):
        e = en_p[i] if i < len(en_p) else {}
        out.append("<div class='pillar'><div class='pl-en'>" + _esc(p["name"]) + "</div>"
                   "<div class='pl-cn'>" + bi(p["cn"], e.get("cn", p["cn"])) + "</div>"
                   "<div class='pl-desc'>" + bi(p["desc"], e.get("desc", p["desc"])) + "</div></div>")
    return "<div class='pillars'>" + "".join(out) + "</div>"


def _scenario_table() -> str:
    s = C.LONG_TERM["scenarios"]
    en_s = I.FACT_LONG_TERM["scenarios"]
    head = "".join("<th>" + bi(x["name"], (en_s[i] if i < len(en_s) else {}).get("name", x["name"])) +
                   "<span class='th-sub'>" +
                   bi(x["cn"], (en_s[i] if i < len(en_s) else {}).get("cn", x["cn"])) + "</span></th>"
                   for i, x in enumerate(s))
    keys = [("st.sales", "sales"), ("st.comps", "comps"), ("st.eps", "eps"), ("st.desc", "desc")]
    body = []
    for key, k in keys:
        tds = []
        for i, x in enumerate(s):
            e = en_s[i] if i < len(en_s) else {}
            tds.append("<td>" + bi(x.get(k, "—"), e.get(k, x.get(k, "—"))) + "</td>")
        body.append("<tr><th class='row-h'>" + S(key) + "</th>" + "".join(tds) + "</tr>")
    cap = "".join("<li>" + bi(x, I.FACT_LONG_TERM["capital"][i] if i < len(I.FACT_LONG_TERM["capital"]) else x)
                  + "</li>" for i, x in enumerate(C.LONG_TERM["capital"]))
    return ("<p class='note'>" + bi(C.LONG_TERM["note"], I.FACT_LONG_TERM["note"]) + "</p>"
            "<table class='tbl'><thead><tr><th class='row-h'>" + S("scen.h1") + "</th>" + head +
            "</tr></thead><tbody>" + "".join(body) + "</tbody></table>"
            "<h4>" + S("scen.capital") + "</h4><ul class='list'>" + cap + "</ul>")


def _risk_html() -> str:
    a = "".join("<li>" + bi(x, I.FACT_MACRO["headwinds"][i] if i < len(I.FACT_MACRO["headwinds"]) else x)
                + "</li>" for i, x in enumerate(C.MACRO["headwinds"]))
    b = "".join("<li>" + bi(x, I.FACT_MACRO["tailwinds"][i] if i < len(I.FACT_MACRO["tailwinds"]) else x)
                + "</li>" for i, x in enumerate(C.MACRO["tailwinds"]))
    return ("<div class='two'><div class='box warn-box'><h4>" + S("risk.head") + "</h4>"
            "<ul class='list'>" + a + "</ul></div>"
            "<div class='box ok-box'><h4>" + S("risk.tail") + "</h4><ul class='list'>" + b + "</ul></div></div>"
            "<p class='note'>" + bi(C.MACRO["note"], I.FACT_MACRO["note"]) + "</p>")


def _followup_html() -> str:
    lis = []
    for i, (zh_title, zh_desc) in enumerate([
        ("CEO 回归进展", "任何关于休假时长或人事安排的披露（8-K 级事件）"),
        ("Q3 FY2026 财报", "关注关税退款退坡后的毛利率与同店表现（预计 11 月发布）"),
        ("住房周转率", "成屋销售与待售签约量能否止跌，是大型项目需求的前置指标"),
        ("SRS 整合与交叉销售", "90% 门店已通过 SRS 成交，关注转化率与 HVAC 垂直放量"),
        ("回购恢复时点", "公司已暂停回购至 2027 年，恢复时点是资本配置转向的信号"),
        ("关税与贸易政策", "Section 101 到期后的成本传导，以及供应链多元化进度"),
    ]):
        en_t, en_d = I.FACT_FOLLOWUP[i]
        lis.append("<li><b>" + bi(zh_title, en_t) + "</b><span class='dash'> —— </span>" +
                   bi(zh_desc, en_d) + "</li>")
    return "<ul class='list'>" + "".join(lis) + "</ul>"


def _store_html() -> str:
    s = C.STORES
    ex = s["expansion"]
    return ("<div class='kpis'>"
            "<div class='kpi'><div class='k-name'>" + S("sk.retail") + "</div>"
            "<div class='k-big'>" + f"{s['retail']:,}" + "</div>"
            "<div class='k-sub'>" + bi(f"当季新开 {ex['q2_opened']} 家", f"{ex['q2_opened']} opened this quarter")
            + "</div>"
            "<div class='k-foot'>" +
            bi(f"全年计划约 {ex['fy2026_new_stores']} 家", f"~{ex['fy2026_new_stores']} planned for FY2026") +
            "</div></div>"
            "<div class='kpi'><div class='k-name'>" + S("sk.srs") + "</div>"
            "<div class='k-big'>" + f"{s['srs_locations']:,}+" + "</div>"
            "<div class='k-sub'>" + S("sk.dist") + "</div>"
            "<div class='k-foot'>" +
            bi("全年计划新增 " + ex["fy2026_new_srs_branches"] + " 家",
               ex["fy2026_new_srs_branches"] + " planned for FY2026") + "</div></div>"
            "<div class='kpi'><div class='k-name'>" + S("sk.emp") + "</div>"
            "<div class='k-big'>" + f"{C.META['employees']:,}" + "</div>"
            "<div class='k-sub'>" + S("sk.global") + "</div>"
            "<div class='k-foot'>" + S("sk.markets") + "</div></div>"
            "<div class='kpi'><div class='k-name'>" + S("sk.tam") + "</div>"
            "<div class='k-big'>$" + str(C.STRATEGY['tam']['current_tn']) + "T</div>"
            "<div class='k-sub'>" +
            bi("由 $" + str(C.STRATEGY['tam']['former_tn']) + "T 扩大",
               "up from $" + str(C.STRATEGY['tam']['former_tn']) + "T") + "</div>"
            "<div class='k-foot'>" +
            bi("其中 Pro 约 $" + str(C.STRATEGY['tam']['pro_pool_tn']) + "T",
               "Pro pool about $" + str(C.STRATEGY['tam']['pro_pool_tn']) + "T") + "</div></div>"
            "</div><p class='note'>" + bi(ex["note"], I.FACT_STORES["expansion_note"]) + "</p>")


def _news_html(news: dict) -> str:
    items = (news or {}).get("items") or []
    if not items:
        return "<p class='muted'>" + S("empty.news") + "</p>"
    lis = []
    for it in items[:14]:
        t = _esc(it.get("title"))
        u = it.get("url") or ""
        pub = _esc(it.get("publisher") or "")
        link = f"<a href='{_esc(u)}' target='_blank' rel='noopener'>{t}</a>" if u else t
        lis.append(f"<li>{link}<span class='muted'> — {pub}</span></li>")
    return "<ul class='list news'>" + "".join(lis) + "</ul>"


def _filings_html(fil: dict) -> str:
    items = (fil or {}).get("items") or []
    if not items:
        return "<p class='muted'>" + S("empty.filings") + "</p>"
    rows = []
    for it in items[:14]:
        u = it.get("url") or ""
        link = (f"<a href='{_esc(u)}' target='_blank' rel='noopener'>{_esc(it['form'])}</a>"
                if u else _esc(it["form"]))
        rows.append(f"<tr><td>{_esc(it['filed'])}</td><td>{link}</td>"
                    f"<td>{_esc(it.get('period'))}</td></tr>")
    return ("<table class='tbl compact'><thead><tr><th>" + S("fil.h1") + "</th><th>" + S("fil.h2") +
            "</th><th>" + S("fil.h3") + "</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>")


def _irdocs_html(ir: dict) -> str:
    pdfs = (ir or {}).get("pdfs") or []
    if not pdfs:
        return "<p class='muted'>" + S("empty.ir") + "</p>"
    lis = "".join(
        f"<li><a href='{_esc(d['url'])}' target='_blank' rel='noopener'>"
        f"{_esc(d['kind'])}{(' · ' + _esc(d['quarter'])) if d.get('quarter') else ''}</a></li>"
        for d in pdfs[:12])
    return "<ul class='list'>" + lis + "</ul>"


def _ir_quarters_html(ir: dict) -> str:
    """按季度的财报材料表：时间 / 发布方 / 主要标题 / 材料清单。"""
    qs = (ir or {}).get("quarters") or []
    if not qs:
        return _irdocs_html(ir)
    cards = []
    for q in qs:
        # 只有拿到新闻稿/电话会 PDF 日期的季度才算「已核实时间」；
        # 仅有 webcast 占位的新季度（日期来自 SEC 8-K 兜底）一律显示「待发布」，避免误用往年日期
        verified = any((it.get("kind") in ("press_release", "transcript"))
                       for it in (q.get("items") or []))
        when = q.get("date_display") or "—"
        if not verified and q.get("date_src") == "SEC 8-K 申报日":
            when = S("irq.pending")
        call = q.get("call_time_et") or ""
        items = []
        for it in q.get("items") or []:
            u = it.get("url") or ""
            nm = bi(it.get("kind_zh") or it.get("kind") or "",
                    it.get("kind_en") or it.get("kind") or "")
            items.append(f"<li><a href='{_esc(u)}' target='_blank' rel='noopener'>{nm}</a></li>"
                         if u else "<li>" + nm + "</li>")
        extra = ""
        if call:
            extra = " · <span class='bdg'>" + S("irq.call") + " " + _esc(call) + "</span>"
        cards.append(
            "<div class='ircard'>"
            "<div class='irq'>" + _esc(q.get("label") or "") + "</div>"
            "<div class='irmeta'><span class='irlab'>" + S("irq.when") + "</span>"
            + _esc(when) + extra + "</div>"
            "<div class='irmeta'><span class='irlab'>" + S("irq.who") + "</span>"
            + bi(ir.get("publisher_zh") or "家得宝公司（IR 官方）",
                 ir.get("publisher") or "The Home Depot, Inc.") + "</div>"
            "<div class='irmeta'><span class='irlab'>" + S("irq.headline") + "</span>"
            "<span class='irhead'>" + _esc(q.get("headline") or "—") + "</span></div>"
            "<ul class='list irdocs'>" + "".join(items) + "</ul></div>")
    return "".join(cards) + "<p class='note'>" + S("irq.note") + "</p>"


def _highlights(q, fil, ir, news) -> str:
    """概览要点：全部由一手数据算出，每条都能追溯到对应章节。"""
    p = q.get("price") or {}
    f = q.get("fundamentals") or {}
    q2 = None
    try:
        import config as _C
        q2 = _C.FINANCIALS["quarters"][0]
    except Exception:  # noqa: BLE001
        q2 = None
    pts = []

    if p.get("last") and p.get("chg_1m") is not None:
        sgn = "涨" if p["chg_1m"] >= 0 else "跌"
        pts.append((
            f"股价 {p['last']} 美元（{p.get('last_date')}），近一月{sgn} {abs(p['chg_1m']):.2f}%，"
            f"距 52 周高 {p.get('from_hi52'):+.2f}%、距 52 周低 {p.get('from_lo52'):+.2f}%。",
            f"Share price {p['last']} on {p.get('last_date')}, {abs(p['chg_1m']):.2f}% "
            f"{'higher' if p['chg_1m'] >= 0 else 'lower'} over the past month; "
            f"{p.get('from_hi52'):+.2f}% from the 52-week high and "
            f"{p.get('from_lo52'):+.2f}% from the low."))
    if q2:
        if q2.get("net_sales_yoy") is not None:
            pts.append((
                f"最近一期 {q2.get('label')}（期末 {q2.get('end')}，{q2.get('release')} 发布）"
                f"净销售额 {q2.get('net_sales', 0)/1000:.1f} 十亿美元，同比 "
                f"{q2['net_sales_yoy']:+.1f}%；同店（comp）{q2.get('comps'):+.1f}%，"
                f"美国同店 {q2.get('comps_us'):+.1f}%。",
                f"Latest quarter {q2.get('label')} (ended {q2.get('end')}, released "
                f"{q2.get('release')}): net sales ${q2.get('net_sales', 0)/1000:.1f}B, "
                f"{q2['net_sales_yoy']:+.1f}% YoY; comparable sales {q2.get('comps'):+.1f}% "
                f"(US {q2.get('comps_us'):+.1f}%)."))
        if q2.get("transactions_yoy") is not None:
            pts.append((
                f"客流与客单价：交易量同比 {q2['transactions_yoy']:+.1f}%，"
                f"平均客单价 {q2.get('avg_ticket')} 美元（同比 {q2.get('avg_ticket_yoy'):+.1f}%）"
                f" —— 增长由客单价驱动而非客流。",
                f"Traffic vs ticket: transactions {q2['transactions_yoy']:+.1f}% YoY, "
                f"average ticket ${q2.get('avg_ticket')} ({q2.get('avg_ticket_yoy'):+.1f}%) — "
                f"growth is driven by ticket size, not traffic."))
    if f.get("trailing_pe") and f.get("target_mean") and p.get("last"):
        pts.append((
            f"估值：滚动市盈率 {f['trailing_pe']:.1f} 倍，一致目标价均值 {f['target_mean']:.2f} 美元"
            f"（对现价 {f.get('upside_pct'):+.1f}%），覆盖分析师 {f.get('analyst_count') or '—'} 位。",
            f"Valuation: trailing P/E {f['trailing_pe']:.1f}x, consensus mean target "
            f"{f['target_mean']:.2f} ({f.get('upside_pct'):+.1f}% vs spot), "
            f"{f.get('analyst_count') or '—'} analysts covering."))

    # 市场反馈：近一周新闻标题（原始标题，不做加工）
    items = (news or {}).get("items") or []
    if items:
        head_zh = "；".join(it.get("title", "") for it in items[:3])
        head_en = "; ".join(it.get("title", "") for it in items[:3])
        pts.append((
            f"市场反馈：近期媒体聚焦 —— {head_zh}。",
            f"Market reaction: recent media focus — {head_en}."))

    # 只统计「已核实」的季度（含新闻稿/电话会 PDF），避免把仅有 webcast 占位的
    # 新季度（日期为 SEC 8-K 兜底，常误用往年日期）当成最近财报材料
    qs = [q for q in ((ir or {}).get("quarters") or [])
          if any(it.get("kind") in ("press_release", "transcript")
                 for it in (q.get("items") or []))]
    if qs:
        latest = max(qs, key=lambda x: x.get("quarter") or 0)
        pts.append((
            f"最近财报材料：{latest.get('label')}，发布于 {latest.get('date') or '—'}"
            + (f"，电话会 {latest.get('call_time_et')}" if latest.get("call_time_et") else "")
            + f"。主要标题：「{latest.get('headline') or '—'}」",
            f"Latest filing set: {latest.get('label')}, published "
            + str(latest.get("date") or "—")
            + (f", call at {latest.get('call_time_et')}" if latest.get("call_time_et") else "")
            + f". Headline: \"{latest.get('headline') or '—'}\""))

    if not pts:
        return "<p class='muted'>" + S("empty.buzz") + "</p>"
    lis = "".join("<li><span>" + bi(z, e) + "</span></li>" for z, e in pts)
    return "<ul class='list hl'>" + lis + "</ul><p class='note'>" + S("hl.note") + "</p>"


# ---------------------------------------------------------------- 载荷
def build_payload(q, fil, ir, news, bz=None) -> dict:
    p = q.get("price") or {}
    bench = q.get("bench") or {}
    spy = bench.get("SPY") or {}
    rel = {"dates": [], "vals": []}
    try:
        dd_h, cc_h = p["dates"], p["close"]
        dd_s, cc_s = spy["dates"], spy["close"]
        s_map = dict(zip(dd_s, cc_s))
        base_h = base_s = None
        for d, ch in zip(dd_h, cc_h):
            if d in s_map:
                cs = s_map[d]
                if base_h is None:
                    base_h, base_s = ch, cs
                rel["dates"].append(d)
                rel["vals"].append(round((ch / base_h) / (cs / base_s) * 100, 2))
    except Exception:  # noqa: BLE001
        pass

    return {
        "colors": {"up": "#d9382f", "down": "#0f9d58", "neu": "#8a94a6",
                   "accent": "#2f6fed", "warn": "#e08b16"},
        "L": I.chart_pack(),
        "meta": C.META,
        "verdict": {"asof": q.get("asof")},
        "px": {k: p.get(k) for k in
               ("last", "last_date", "chg_1w", "chg_1m", "chg_3m", "chg_6m", "chg_1y",
                "hi52", "lo52", "from_hi52", "from_lo52", "ma20", "ma60", "ma120", "ma200",
                "vol_1y", "vol_60d", "mdd_1y", "dates", "close")},
        "bench": {k: {kk: v.get(kk) for kk in ("last", "chg_1y", "chg_1m", "chg_3m")}
                  for k, v in bench.items()},
        "rel": rel,
        "fund": q.get("fundamentals") or {},
        "fin": C.FINANCIALS["quarters"],
        "half": C.FINANCIALS["half_year"],
        "segments": C.FINANCIALS["segment_highlights"],
        "tariff": C.TARIFF,
        "scenarios": C.LONG_TERM["scenarios"],
        "stores": C.STORES,
    }


# ---------------------------------------------------------------- 模板
_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN" data-theme="light" data-lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{doc.title}}</title>
<script>
/* 主题/语言在样式生效前落定，避免浅→深闪烁。
   优先级：URL 参数（?theme=dark&lang=en）> localStorage > 系统偏好 > 默认。
   localStorage 不可用时静默降级，不影响页面。 */
(function(){try{
  var qs=location.search||'';
  function qv(n){var m=qs.match(new RegExp('[?&]'+n+'=([^&]+)'));return m?decodeURIComponent(m[1]):'';}
  var th=qv('theme')||localStorage.getItem('hd-theme');
  if(!th){th=(window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches)?'dark':'light';}
  document.documentElement.setAttribute('data-theme',th==='dark'?'dark':'light');
  var lg=qv('lang')||localStorage.getItem('hd-lang');
  if(lg==='zh'||lg==='en'){document.documentElement.setAttribute('data-lang',lg);}
}catch(e){document.documentElement.setAttribute('data-theme','light');}})();
</script>
__ECHARTS__
<style>
  :root{
    --bg:#f5f7fa; --card:#fff; --ink:#1b2230; --ink2:#4a5568; --muted:#8a94a6;
    --line:#e3e8f0; --up:#d9382f; --down:#0f9d58; --accent:#2f6fed; --warn:#e08b16;
    --soft:#fbfcfe; --thead:#f0f3f8; --rowh:#fafbfd; --note-bg:#f7f9fc;
    --badge-bg:#e8eefc; --badge-w-bg:#fdf0dd;
    --warnbox-bg:#fefaef; --warnbox-bd:#f2e0bb; --okbox-bg:#f3fbf6; --okbox-bd:#cbe9d6;
    --warnpill-bg:#fdf0dd; --okpill-bg:#e9f5ee;
    --disc-bg:#fff8f8; --disc-bd:#f0d6d6; --disc-ink:#7a3b3b;
    --ctrl-bg:#eef1f7; --ctrl-on:#fff;
    --shadow:0 1px 3px rgba(20,30,50,.04);
    --axis-line:#c9d2e0; --axis-label:#6b7686; --split:#eef1f6; --val:#4a5568;
    --tip-bg:rgba(255,255,255,.96); --tip-bd:#d8dfe9; --tip-ink:#1b2230;
    --violet:#7a5cd6;
  }
  html[data-theme="dark"]{
    --bg:#0e1219; --card:#161c26; --ink:#e7ecf4; --ink2:#b4bdcc; --muted:#7f8a9c;
    --line:#26303f; --up:#ff5f52; --down:#2bbd7a; --accent:#6b96ff; --warn:#e5a63c;
    --soft:#1a212c; --thead:#1c2431; --rowh:#181f2a; --note-bg:#182231;
    --badge-bg:#1d2b45; --badge-w-bg:#3a2e14;
    --warnbox-bg:#241f13; --warnbox-bd:#4a3d1e; --okbox-bg:#12241a; --okbox-bd:#27513a;
    --warnpill-bg:#33290f; --okpill-bg:#14301f;
    --disc-bg:#2a1a1c; --disc-bd:#4a2b2e; --disc-ink:#e2adad;
    --ctrl-bg:#1c2431; --ctrl-on:#2e3a4d;
    --shadow:0 1px 3px rgba(0,0,0,.35);
    --axis-line:#39435a; --axis-label:#93a0b5; --split:#232c3a; --val:#b6c0d0;
    --tip-bg:rgba(22,28,38,.96); --tip-bd:#3a4560; --tip-ink:#e7ecf4;
    --violet:#a08cf0;
  }
  /* 英文模式切换为国际涨跌色惯例（绿涨红跌）；深色英文用亮化变体。
     放在暗色规则之后以获得更高优先级（同 specificity，后者胜出）。 */
  html[data-lang="en"]{ --up:#0f9d58; --down:#d9382f; }
  html[data-theme="dark"][data-lang="en"]{ --up:#2bbd7a; --down:#ff5f52; }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);
    font:14px/1.66 -apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB",
    "Microsoft YaHei",Segoe UI,sans-serif;-webkit-text-size-adjust:100%}
  html[data-lang="en"] body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,
    "Helvetica Neue","PingFang SC","Microsoft YaHei",sans-serif}
  a{color:var(--accent);text-decoration:none} a:hover{text-decoration:underline}
  .wrap{max-width:1180px;margin:0 auto;padding:24px 18px 70px}
  header.top{border-bottom:2px solid var(--ink);padding-bottom:14px;margin-bottom:22px}
  .hd-row{display:flex;gap:14px;align-items:flex-start;justify-content:space-between;flex-wrap:wrap}
  h1{margin:0 0 6px;font-size:25px;letter-spacing:.3px}
  h1 small{font-size:14px;color:var(--muted);font-weight:400;margin-left:8px}
  .asof{color:var(--muted);font-size:12.5px}
  .badges{margin-top:10px;display:flex;gap:7px;flex-wrap:wrap}
  .badge{background:var(--badge-bg);color:var(--accent);border-radius:20px;padding:3px 11px;font-size:12px}
  .badge.w{background:var(--badge-w-bg);color:var(--warn)}
  .ctrl{display:flex;gap:8px;flex-wrap:wrap;flex:0 0 auto}
  .seg{display:inline-flex;background:var(--ctrl-bg);border-radius:9px;padding:3px;border:1px solid var(--line)}
  .seg button{border:0;background:transparent;color:var(--ink2);font:inherit;font-size:12.5px;
    padding:4px 12px;border-radius:7px;cursor:pointer;white-space:nowrap;line-height:1.5}
  .seg button:hover{color:var(--ink)}
  .seg button.on{background:var(--ctrl-on);color:var(--accent);font-weight:600;
    box-shadow:0 1px 2px rgba(20,30,50,.12)}
  h2{font-size:18px;margin:34px 0 12px;padding-left:11px;border-left:4px solid var(--accent)}
  h3{font-size:15px;margin:20px 0 9px;color:var(--ink2)}
  h4{font-size:13.5px;margin:16px 0 7px;color:var(--ink2)}
  .card{background:var(--card);border:1px solid var(--line);border-radius:11px;
    padding:16px 18px;margin-bottom:14px;box-shadow:var(--shadow)}
  .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
  .kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:11px 13px}
  .k-name{font-size:11.5px;color:var(--muted);letter-spacing:.4px}
  .k-big{font-size:21px;font-weight:600;margin:3px 0 1px;font-variant-numeric:tabular-nums}
  .k-sub{font-size:12px;color:var(--ink2)}
  .k-foot{font-size:11px;color:var(--muted);margin-top:3px}
  .up{color:var(--up)} .down{color:var(--down)} .neu{color:var(--ink)}
  table.tbl{width:100%;border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums}
  table.tbl th,table.tbl td{border-bottom:1px solid var(--line);padding:7px 9px;text-align:right}
  table.tbl thead th{background:var(--thead);font-weight:600;font-size:12px;color:var(--ink2)}
  table.tbl .row-h{text-align:left;font-weight:500;color:var(--ink2);background:var(--rowh)}
  .th-sub{display:block;font-size:10.5px;color:var(--muted);font-weight:400}
  .td-sub{display:block;font-size:10.5px;color:var(--muted)}
  table.compact th,table.compact td{padding:6px 8px;font-size:12.5px}
  .src{color:var(--muted);font-size:11px;text-align:left}
  .list{margin:6px 0 0;padding-left:19px}
  .list li{margin:4px 0}
  .list.quote li{color:var(--ink2);font-style:italic}
  .list.news li{margin:6px 0;line-height:1.55}
  .dash{color:var(--muted)}
  .note{background:var(--note-bg);border-left:3px solid var(--accent);padding:9px 12px;
    font-size:12.8px;color:var(--ink2);border-radius:0 6px 6px 0;margin:10px 0}
  .muted{color:var(--muted)}
  .two{display:grid;grid-template-columns:1fr 1fr;gap:12px}
  @media(max-width:760px){.two{grid-template-columns:1fr}}
  .box{border-radius:10px;padding:12px 15px;border:1px solid var(--line)}
  .warn-box{background:var(--warnbox-bg);border-color:var(--warnbox-bd)}
  .ok-box{background:var(--okbox-bg);border-color:var(--okbox-bd)}
  .vlist{list-style:none;padding:0;margin:0}
  .vlist li{display:flex;gap:10px;padding:7px 0;border-bottom:1px dashed var(--line);font-size:13px}
  .vlist li:last-child{border-bottom:0}
  .vtag{flex:0 0 96px;font-size:11.5px;color:#fff;background:var(--accent);
    border-radius:5px;text-align:center;height:20px;line-height:20px;white-space:nowrap}
  html[data-lang="en"] .vtag{flex-basis:118px;font-size:10.5px}
  .vtag.warn{background:var(--warn)} .vtag.down{background:var(--down)} .vtag.up{background:var(--up)}
  .pillars{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:11px}
  .pillar{border:1px solid var(--line);border-radius:10px;padding:12px 14px;background:var(--soft)}
  .pl-en{font-size:11.5px;color:var(--accent);letter-spacing:.3px}
  .pl-cn{font-size:15px;font-weight:600;margin:2px 0 5px}
  .pl-desc{font-size:12.4px;color:var(--ink2)}
  .ppl{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px}
  .person{border:1px solid var(--line);border-radius:10px;padding:11px 13px;background:var(--soft)}
  .p-head{display:flex;justify-content:space-between;align-items:baseline;gap:8px;flex-wrap:wrap}
  .p-title{font-size:11.5px;color:var(--muted)}
  .p-status{font-size:11.5px;margin-top:5px;display:inline-block;padding:1px 8px;border-radius:20px}
  .p-status.warn{background:var(--warnpill-bg);color:var(--warn)}
  .p-status.ok{background:var(--okpill-bg);color:var(--down)}
  .p-note{font-size:12.2px;color:var(--ink2);margin-top:6px}
  .chart{width:100%;height:330px}
  .chart.sm{height:270px}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:13px}
  @media(max-width:820px){.grid2{grid-template-columns:1fr}}
  footer{margin-top:40px;padding-top:16px;border-top:1px solid var(--line);
    font-size:11.5px;color:var(--muted);line-height:1.75}
  .disc{background:var(--disc-bg);border:1px solid var(--disc-bd);border-radius:9px;padding:12px 15px;
    font-size:12.2px;color:var(--disc-ink);margin-top:14px}

  /* ---- 网评分 / 畅销榜 / buzz 区块 ---- */
  .bzblk{margin:0 0 18px}
  .bzblk:last-child{margin-bottom:0}
  .bzblk h4{margin:0 0 7px;font-size:13px;font-weight:600;color:var(--ink);
    display:flex;justify-content:space-between;align-items:baseline;gap:10px}
  .bzblk h4 .muted{font-weight:400;font-size:11.5px}
  table.tbl.bzt td{vertical-align:top}
  table.tbl.bzt td.num{white-space:nowrap;text-align:right}
  .bzv{color:var(--accent);font-weight:600}
  .mgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:4px}
  @media(max-width:760px){.mgrid{grid-template-columns:1fr}}
  .mcard{background:var(--soft);border:1px solid var(--line);border-radius:8px;padding:11px 13px}
  .mcard .mh{display:flex;justify-content:space-between;align-items:baseline;
    font-weight:600;font-size:12.5px;margin-bottom:5px}
  .mcard .mw{color:var(--accent);font-variant-numeric:tabular-nums}
  .mcard .md{margin:0;font-size:12px;line-height:1.62;color:var(--ink2)}
  details.lim{margin-top:11px;border-top:1px solid var(--line);padding-top:9px}
  details.lim summary{cursor:pointer;font-weight:600;font-size:12.5px;color:var(--ink)}
  details.lim ul{margin:8px 0 0}
  .bdg{display:inline-block;background:var(--badge-bg);color:var(--accent);border-radius:4px;
    padding:1px 7px;font-size:11.5px;white-space:nowrap}
  .tier{display:inline-block;background:var(--soft);border:1px solid var(--line);border-radius:4px;
    padding:0 6px;font-size:11px;color:var(--ink2);white-space:nowrap}
  .small{font-size:11.5px;line-height:1.58}

  /* ---- 章节十三：品类档次对标 / 明星图 / 差评归纳 / IR 季度卡 ---- */
  .list.hl li{display:flex;gap:9px;margin:7px 0}
  .list.hl li:before{content:"";flex:0 0 6px;height:6px;margin-top:8px;border-radius:50%;
    background:var(--accent)}
  .pimg{border:1px solid var(--line);border-radius:7px;background:#fff;object-fit:contain;
    display:block}
  .pimg.ph{display:flex;align-items:center;justify-content:center;color:var(--muted);
    font-size:10.5px;background:var(--soft)}
  .sgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:12px}
  .scard{border:1px solid var(--line);border-radius:9px;padding:10px 11px;background:var(--soft)}
  .scat{font-weight:650;margin-bottom:8px;font-size:13px}
  .srow{display:grid;grid-template-columns:1fr 1fr;gap:10px}
  .scell{text-align:center}
  .scell .pimg{margin:0 auto 6px}
  .sh{font-size:11px;color:var(--muted);margin-bottom:5px;letter-spacing:.03em}
  .sname{font-size:12px;line-height:1.42;margin-bottom:3px}
  .smeta{margin-top:2px}
  .hbar{height:9px;border-radius:5px;background:var(--ctrl-bg);overflow:hidden}
  .hbar i{display:block;height:100%;border-radius:5px;background:var(--up)}
  .sbar{height:5px;border-radius:3px;background:var(--ctrl-bg);overflow:hidden;margin:2px 0}
  .sbar i{display:block;height:100%;background:var(--accent)}
  .sbar.wm i{background:var(--violet)}
  table.heat td.hm{font-variant-numeric:tabular-nums;text-align:center}
  th.rot{writing-mode:vertical-rl;transform:rotate(180deg);text-align:left;
    white-space:nowrap;font-weight:600;padding:6px 2px;vertical-align:bottom}
  th.grp{text-align:center;background:var(--thead)}
  .ircard{border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:8px;
    padding:11px 13px;margin-bottom:11px;background:var(--soft)}
  .irq{font-weight:700;font-size:14px;margin-bottom:6px}
  .irmeta{font-size:12.5px;margin:3px 0;display:flex;gap:8px;align-items:baseline}
  .irlab{flex:0 0 62px;color:var(--muted);font-size:11.5px}
  .irhead{font-weight:600}
  ul.irdocs{margin:7px 0 0;padding-left:16px;font-size:12.5px}
  ul.irdocs li{margin:2px 0}
  ul.quote.neg li{display:block}
  .qtag{display:inline-block;background:var(--badge-w-bg);color:var(--warn);
    border-radius:4px;padding:1px 7px;font-size:11.5px;margin-right:7px;white-space:nowrap}
  .qtext{font-size:12.5px;color:var(--ink2)}
  .rk{color:var(--muted);font-weight:600}
  ul.list.read li{display:flex;gap:8px;align-items:baseline;margin:5px 0;font-size:12.5px}
  ul.list.read .bdg{flex:none}
  .lowconf{color:var(--warn);cursor:help;font-weight:700}
</style>
</head>
<body>
<div class="wrap">

<header class="top">
  <div class="hd-row">
    <div>
      <h1>Home Depot <small>{{h.sub}}</small></h1>
      <div class="asof">{{asof.data}} __ASOF__ · {{asof.px}} __PX_DATE__ · {{asof.q}} __LATEST_Q__</div>
    </div>
    <div class="ctrl">
      <div class="seg" id="segLang" role="group" aria-label="Language">
        <button type="button" data-v="zh">{{btn.zh}}</button>
        <button type="button" data-v="en">{{btn.en}}</button>
      </div>
      <div class="seg" id="segTheme" role="group" aria-label="Theme">
        <button type="button" data-v="light">{{btn.light}}</button>
        <button type="button" data-v="dark">{{btn.dark}}</button>
      </div>
    </div>
  </div>
  <div class="badges">__BADGES__</div>
</header>

<h2>{{sec1}}</h2>
<div class="card">
  <ul class="vlist">__VERDICT__</ul>
  <p class="note">{{sec1.note}}</p>
</div>
<div class="card">
  <h3>{{c.highlights}}</h3>
  __HIGHLIGHTS__
</div>

<h2>{{sec2}}</h2>
<div class="kpis">__KPI__</div>
<div class="card" style="margin-top:14px">
  <h3>{{c.px}}</h3>
  <div id="c-px" class="chart"></div>
</div>
<div class="grid2">
  <div class="card">
    <h3>{{c.rel}}</h3>
    <div id="c-rel" class="chart sm"></div>
    <p class="note">{{c.rel.note}}</p>
  </div>
  <div class="card">
    <h3>{{c.chg}}</h3>
    <div id="c-chg" class="chart sm"></div>
  </div>
</div>
<div class="card">
  <h3>{{c.struct}}</h3>
  <table class="tbl compact"><tbody>__VOLROWS__</tbody></table>
</div>

<h2>{{sec3}}</h2>
<div style="margin-bottom:14px">__UPCOMING__</div>
<div class="card">
  <h3>{{c.qtable}}</h3>
  __QTABLE__
  <p class="note">{{qtable.note}}</p>
</div>
<div class="grid2">
  <div class="card">
    <h3>{{c.fin}}</h3>
    <div id="c-fin" class="chart sm"></div>
  </div>
  <div class="card">
    <h3>{{c.mar}}</h3>
    <div id="c-mar" class="chart sm"></div>
  </div>
</div>
<div class="card">
  <h3>{{c.volsplit}}</h3>
  <div id="c-vol" class="chart sm"></div>
  <p class="note">{{volsplit.note}}</p>
</div>
<div class="card">
  <h3>{{c.seg}}</h3>
  <table class="tbl compact"><tbody>__SEGROWS__</tbody></table>
  <p class="note">{{sec3.irhint}}
    <a href="#sec-irdocs">{{sec3.irhint.link}}</a></p>
</div>

<h2>{{sec4}}</h2>
<div class="card">__LEADERS__</div>
<div class="card">
  <h3>{{c.quotes}}</h3>
  <ul class="list quote">__QUOTES__</ul>
</div>

<h2>{{sec5}}</h2>
__STORES__
<div class="card">
  <h3>{{c.store}}</h3>
  <div id="c-store" class="chart sm"></div>
  <p class="note">{{store.note}}</p>
</div>

<h2>{{sec6}}</h2>
<div class="card">
  <p class="note">__TARIFF_HEAD__</p>
  __TARIFF__
</div>
<div class="card">
  <h3>{{c.tar}}</h3>
  <div id="c-tar" class="chart sm"></div>
  <p class="note">{{tar.note}}</p>
</div>

<h2>{{sec7}}</h2>
<div class="card">
  <h3>{{c.pillars}}</h3>
  __STRATEGY__
  <p class="note">__TAM_NOTE__</p>
</div>
<div class="card">
  <h3>{{c.scenario}}</h3>
  __SCENARIO__
</div>
<div class="card">
  <h3>{{c.scenchart}}</h3>
  <div id="c-scen" class="chart sm"></div>
</div>

<h2>{{sec8}}</h2>
<div class="card">__RISK__</div>
<div class="card">
  <h3>{{c.follow}}</h3>
  __FOLLOWUP__
</div>

<h2>{{sec9}}</h2>
__PB__

<h2>{{sec10}}</h2>
<div class="card">
  <h3>{{c.filings}}</h3>
  __FILINGS__
</div>
<div class="card" id="sec-irdocs">
  <h3>{{c.irquarters}}</h3>
  __IRDOCS__
</div>
<div class="card">
  <h3>{{c.news}}</h3>
  __NEWS__
</div>

<footer>
  <div><b>{{ft.src}}</b>：{{ft.src.v}}</div>
  <div><b>{{ft.freq}}</b>：{{ft.freq.v}}</div>
  <div><b>{{ft.rule}}</b>：{{ft.rule.v}}</div>
  <div class="disc">__DISCLAIMER__</div>
</footer>

</div>
<script id="payload" type="application/json">__PAYLOAD__</script>
<script>
(function () {
  var D = JSON.parse(document.getElementById('payload').textContent);
  var L = D.L || { zh: {}, en: {} };
  var root = document.documentElement;
  var lang = root.getAttribute('data-lang') === 'en' ? 'en' : 'zh';
  var theme = root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';

  function t(k) {
    var m = L[lang] || {};
    if (m[k] != null) { return m[k]; }
    return (L.zh && L.zh[k] != null) ? L.zh[k] : k;
  }
  function cv(n, fb) {
    var v = getComputedStyle(root).getPropertyValue(n);
    v = v ? v.trim() : '';
    return v || fb;
  }
  var UP, DOWN, NEU, ACC, WARN, VAL;
  function palette() {
    UP = cv('--up', '#d9382f'); DOWN = cv('--down', '#0f9d58');
    NEU = cv('--ink', '#1b2230'); ACC = cv('--accent', '#2f6fed');
    WARN = cv('--warn', '#e08b16'); VAL = cv('--val', '#4a5568');
  }
  function col(v) { return v > 0 ? UP : (v < 0 ? DOWN : NEU); }
  function AX() {
    return {
      axisLine: { lineStyle: { color: cv('--axis-line', '#c9d2e0') } },
      axisLabel: { color: cv('--axis-label', '#6b7686'), fontSize: 11 },
      splitLine: { lineStyle: { color: cv('--split', '#eef1f6') } }
    };
  }
  function TIP(extra) {
    var o = { backgroundColor: cv('--tip-bg', '#fff'), borderColor: cv('--tip-bd', '#d8dfe9'),
              textStyle: { color: cv('--tip-ink', '#1b2230'), fontSize: 12 } };
    if (extra) { for (var k in extra) { o[k] = extra[k]; } }
    return o;
  }
  function LBL() { return { color: cv('--val', '#4a5568'), fontSize: 10 }; }
  function LEG() { return { top: 0, textStyle: { fontSize: 11, color: cv('--axis-label', '#6b7686') } }; }

  /* ---------- 懒渲染 + 可重绘 ---------- */
  var charts = [], pending = [], io = null;
  function drawOne(it) {
    if (it.chart || !window.echarts) { return; }
    var el = document.getElementById(it.id);
    if (!el) { return; }
    it.chart = echarts.init(el);
    it.chart.setOption(it.opt);
  }
  function makeIO() {
    if (io) { io.disconnect(); }
    io = ('IntersectionObserver' in window)
      ? new IntersectionObserver(function (es) {
          es.forEach(function (e) {
            if (!e.isIntersecting) { return; }
            for (var i = 0; i < pending.length; i++) {
              if (document.getElementById(pending[i].id) === e.target) { drawOne(pending[i]); break; }
            }
            io.unobserve(e.target);
          });
        }, { rootMargin: '800px 0px' })
      : null;
  }
  var builders = [];
  function chart(id, fn) { builders.push({ id: id, fn: fn }); }
  function render() {
    try { charts.forEach(function (c) { c.dispose(); }); } catch (e) { /* noop */ }
    charts = []; pending = []; makeIO();
    palette();
    builders.forEach(function (b) {
      var el = document.getElementById(b.id);
      if (!el || !window.echarts) { return; }
      var opt = null;
      try { opt = b.fn(); } catch (e) { return; }
      if (!opt) { return; }
      var it = { id: b.id, opt: opt, chart: null };
      if (io) { pending.push(it); io.observe(el); } else { drawOne(it); }
    });
  }
  window.addEventListener('resize', function () {
    charts.forEach(function (c) { c.resize(); });
  });

  /* ---------- 1. 股价走势 ---------- */
  chart('c-px', function () {
    var P = D.px;
    if (!P.dates || !P.dates.length) { return null; }
    var series = [{
      name: t('px.hd'), type: 'line', data: P.close, showSymbol: false,
      lineStyle: { width: 1.8, color: ACC }, itemStyle: { color: ACC },
      areaStyle: { color: ACC, opacity: 0.08 }
    }];
    [['ma20', 'MA20', WARN], ['ma60', 'MA60', cv('--muted', '#8a94a6')], ['ma200', 'MA200', cv('--violet', '#7a5cd6')]]
      .forEach(function (m) {
        if (!P[m[0]]) { return; }
        series.push({
          name: m[1], type: 'line', showSymbol: false,
          lineStyle: { width: 1, color: m[2], type: 'dashed' },
          data: P.dates.map(function (d, i) {
            if (i < 3) { return null; }
            var w = m[0] === 'ma20' ? 20 : (m[0] === 'ma60' ? 60 : 200);
            if (i + 1 < w) { return null; }
            var s = 0; for (var k = i - w + 1; k <= i; k++) { s += P.close[k]; }
            return +(s / w).toFixed(2);
          })
        });
      });
    return {
      color: [ACC, WARN, cv('--muted', '#8a94a6'), cv('--violet', '#7a5cd6')],
      tooltip: TIP({ trigger: 'axis' }),
      legend: LEG(),
      grid: { left: 52, right: 18, top: 34, bottom: 32 },
      xAxis: Object.assign({ type: 'category', data: P.dates, boundaryGap: false }, AX()),
      yAxis: Object.assign({ type: 'value', scale: true }, AX()),
      series: series
    };
  });

  /* ---------- 2. 相对强弱 ---------- */
  chart('c-rel', function () {
    var R = D.rel;
    if (!R.dates || !R.dates.length) { return null; }
    return {
      tooltip: TIP({ trigger: 'axis' }),
      grid: { left: 48, right: 16, top: 16, bottom: 30 },
      xAxis: Object.assign({ type: 'category', data: R.dates, boundaryGap: false }, AX()),
      yAxis: Object.assign({ type: 'value', scale: true }, AX()),
      series: [{
        name: t('rel.name'), type: 'line', data: R.vals, showSymbol: false,
        lineStyle: { width: 1.8, color: DOWN }, itemStyle: { color: DOWN },
        areaStyle: { color: DOWN, opacity: 0.08 },
        markLine: {
          silent: true, symbol: 'none', data: [{ yAxis: 100 }],
          lineStyle: { color: cv('--axis-line', '#b9c3d1'), type: 'dashed' },
          label: { formatter: t('rel.base'), fontSize: 10, color: cv('--muted', '#8a94a6') }
        }
      }]
    };
  });

  /* ---------- 3. 多周期涨跌 ---------- */
  chart('c-chg', function () {
    var P = D.px;
    var labs = [t('chg.1w'), t('chg.1m'), t('chg.3m'), t('chg.6m'), t('chg.1y')];
    var vals = [P.chg_1w, P.chg_1m, P.chg_3m, P.chg_6m, P.chg_1y];
    var data = vals.map(function (v) { return { value: v, itemStyle: { color: col(v) } }; });
    return {
      tooltip: TIP({
        trigger: 'axis', axisPointer: { type: 'shadow' },
        formatter: function (p) {
          return labs[p[0].dataIndex] + ': ' + (p[0].value == null ? '—' : p[0].value + '%');
        }
      }),
      grid: { left: 44, right: 20, top: 14, bottom: 30 },
      xAxis: Object.assign({ type: 'category', data: labs }, AX()),
      yAxis: Object.assign({ type: 'value' }, AX()),
      series: [{
        type: 'bar', data: data, barWidth: '52%',
        label: { show: true, position: 'top', fontSize: 11, color: VAL,
          formatter: function (p) { return p.value == null ? '' : p.value + '%'; } }
      }]
    };
  });

  /* ---------- 4. 营收与净利 ---------- */
  chart('c-fin', function () {
    var F = D.fin || [];
    if (!F.length) { return null; }
    return {
      color: [ACC, WARN],
      tooltip: TIP({ trigger: 'axis', axisPointer: { type: 'shadow' } }),
      legend: LEG(),
      grid: { left: 60, right: 18, top: 34, bottom: 28 },
      xAxis: Object.assign({ type: 'category', data: F.map(function (q) { return q.label; }) }, AX()),
      yAxis: Object.assign({ type: 'value' }, AX()),
      series: [
        { name: t('fin.sales'), type: 'bar', barWidth: '32%',
          data: F.map(function (q) { return q.net_sales; }),
          label: { show: true, position: 'top', fontSize: 10, color: VAL } },
        { name: t('fin.earn'), type: 'bar', barWidth: '32%',
          data: F.map(function (q) { return q.net_earnings; }),
          label: { show: true, position: 'top', fontSize: 10, color: VAL } }
      ]
    };
  });

  /* ---------- 5. 利润率 ---------- */
  chart('c-mar', function () {
    var F = D.fin || [];
    if (!F.length) { return null; }
    return {
      color: [cv('--violet', '#7a5cd6'), DOWN, WARN],
      tooltip: TIP({ trigger: 'axis', valueFormatter: function (v) { return v + '%'; } }),
      legend: LEG(),
      grid: { left: 48, right: 18, top: 34, bottom: 28 },
      xAxis: Object.assign({ type: 'category', data: F.map(function (q) { return q.label; }) }, AX()),
      yAxis: Object.assign({ type: 'value', axisLabel: { formatter: '{value}%', color: cv('--axis-label', '#6b7686'), fontSize: 11 } }, AX()),
      series: [
        { name: t('mar.gross'), type: 'line', data: F.map(function (q) { return q.gross_margin; }),
          symbolSize: 7, label: { show: true, fontSize: 10, color: VAL } },
        { name: t('mar.op'), type: 'line', data: F.map(function (q) { return q.operating_margin; }),
          symbolSize: 7, label: { show: true, fontSize: 10, color: VAL } }
      ]
    };
  });

  /* ---------- 6. 量价拆分 ---------- */
  chart('c-vol', function () {
    var F = D.fin || [];
    if (!F.length) { return null; }
    return {
      tooltip: TIP({ trigger: 'axis', axisPointer: { type: 'shadow' },
        valueFormatter: function (v) { return v + '%'; } }),
      legend: LEG(),
      grid: { left: 52, right: 18, top: 34, bottom: 28 },
      xAxis: Object.assign({ type: 'category', data: F.map(function (q) { return q.label; }) }, AX()),
      yAxis: Object.assign({ type: 'value', axisLabel: { formatter: '{value}%', color: cv('--axis-label', '#6b7686'), fontSize: 11 } }, AX()),
      series: [
        { name: t('vol.ticket'), type: 'bar', barWidth: '30%',
          data: F.map(function (q) { return { value: q.avg_ticket_yoy, itemStyle: { color: col(q.avg_ticket_yoy) } }; }) },
        { name: t('vol.tx'), type: 'bar', barWidth: '30%',
          data: F.map(function (q) { return { value: q.transactions_yoy, itemStyle: { color: col(q.transactions_yoy) } }; }) }
      ]
    };
  });

  /* ---------- 7. 门店扩张 ---------- */
  chart('c-store', function () {
    var S = D.stores;
    return {
      tooltip: TIP({ trigger: 'axis', axisPointer: { type: 'shadow' } }),
      legend: LEG(),
      grid: { left: 58, right: 18, top: 34, bottom: 28 },
      xAxis: Object.assign({ type: 'category', data: [t('store.retail'), t('store.srs')] }, AX()),
      yAxis: Object.assign({ type: 'value' }, AX()),
      series: [
        { name: t('store.total'), type: 'bar', barWidth: '26%',
          data: [S.retail, S.srs_locations].map(function (v) { return { value: v, itemStyle: { color: ACC } }; }),
          label: { show: true, position: 'top', fontSize: 11, color: VAL } },
        { name: t('store.plan'), type: 'bar', barWidth: '26%',
          data: [S.expansion.fy2026_new_stores, 45].map(function (v) { return { value: v, itemStyle: { color: WARN } }; }),
          label: { show: true, position: 'top', fontSize: 11, color: VAL } }
      ]
    };
  });

  /* ---------- 8. 关税传导 ---------- */
  chart('c-tar', function () {
    var items = [
      { n: t('tar.refund'), v: 145, c: UP },
      { n: t('tar.cost'), v: -60, c: DOWN },
      { n: t('tar.acq'), v: -60, c: DOWN },
      { n: t('tar.net'), v: 25, c: cv('--violet', '#7a5cd6') }
    ];
    return {
      tooltip: TIP({ trigger: 'axis', axisPointer: { type: 'shadow' },
        valueFormatter: function (v) { return v + ' ' + t('tar.unit'); } }),
      grid: { left: 150, right: 52, top: 16, bottom: 30 },
      xAxis: Object.assign({ type: 'value', axisLabel: { formatter: '{value}', color: cv('--axis-label', '#6b7686'), fontSize: 11 } }, AX()),
      yAxis: Object.assign({ type: 'category', data: items.map(function (x) { return x.n; }) }, AX()),
      series: [{
        type: 'bar', barWidth: '50%',
        data: items.map(function (x) { return { value: x.v, itemStyle: { color: x.c } }; }),
        label: { show: true, position: 'right', fontSize: 11, color: VAL,
          formatter: function (p) { return (p.value > 0 ? '+' : '') + p.value + ' ' + t('tar.unit'); } }
      }]
    };
  });

  /* ---------- 9. 情景对比 ---------- */
  chart('c-scen', function () {
    var SCN = D.scenarios || [];
    if (!SCN.length) { return null; }
    var zhMode = (lang === 'zh');
    var names = SCN.map(function (s, i) {
      var en = D.scen_en && D.scen_en[i] ? D.scen_en[i].name : s.name;
      return zhMode ? s.name : en;
    });
    function nums(key) {
      return SCN.map(function (s) {
        var m = String(s[key] || '').match(/-?\d+(\.\d+)?/g);
        if (!m) { return null; }
        var a = parseFloat(m[0]);
        if (m.length > 1) { a = (a + parseFloat(m[1])) / 2; }
        return a;
      });
    }
    return {
      tooltip: TIP({
        trigger: 'axis', axisPointer: { type: 'shadow' },
        formatter: function (ps) {
          var i = ps[0].dataIndex, s = SCN[i];
          var en = (D.scen_en && D.scen_en[i]) ? D.scen_en[i] : s;
          var v = zhMode ? s : en;
          return '<b>' + names[i] + '</b><br/>' + t('tt.sales') + ': ' + v.sales + '<br/>' +
                 t('tt.comps') + ': ' + v.comps + '<br/>' + t('tt.eps') + ': ' + v.eps;
        }
      }),
      legend: LEG(),
      grid: { left: 48, right: 20, top: 34, bottom: 30 },
      xAxis: Object.assign({ type: 'category', data: names }, AX()),
      yAxis: Object.assign({ type: 'value', axisLabel: { formatter: '{value}%', color: cv('--axis-label', '#6b7686'), fontSize: 11 } }, AX()),
      series: [
        { name: t('scen.sales'), type: 'bar', barWidth: '30%',
          data: nums('sales').map(function (v) { return { value: v, itemStyle: { color: ACC } }; }),
          label: { show: true, position: 'top', fontSize: 10, color: VAL,
            formatter: function (p) { return p.value == null ? '' : p.value + '%'; } } },
        { name: t('scen.comps'), type: 'bar', barWidth: '30%',
          data: nums('comps').map(function (v) { return { value: v, itemStyle: { color: WARN } }; }),
          label: { show: true, position: 'top', fontSize: 10, color: VAL,
            formatter: function (p) { return p.value == null ? '' : p.value + '%'; } } }
      ]
    };
  });

  /* ---------- 语言 / 主题切换 ---------- */
  function store(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* noop */ } }

  function applyLang(next) {
    lang = (next === 'en') ? 'en' : 'zh';
    root.setAttribute('data-lang', lang);
    root.setAttribute('lang', lang === 'en' ? 'en' : 'zh-CN');
  var nodes = document.querySelectorAll('.i18n');
  function md(s) { return String(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>'); }
  for (var i = 0; i < nodes.length; i++) {
      var v = nodes[i].getAttribute('data-' + lang);
      if (v != null) { nodes[i].innerHTML = md(v); }
  }
    document.title = t('doc.title');
    syncSeg();
    render();
  }
  function applyTheme(next) {
    theme = (next === 'dark') ? 'dark' : 'light';
    root.setAttribute('data-theme', theme);
    syncSeg();
    render();
  }
  function syncSeg() {
    sync('segLang', lang);
    sync('segTheme', theme);
  }
  function sync(id, val) {
    var box = document.getElementById(id);
    if (!box) { return; }
    var bs = box.querySelectorAll('button');
    for (var i = 0; i < bs.length; i++) {
      var on = bs[i].getAttribute('data-v') === val;
      if (on) { bs[i].classList.add('on'); } else { bs[i].classList.remove('on'); }
    }
  }
  function bindSeg(id, fn, key) {
    var box = document.getElementById(id);
    if (!box) { return; }
    box.addEventListener('click', function (e) {
      var b = e.target;
      while (b && b.tagName !== 'BUTTON') { b = b.parentNode; }
      if (!b || b.tagName !== 'BUTTON') { return; }
      var v = b.getAttribute('data-v');
      store(key, v);
      fn(v);
    });
  }
  bindSeg('segLang', applyLang, 'hd-lang');
  bindSeg('segTheme', applyTheme, 'hd-theme');

  applyLang(lang);
  if (theme === 'dark') { root.setAttribute('data-theme', 'dark'); }
})();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------- 组装
def _vol_rows(q: dict) -> str:
    p = q.get("price") or {}
    f = q.get("fundamentals") or {}
    rows = [
        ("vr.range", f"${_n(p.get('lo52'))} – ${_n(p.get('hi52'))}"),
        ("vr.fromhl", _pct(p.get("from_hi52")) + " / " + _pct(p.get("from_lo52"))),
        ("vr.mdd", _pct(p.get("mdd_1y"))),
        ("vr.vol1y", _pct(p.get("vol_1y"), 1, sign=False)),
        ("vr.vol60", _pct(p.get("vol_60d"), 1, sign=False)),
        ("vr.beta", _n(f.get("beta"))),
        ("vr.ma20", f"${_n(p.get('ma20'))} / ${_n(p.get('ma60'))}（" +
         bi("现价", "vs price") + " " + _pct(p.get("vs_ma20")) + " / " + _pct(p.get("vs_ma60")) + "）"),
        ("vr.ma200", f"${_n(p.get('ma200'))}（" + bi("现价", "vs price") + " " + _pct(p.get("vs_ma200")) + "）"),
        ("vr.mcap", _usd_b(f.get("market_cap")) + " / " + _usd_b(f.get("ev"))),
        ("vr.ttm", _usd_b(f.get("revenue_ttm")) + " / " + _usd_b(f.get("free_cashflow"))),
    ]
    return "".join("<tr><th class='row-h'>" + S(k) + "</th><td>" + v + "</td></tr>" for k, v in rows)


def _seg_rows() -> str:
    rows = []
    for i, x in enumerate(C.FINANCIALS["segment_highlights"]):
        e = I.FACT_SEGMENTS[i] if i < len(I.FACT_SEGMENTS) else {}
        rows.append("<tr><th class='row-h'>" + bi(x["k"], e.get("k", x["k"])) + "</th>"
                    "<td>" + bi(x["v"], e.get("v", x["v"])) + "</td>"
                    "<td class='src'>" + I.src_bi(x.get("src", "")) + "</td></tr>")
    return "".join(rows)


def _quotes() -> str:
    qs = [
        ("Q2 FY2026 财报新闻稿 · CFO Richard McPhail",
         "Our second quarter results exceeded our expectations. We saw broad based demand across the "
         "business as customers continued to engage in smaller projects."),
        ("Q2 FY2026 财报新闻稿 · SEVP Ann-Marie Campbell",
         "This quarter's results were a testament to our investments across the business and our "
         "associates' focus on customer service. Our teams did an exceptional job executing throughout "
         "a dynamic environment."),
        ("Q2 FY2026 电话会 · CFO McPhail（关于关税退款）",
         "Tariff refunds are a market-borne benefit. What tariff refunds allowed us to do was offset "
         "increased costs in our environment, and it allowed us to maintain values in the market."),
        ("Q2 FY2026 电话会 · CFO McPhail（关于全年口径）",
         "We expect the increased costs will fully offset the benefit from tariff refunds over the year."),
        ("Q2 FY2026 电话会 · CFO McPhail（关于需求与住房）",
         "While consumer uncertainty and housing affordability continue to pressure demand for larger "
         "home improvement projects, we remain focused on what we can control."),
        ("2025 投资者大会 · CEO Ted Decker",
         "We believe we are well positioned to grow share in an approximately $1.1 trillion total "
         "addressable market."),
        ("2025 投资者大会 · CFO McPhail（关于市场复苏情景）",
         "Our Market Recovery Case reflects our performance expectations once we see momentum in housing "
         "activity and increased spend on larger projects driven by pent-up demand."),
    ]
    out = []
    for i, (tag, body) in enumerate(qs):
        en_tag = I.FACT_QUOTES_TAGS[i] if i < len(I.FACT_QUOTES_TAGS) else tag
        out.append("<li><b>" + bi(tag, en_tag) + "</b><br>" + _esc(body) + "</li>")
    return "".join(out)


def _badges(q: dict) -> str:
    p = q.get("price") or {}
    f = I.FACT_BADGES_FIXED
    out = []
    if (p.get("from_lo52") or 99) < C.THRESHOLDS["near_low_pct"]:
        out.append(("w", bi("股价处于 52 周低点附近", f["near_low"])))
    if (p.get("chg_1y") or 0) < 0:
        out.append(("w", bi("近一年 " + _pct(p.get("chg_1y")), "1Y " + _pct(p.get("chg_1y")))))
    out.append(("", bi("CEO 临时病休中", f["ceo_leave"])))
    out.append(("", bi("关税退款一次性收益", f["refund"])))
    out.append(("", bi("SRS 分销高增长", f["srs"])))
    return "".join('<span class="badge ' + c + '">' + t + "</span>" for c, t in out)


def build() -> str:
    q = load("quote.json", {}) or {}
    fil = load("filings.json", {}) or {}
    ir = load("ir.json", {}) or {}
    news = load("news.json", {}) or {}

    p = q.get("price") or {}
    q2 = C.FINANCIALS["quarters"][0]
    vd = verdict(q)
    vitems = "".join(
        '<li><span class="vtag ' + c + '">' + S(tag) + '</span><span>' + bi(zh, en) + "</span></li>"
        for tag, c, zh, en in vd["points"])

    payload = build_payload(q, fil, ir, news)
    # 情景英文名单独给图表用（中文名在 scenarios[].name）
    payload["scen_en"] = I.FACT_LONG_TERM["scenarios"]

    tpl = _TEMPLATE
    repl = {
        "__ECHARTS__": _echarts_head(),
        "__ASOF__": _esc(q.get("asof") or datetime.datetime.now().strftime("%Y-%m-%d %H:%M")),
        "__PX_DATE__": _esc(p.get("last_date")),
        "__LATEST_Q__": _esc(q2["label"] + "（" + q2["end"] + "）"),
        "__BADGES__": _badges(q),
        "__VERDICT__": vitems,
        "__KPI__": _kpi_cards(q),
        "__VOLROWS__": _vol_rows(q),
        "__QTABLE__": _quarter_table(),
        "__UPCOMING__": _upcoming_html(),
        "__SEGROWS__": _seg_rows(),
        "__LEADERS__": _leadership_html(),
        "__QUOTES__": _quotes(),
        "__STORES__": _store_html(),
        "__TARIFF_HEAD__": bi(C.TARIFF["headline"], I.FACT_TARIFF["headline"]),
        "__TARIFF__": _tariff_table(),
        "__STRATEGY__": _strategy_html(),
        "__TAM_NOTE__": bi(C.STRATEGY["tam"]["note"] + " " + C.STRATEGY["share"],
                           I.FACT_STRATEGY_TAM["note"] + " " + I.FACT_STRATEGY_TAM["share"]),
        "__SCENARIO__": _scenario_table(),
        "__RISK__": _risk_html(),
        "__PB__": _pb_html(),
        "__FOLLOWUP__": _followup_html(),
        "__FILINGS__": _filings_html(fil),
        "__IRDOCS__": _ir_quarters_html(ir),
        "__HIGHLIGHTS__": _highlights(q, fil, ir, news),
        "__NEWS__": _news_html(news),
        "__DISCLAIMER__": bi(C.DISCLAIMER, I.FACT_DISCLAIMER),
    }
    for k, v in repl.items():
        if k == "__ECHARTS__":
            continue
        tpl = tpl.replace(k, v)

    # 静态文案 {{key}} → 双语 span
    missing = []

    def _sub(m):
        key = m.group(1)
        if key not in I.UI:
            missing.append(key)
            return key
        return I.S(key)

    tpl = re.sub(r"\{\{([A-Za-z0-9_.]+)\}\}", _sub, tpl)
    if missing:
        raise ValueError("模板引用了不存在的文案 key：" + ", ".join(sorted(set(missing))))

    # payload 最后注入，避免其内容参与其他占位符扫描
    tpl = tpl.replace("__PAYLOAD__", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    tpl = tpl.replace("__ECHARTS__", _echarts_head())

    os.makedirs(C.DASHBOARD_DIR, exist_ok=True)
    out = os.path.join(C.DASHBOARD_DIR, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(tpl)
    return out


if __name__ == "__main__":
    print("看板已生成 →", build())
