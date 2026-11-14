# -*- coding: utf-8 -*-
"""
双语词条库 —— 看板的中英对照文案。

约定
----
1. 中文事实的**权威源仍然是 config.py**（读财报原文录入，每条带 src）。
   本文件的 `FACT_*` 系列只是它的英文译文，**按位置一一对应**，
   渲染时用 `bi(中文, 英文)` 成对输出。改 config 的结构时要同步改这里。
2. `UI` 是界面自身文案（标题、表头、按钮），中英都在这里，单一来源。
3. `CH` 是 ECharts 图表内文案（canvas 里画不了 DOM，只能走 payload 字典）。
4. 任何 key 缺失都会退化为中文，不会白屏 —— 这是刻意的降级策略。
"""
import html


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def _md(s):
    """把 `**加粗**` 转成 <b>（先转义再插入标签，顺序不能反）。

    文案里长期用 ** 做强调，但渲染端一直按纯文本输出，页面上就会出现字面的星号。
    在唯一的出口处统一处理一次，避免逐个 note 手改。
    data-zh / data-en 属性里**保留原始 ** 标记**，由前端 md() 在切换语言时同样转换。
    """
    import re as _re
    return _re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", esc(s))


def bi(zh, en, tag="span"):
    """成对输出中英，前端按 data-zh / data-en 切换。"""
    return (f'<{tag} class="i18n" data-zh="{esc(zh)}" data-en="{esc(en)}">'
            f'{_md(zh)}</{tag}>')


