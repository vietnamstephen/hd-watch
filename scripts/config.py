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
    "employees": 472400,
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
    "note": "2026-11-17 宣布：CEO Ted Decker 已结束病休归队，并推动继任计划进入下一阶段 —— "
            "自 2026-11-23 起 Richard McPhail 出任 CEO 并进入董事会，Ann-Marie Campbell 出任总裁兼 COO，"
            "Decker 留任董事长（Chair）；Jordan Broggi 接任 CFO。临时 CEO 办公室机制同日结束。",
    "src": "8-K (2026-11-17)×2 + Q3 FY2026 电话会（2026-11-17）+ 新闻稿",
    "people": [
        {"name": "Ted Decker", "title": "董事长（Chair）", "photo": "decker",
         "status": "已结束病休归队；2026-11-23 起卸任 CEO、留任董事长", "since": "2022 年任 CEO",
         "note": "Pro 战略的主要推动者；Q3 电话会开场称「I'm glad to be back」，并主持交接安排"},
        {"name": "Richard McPhail", "title": "CEO（候任，2026-11-23 生效）", "photo": "mcphail",
         "status": "在任 CFO 至交接完成；2026-11-23 起任 CEO 并加入董事会",
         "age": 56, "since": "2019 年 9 月任 CFO，2026-11 起任 CEO",
         "note": "2005 年入职，21 年司龄；病休期间为 SEC 口径下的临时主要执行官，Q3 电话会由其主讲财务与指引"},
        {"name": "Ann-Marie Campbell", "title": "总裁兼 COO（候任，2026-11-23 生效）", "photo": "campbell",
         "status": "在任 SEVP；2026-11-23 起任总裁兼 COO", "age": 61,
         "note": "1985 年以收银员身份入职，41 年司龄；历任南部区域总裁、美国门店 EVP 等职"},
        {"name": "Jordan Broggi", "title": "CFO（候任）", "photo": "broggi",
         "status": "在任 EVP 互联零售；接任 CFO",
         "note": "13 年司龄，曾任 EVP 互联零售兼线上业务总裁，早年在财务体系（FP&A、战略、供应链财务）任职",
         "src": "Q3 FY2026 电话会（2026-11-17）"},
        {"name": "Billy Bastek", "title": "执行副总裁，商品（Merchandising）", "photo": "bastek",
         "status": "在任；2026-08 起增管产品开发与自有品牌",
         "note": "负责品类与供应商关系、关税与供应链应对；Q3 电话会主讲商品与需求"},
        {"name": "Teresa Wynn Roseborough", "title": "执行副总裁、总法律顾问兼公司秘书", "photo": "roseborough",
         "status": "在任",
         "note": "法律、合规与公司治理负责人", "src": "8-K (2026-08-21) 签署人"},
        {"name": "Isabel Janci", "title": "副总裁，投资者关系兼司库", "photo": "janci",
         "status": "在任",
         "note": "Q3 FY2026 电话会主持人", "src": "Q3 FY2026 电话会记录"},
        {"name": "Greg Brenneman", "title": "独立首席董事", "photo": "brenneman",
         "status": "在任；CEO 病休期间曾主持董事会",
         "note": "经董事会决议，由其在 CEO 缺席期间主持董事会工作"},
    ],
    # 重大变动时间线：只收录有 SEC 文件或官方公告佐证的条目
    "changes": [
        {"date": "2026-11-23", "filed": "2026-11-17（8-K×2）",
         "title": "CEO 交接：McPhail 接任 CEO，Campbell 任总裁兼 COO，Decker 留任董事长",
         "detail": "Decker 结束病休归队后，董事会与其本人同意启动继任计划下一阶段：11-23 起临时 CEO 办公室"
                   "（Office of the CEO）结束，McPhail 任 CEO 并加入董事会，Campbell 任总裁兼 COO，"
                   "Decker 继续担任董事长；Jordan Broggi 接任 CFO。",
         "src": "Q3 FY2026 电话会记录（2026-11-17）+ 新闻稿 + 8-K (2026-11-17)"},
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

# ---------------------------------------------------------------- 自有品牌
# 来源分级：A = 公司官方披露（SEC 文件 / IR 材料原文）；B = 第三方估计或本项目
# 渠道抓取归纳（非公司披露，仅供参考）。HD 不在财报中披露自有品牌销售占比。
PRIVATE_BRANDS = {
    "note": "Home Depot 不在财报中披露自有品牌（Private / Exclusive Brands）的销售占比，"
            "本节只汇总可核实的官方信息与明确标注的第三方估计。",
    "trademark": {
        "grade": "A",
        "src": "最新财年 10-K「知识产权」章节（ir.homedepot.com）",
        "url": "https://ir.homedepot.com/~/media/Files/H/HomeDepot-IR/reports-and-presentations/quarterly-earnings/2025/q4-2025-10-k.pdf",
        "brands": ["HDX", "Husky", "Hampton Bay", "Home Decorators Collection",
                   "Glacier Bay", "Vigoro", "Everbilt", "LifeProof"],
        "desc": "10-K 列名的注册自有品牌商标，覆盖工具、浴室厨房、灯扇、地板、园艺、五金等核心品类；"
                "公司声明「定期评估扩充自有品牌组合」。",
    },
    "licensed": {
        "grade": "A",
        "src": "公司年报 / 公开资料",
        "brands": [
            {"name": "Ridgid / Ryobi", "desc": "电动工具独家授权（Ridgid 为 Emerson 商标、Ryobi 为 TTI 旗下）"},
            {"name": "BEHR", "desc": "涂料独家销售品牌（商标属 Masco，仅在 HD 渠道销售）"},
        ],
        "desc": "非自有但 HD 独家：授权工具平台与独家涂料，形成电池生态与油漆品类粘性。",
    },
    "outdoor_matrix": {
        "grade": "B",
        "src": "本项目 Walmart 渠道抓取归纳（data/buzz_analysis.json）",
        "items": [
            {"name": "Hampton Bay", "pos": "户外家具主力品牌"},
            {"name": "Stylewell", "pos": "性价比线"},
            {"name": "Home Decorators Collection", "pos": "高端线"},
            {"name": "Martha Stewart", "pos": "联名线"},
        ],
        "desc": "户外家具以自有品牌为主（与 Amazon 以国民品牌为主的结构形成反差）；"
                "结论来自渠道在架商品的品牌抽样，非公司披露。",
    },
    "bastek": {
        "grade": "A",
        "src": "8-K Item 5.02（filed 2026-08-21）+ 电话会",
        "desc": "商品 EVP Billy Bastek 自 2026-08 起增管「产品开发与自有品牌」，"
                "并获 $50 万限制性股票（两年归属）——管理层将自有品牌提到更高优先级的治理信号。",
    },
    "third_party": [
        {"grade": "B",
         "src": "Orply（引行业估计）",
         "url": "https://orply.com/articles/acquired/home-depot-5d215538",
         "fact": "house brands（自有 + 独家品牌）约占销售额 15%–25%"},
        {"grade": "B",
         "src": "Datavations 品类监测（Q1 2026，浴室面盆龙头）",
         "url": "https://www.datavations.ai/post/bathroom-sink-faucet-category-home-depot-lowes",
         "fact": "Glacier Bay 占 HD 该品类销售额 30%（约 $4,250 万、ASP $55，比 Kohler 低 40%），"
                 "为该品类第一品牌，高于 Delta（22%）与 Kohler（15%）"},
    ],
}

# ---------------------------------------------------------------- 门店与扩张
STORES = {
    "retail": 2372,
    "srs_locations": 1340,
    "srs_note": "SRS 网点数为「1,340 余处」",
    "countries": "美国 50 州 + 哥伦比亚特区 + 波多黎各 + 美属维尔京群岛 + 关岛 + 加拿大 10 省 + 墨西哥",
    "expansion": {
        "q2_opened": 3,
        "q3_opened": 8,
        "fy2026_new_stores": 15,
        "fy2026_new_srs_branches": "40–50",
        "note": "零售门店扩张已进入低速阶段（全年约 15 家），"
                "增量扩张主要发生在 SRS 分销网点（40–50 家/年）。",
    },
    # ---- 门店明细（10-K 原文表格，2026-02-01 口径）----
    "detail_10k": {
        "asof": "2026-02-01",
        "total": 2359,
        "overseas_stores": 324,
        "overseas_share": 13.7,
        "by_country": [
            {"name": "美国", "name_en": "United States", "stores": 2035, "share": 86.3,
             "note": "含波多黎各 10、关岛 1、美属维尔京群岛 2；本土 50 州 + 华盛顿特区合计 2,022",
             "note_en": "Includes Puerto Rico 10, Guam 1 and U.S. Virgin Islands 2; 2,022 across the "
                        "50 states and Washington, D.C."},
            {"name": "加拿大", "name_en": "Canada", "stores": 182, "share": 7.7,
             "note": "覆盖 10 个省，安大略 88 家最多",
             "note_en": "All 10 provinces; Ontario leads with 88"},
            {"name": "墨西哥", "name_en": "Mexico", "stores": 142, "share": 6.0,
             "note": "覆盖 32 个州级行政区，新莱昂 14 家最多",
             "note_en": "32 states; Nuevo León leads with 14"},
        ],
        "top_states": [["加利福尼亚", "California", 247], ["德克萨斯", "Texas", 190],
                       ["佛罗里达", "Florida", 163], ["纽约", "New York", 101],
                       ["佐治亚", "Georgia", 90], ["伊利诺伊", "Illinois", 76]],
        "avg_size": "单店约 10.4 万平方英尺室内 + 约 2.4 万平方英尺户外花园",
        "src": "FY2025 Form 10-K（截至 2026-02-01），Item 2. Properties 门店州/省明细表",
    },
    # ---- 员工明细（10-K 人力资本章节，2026-02-01 口径）----
    "workforce": {
        "asof": "2026-02-01",
        "total": 472400,
        "salaried": 53400,
        "by_country": [
            {"name": "美国", "name_en": "United States", "n": 422500, "pct": 89.4},
            {"name": "加拿大", "name_en": "Canada", "n": 31700, "pct": 6.7},
            {"name": "墨西哥", "name_en": "Mexico", "n": 17800, "pct": 3.8},
            {"name": "其他（采购办）", "name_en": "Other (sourcing)", "n": 400, "pct": 0.1},
        ],
        "other_note": "采购与采购办分布于印度、意大利、波兰、土耳其、中国台湾、越南、中国；"
                      "公司只披露「其他」合计 400 人，未逐国拆分",
        "src": "FY2025 Form 10-K，Human Capital — Geographic makeup of our workforce（第 7 页）",
    },
    "src": "Q3 FY2026 新闻稿 + 电话会；门店/员工国家分布取 FY2025 10-K",
}

# ---------------------------------------------------------------- 中美贸易 / 关税
TARIFF = {
    "headline": "IEEPA 关税退款已在 Q2 集中兑现、Q3 材料未再提及；Q3 毛利率同比降约 60 个基点，"
                "主因是成本上行与收购带来的结构变化，而非新增关税冲击。",
    "facts": [
        {"k": "Q3 毛利率", "v": "32.8%，同比 −约 60 个基点", "src": "Q3 电话会 CFO 表述"},
        {"k": "Q3 毛利率下滑原因", "v": "投入成本上升 + 收购（SRS HVAC 等）带来的品类结构变化", "src": "Q3 电话会"},
        {"k": "Q3 是否再有退款", "v": "未提及新的关税退款；Q2 的 $7.30 亿为主要一次性来源", "src": "Q3 电话会"},
        {"k": "退款总额（Q2 收到）", "v": "$7.30 亿", "src": "Q2 电话会 / 8-K"},
        {"k": "流入销货成本（COGS）", "v": "$6.85 亿", "src": "Q2 电话会 CFO 表述"},
        {"k": "对 Q2 毛利率的拉动", "v": "约 +145 个基点", "src": "Q2 电话会 Q&A"},
        {"k": "剩余可收退款", "v": "「不重大」，下半年少量", "src": "Q2 电话会 CFO 表述"},
    ],
    "management_view": [
        "CFO McPhail：「退款是市场共担的收益（market-borne benefit），它让我们得以在成本上行时维持市场价格。」",
        "CFO McPhail：「我们预期，全年的成本上行会完全抵消掉关税退款带来的收益。」",
        "Q3 McPhail：市场「比年初预期更软」，公司仍靠份额提升实现增长；营业利润率指引下移仅因毛利率结构性变化（品类结构 + 收购）。",
        "因此 Q2 的高毛利不可外推 —— 退款集中在 Q2 兑现，Q3 起毛利率已回到 32.8% 的正常化水平。",
    ],
    "policy_timeline": [
        {"date": "2026-07", "event": "Section 101 关税条款到期，形成增量成本压力"},
        {"date": "2026-08", "event": "Q2 收到 IEEPA 关税退款 $7.30 亿，为申报金额的「绝大部分」"},
        {"date": "2026-11", "event": "Q3 材料未再提及关税退款；毛利率同比 −60bp，公司归因为成本环境上升与收购结构"},
    ],
    "supply_chain": "公司持续推动供应链多元化以降低关税与贸易政策风险（见财报前瞻性声明中的"
                    "「trade policy changes… diversify our supply chain」表述）。"
                    "SRS/GMS 等分销资产本身即降低了对单一进口来源的依赖。",
    "src": "Q2 FY2026 电话会记录（2026-08-18）+ 新闻稿指引脚注",
}

# ---------------------------------------------------------------- 财务指引与长期目标
GUIDANCE = {
    "fy": "FY2026",
    "as_of": "2026-11-17（Q3 财报更新指引）",
    "items": [
        {"k": "总销售额增长", "v": "约 4.5%"},
        {"k": "可比销售增长", "v": "约 1.4%"},
        {"k": "新开门店", "v": "约 15 家（另 40–50 家 SRS 网点）"},
        {"k": "毛利率", "v": "约 33.0%"},
        {"k": "营业利润率", "v": "约 12.4%"},
        {"k": "调整后营业利润率", "v": "约 12.8%"},
        {"k": "有效税率", "v": "约 24.6%"},
        {"k": "净利息支出", "v": "约 $22 亿"},
        {"k": "摊薄 EPS 增长", "v": "约 +1.5%（自 FY2025 的 $14.23）"},
        {"k": "调整后摊薄 EPS 增长", "v": "约 +2.0%（自 FY2025 的 $14.69）"},
        {"k": "资本开支", "v": "约占总销售额 2.5%"},
    ],
    "note": "与 Q2 指引（销售 +2.5%~4.5%、可比 持平~+2.0%、营业利润率 12.4%~12.6%）相比："
            "销售与可比销售收敛为点估计并落在原区间上半部，营业利润率收敛到原区间低端 —— "
            "公司称营业利润率下移「solely」源于毛利率结构变化（品类结构与 SRS HVAC 等收购摊薄），"
            "税率为调整后 EPS 增速带来小幅压力。指引**已包含**关税退款的一次性影响。",
    "src": "Q3 FY2026 财报新闻稿（2026-11-17）+ 电话会 CFO 表述",
}

LONG_TERM = {
    "note": "HD 不公布逐年的 5 年数字目标，而是给出三种情景框架（2025-12-09 投资者大会）。"
            "其中「市场复苏情景」即为公司对住房周期回归常态后的中长期能力表述。",
    "scenarios": [
        {"key": "base", "name": "基准（FY2026 更新指引）", "cn": "住房持续冻结",
         "sales": "约 4.5%", "comps": "约 1.4%", "eps": "调整后约 +2.0%",
         "desc": "家装市场 −1% ~ +1%，大型项目需求继续被压制；Q3 后指引收敛为点估计（2026-11-17）"},
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
    "qlabel": "FY2026 Q4（全年）",
    "call": "预计 2027 年 2 月下旬（公司尚未官宣具体日期）",
    "note": "Q3 FY2026 已于 2026-11-17 盘前披露（8-K 同日提交，10-Q 待申报），"
            "本页数据已收录该季度完整损益表与电话会内容。"
            "按公司惯例，Q4 暨全年财报通常在 2 月下旬发布，具体日期以 IR 官网公告为准。",
    "webcast": "",
    "src": "ir.homedepot.com 财报日历（历史排期惯例）；Q3 数据源：data/docs/q3_release.pdf + q3_transcript.pdf",
}

# ---------------------------------------------------------------- 已核实季度数据
# 单位：百万美元（除每股数据）。取自财报原文损益表，非第三方推算。
FINANCIALS = {
    "currency": "USD",
    "unit": "million",
    "quarters": [
        {
            "label": "Q3 FY2026", "end": "2026-11-01", "filed": "10-Q 待申报（8-K 2026-11-17）",
            "release": "2026-11-17",
            "net_sales": 43398, "net_sales_yoy": 4.9,
            "gross_profit": 14220, "gross_margin": 32.77,
            "operating_income": 5479, "operating_margin": 12.62,
            "net_earnings": 3713, "net_earnings_yoy": 3.1,
            "eps_diluted": 3.72, "eps_adjusted": 3.86,
            "comps": 2.2, "comps_us": 2.2,
            "transactions_m": 392.7, "transactions_yoy": -0.2,
            "avg_ticket": 93.09, "avg_ticket_yoy": 3.0,
            "prev": {"net_sales": 41352, "net_earnings": 3601,
                     "eps_diluted": 3.62, "eps_adjusted": 3.74, "comps": 0.2},
            "src": "data/docs/q3_release.pdf（损益表）",
        },
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
        {"k": "SRS 分销业务", "v": "Q3 同店正增长；全年指引为低个位数有机增长，HVAC 垂直通过收购扩张",
         "src": "Q3 电话会（McPhail）"},
        {"k": "大额交易（>$1,000）", "v": "同比 +4.5%，由动力工具与家电驱动", "src": "Q3 电话会（Billy Bastek）"},
        {"k": "线上销售", "v": "连续第六个季度双位数增长（Q3 约 +13%）", "src": "Q3 电话会"},
        {"k": "Pro vs DIY", "v": "两者均正 comp、Pro 跑赢；DIY 家电/收纳/硬景/龙头走强",
         "src": "Q3 电话会（Billy Bastek）"},
        {"k": "国际", "v": "墨西哥、加拿大与 SRS 均为正 comp；美国北部与西部大区正增长，南部基本持平",
         "src": "Q3 电话会"},
        {"k": "平均客单价 vs 交易量", "v": "客单价 +3.0% 而交易量 −0.2% —— 增长仍由价格/结构驱动",
         "src": "Q3 财报新闻稿"},
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
