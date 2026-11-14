# -*- coding: utf-8 -*-
"""
Home Depot (NYSE: HD) 专项研究看板 —— 配置与已核实事实库

设计原则
--------
1. **一切可回溯**：每条静态事实都标 `src`（来源文件 / 链接），看板上会展示。
   动态数据（股价、财季数字）由 fetch_hd.py 抓取，不写死在这里。
2. **量价分离**：HD 的增长常来自客单价（含关税传导）而非客流，
   所以交易数与平均客单价必须并列展示，否则会误读成"需求变好"。
3. **关税口径**：IEEPA 退款是一次性现金流收益，不是经营性改善，
   必须与"被它抵消掉的"非计划成本成对呈现。

本文件中的静态事实全部来自：
  - Q2 FY2026 财报新闻稿（2026-08-18）      data/docs/q2_release.pdf
  - Q2 FY2026 电话会记录（2026-08-18）      data/docs/q2_transcript.pdf
  - Q1 FY2026 财报新闻稿（2026-05-19）      data/docs/q1_release.pdf
  - 2025 投资者与分析师大会新闻稿（2025-12-09）
  - CEO 临时病休公告 8-K + Exhibit 99.1（2026-08-12）
人工核对日期：2026-10-05
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DOCS_DIR = os.path.join(DATA_DIR, "docs")
DASHBOARD_DIR = os.path.join(BASE_DIR, "dashboard")

# ---------------------------------------------------------------- 公司档案
META = {
    "ticker": "HD",
    "name": "The Home Depot, Inc.",
    "cn": "家得宝",
    "exchange": "NYSE",
    "cik": "0000354950",
    "sector": "Consumer Cyclical / Home Improvement Retail",
    "founded": 1978,
    "employees": 470000,
    "index_membership": ["道琼斯工业平均指数", "标普500"],
    "hq": "Atlanta, Georgia",
    "business": "全球最大的家居建材零售与专业分销商，业务覆盖美国 50 州、哥伦比亚特区、"
                "波多黎各、美属维尔京群岛、关岛、加拿大 10 省与墨西哥。",
}

# ---------------------------------------------------------------- 战略框架
# 来源：2025 Investor & Analyst Conference（2025-12-09）
STRATEGY = {
    "pillars": [
        {"key": "core", "name": "Drive Core and Culture", "cn": "做强核心业务与文化",
         "desc": "门店体验、商品可得性、员工能力——把基本盘做扎实"},
        {"key": "interconnect", "name": "Deliver a Frictionless Interconnected Experience",
         "cn": "打造无缝互联体验",
         "desc": "线上线下一体化：Express Delivery、Magic Apron AI 助手、数字化报价与履约"},
        {"key": "pro", "name": "Win the Pro", "cn": "赢下专业承包商",
         "desc": "围绕 SRS / GMS / Mingledorff's 构建 Pro 生态，从零售走向专业分销"},
    ],
    "tam": {
        "current_tn": 1.2,
        "former_tn": 1.1,
        "pro_pool_tn": 0.7,
        "hvac_pool_bn": 100,
        "note": "收购 SRS、GMS、Mingledorff's 后，可寻址市场（TAM）由约 1.1 万亿美元扩大至约 1.2 万亿美元；"
                "其中 Pro 细分机会接近 7,000 亿美元。Mingledorff's 打开了约 1,000 亿美元的暖通空调（HVAC）分销市场。",
        "src": "2025 投资者大会新闻稿 + Q2 FY2026 电话会",
    },
    "share": "美国家装市场份额约 47%–51%，为行业第一；战略重心转向高价值的「复杂 Pro」项目",
}

# ---------------------------------------------------------------- 管理层
LEADERSHIP = {
    "note": "2026-08-12 公告：董事长、总裁兼 CEO Ted Decker 因健康原因临时休假，"
            "公司预计其「未来数月内」回归，但未给出确定时间表；未任命永久继任者，"
            "由两位资深高管共同主持 CEO 办公室。",
    "src": "8-K (2026-08-11) + Exhibit 99.1 公告；8-K (2026-08-21, Item 5.02)；Q2 FY2026 电话会",
    "people": [
        {"name": "Ted Decker", "title": "董事长、总裁兼 CEO",
         "status": "临时病休中（自 2026-08-12）", "since": "2022 年任 CEO",
         "note": "Pro 战略的主要推动者；休假前主持了 2025 年投资者大会"},
        {"name": "Ann-Marie Campbell", "title": "高级执行副总裁（SEVP）",
         "status": "代理主持日常运营", "age": 61,
         "note": "1985 年以收银员身份入职，历任南部区域总裁、美国门店 EVP 等职，是公司任职最久的高管之一"},
        {"name": "Richard McPhail", "title": "执行副总裁兼 CFO",
         "status": "代理财务管理与 Pro 子公司；已指定为 SEC 口径下的临时主要执行官",
         "age": 56, "since": "2019 年 9 月任 CFO",
         "note": "2005 年入职，历任全球 FP&A、战略与业务发展 SVP；2026-08 起牵头 Office of Pro Acceleration"},
        {"name": "Billy Bastek", "title": "执行副总裁，商品（Merchandising）",
         "status": "在任；2026-08 起增管产品开发与自有品牌",
         "note": "负责品类与供应商关系、关税与供应链应对；Q2 电话会主讲商品与需求"},
        {"name": "Jordan Broggi", "title": "执行副总裁，互联零售（Interconnected Retail）",
         "status": "在任；2026-08 起增管会员体系、信用服务与支付",
         "note": "线上线下一体化履约与数字化体验的负责人", "src": "8-K (2026-08-21, Item 5.02)"},
        {"name": "Teresa Wynn Roseborough", "title": "执行副总裁、总法律顾问兼公司秘书",
         "status": "在任",
         "note": "法律、合规与公司治理负责人", "src": "8-K (2026-08-21) 签署人"},
        {"name": "Isabel Janci", "title": "副总裁，投资者关系兼司库",
         "status": "在任",
         "note": "Q2 FY2026 电话会主持人", "src": "Q2 FY2026 电话会记录"},
        {"name": "Greg Brenneman", "title": "独立首席董事",
         "status": "休假期间主持董事会", "note": "经董事会决议，由其在 CEO 缺席期间主持董事会工作"},
    ],
    # 重大变动时间线：只收录有 SEC 文件或官方公告佐证的条目
    "changes": [
        {"date": "2026-08-20", "filed": "2026-08-21（8-K Item 5.02）",
         "title": "高管职责扩容（2026-07-30 公告）",
         "detail": "Bastek 增管产品开发与自有品牌；Broggi 增管会员、信用服务与支付；"
                   "McPhail 牵头 Office of Pro Acceleration，统筹 Home Depot Pro、HD Supply、"
                   "SRS Distribution 与 Construction Resources。三人各获 50 万美元限制性股票，"
                   "自授予日两周年归属，以持续任职为条件。",
         "src": "data/docs/8k_20260821_exec_changes.htm"},
        {"date": "2026-08-11", "filed": "2026-08-12（8-K + Exhibit 99.1）",
         "title": "CEO Ted Decker 临时病休",
         "detail": "因健康原因临时休假，预计「未来数月内」回归但无确定时间表；未任命永久继任者。"
                   "由 Campbell 与 McPhail 共同主持 CEO 办公室，McPhail 为 SEC 口径下临时主要执行官，"
                   "Brenneman 主持董事会。",
         "src": "8-K (2026-08-12) + Exhibit 99.1"},
    ],
}

# ---------------------------------------------------------------- 门店与扩张
STORES = {
    "retail": 2364,
    "srs_locations": 1340,
    "srs_note": "SRS 网点数为「1,340 余处」",
    "countries": "美国 50 州 + 哥伦比亚特区 + 波多黎各 + 美属维尔京群岛 + 关岛 + 加拿大 10 省 + 墨西哥",
    "expansion": {
        "q2_opened": 3,
        "fy2026_new_stores": 15,
        "fy2026_new_srs_branches": "40–50",
        "note": "零售门店扩张已进入低速阶段（全年约 15 家），"
                "增量扩张主要发生在 SRS 分销网点（40–50 家/年）。",
    },
    "src": "Q2 FY2026 新闻稿 + 电话会",
}

# ---------------------------------------------------------------- 中美贸易 / 关税
TARIFF = {
    "headline": "IEEPA 关税退款是 Q2 利润超预期的主要来源，但属一次性收益，且全年将被上升的投入成本抵消。",
    "facts": [
        {"k": "退款总额（Q2 收到）", "v": "$7.30 亿", "src": "Q2 电话会 / 8-K"},
        {"k": "流入销货成本（COGS）", "v": "$6.85 亿", "src": "Q2 电话会 CFO 表述"},
        {"k": "对毛利率的拉动", "v": "约 +145 个基点", "src": "Q2 电话会 Q&A"},
        {"k": "被非计划燃料/能源/投入成本吃掉", "v": "约 −60 个基点", "src": "Q2 电话会 Q&A"},
        {"k": "被收购结构（GMS / Mingledorff's）拖累", "v": "约 −60 个基点", "src": "Q2 电话会 Q&A"},
        {"k": "净改善", "v": "约 +25 个基点 → Q2 毛利率 33.7%", "src": "Q2 电话会 Q&A"},
        {"k": "剩余可收退款", "v": "「不重大」，下半年少量", "src": "Q2 电话会 CFO 表述"},
    ],
    "management_view": [
        "CFO McPhail：「退款是市场共担的收益（market-borne benefit），它让我们得以在成本上行时维持市场价格。」",
        "CFO McPhail：「我们预期，全年的成本上行会完全抵消掉关税退款带来的收益。」",
        "因此 Q2 的高毛利不可外推 —— 退款集中在 Q2、Q3 兑现，下半年面临高基数对比。",
    ],
    "policy_timeline": [
        {"date": "2026-07", "event": "Section 101 关税条款到期，形成增量成本压力"},
        {"date": "2026-08", "event": "Q2 收到 IEEPA 关税退款 $7.30 亿，为申报金额的「绝大部分」"},
        {"date": "2026 H2", "event": "退款收益退坡，公司需自行消化燃料、能源及商品投入成本上行"},
    ],
    "supply_chain": "公司持续推动供应链多元化以降低关税与贸易政策风险（见财报前瞻性声明中的"
                    "「trade policy changes… diversify our supply chain」表述）。"
                    "SRS/GMS 等分销资产本身即降低了对单一进口来源的依赖。",
    "src": "Q2 FY2026 电话会记录（2026-08-18）+ 新闻稿指引脚注",
}

# ---------------------------------------------------------------- 财务指引与长期目标
GUIDANCE = {
    "fy": "FY2026",
    "as_of": "2026-08-18（Q2 财报重申）",
    "items": [
        {"k": "总销售额增长", "v": "约 2.5% – 4.5%"},
        {"k": "可比销售增长", "v": "约 持平 – 2.0%"},
        {"k": "新开门店", "v": "约 15 家"},
        {"k": "毛利率", "v": "约 33.1%"},
        {"k": "营业利润率", "v": "约 12.4% – 12.6%"},
        {"k": "调整后营业利润率", "v": "约 12.8% – 13.0%"},
        {"k": "有效税率", "v": "约 24.3%"},
        {"k": "净利息支出", "v": "约 $23 亿"},
        {"k": "摊薄 EPS 增长", "v": "约 持平 – 4.0%（自 FY2025 的 $14.23）"},
        {"k": "调整后摊薄 EPS 增长", "v": "约 持平 – 4.0%（自 FY2025 的 $14.69）"},
        {"k": "资本开支", "v": "约占总销售额 2.5%"},
    ],
    "note": "该指引**已包含** IEEPA 关税退款，用以部分抵消全年的非计划燃料、能源及其他投入成本。",
    "src": "Q2 FY2026 财报新闻稿",
}

LONG_TERM = {
    "note": "HD 不公布逐年的 5 年数字目标，而是给出三种情景框架（2025-12-09 投资者大会）。"
            "其中「市场复苏情景」即为公司对住房周期回归常态后的中长期能力表述。",
    "scenarios": [
        {"key": "base", "name": "基准（FY2026 指引）", "cn": "住房持续冻结",
         "sales": "2.5% – 4.5%", "comps": "持平 – 2.0%", "eps": "持平 – 4.0%",
         "desc": "家装市场 −1% ~ +1%，大型项目需求继续被压制"},
        {"key": "recovery", "name": "市场复苏情景", "cn": "住房活动回暖",
         "sales": "约 5% – 6%", "comps": "约 4% – 5%", "eps": "中至高个位数增长",
         "desc": "营业利润增速快于销售；CFO 称这是「一旦住房活动出现动能、"
                 "积压需求推动大型项目支出」时的表现预期"},
        {"key": "accelerated", "name": "加速复苏情景", "cn": "住房强劲反弹",
         "sales": "快于复苏情景", "comps": "—", "eps": "快于复苏情景",
         "desc": "若住房出现更陡峭的复苏，销售与 EPS 增长可更快"},
    ],
    "capital": [
        "资本配置纪律：**股票回购计划已暂停至 2027 年**，资源优先用于收购整合与降杠杆",
        "股息：季度派息约 $23 亿（Q2 FY2026 实际支付），派息率约 65%，属长期连续增派标的",
        "资本开支维持约总销售 2.5%",
    ],
    "src": "2025 投资者与分析师大会新闻稿（2025-12-09）+ Q2 FY2026 电话会",
}

# ---------------------------------------------------------------- 下一份财报（已官宣排期）
UPCOMING_EARNINGS = {
    "qlabel": "FY2026 Q3",
    "call": "2026-11-17（周二）9:00 ET，盘前发布",
    "note": "公司已于 2026-11-03 官宣：Q3 财报电话会定于 11 月 17 日（周二）上午 9 点 ET。"
            "截至本页数据时间，Q3 财报**尚未发布**（SEC 尚无 Q3 的 8-K / 10-Q）；"
            "材料发布后本看板将在下一轮更新中收录。",
    "webcast": "https://event.choruscall.com/mediaframe/webcast.html?webcastid=tz6tzaIE",
    "src": "公司新闻稿（PRNewswire，2026-11-03）+ ir.homedepot.com（webcast 链接与 IR 页一致）",
}

# ---------------------------------------------------------------- 已核实季度数据
# 单位：百万美元（除每股数据）。取自财报原文损益表，非第三方推算。
FINANCIALS = {
    "currency": "USD",
    "unit": "million",
    "quarters": [
        {
            "label": "Q2 FY2026", "end": "2026-08-02", "filed": "2026-08-25",
            "release": "2026-08-18",
            "net_sales": 47861, "net_sales_yoy": 5.7,
            "gross_profit": 16115, "gross_margin": 33.67,
            "operating_income": 6839, "operating_margin": 14.29,
            "net_earnings": 4766, "net_earnings_yoy": 4.7,
            "eps_diluted": 4.79, "eps_adjusted": 4.92,
            "comps": 1.7, "comps_us": 1.3,
            "transactions_m": 443.2, "transactions_yoy": -0.8,
            "avg_ticket": 92.50, "avg_ticket_yoy": 2.8,
            "prev": {"net_sales": 45277, "net_earnings": 4551,
                     "eps_diluted": 4.58, "eps_adjusted": 4.68, "comps": 1.0},
            "src": "data/docs/q2_release.pdf（损益表）",
        },
        {
            "label": "Q1 FY2026", "end": "2026-05-03", "filed": "2026-05-27",
            "release": "2026-05-19",
            # 由半年报减去 Q2 得出，两处一致
            "net_sales": 41765, "net_sales_yoy": 4.9,
            "gross_profit": 13781, "gross_margin": 33.00,
            "operating_income": 4981, "operating_margin": 11.93,
            "net_earnings": 3289, "net_earnings_yoy": None,
            "eps_diluted": 3.30, "eps_adjusted": None,
            "comps": 0.6, "comps_us": 0.4,
            "transactions_m": 391.1, "transactions_yoy": -1.0,
            "avg_ticket": 92.74, "avg_ticket_yoy": 2.2,
            "prev": {"net_sales": 39856, "net_earnings": 3433,
                     "eps_diluted": 3.45, "eps_adjusted": None, "comps": -0.3},
            "src": "data/docs/q1_release.pdf + q2_release.pdf（半年报倒推）",
        },
    ],
    "half_year": {
        "net_sales": 89626, "net_sales_yoy": 5.3,
        "operating_income": 11820, "operating_income_yoy": 1.1,
        "net_earnings": 8055, "net_earnings_yoy": 0.9,
        "eps_diluted": 8.09, "eps_diluted_yoy": 0.7,
        "comps": 1.2, "comps_prev": 0.4,
        "src": "data/docs/q2_release.pdf（六个月合计列）",
    },
    "balance_sheet": {
        "as_of": "2026-08-02",
        "cash": 2085, "receivables": 6963, "inventory": 26847,
        "total_current_assets": 37720, "net_ppe": 28147,
        "goodwill": 22899, "intangibles": 10482,
        "inventory_yoy": 8.1,
        "src": "data/docs/q2_release.pdf（简明合并资产负债表）",
    },
    "segment_highlights": [
        {"k": "SRS 分销业务", "v": "Q2 销售同比 +62% 至 $51 亿；所有垂直领域正 comp，且高于公司整体",
         "src": "Q2 电话会 + 第三方研报"},
        {"k": "大额交易（>$1,000）", "v": "同比 +2.4%", "src": "Q2 电话会"},
        {"k": "线上销售", "v": "连续第五个季度双位数增长（Q2 +11%，三年最强）", "src": "Q2 电话会"},
        {"k": "Pro vs DIY", "v": "Pro 正 comp 且跑赢 DIY；DIY 便携动力、露台、防腐木等品类走强",
         "src": "Q2 电话会（Billy Bastek）"},
        {"k": "国际", "v": "加拿大与墨西哥均跑赢公司整体", "src": "Q2 电话会"},
        {"k": "平均客单价 vs 交易量", "v": "客单价 +2.8% 而交易量 −0.8% —— 增长由价格而非客流驱动",
         "src": "Q2 财报新闻稿"},
    ],
}

# ---------------------------------------------------------------- 宏观与行业
MACRO = {
    "headwinds": [
        "成屋成交量周转率已连续四年处于多年低位（people buy and sell homes 的频次未恢复）",
        "住房可负担性压制大型改造项目，客户转向小型项目（smaller projects）",
        "美联储在杰克逊霍尔释放「更高更久（higher for longer）」信号，房贷利率维持高位",
        "美国待售房屋签约量自 2026 年春季以来持续下滑",
    ],
    "tailwinds": [
        "被压抑的大型项目需求（积压需求）一旦释放，将给家装市场强于整体经济的支撑",
        "Pro 市场份额持续提升，且在疲弱环境中仍在抢份额",
        "SRS / GMS / Mingledorff's 打开 HVAC、屋面、建材等新垂直领域",
    ],
    "note": "管理层对当前环境的定性词是「frozen（冻结）」——增长未加速，但公司在抢份额。",
    "src": "Q2 电话会 + 第三方研报综合",
}

# ---------------------------------------------------------------- 抓取配置
FETCH = {
    "ticker": "HD",
    "benchmark": "SPY",
    "peers": ["LOW", "HD", "XRT", "RTH"],
    "sec_cik": "0000354950",
    "ir_press_release_page": "https://ir.homedepot.com/financial-reports/quarterly-earnings",
    "sec_submissions": "https://data.sec.gov/submissions/CIK0000354950.json",
    "news_keywords": ["Home Depot", "家得宝", "HD stock", "home improvement retail",
                      "SRS Distribution", "Pro ecosystem", "tariff"],
    "history_days": 504,
}

THRESHOLDS = {
    "drawdown_alert_pct": -25.0,   # 距 52 周高点回撤超过该值 → 提示
    "near_low_pct": 3.0,           # 距 52 周低点不足该值 → 提示逼近低点
    "comps_weak_pct": 0.0,         # 可比销售转负 → 提示
    "vol_high_pct": 35.0,          # 年化波动率超过该值 → 提示
}

DISCLAIMER = ("以上内容基于公开数据与量化分析，仅供参考，不构成投资建议。"
              "市场有风险，投资需谨慎。任何投资决策应结合个人风险承受能力、"
              "资金状况和投资目标独立判断，必要时咨询持牌专业机构。过往表现不预示未来收益。")