# ================================================================ 界面文案
UI = {
    "doc.title": ("Home Depot 专项研究 · 公司运营与市场看板",
                  "Home Depot Research · Operations & Market"),
    "h.sub": ("NYSE: HD · 公司运营 · 股价 · 关税影响 · 市场反馈",
              "NYSE: HD · operations, share price, tariffs, market reaction"),
    "asof.data": ("数据时间", "Data as of"),
    "asof.px": ("行情截至", "Prices through"),
    "asof.q": ("最新财报", "Latest results"),
    "live": ("本地单文件 · 零外部请求", "Self-contained · zero external requests"),

    # ---- 一、结论摘要
    "sec1": ("一、结论摘要", "1. Executive Summary"),
    "sec1.note": (
        "本页所有结论均由下方实际抓取的数据推导，每条数据标注来源，可逐项回溯。"
        "看板不提供买卖建议，只回答「发生了什么、为什么、接下来看什么」。",
        "Every conclusion on this page is derived from the data fetched below; each item is labelled "
        "with its source and can be traced back individually. This dashboard gives no buy/sell advice — "
        "it answers only: what happened, why, and what to watch next."),

    # ---- 二、股价与市场表现
    "sec2": ("二、股价与市场表现", "2. Share Price & Market Performance"),
    "c.px": ("股价走势（近两年）", "Share price (last two years)"),
    "c.rel": ("相对标普500 强弱（归一化）", "Relative strength vs S&P 500 (rebased)"),
    "c.rel.note": ("曲线下行代表跑输大盘。归一化起点 = 100。",
                   "A falling line means underperformance. Rebased to 100 at the start."),
    "c.chg": ("多周期涨跌幅", "Returns by period"),
    "c.struct": ("波动与结构", "Volatility & structure"),

    # ---- 三、季度财报
    "sec3": ("三、季度财报归纳", "3. Quarterly Results Digest"),
    "c.upcoming": ("下一份财报排期", "Next earnings date"),
    "c.upcoming.none": ("暂无已官宣的下一份财报排期。", "No officially announced next earnings date yet."),
    "sec3.irhint": (
        "本季的官方材料共 5 份（新闻稿 / 10-Q / 电话会记录 / 非 GAAP 调节表 / 财报信息图）。"
        "读它们最常踩的坑是「不知道是哪一场」—— 每个季度里可能有多份材料、电话会记录也另有版本。"
        "「九、数据来源与口径」一节按季度列出了每份材料的**发布时间、发布方与主要标题**，"
        "电话会另标了美东开会时刻。另：§一 的要点里也已带出本季材料的日期、电话会时刻与标题。",
        "Five official documents per quarter (press release / 10-Q / call transcript / "
        "non-GAAP reconciliation / infographic). The usual pitfall is not knowing which "
        "event a document belongs to. Section 9 lists, quarter by quarter, the "
        "**release date, publisher and main headline** of every document, with the "
        "US Eastern call time called out separately."),
    "sec3.irhint.link": ("跳到季度材料清单 →", "Jump to the quarterly materials list →"),
    "c.qtable": ("核心财务对比", "Core financial comparison"),
    "qtable.h1": ("项目", "Item"),
    "qtable.note": (
        "口径说明：Q1 的季度数由半年报减去 Q2 得出，两处数据一致；客户交易量与平均客单价"
        "不含 HD Supply 与 SRS（与公司口径一致）。",
        "Method note: Q1 figures are derived by subtracting Q2 from the half-year report; the two sources "
        "agree. Customer transactions and average ticket exclude HD Supply and SRS, consistent with the "
        "company's own definition."),
    "c.fin": ("营收与净利（百万美元）", "Revenue & net earnings (US$ mn)"),
    "c.mar": ("利润率结构", "Margin structure"),
    "c.volsplit": ("量价拆分：增长从哪来", "Price vs volume: where the growth came from"),
    "volsplit.note": (
        "这是本季最容易被误读的一点 —— 交易量在下滑，增长由客单价（含关税成本传导）贡献。",
        "This is the most misread point of the quarter — transactions are falling; growth came from "
        "average ticket (including tariff cost pass-through)."),
    "c.seg": ("业务亮点", "Business highlights"),

    # ---- 四、管理层
    "sec4": ("四、管理层与治理", "4. Leadership & Governance"),
    "c.leadchanges": ("重大变动时间线（均有 SEC 文件佐证）",
                      "Key leadership changes (all backed by SEC filings)"),
    "lead.filed": ("文件", "Filing"),
    "lead.src": ("出处", "Source"),
    "c.quotes": ("本季管理层原话（摘录自财报新闻稿与电话会记录）",
                 "Management's own words this quarter (from the release and the call transcript)"),

    # ---- 五、扩店
    "sec5": ("五、扩店与 Pro 生态", "5. Store Expansion & the Pro Ecosystem"),
    "c.store": ("门店与分销网络扩张节奏", "Pace of store & branch expansion"),
    "store.note": (
        "零售门店年增约 15 家已属低速，真正的扩张发生在 SRS 分销网点（年增 40–50 家），"
        "这反映公司从「零售连锁」向「专业分销平台」的结构性迁移。",
        "Adding ~15 retail stores a year is a low-growth pace; the real expansion is in SRS distribution "
        "branches (40–50 a year). This reflects a structural shift from retail chain to professional "
        "distribution platform."),

    # ---- 六、关税
    "sec6": ("六、中美贸易与关税影响", "6. US–China Trade & Tariffs"),
    "c.tar": ("关税退款对毛利率的传导拆解（基点）",
              "Tariff refund: flow-through to gross margin (bps)"),
    "tar.note": (
        "退款是一次性现金流收益，集中在 Q2–Q3 兑现；下半年面临高基数对比，"
        "这也是「Q2 的超预期不可线性外推」的核心原因。",
        "The refund is a one-off cash benefit concentrated in Q2–Q3; H2 faces a tough comparison — the "
        "central reason Q2's beat should not be extrapolated linearly."),
    "tar.h1": ("项目", "Item"),
    "tar.h2": ("数值", "Value"),
    "tar.h3": ("来源", "Source"),
    "tar.timeline": ("政策时间线", "Policy timeline"),
    "tar.quotes": ("管理层原话", "Management's own words"),

    # ---- 七、战略
    "sec7": ("七、战略与长期目标", "7. Strategy & Long-Term Targets"),
    "c.pillars": ("三大战略支柱", "Three strategic pillars"),
    "pillar.tag": ("战略支柱", "Strategy pillar"),
    "c.scenario": ("情景框架（公司给出的中长期能力边界）",
                   "Scenario framework (management's own medium-term capability ranges)"),
    "scen.h1": ("维度", "Dimension"),
    "scen.capital": ("资本配置", "Capital allocation"),
    "c.scenchart": ("情景对比图", "Scenario comparison"),

    # ---- 八、风险
    "sec8": ("八、风险与观察清单", "8. Risks & Watch List"),
    "risk.head": ("压力与风险", "Pressures & risks"),
    "risk.tail": ("支撑与机会", "Support & opportunities"),
    "c.follow": ("下一阶段重点跟踪", "What to watch next"),

    # ---- 九、来源
    "sec9": ("九、市场反馈与数据来源", "9. Market Reaction & Sources"),
    "c.filings": ("监管文件（SEC EDGAR，CIK 0000354950）",
                  "Regulatory filings (SEC EDGAR, CIK 0000354950)"),
    "fil.h1": ("提交日", "Filed"), "fil.h2": ("类型", "Form"), "fil.h3": ("报告期", "Period"),
    "c.irdocs": ("投资者关系财报材料", "IR earnings materials"),
    "c.news": ("近期相关新闻", "Recent news"),

    # ---- 空态
    "empty.news": ("本轮未取到相关新闻。", "No related news retrieved this run."),
    "empty.filings": ("未取到监管文件。", "No regulatory filings retrieved."),
    "empty.ir": ("未取到财报材料链接。", "No IR document links retrieved."),
    "empty.group": ("该品类在当期榜单中无匹配商品。",
                    "No matching items for this category in the current boards."),

    # ---- footer
    "ft.src": ("数据来源", "Sources"),
    "ft.src.v": ("SEC EDGAR（监管文件）、Home Depot 投资者关系网站（财报新闻稿与电话会记录）、"
                 "Yahoo Finance（行情与基本面）、公司公告。静态事实均标注原始出处，动态数据每轮抓取刷新。",
                 "SEC EDGAR (regulatory filings), Home Depot Investor Relations (earnings releases and "
                 "call transcripts), Yahoo Finance (prices and fundamentals) and company announcements. "
                 "Static facts are labelled with their original source; market data refreshes every run."),
    "ft.freq": ("更新频率", "Update cadence"),
    "ft.freq.v": ("每月更新一次；每季度财报发布后要点同步更新。",
                  "Updated monthly; key points are refreshed after each quarterly earnings release."),
    "ft.rule": ("口径", "Conventions"),
    "ft.rule.v": ("金额单位为美元；财务数据单位百万美元；涨跌颜色采用中文语境（涨红跌绿）。",
                  "Amounts in US dollars; financials in US$ millions. Up/down colours follow the "
                  "regional convention of the selected language: Chinese mode uses red for gains and "
                  "green for losses, English mode uses the international convention (green up, red down)."),

    # ---- 切换控件
    "ctl.lang": ("语言", "Language"),
    "ctl.theme": ("主题", "Theme"),
    "btn.zh": ("中文", "中文"), "btn.en": ("EN", "EN"),
    "btn.light": ("☀ 浅色", "☀ Light"), "btn.dark": ("☾ 深色", "☾ Dark"),

    # ---- 波动与结构表行
    "vr.range": ("52 周区间", "52-week range"),
    "vr.fromhl": ("距 52 周高 / 低", "vs 52-week high / low"),
    "vr.mdd": ("近一年最大回撤", "Max drawdown (1Y)"),
    "vr.vol1y": ("年化波动率（近一年）", "Annualised volatility (1Y)"),
    "vr.vol60": ("年化波动率（近 60 日）", "Annualised volatility (60D)"),
    "vr.beta": ("Beta", "Beta"),
    "vr.ma20": ("MA20 / MA60", "MA20 / MA60"),
    "vr.ma200": ("MA200", "MA200"),
    "vr.mcap": ("市值 / 企业价值", "Market cap / Enterprise value"),
    "vr.ttm": ("TTM 营收 / 自由现金流", "TTM revenue / Free cash flow"),
    "vr.vs": ("现价", "vs price"),

    # ---- 财报表行
    "qt.net": ("净销售（百万美元）", "Net sales (US$ mn)"),
    "qt.gross": ("毛利（百万美元）", "Gross profit (US$ mn)"),
    "qt.op": ("营业利润（百万美元）", "Operating income (US$ mn)"),
    "qt.earn": ("净利（百万美元）", "Net earnings (US$ mn)"),
    "qt.gm": ("毛利率", "Gross margin"),
    "qt.om": ("营业利润率", "Operating margin"),
    "qt.eps": ("摊薄 EPS", "Diluted EPS"),
    "qt.eps_adj": ("调整后 EPS", "Adjusted EPS"),
    "qt.comps": ("可比销售", "Comparable sales"),
    "qt.comps_us": ("美国可比销售", "Comparable sales, U.S."),
    "qt.tx": ("客户交易量（百万笔）", "Customer transactions (mn)"),
    "qt.ticket": ("平均客单价", "Average ticket"),
    "qt.ly": ("去年", "LY"),
    "hl": "<!-- placeholder keeps dict ordering readable -->",

    # ---- 情景表行
    "st.sales": ("总销售增长", "Total sales growth"),
    "st.comps": ("可比销售", "Comparable sales"),
    "st.eps": ("EPS 增速", "EPS growth"),
    "st.desc": ("情景描述", "Scenario description"),

    # ---- KPI 卡片名
    "kpi.price": ("股价", "Share price"),
    "kpi.ret1y": ("近一年涨跌", "1-year return"),
    "kpi.netsales": ("Q2 净销售", "Q2 net sales"),
    "kpi.eps": ("Q2 调整后 EPS", "Q2 adjusted EPS"),
    "kpi.comps": ("可比销售", "Comparable sales"),
    "kpi.tx": ("交易量", "Transactions"),
    "kpi.pe": ("市盈率", "P/E"),
    "kpi.target": ("分析师目标", "Analyst target"),

    # ---- 结论标签
    "vtag.market": ("市场", "Market"),
    "vtag.quality": ("盈利质量", "Earnings quality"),
    "vtag.pv": ("量价结构", "Price–volume"),
    "vtag.growth": ("增长引擎", "Growth engine"),
    "vtag.gov": ("治理", "Governance"),
    "vtag.val": ("估值", "Valuation"),
    "vtag.cycle": ("周期", "Cycle"),

    # ---- 扩店 KPI 卡片
    "sk.retail": ("零售门店", "Retail stores"),
    "sk.srs": ("SRS 网点", "SRS branches"),
    "sk.dist": ("分销网络", "Distribution network"),
    "sk.emp": ("员工", "Employees"),
    "sk.global": ("全球", "Worldwide"),
    "sk.markets": ("覆盖 7 个国家/地区市场", "Across 7 countries / markets"),
    "sk.tam": ("可寻址市场", "Addressable market"),

    # ================================================================
    # 网评分 / 畅销榜 / buzz 分析（2026-10-05 追加）
    # ================================================================

    # ---- 章节十：网评分与畅销榜
    "sec10": ("十、网评分与畅销榜（Amazon 一手数据）",
              "10. Ratings & Best Sellers (first-party Amazon data)"),
    "sec10.note": (
        "本节的评分、评论数、名次全部来自亚马逊官方榜单页的原始字段，直抓所得，未经二次加工。"
        "两个必须知道的口径：① 畅销榜按**销售件数**排名，不是销售额，因此低单价、高复购的耗材"
        "天然占优 —— 这正是「庭院与户外」总榜头部被杀虫剂占据的原因；② 评论数是**累计值**，"
        "上架越久的商品天然越高，所以它衡量的是「已经积累了多少声量」，不是「当下有多火」。",
        "Every rating, review count and rank below is an untouched field from Amazon's own "
        "leaderboard pages, scraped directly. Two conventions matter: (a) these boards rank by "
        "units sold, not revenue, so cheap repeat-purchase consumables are structurally "
        "advantaged — which is why the overall Patio, Lawn & Garden board is topped by "
        "insecticides; (b) review counts are cumulative, so older listings score higher by "
        "default. They measure accumulated buzz, not current heat."),
    "c.buzzboard": ("各榜单的声量与口碑", "Volume and valence, board by board"),
    "c.buzzboard.note": (
        "柱为各榜单的**中位**评论数，折线为**中位**评分，两条要分开读："
        "中位评论数反映该品类的评论密度（上架久、复购多的品类天然更高），"
        "中位评分反映该品类的整体口碑水位。用中位数而非平均数，是为了不被个别爆款拉偏。",
        "Bars show each board's median review count; the line shows median rating. Read them "
        "separately: median reviews reflect the category's review density (older, repeat-purchase "
        "categories rank higher by nature), while median rating reflects its overall satisfaction "
        "level. Medians are used instead of means so single breakout hits cannot skew the picture."),
    "c.buzzmix": ("品类构成（8 个榜单汇总）", "Category mix across all 8 boards"),
    "c.buzzmix.note": (
        "亚马逊的分类节点比名字宽：名为「户外家具与配件」的节点里，冷藏箱、保温冰袋、露营椅"
        "都算在内。因此这里按商品标题关键词重新归了类，口径与结果都摊开在图上，"
        "避免把冷藏箱当成户外家具来读。",
        "Amazon's category nodes are wider than their names suggest — the 'Patio Furniture & "
        "Accessories' node includes coolers, ice packs and camping chairs. Products are therefore "
        "re-classified here by title keywords, with both method and result shown, so coolers are "
        "not misread as outdoor furniture."),
    "c.buzzmap": ("明星地图：声量 × 口碑", "Star map: volume vs valence"),
    "c.buzzmap.note": (
        "横轴为累计评论数（对数刻度 —— 评论数跨越三个数量级，线性轴会把所有中小商品压成一点），"
        "纵轴为平均星级，点的大小为 buzz 综合分。右上角是「又火口碑又好」的象限。",
        "The x-axis is cumulative ratings on a log scale (counts span three orders of magnitude; a "
        "linear axis would flatten everything else into one point), the y-axis is average rating, "
        "and bubble size is the buzz score. The top-right quadrant is both popular and well rated."),
    "c.bslist": ("各子类畅销榜 Top 8", "Best Sellers: top 8 of each sub-category"),
    "c.bslist.note": (
        "每个子类取名次最前的 8 件。名次是抓取时刻的实时排名，会随时间变动；"
        "价格字段仅在榜单页直接渲染时才有，因此部分商品为空 —— 空即未取到，不做补值。",
        "The top 8 of each sub-category. Ranks are live as of the scrape; prices appear only when "
        "the leaderboard page renders them inline, so some cells are empty. Empty means "
        "not retrieved — never filled in with an estimate."),

    # ---- 章节十一：Patio 明星产品 buzz 分析
    "sec11": ("十一、Patio 明星产品 buzz 分析", "11. Patio Star Products — a Buzz Analysis"),
    "sec11.note": (
        "「明星产品」不等于最贵或最好，而是**声量、口碑、当下动能**三者综合最强。"
        "三个分量各自归一化后在榜内加权，因此不同榜单的商品之间不做直接比较 —— "
        "新品榜的评论数天然只有畅销榜的百分之一，跨榜比分数等于在比上架时间。",
        "'Star product' does not mean most expensive or best — it means strongest on volume, "
        "valence and current momentum combined. Each component is normalised and weighted within "
        "its own board, so products from different boards are never compared directly: a New "
        "Releases listing naturally has a fraction of a Best Seller's review count, and comparing "
        "raw scores would only measure how long each has been on sale."),
    "method.title": ("buzz 打分方法", "How the buzz score works"),
    "method.v": ("声量 Volume", "Volume"),
    "method.q": ("口碑 Valence", "Valence"),
    "method.m": ("动能 Momentum", "Momentum"),
    "method.formula": ("加权公式", "Weighted formula"),
    "method.limits": ("这套方法回答不了什么", "What this method cannot answer"),
    "c.buzz3": ("三层分层：各自的头部商品", "Leaders within each of the three layers"),
    "c.buzz3.note": (
        "家具、设备、配件必须分开看。配件的评论数天然高于大件（低单价、高频、易复购），"
        "混排的结果是配件永远霸榜，读者会误以为「露台就是卖杯子套的」。"
        "分层之后才看得出各层真正的头部是谁。",
        "Furniture, equipment and accessories must be read separately. Accessories accumulate far "
        "more reviews than big-ticket items (cheap, frequent, repeat-purchase), so a combined "
        "ranking would put accessories on top forever and leave the false impression that patio "
        "retail is mostly about cup holders. Only after layering does each layer's real leader "
        "become visible."),
    "g.furniture": ("大件家具", "Furniture"),
    "g.equipment": ("户外设备", "Equipment"),
    "g.accessory": ("配件与耗材", "Accessories"),
    "c.proven": ("高口碑长销（评论 ≥ 5,000 且评分 ≥ 4.5）",
                 "Proven performers (≥5,000 ratings and ≥4.5★)"),
    "c.proven.note": (
        "同时满足「声量已足够大」和「口碑仍站得住」的商品。"
        "门槛刻意设得高：评论上千并不稀奇，上万且不掉星才说明经得住时间。",
        "Items that are both widely reviewed and still well rated. The bar is deliberately high: "
        "a thousand reviews is routine; ten thousand without a ratings slide is what signals "
        "durability."),
    "c.newcomers": ("新星（新品榜，评论数低是正常的）",
                    "Rising stars (New Releases — low counts are expected)"),
    "c.newcomers.note": (
        "新品榜捕捉的是**正在起量**的商品。这里的评论数普遍只有几十到几百，"
        "不要与畅销榜的数字并排比较；它的价值在于看「谁刚进来」，而不是「谁已经赢了」。",
        "The New Releases board captures what is ramping up right now. Review counts here are "
        "typically in the tens or hundreds — never compare them side by side with Best Seller "
        "figures. Its value is showing who has just arrived, not who has already won."),

    # ---- 章节十二：双渠道对标
    "sec12": ("十二、双渠道对标：Amazon vs Walmart（均为一手直抓）",
              "12. Two-Channel Comparison: Amazon vs Walmart (both first-party)"),
    "sec12.note": (
        "本节只对标**能站内直抓的两家** —— Amazon（8 个畅销榜）与 Walmart（7 个品类页 +"
        "评论页）。之所以不做多渠道并列，是因为另三家的站内数据根本拿不到，"
        "硬凑进来只会让「可比性」变成幻觉：Home Depot 与 Lowe's 被 Akamai 指纹级拦截"
        "（实测商品页与 robots.txt 均返回 403，Lowe's 连首页都是 Access Denied），"
        "Costco 为纯客户端渲染（HTML 里约 350 处 Skeleton 占位、零商品数据）。"
        "因此本节做的是**同口径的两渠道特征对比**，不是份额对比 —— 拿不到的数据一律不出现。",
        "This section benchmarks only the **two channels that scrape cleanly from the site "
        "itself** — Amazon (8 best-seller boards) and Walmart (7 category pages plus review "
        "pages). A wider line-up was deliberately dropped, because the other three cannot be "
        "retrieved on-site at all and listing them would only fake comparability: Home Depot "
        "and Lowe's sit behind fingerprint-level Akamai blocks (product pages and robots.txt "
        "both returned 403 in testing; Lowe's serves Access Denied even on its homepage), and "
        "Costco is purely client-side rendered (roughly 350 skeleton placeholders, zero product "
        "data). This is therefore a like-for-like comparison of two channels, not a share "
        "comparison — what could not be retrieved simply does not appear."),
    "c.chan": ("渠道特征对比", "How the two channels differ"),
    "bz.excluded": ("未纳入本节的三家渠道", "Three channels not covered here"),
    "excluded.note": (
        "Home Depot、Lowe's、Costco 已整体移出对标：三家的站内商品页都无法直抓，"
        "拿不到可比的排名 / 评分 / 评论数，**任何跨渠道数字都会被不可控的口径差污染**。"
        "移出的是「渠道对比」，不是「研究覆盖」—— Home Depot 本身仍是本看板的研究主体，"
        "其行情、财报、IR 材料与新闻见第一至第十一章。",
        "Home Depot, Lowe's and Costco have been dropped from this comparison entirely: none of "
        "their on-site product pages can be scraped, so no comparable rank, rating or review "
        "count exists, and **any cross-channel number would be contaminated by an uncontrollable "
        "definition gap**. What was removed is the channel comparison, not research coverage — "
        "Home Depot remains the subject of this dashboard, with its price action, financials, IR "
        "materials and news in sections 1 through 11."),
    "th.access": ("可达性：", "Access: "),
    "c.hditems": ("Home Depot：公开渠道披露的关键单品",
                  "Home Depot: key items from public disclosures"),
    "c.lowitems": ("Lowe's：公开渠道披露的关键单品",
                   "Lowe's: key items from public disclosures"),
    "c.srcnote": ("数据来源与可靠性等级", "Sources and reliability tiers"),
    "tier.index": ("搜索索引快照（零售商页面原文）", "Search-index snapshot (retailer page text)"),
    "tier.media_cited": ("媒体引用零售商网站", "Retailer data cited by third-party media"),
    "tier.brand_site": ("品牌官方站点", "Brand's own website"),
    "srctier.label": ("可靠性", "Reliability"),
    "srctier.restricted": ("受限：站内不可直抓", "Restricted: on-site data not scrapable"),
    "srctier.firstparty": ("一手直抓", "First-party scrape"),

    # ---- 章节十三：品类档次对标（Amazon × Walmart 一手）
    "sec13": ("十三、HD 主流品类档次对标（Amazon × Walmart 一手）",
              "13. Benchmarking HD's Core Categories (first-party Amazon × Walmart)"),
    "sec13.note": (
        "这一节回答一个具体问题：**Home Depot 的主打品类，放到全渠道上是什么档次？**"
        " 口径按 Home Depot 的 patio 类目体系划成 7 类（成套家具 / 单件组合家具 / 遮阳伞 / "
        "篷房与凉亭 / 露营与便携 / 配件与耗材 / 烧烤与火炉）。"
        "供给密度与口碑取自 Walmart 的一手品类页（296 件）与 Amazon 的 8 个畅销榜（240 件），"
        "差评主题取自 Walmart 评论的「最低分优先」页（14 款商品、约 280 条 1–2 星评论）。"
        "⚠️ 定位分是**这 7 类之间的相对排名**（z 分数加权），不是绝对好坏；"
        "Home Depot 与 Lowe's 站内数据仍受反爬保护，本节不含它们的量化份额。",
        "This section answers one concrete question: **how does Home Depot's core assortment "
        "rank across channels?** Categories follow Home Depot's own patio taxonomy, in 7 buckets "
        "(Patio Sets / Mix & Match / Umbrellas / Canopies & Gazebos / Camping & Portable / "
        "Accessories / Grills & Fire). Supply depth and sentiment come from first-party Walmart "
        "category pages (296 items) and eight Amazon best-seller boards (240 items); complaint "
        "themes come from Walmart's lowest-rated review pages (14 products, ~280 one- and two-star "
        "reviews). Positioning is a **relative ranking among these 7 buckets** (weighted z-scores), "
        "not an absolute verdict. Home Depot and Lowe's on-site data remain behind anti-bot "
        "protection, so no quantitative share for them appears here."),

    "c.ladder": ("品类档次阶梯", "Category positioning ladder"),
    "ladder.note": (
        "定位分 = 0.40×需求体量(z) + 0.35×加权星级(z) + 0.25×抗差评(z)。"
        "需求体量取**两渠道累计评论数的对数**——刻意不用「在架件数」，因为件数反映的是"
        "渠道的招商策略，不是品类本身的需求规模；早期版本用了件数，把成套家具压到末位"
        "并打成「机会/利基」，而它恰恰是 Home Depot 的门面品类，属于口径造成的误导。"
        "加权星级按各品类累计评论数加权，等价于把该品类所有评论揉在一起算平均分。"
        "梯队只按排名分档，不暗示谁该做谁不该做；「抱怨压力」单独成列，因为规模大与"
        "抱怨多可以同时成立（成套家具正是如此）。",
        "Positioning = 0.40×demand mass(z) + 0.35×weighted rating(z) + 0.25×low-star "
        "resistance(z). Demand mass uses the **log of cumulative ratings across both "
        "channels** — deliberately not item counts, because shelf counts reflect a channel's "
        "merchandising strategy rather than underlying demand. An earlier version used counts, "
        "which pushed Patio Sets to last place and labelled it \"opportunity / niche\" — yet it "
        "is precisely Home Depot's flagship, a clear artefact of the wrong denominator. Weighted "
        "rating weights each item by review count, pooling every review in the category into one "
        "average. Tiers are rank bands only and imply nothing about where to invest; complaint "
        "pressure sits in its own column, because large scale and heavy complaints can coexist "
        "(Patio Sets is exactly that case)."),
    "th.pos": ("定位分", "Positioning"),
    "th.revmass": ("需求体量（累计评论）", "Demand mass (cumulative ratings)"),
    "th.supply": ("在架商品数", "Items on shelf"),
    "th.wrat": ("加权星级", "Weighted rating"),
    "th.negshare": ("差评率 (1–2 星)", "Low-star share (1–2★)"),
    "th.ctier": ("梯队", "Tier"),
    "th.risk": ("抱怨压力", "Complaint pressure"),
    "th.toptheme": ("主要抱怨", "Top complaints"),
    "ctier.t1": ("第一梯队", "Tier 1"),
    "ctier.t2": ("第二梯队", "Tier 2"),
    "ctier.t3": ("第三梯队", "Tier 3"),
    "risk.low": ("低", "Low"),
    "risk.mid": ("中", "Medium"),
    "risk.high": ("高", "High"),
    "ladder.hint": (
        "把这个表横过来读：**需求体量回答「这块有多大」，加权星级与差评率回答「做得好不好」**。"
        "两者不必同向 —— 体量最大的品类未必口碑最好，口碑最好的未必体量最大，"
        "而体量厚、口碑又承压的品类，才是经营上真正要盯的地方。",
        "Read this table sideways: **demand mass answers \"how big is this\", weighted rating "
        "and low-star share answer \"how well is it done\"**. The two need not align — the "
        "biggest category is not necessarily the best rated, and vice versa. The categories that "
        "are both large and under sentiment pressure are the ones that actually deserve "
        "operational attention."),
    "ladder.lowconf": (
        "* 该品类抽样商品的评论总量不足 1,000 条，其差评率与加权星级的抽样误差较大，"
        "请结合「主要抱怨」一并判断。",
        "* The sampled products for this category total fewer than 1,000 ratings, so its "
        "low-star share and weighted rating carry wider sampling error — read them together "
        "with the top-complaint column."),

    "c.catcmp": ("渠道 × 品类：供给与口碑对照",
                 "Channel × category: supply and sentiment"),
    "catcmp.note": (
        "同一品类在两个渠道的供给厚度对比，是本节最直观的一张表。"
        "看「成套家具」这一行：Amazon 0 件、Walmart 27 件 —— 大件家具几乎不上亚马逊的榜单，"
        "这正是 Home Depot 的主场所在。",
        "The most direct table in this section: how deep each category is on each channel. "
        "Look at Patio Sets — 0 items on Amazon versus 27 on Walmart. Bulky furniture barely "
        "reaches Amazon's leaderboards at all, and that is exactly Home Depot's home turf."),
    "th.amzonly": ("Amazon", "Amazon"),
    "th.wmonly": ("Walmart", "Walmart"),
    "catcmp.bar": ("供给厚度", "Supply depth"),
    "ch.nitems": ("件数", "Items"),

    "c.starcross": ("各品类明星产品（实物图）", "Category champions, with product photos"),
    "starcross.note": (
        "每个品类并列两个渠道各自的榜首商品（亚马逊侧按 buzz 综合分，沃尔玛侧按页内归一化分）。"
        "⚠️ 两渠道分数各自在榜内归一化，**数值不可直接比较**，因此这里只并列、不排序。"
        "配图为沃尔玛公开商品图（Amazon 商品主图实测三路皆封：商品页 captcha、榜单页图片懒加载、"
        "遗留图片端点 403）。",
        "For each category the two channels' leaders sit side by side (Amazon by composite buzz, "
        "Walmart by within-page normalised score). Scores are normalised inside each board, so the "
        "**numbers are not comparable across channels** — they are listed, not ranked. Photos come "
        "from Walmart's public product-image CDN; Amazon main images were blocked on all three "
        "routes tested (product page captcha, lazy-loaded board images, legacy image endpoint 403)."),
    "star.ph": ("无图", "no photo"),
    "star.pick": ("选品口径", "Selection rule"),
    "star.rule": ("log10(评论数+1) × 评分/5 —— 兼顾体量与口碑，避免 3.8 星老品霸榜",
                  "log10(ratings+1) × rating/5 — balances scale and sentiment, so a 3.8★ "
                  "long-runner cannot top the list"),

    "c.neg": ("客户负面反馈归纳（Walmart 一手评论）",
              "Recurring complaints (first-party Walmart reviews)"),
    "neg.note": (
        "数据来自 Walmart 评论页的「最低分优先」排序 —— 这是**平台提供的排序**，不是我们挑的，"
        "所以样本天然是 1–2 星。痛点主题由固定词表对差评正文做命中统计（同一段评论对同一主题"
        "只记一次）。⚠️ 评论正文由机器翻译级别的词表匹配，属于**定性归纳**，"
        "不该当作精确比例使用；但它足以回答「客户主要在骂什么」。",
        "Sourced from Walmart's \"lowest rating first\" review sort — the **platform's own "
        "ordering**, not our pick, so the sample is inherently one- and two-star. Themes are "
        "counted by matching review text against a fixed vocabulary (a given review counts once "
        "per theme). ⚠️ This is machine matching over review prose, so treat it as **qualitative "
        "summarisation**, not a precise ratio — but it answers \"what are customers actually "
        "complaining about\" well enough."),
    "th.theme": ("抱怨主题", "Complaint theme"),
    "th.hits": ("提及数", "Mentions"),
    "th.cover": ("覆盖商品", "Products covered"),
    "c.negcat": ("品类 × 痛点：抱怨集中在哪里",
                 "Category × pain point: where complaints concentrate"),
    "c.quote": ("差评原声（各主题最典型的一条）",
                "In their own words — the most representative review per theme"),
    "neg.sample": ("样本", "Sample"),
    "neg.negrev": ("条差评", "negative reviews"),
    "neg.products": ("款商品", "products"),

    "c.highlights": ("数据要点", "Key data points"),
    "hl.note": (
        "自动生成的要点，全部来自本页下方的一手数据；每一条都能在对应章节找到出处。",
        "Auto-generated from the first-party data further down this page. Every line traces back "
        "to a specific section."),

    "irq.when": ("时间", "When"),
    "irq.pending": ("待发布（电话会已排期）", "Pending release (call scheduled)"),
    "irq.who": ("发布方", "Publisher"),
    "irq.headline": ("主要标题", "Main headline"),
    "irq.call": ("电话会", "Earnings call"),
    "c.irquarters": ("按季度的财报材料（含发布时间、发布方与标题）",
                     "Quarterly materials — with date, publisher and headline"),
    "irq.note": (
        "此处的时间与标题不是页面上的装饰性文字，而是**下载财报 PDF 后从首页正文里解析出来的**："
        "新闻稿正文电头形如「ATLANTA, August 18, 2026 --」，电话会记录页首形如"
        "「EVENT DATE/TIME: August 18, 2026 / 09:00AM ET」。"
        "此前只列类型不列时间，多个季度看起来一模一样，无法分辨 —— 这是本次修正的原因。",
        "The dates and headlines here are not page decoration — they were **parsed out of the "
        "earnings PDFs after download**, from the press-release dateline (\"ATLANTA, August 18, "
        "2026 --\") and the transcript header (\"EVENT DATE/TIME: August 18, 2026 / 09:00AM ET\"). "
        "Previously only the material type was listed, so multiple quarters looked identical and "
        "could not be told apart — which is what this fixes."),

    # ---- 表格与图内文案
    "th.product": ("商品", "Product"),
    "th.brand": ("品牌", "Brand"),
    "th.rank": ("名次", "Rank"),
    "th.rating": ("评分", "Rating"),
    "th.reviews": ("评论数", "Ratings"),
    "th.price": ("价格", "Price"),
    "th.buzz": ("buzz 分", "Buzz"),
    "th.cat": ("品类", "Category"),
    "th.note": ("说明", "Note"),
    "th.src": ("来源", "Source"),
    "th.channel": ("渠道", "Channel"),
    "th.brands": ("主力品牌", "Main brands"),
    "th.strength": ("渠道特征", "Channel characteristics"),
    "ch.medianrev": ("中位评论数", "Median ratings"),
    "ch.medianrat": ("中位评分", "Median rating"),
    "ch.reviews": ("评论数", "Ratings"),
    "ch.buzz": ("buzz 综合分", "Buzz score"),
    "ch.count": ("商品数", "Products"),
    "ch.share": ("占比", "Share"),
    "ch.cumrev": ("累计评论数", "Cumulative ratings"),
    "buzz.header": ("buzz 分析", "Buzz analysis"),
    "bz.top3": ("Top3 占声量", "Top-3 share"),
    "bz.maxrev": ("最高评论数", "Max ratings"),
    "bz.of": ("（各子类名次最前的 8 件）", " — top 8 of this sub-category"),
    "bz.errors": ("本轮采集异常", "Collection errors this run"),
    "bz.firstparty": ("一手直抓渠道", "First-party channels"),
    "bz.restricted": ("受限渠道（站内不可直抓，仅作定性对照）",
                      "Restricted channels (not scrapable, qualitative only)"),
    "empty.buzz": ("暂无数据。", "No data yet."),
}

# ---- 让 "hl" 这种占位不出现在真正输出里
UI.pop("hl", None)


# ================================================================ 图表文案
CH = {
    "doc.title": UI["doc.title"],
    "px.hd": ("HD 收盘价", "HD close"),
    "px.hd_full": ("Home Depot 收盘价（美元）", "Home Depot close (USD)"),
    "rel.base": ("起点 100", "Rebased to 100"),
    "rel.name": ("HD / SPY", "HD / SPY"),
    "chg.1w": ("1 周", "1W"), "chg.1m": ("1 月", "1M"), "chg.3m": ("3 月", "3M"),
    "chg.6m": ("6 月", "6M"), "chg.1y": ("1 年", "1Y"),
    "fin.sales": ("净销售", "Net sales"),
    "fin.earn": ("净利", "Net earnings"),
    "mar.gross": ("毛利率", "Gross margin"),
    "mar.op": ("营业利润率", "Operating margin"),
    "vol.ticket": ("平均客单价同比", "Avg ticket y/y"),
    "vol.tx": ("交易量同比", "Transactions y/y"),
    "store.retail": ("零售门店", "Retail stores"),
    "store.srs": ("SRS 网点", "SRS branches"),
    "store.total": ("当前总数", "Current total"),
    "store.plan": ("FY2026 计划新增", "FY2026 planned"),
    "tar.refund": ("退款对毛利拉动", "Refund: gross-margin uplift"),
    "tar.cost": ("非计划投入成本", "Unplanned input costs"),
    "tar.acq": ("收购结构影响", "Acquisition mix"),
    "tar.net": ("净改善", "Net improvement"),
    "tar.unit": ("基点", "bp"),
    "scen.sales": ("总销售增长（区间中值）", "Total sales growth (midpoint)"),
    "scen.comps": ("可比销售（区间中值）", "Comparable sales (midpoint)"),
    "tt.sales": ("总销售", "Total sales"),
    "tt.comps": ("可比销售", "Comps"),
    "tt.eps": ("EPS", "EPS"),
    "kpi.week": ("（近周）", "(1W)"),
    "kpi.spx": ("标普500", "S&P 500"),
    "kpi.excess": ("超额收益", "Excess return"),
    "kpi.yoy": ("同比", "y/y"),
    "kpi.us": ("美国", "U.S."),
    "kpi.ticket_pos": ("含客单价正贡献", "Positive ticket contribution"),
    "kpi.divergence": ("量价背离", "Price–volume divergence"),
    "kpi.fwd": ("前瞻", "Fwd"),
    "kpi.yield": ("股息率", "Yield"),
    "kpi.vs_price": ("较现价", "vs price"),
    "kpi.cover": ("位覆盖", " analysts"),
    "kpi.gaap": ("GAAP", "GAAP"),
    "kpi.ly": ("去年同期", "LY"),
    "new": ("新增", "new"),
}


# ================================================================ config 静态事实的英文译文
# 顺序与 config.py 中对应列表**严格一一对应**，渲染时按索引配对。

FACT_META = {
    "index_membership": ["Dow Jones Industrial Average", "S&P 500"],
    "business": ("The world's largest home-improvement retailer and professional distributor, operating "
                 "across all 50 U.S. states, the District of Columbia, Puerto Rico, the U.S. Virgin Islands, "
                 "Guam, 10 Canadian provinces and Mexico."),
}

FACT_STRATEGY_PILLARS = [
    {"cn": "Drive the core business and culture",
     "desc": "Store experience, product availability and associate capability — getting the base right"},
    {"cn": "Deliver a seamless interconnected experience",
     "desc": "One experience online and in store: Express Delivery, the Magic Apron AI assistant, "
             "digital quotes and fulfilment"},
    {"cn": "Win the Pro",
     "desc": "A Pro ecosystem built on SRS, GMS and Mingledorff's — moving from retail into "
             "professional distribution"},
]

FACT_STRATEGY_TAM = {
    "note": ("Following the acquisitions of SRS, GMS and Mingledorff's, the total addressable market (TAM) "
             "expands from roughly US$1.1 trillion to about US$1.2 trillion; the Pro opportunity alone is "
             "close to US$700 billion. Mingledorff's opens up an HVAC distribution market of about "
             "US$100 billion."),
    "share": ("Roughly 47%–51% of the U.S. home-improvement market, the industry leader; the strategic focus "
              "is shifting toward high-value complex Pro projects"),
}

FACT_LEADERSHIP = {
    "note": ("Announced 2026-08-12: Chairman, President and CEO Ted Decker is on a temporary medical leave "
             "of absence. The company expects him to return \"within the coming months\" but has given no "
             "fixed timetable; no permanent successor has been named — two senior executives are jointly "
             "leading the Office of the CEO."),
    "people": [
        {"title": "Chairman, President & CEO",
         "status": "On temporary medical leave (since 2026-08-12)",
         "note": "The principal architect of the Pro strategy; chaired the 2025 Investor Conference "
                 "before his leave"},
        {"title": "Senior Executive Vice President (SEVP)",
         "status": "Leading day-to-day operations in the interim",
         "note": "Joined in 1985 as a cashier; previously President of the Southern Division and EVP of "
                 "U.S. Stores — one of the company's longest-serving executives"},
        {"title": "Executive Vice President & CFO",
         "status": "Leading finance and the Pro subsidiaries in the interim; designated interim principal "
                   "executive officer for SEC purposes",
         "note": "Joined in 2005; previously SVP of Global FP&A and Strategy & Business Development"},
        {"title": "Independent Lead Director",
         "status": "Chairing the board during the leave",
         "note": "Resolved by the board to lead board proceedings in the CEO's absence"},
        {"title": "Executive Vice President, Merchandising",
         "status": "In office; additionally oversees product development and private brands since 2026-08",
         "note": "Responsible for category and supplier relationships, tariffs and supply-chain response; "
                 "led merchandising commentary on the Q2 call"},
        {"title": "Executive Vice President, Interconnected Retail",
         "status": "In office; additionally oversees loyalty, credit services and payments since 2026-08",
         "note": "Owns omnichannel fulfilment and digital experience",
         "src": "8-K (2026-08-21, Item 5.02)"},
        {"title": "Executive Vice President, General Counsel & Corporate Secretary",
         "status": "In office",
         "note": "Legal, compliance and corporate governance",
         "src": "Signatory of the 8-K (2026-08-21)"},
        {"title": "Vice President, Investor Relations & Treasurer",
         "status": "In office",
         "note": "Host of the Q2 FY2026 earnings call",
         "src": "Q2 FY2026 earnings call transcript"},
    ],
    "changes": [
        {"title": "Executive responsibility expansions (announced 2026-07-30)",
         "detail": ("Billy Bastek additionally took on product development and private brands; Jordan Broggi "
                    "additionally took on loyalty, credit services and payments; CFO Richard McPhail now leads "
                    "the Office of Pro Acceleration, coordinating Home Depot Pro, HD Supply, SRS Distribution "
                    "and Construction Resources. Each of the three received restricted stock with a grant-date "
                    "fair value of $500,000, vesting on the second anniversary subject to continued employment."),
         "src": "data/docs/8k_20260821_exec_changes.htm"},
        {"title": "CEO Ted Decker placed on temporary medical leave",
         "detail": ("Announced 2026-08-12 (event date 2026-08-11): expected to return \"within the coming "
                     "months\" with no fixed timetable and no permanent successor. Ann-Marie Campbell and CFO "
                     "Richard McPhail jointly lead the Office of the CEO; McPhail is interim principal executive "
                     "officer for SEC purposes; Greg Brenneman chairs the board."),
         "src": "8-K (2026-08-12) + Exhibit 99.1"},
    ],
}

FACT_STORES = {
    "srs_note": "SRS branch count is \"more than 1,340\"",
    "countries": ("All 50 U.S. states + District of Columbia + Puerto Rico + U.S. Virgin Islands + Guam + "
                  "10 Canadian provinces + Mexico"),
    "expansion_note": ("Retail expansion has entered a low-growth phase (~15 stores a year); incremental "
                       "growth is mainly in SRS distribution branches (40–50 a year)."),
}

FACT_TARIFF = {
    "headline": ("IEEPA tariff refunds were the main source of the Q2 earnings beat, but they are a one-off "
                 "benefit and are expected to be fully offset by rising input costs over the full year."),
    "facts": [
        {"k": "Total refund received in Q2", "v": "US$730 million"},
        {"k": "Credited to cost of sales (COGS)", "v": "US$685 million"},
        {"k": "Impact on gross margin", "v": "About +145 bps"},
        {"k": "Absorbed by unplanned fuel/energy/input costs", "v": "About −60 bps"},
        {"k": "Drag from acquisition mix (GMS / Mingledorff's)", "v": "About −60 bps"},
        {"k": "Net improvement", "v": "About +25 bps → Q2 gross margin 33.7%"},
        {"k": "Refunds still to be received", "v": "\"Not significant\"; a small amount in H2"},
    ],
    "management_view": [
        "CFO McPhail: \"Tariff refunds are a market-borne benefit. What tariff refunds allowed us to do was "
        "offset increased costs in our environment, and it allowed us to maintain values in the market.\"",
        "CFO McPhail: \"We expect the increased costs will fully offset the benefit from tariff refunds "
        "over the year.\"",
        "So Q2's high gross margin cannot be extrapolated — the refunds land mainly in Q2–Q3, and H2 faces "
        "a demanding base comparison.",
    ],
    "policy_timeline": [
        {"event": "Section 101 tariff provision expires, creating incremental cost pressure"},
        {"event": "Q2 receives US$730 million of IEEPA tariff refunds — \"the vast majority\" of amounts filed"},
        {"event": "Refund benefit rolls off; the company must absorb higher fuel, energy and merchandise "
                 "input costs on its own"},
    ],
    "supply_chain": ("The company continues to diversify its supply chain to reduce tariff and trade-policy "
                     "risk (see the forward-looking statement's reference to \"trade policy changes… diversify "
                     "our supply chain\"). Distribution assets such as SRS and GMS inherently reduce reliance "
                     "on a single import source."),
}

FACT_SEGMENTS = [
    {"k": "SRS distribution business",
     "v": "Q2 sales +62% y/y to US$5.1 billion; positive comps in every vertical and ahead of the "
          "company overall"},
    {"k": "Big-ticket transactions (>$1,000)", "v": "+2.4% y/y"},
    {"k": "Online sales", "v": "Fifth consecutive quarter of double-digit growth (Q2 +11%, strongest in "
                               "three years)"},
    {"k": "Pro vs DIY", "v": "Pro comps positive and ahead of DIY; DIY strength in portable power, patio "
                             "and pressure-treated lumber"},
    {"k": "International", "v": "Canada and Mexico both outperformed the company overall"},
    {"k": "Avg ticket vs transactions", "v": "Ticket +2.8% while transactions −0.8% — growth driven by "
                                             "price, not footfall"},
]

FACT_UPCOMING = {
    "note": ("Announced on 2026-11-03: the Q3 FY2026 earnings call is scheduled for Tuesday, "
             "November 17 at 9 a.m. ET (results released before the open). As of this page's data "
             "timestamp, Q3 results have **not** been published yet — no Q3 8-K / 10-Q on SEC EDGAR. "
             "The dashboard will pick them up in the next update run."),
}

FACT_LONG_TERM = {
    "note": ("HD does not publish year-by-year five-year numerical targets; instead it provides a "
             "three-scenario framework (2025-12-09 Investor Conference). The \"Market Recovery Case\" is the "
             "company's own articulation of its medium-term capability once the housing cycle normalises."),
    "scenarios": [
        {"name": "Base case (FY2026 guidance)", "cn": "Housing stays frozen",
         "sales": "2.5% – 4.5%", "comps": "flat – 2.0%", "eps": "flat – 4.0%",
         "desc": "Home-improvement market −1% to +1%; demand for large projects remains suppressed"},
        {"name": "Market Recovery Case", "cn": "Housing activity improves",
         "sales": "About 5% – 6%", "comps": "About 4% – 5%", "eps": "Mid-to-high single digit growth",
         "desc": "Operating profit grows faster than sales; the CFO describes this as the expected "
                 "performance \"once we see momentum in housing activity and increased spend on larger "
                 "projects driven by pent-up demand\""},
        {"name": "Accelerated Recovery Case", "cn": "Sharp housing rebound",
         "sales": "Faster than the Recovery Case", "comps": "—", "eps": "Faster than the Recovery Case",
         "desc": "If housing recovers more steeply, sales and EPS growth could accelerate further"},
    ],
    "capital": [
        "Capital-allocation discipline: **the share repurchase programme is paused through 2027**, with "
        "resources prioritised for acquisition integration and deleveraging",
        "Dividends: about US$2.3 billion paid per quarter (actual Q2 FY2026), a payout ratio of roughly "
        "65% — a long-standing dividend grower",
        "Capex maintained at about 2.5% of total sales",
    ],
}

FACT_MACRO = {
    "headwinds": [
        "Existing-home turnover has sat at multi-year lows for four consecutive years (purchase-and-sale "
        "frequency has not recovered)",
        "Housing affordability is suppressing large remodelling projects; customers are shifting to smaller "
        "projects",
        "The Fed signalled \"higher for longer\" at Jackson Hole; mortgage rates remain elevated",
        "U.S. pending home sales have been declining since spring 2026",
    ],
    "tailwinds": [
        "If pent-up demand for large projects is released, it will support home improvement more strongly "
        "than the wider economy",
        "Pro market share continues to rise — even in a weak environment the company is taking share",
        "SRS / GMS / Mingledorff's open up new verticals including HVAC, roofing and building materials",
    ],
    "note": ("Management's own description of the current environment is \"frozen\" — growth has not "
             "accelerated, but the company is taking share."),
}

FACT_DISCLAIMER = ("This material is based on publicly available data and quantitative analysis, is for "
                   "reference only and does not constitute investment advice. Markets carry risk; invest "
                   "prudently. Any investment decision should be made independently in light of your own "
                   "risk tolerance, financial position and objectives, consulting a licensed professional "
                   "where appropriate. Past performance does not guarantee future results.")

FACT_QUOTES_TAGS = [
    "Q2 FY2026 earnings release · CFO Richard McPhail",
    "Q2 FY2026 earnings release · SEVP Ann-Marie Campbell",
    "Q2 FY2026 earnings call · CFO McPhail (on tariff refunds)",
    "Q2 FY2026 earnings call · CFO McPhail (on the full-year outlook)",
    "Q2 FY2026 earnings call · CFO McPhail (on demand and housing)",
    "2025 Investor Conference · CEO Ted Decker",
    "2025 Investor Conference · CFO McPhail (on the Market Recovery Case)",
]

FACT_FOLLOWUP = [
    ("CEO return timeline", "any disclosure on the length of the leave or on succession (an 8-K level event)"),
    ("Q3 FY2026 results", "gross margin and comps after the tariff refund rolls off (due November)"),
    ("Housing turnover", "whether existing-home sales and pending contracts stop falling — the leading "
                         "indicator for big-ticket demand"),
    ("SRS integration and cross-sell", "90% of stores already transact via SRS; watch conversion rates and "
                                       "the HVAC vertical ramp"),
    ("Timing of buyback resumption", "buybacks are paused through 2027; resumption would signal a shift in "
                                     "capital allocation"),
    ("Tariffs and trade policy", "cost pass-through after the Section 101 expiry, and progress on supply-"
                                 "chain diversification"),
]

FACT_BADGES_FIXED = {
    "ceo_leave": "CEO on temporary medical leave",
    "refund": "One-off tariff refund",
    "srs": "SRS distribution growing fast",
    "near_low": "Share price near 52-week low",
}


# ================================================================ 来源标注的英文对照
# 精确匹配 config.py 中的 src 字段；未收录的保持原文（可接受的降级）。
SRC_EN = {
    "Q2 电话会 + 第三方研报": "Q2 earnings call + third-party research",
    "Q2 电话会 + 第三方研报综合": "Q2 earnings call + third-party research",
    "Q2 电话会": "Q2 FY2026 earnings call",
    "Q2 电话会（Billy Bastek）": "Q2 FY2026 earnings call (Billy Bastek)",
    "Q2 财报新闻稿": "Q2 FY2026 earnings release",
    "Q2 电话会 / 8-K": "Q2 earnings call / Form 8-K",
    "Q2 电话会 CFO 表述": "Q2 earnings call, CFO remarks",
    "Q2 电话会 Q&A": "Q2 earnings call Q&A",
    "8-K (2026-08-11) + Exhibit 99.1 公告": "Form 8-K (2026-08-11) + Exhibit 99.1 announcement",
    "2025 投资者大会新闻稿 + Q2 FY2026 电话会":
        "2025 Investor Conference release + Q2 FY2026 earnings call",
    "Q2 FY2026 电话会记录（2026-08-18）+ 新闻稿指引脚注":
        "Q2 FY2026 call transcript (2026-08-18) + guidance footnote in the release",
    "2025 投资者大会新闻稿（2025-12-09）+ Q2 FY2026 电话会":
        "2025 Investor Conference release (2025-12-09) + Q2 FY2026 earnings call",
}


def src_bi(s):
    """来源标注双语：有对照用对照，没有就中英同文。"""
    s = str(s if s is not None else "")
    return bi(s, SRC_EN.get(s, s))


# ================================================================ 查询接口
def get(key):
    """取 (zh, en)；找不到时退化为 (key, key)，不抛异常。"""
    if key in UI:
        return UI[key]
    if key in CH:
        return CH[key]
    return (key, key)


def S(key, tag="span"):
    zh, en = get(key)
    return bi(zh, en, tag)


def chart_pack():
    """给 ECharts 用的 payload 字典：{"zh": {...}, "en": {...}}"""
    keys = set(CH) | set(UI)
    return {
        "zh": {k: get(k)[0] for k in keys},
        "en": {k: get(k)[1] for k in keys},
    }
