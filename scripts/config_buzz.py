# -*- coding: utf-8 -*-
"""
渠道口径 + buzz 分析方法论。

对标口径：只保留能站内直抓的两家（2026-10-15 收敛）
--------------------------------------------------
看板第十二章与小程序「渠道对标」页**只对标 Amazon 与 Walmart** —— 这两家的站内数据
可以直抓，能给出同口径的排名 / 评分 / 评论数：

  Amazon   8 个畅销榜 / 新品榜，商品详情页有 captcha（主图取不到，配图用 Walmart 侧）
  Walmart  7 个 patio 品类页 + 评论页（支持「最低分优先」排序）

另三家已整体移出对标，原因是站内数据根本拿不到，并列进来只会伪造「可比性」：

  Home Depot  Akamai 指纹级拦截，类目页 / 产品页 / 内容页与 robots.txt 均 403
              （无头 Chrome、CORS 代理、r.jina.ai 文本代理同样被拒）
  Lowe's      整站 403 —— 实测连首页都是 Akamai「Access Denied」，
              robots.txt / sitemap.xml / 品类页 / 商品页全 403；api.lowes.com 需合作资质
  Costco      纯客户端渲染，HTML 里约 350 处 Skeleton 占位、零商品数据，三个内部接口 404

本机网络出口为共享代理，判定为「IP 段 + TLS 指纹」双重封锁，已无可绕行路径。

⚠️ 移出的是「渠道对比」，不是「研究覆盖」—— Home Depot 仍是本看板的研究主体。

存档：受限渠道的公开材料（不再渲染）
--------------------------------------------------
HD_ITEMS / HD_SRC 与 LOW_ITEMS / LOW_SRC 收录了这两家「公开渠道披露」的单品评分与
畅销信息，每条带 src 与可靠性等级。**这些数据保留在本文件里作存档**，但 CHANNELS 中
已标记 excluded=True，看板与小程序都不再渲染。若日后要恢复对比，改标记即可。

  index       搜索引擎索引到的零售商页面原文（如 homedepot.com.mx 商品列表）
  media_cited 第三方媒体在报道中引用零售商网站的数据（星级/评论数/价格）
  brand_site  品牌方官方站点的自述数据

铁律：**绝不估算、不推测、不用模型知识补数字。**
"""

CAPTURED_AT = "2026-10-05"

# ================================================================ 方法论
METHOD = {
    "framework_zh": [
        ("声量 Volume", "累计评分人数（reviews）。一个商品被多少人评价过，"
                        "是「有多少人在谈论/购买」最直接的公开代理指标。"),
        ("口碑 Valence", "平均星级（rating）。衡量这些谈论是偏正面还是偏负面。"
                         "换算为 3.5 星=0 分、5.0 星=1 分的线性刻度。"),
        ("动能 Momentum", "榜单名次。畅销榜反映当下正在卖得动的程度；"
                          "新品榜反映正在起量的新面孔。名次越靠前分越高。"),
    ],
    "framework_en": [
        ("Volume", "Cumulative rating count — the most direct public proxy for how many "
                   "people are talking about and buying an item."),
        ("Valence", "Average star rating — whether that chatter is positive. Scaled linearly "
                    "from 3.5★ = 0 to 5.0★ = 1."),
        ("Momentum", "Leaderboard rank — current sales velocity on the Best Sellers board, "
                     "and emerging demand on the New Releases board."),
    ],
    "weights": {"volume": 0.45, "valence": 0.30, "momentum": 0.25},
    "formula_zh": "buzz 综合分 = 0.45×声量分 + 0.30×口碑分 + 0.25×动能分（各分量先归一化到 0–1）",
    "formula_en": "buzz score = 0.45×Volume + 0.30×Valence + 0.25×Momentum (each normalised to 0–1)",
    "why_weights_zh": "声量权重最高，因为「多少人买过」比「少数人打几分」更难被操纵，"
                      "也更能代表真实的市场渗透；口碑次之；名次权重最低，因为榜单名次"
                      "波动最快、噪声最大。",
    "why_weights_en": "Volume carries the most weight because how many people bought is harder "
                      "to game than how a few people rated; rank carries the least because it "
                      "is the noisiest and moves fastest.",
    "limits_zh": [
        "只有累计评论数，没有评论增速 —— 因此本分析回答「谁已经火了」，"
        "不能回答「谁正在变火」。真正的增速需要历史快照，本项目靠每轮运行逐步积累。",
        "评论数受上架时间影响：老品的累计评论天然更高。跨品类比较时已按榜单内归一化处理，"
        "但仍不宜把「评论多」直接等同于「更受欢迎」。",
        "Amazon 榜单是「销量排名」，不是销售额排名，低价高频商品（如杀虫剂、泳池药剂）"
        "天然占优。这正是总榜头部被耗材占据的原因。",
        "一手数据只覆盖 Amazon 与 Walmart 两个渠道。Home Depot、Lowe's、Costco 的站内"
        "数据无法直抓（已整体移出对标，见第十二章），因此本页不提供跨渠道份额口径，"
        "也不把任何两家的原始分直接混算。",
    ],
    "limits_en": [
        "Only cumulative ratings, no velocity — this answers who is already big, not who is "
        "accelerating. True momentum needs historical snapshots, which this project accrues run by run.",
        "Rating counts favour older listings. Comparisons are normalised within each board, but "
        "'more reviews' still does not mean 'more loved'.",
        "Amazon boards rank by units, not revenue, so cheap high-frequency consumables "
        "(insecticides, pool chemicals) are structurally advantaged — which is exactly why the "
        "overall board is topped by consumables.",
        "First-party data covers Amazon and Walmart only. Home Depot, Lowe's and Costco cannot be "
        "scraped on-site and have been dropped from the comparison entirely (see section 12), so "
        "no cross-channel share metric is offered and no two channels' raw scores are ever blended.",
    ],
}

# ================================================================ Home Depot
HD_SRC = {
    "nb": {"name": "NewsBreak《11 Best New Home Depot Patio Finds》",
           "url": "https://www.newsbreak.com/n/1CYT6HyZ", "tier": "media_cited"},
    "mx": {"name": "homedepot.com.mx 商品列表（搜索索引快照）",
           "url": "https://www.homedepot.com.mx/b/jardin/muebles-de-jardin-y-accesorios/juegos-de-jardin",
           "tier": "index"},
    "bi": {"name": "Business Insider《16 best places to buy patio furniture in 2026》",
           "url": "https://thisisinsider.com/guides/home/yardbird-outdoor-furniture-overview",
           "tier": "media_cited"},
    "ca": {"name": "ConsumerAffairs：Hampton Bay 用户投诉汇总（530 条）",
           "url": "https://www.consumeraffairs.com/furniture/hampton_bay.html",
           "tier": "media_cited"},
}

# rating / reviews 为 None 表示该来源未披露该项 —— 不推测
HD_ITEMS = [
    {"brand": "Hampton Bay", "name_zh": "Chalk 金属庭院凳（可作边几/脚凳）",
     "name_en": "Chalk Metal Patio Garden Stool", "price": 44.0,
     "rating": 4.9, "reviews": None, "note_zh": "HD 网站评分 4.9，含 200+ 条五星评价",
     "note_en": "4.9-star average on Home Depot with 200+ five-star reviews", "src": "nb"},
    {"brand": "Hampton Bay", "name_zh": "Ashbourne 5 件套金属客厅组",
     "name_en": "Ashbourne 5-Piece Metal Patio Conversation Set", "price": 678.0,
     "rating": None, "reviews": None, "note_zh": "测评与用户评论称钢结构扎实、做工不廉价",
     "note_en": "Reviewers call it solid and heavy-duty rather than flimsy", "src": "nb"},
    {"brand": "Hampton Bay", "name_zh": "Windy Hill 3 件套相思木休闲组",
     "name_en": "Windy Hill 3-Piece Acacia Wood Outdoor Chat Set", "price": 278.0,
     "rating": None, "reviews": None, "note_zh": "小空间适配，常出现在促销位",
     "note_en": "Small-space pick, frequently promoted", "src": "nb"},
    {"brand": "Hampton Bay", "name_zh": "Autumn Glen 户外扶手椅",
     "name_en": "Autumn Glen Adirondack Chair", "price": 139.0,
     "rating": None, "reviews": None, "note_zh": "复合材料，耐久优于传统木材",
     "note_en": "Composite build, more durable than traditional wood", "src": "nb"},
    {"brand": "Hampton Bay", "name_zh": "LED 串灯（灯笼造型）",
     "name_en": "LED Lantern String Light", "price": 22.51,
     "rating": None, "reviews": None, "note_zh": "低单价高频配件，评论以氛围感为主",
     "note_en": "Low-ticket accessory, reviews focus on ambience", "src": "nb"},
    {"brand": "Hampton Bay", "name_zh": "嵌入式 LED 地台灯",
     "name_en": "Integrated LED Deck Light", "price": 29.97,
     "rating": None, "reviews": None, "note_zh": "49 流明，用作安全与氛围照明",
     "note_en": "49 lumens, dual safety and ambience use", "src": "nb"},
    {"brand": "Home Decorators Collection", "name_zh": "Palm Cove 室内外吊扇",
     "name_en": "Palm Cove Indoor/Outdoor Ceiling Fan", "price": 149.0,
     "rating": None, "reviews": None, "note_zh": "半户外空间的降温方案",
     "note_en": "Cooling for covered outdoor spaces", "src": "nb"},

    {"brand": "Hampton Bay", "name_zh": "Laurel Oaks 4 件套（金属框架）",
     "name_en": "Laurel Oaks 4-Piece Set (Metal Frame)", "price": None,
     "rating": 4.7, "reviews": 576, "note_zh": "HD 官网商品页评分，SKU 201862",
     "note_en": "Home Depot listing rating, SKU 201862", "src": "mx"},
    {"brand": "Hampton Bay", "name_zh": "Danbury 4 件套金属组",
     "name_en": "Danbury 4-Piece Metal Set", "price": None,
     "rating": 4.7, "reviews": 41, "note_zh": "HD 官网商品页评分，SKU 214805",
     "note_en": "Home Depot listing rating, SKU 214805", "src": "mx"},
    {"brand": "StyleWell", "name_zh": "Barksdale 4 件套",
     "name_en": "Barksdale 4-Piece Set", "price": None,
     "rating": 4.4, "reviews": 7, "note_zh": "HD 官网商品页评分，SKU 234007",
     "note_en": "Home Depot listing rating, SKU 234007", "src": "mx"},

    {"brand": "Hampton Bay / Stylewell", "name_zh": "自有品牌矩阵（户外线）",
     "name_en": "Private-label matrix (outdoor)", "price": None,
     "rating": None, "reviews": None,
     "note_zh": "HD 户外家具以自有品牌为主：Hampton Bay（主力）、Stylewell（性价比）、"
                "Home Decorators Collection（高端）、Martha Stewart（联名）",
     "note_en": "HD outdoor furniture is led by private labels: Hampton Bay (core), "
                "Stylewell (value), Home Decorators Collection (premium), Martha Stewart (licensed)",
     "src": "bi"},
    {"brand": "Hampton Bay", "name_zh": "质量口碑的双面性",
     "name_en": "Two-sided quality reputation", "price": None,
     "rating": 1.2, "reviews": 530,
     "note_zh": "ConsumerAffairs 上 530 条投诉帖给出 1.2 分，集中在锈蚀、缺件、客服响应慢；"
                "该站为投诉聚合站，样本天然负面，不能与零售站评分直接对比，仅作风险提示",
     "note_en": "530 complaint threads average 1.2 on ConsumerAffairs, focused on rust, missing "
                "parts and slow service. A complaint aggregator skews negative by design and must "
                "not be compared head-to-head with retail ratings — shown as a risk flag only",
     "src": "ca"},
]

# ================================================================ Lowe's
LOW_SRC = {
    "hunk": {"name": "Hunker《5 Patio Finds At Lowe's With Deep Discounts》",
             "url": "https://www.hunker.com/2213135/lowes-patio-finds-deep-discounts-july-2026/",
             "tier": "media_cited"},
    "bl1": {"name": "Best Life《11 Best Lowe's Sales Starting This Week》",
            "url": "https://bestlifeonline.com/lowes-sales-sept-16-2026/", "tier": "media_cited"},
    "bl2": {"name": "Best Life《11 Best New Lowe's Finds Flying Off Shelves》",
            "url": "https://bestlifeonline.com/lowes-finds-flying-this-weekend-sept-27-2026/",
            "tier": "media_cited"},
    "ar": {"name": "allen + roth 品牌站",
           "url": "https://allenrothco.com/allen-and-roth-patio-furniture", "tier": "brand_site"},
    "yh": {"name": "Yahoo News《6 Best Outdoor Furniture Brands》",
           "url": "https://sg.news.yahoo.com/6-best-outdoor-furniture-brands-103222509.html",
           "tier": "media_cited"},
}

LOW_ITEMS = [
    {"brand": "allen + roth", "name_zh": "Glenwillow 5 件套餐桌组",
     "name_en": "Glenwillow 5-Piece Dining Set", "price": None,
     "rating": 4.5, "reviews": 1247, "note_zh": "4.5 星 / 1,247 条已验证评论，是 Lowe's 户外线里"
                                              "评论量最大的单品之一",
     "note_en": "4.5★ across 1,247 verified reviews — among the highest-volume Lowe's outdoor SKUs",
     "src": "ar"},
    {"brand": "allen + roth", "name_zh": "32 英寸钢制方形火炉桌",
     "name_en": "32-in Steel Square Fire Pit Table", "price": 279.0,
     "rating": None, "reviews": None,
     "note_zh": "被明确描述为 Lowe's 畅销款；原价 $399 促销至 $279，多用户给出五星",
     "note_en": "Described as Lowe's bestseller; $399 cut to $279, with many five-star reviews",
     "src": "hunk"},
    {"brand": "Tommy Bahama", "name_zh": "Sojag 10×12 双顶凉亭",
     "name_en": "Sojag 10×12 Brown Gazebo", "price": 1900.0,
     "rating": None, "reviews": None,
     "note_zh": "原价 $3,565；安装难度高是评论集中反馈点",
     "note_en": "$3,565 list; difficult assembly is the recurring complaint", "src": "hunk"},
    {"brand": "allen + roth", "name_zh": "Chatham Pier 4 件套客厅组",
     "name_en": "Chatham Pier 4-Piece Conversation Set", "price": 548.0,
     "rating": None, "reviews": None,
     "note_zh": "用户实测抗风雪，极端天气后结构无变形",
     "note_en": "Reviewers report it survived a blizzard with no structural damage", "src": "bl1"},
    {"brand": "Style Selections", "name_zh": "铝制长椅（含灰色坐垫）",
     "name_en": "Aluminum Bench with Gray Cushion", "price": 149.0,
     "rating": None, "reviews": None, "note_zh": "铝合金框架，主打轻量耐用",
     "note_en": "Aluminium frame, positioned on light weight and durability", "src": "bl1"},
    {"brand": "Fire Sense", "name_zh": "落地式丙烷取暖器",
     "name_en": "Floorstanding Propane Patio Heater", "price": 152.71,
     "rating": 4.8, "reviews": None,
     "note_zh": "Lowe's 网站 4.8 星，48,000 BTU、覆盖 18 英尺",
     "note_en": "4.8★ on Lowe's site; 48,000 BTU covering an 18-ft radius", "src": "bl2"},
    {"brand": "allen + roth", "name_zh": "31.5 英寸圆形燃木火盆",
     "name_en": "31.5-in Round Wood-Burning Fire Pit", "price": 129.0,
     "rating": None, "reviews": None, "note_zh": "含防尘盖、网罩与拨火棍",
     "note_en": "Includes cover, screen and poker", "src": "bl2"},
    {"brand": "allen + roth", "name_zh": "水葫芦编织收纳篮",
     "name_en": "Large Natural Water Hyacinth Stackable Basket", "price": 29.48,
     "rating": 4.8, "reviews": None, "note_zh": "Lowe's 网站 4.8 星，价格敏感型高频配件",
     "note_en": "4.8★ on Lowe's site; a price-sensitive high-frequency accessory", "src": "bl2"},
    {"brand": "allen + roth", "name_zh": "Vineburg 3 件套藤编小桌组",
     "name_en": "Vineburg 3-Piece Wicker Bistro Set", "price": 279.0,
     "rating": None, "reviews": None, "note_zh": "小空间咖啡角方案",
     "note_en": "Small-footprint coffee-corner solution", "src": "ar"},
    {"brand": "allen + roth", "name_zh": "Bramblewood 6 件套户外餐桌组",
     "name_en": "Bramblewood 6-Piece Patio Dining Set", "price": 498.0,
     "rating": None, "reviews": None, "note_zh": "带坐垫，定位家庭烧烤场景",
     "note_en": "With cushions, aimed at family cookouts", "src": "ar"},
    {"brand": "allen + roth", "name_zh": "品牌规模与定位",
     "name_en": "Brand scale and positioning", "price": None,
     "rating": None, "reviews": None,
     "note_zh": "2007 年推出，覆盖 8+ 户外家具品类，进入 1,700+ 家 Lowe's 门店；"
                "定位介于性价比与中端之间，并与 POLYWOOD 合作推出联名线",
     "note_en": "Launched 2007, spans 8+ outdoor categories across 1,700+ Lowe's stores, sits "
                "between value and mid-tier, and has a co-branded line with POLYWOOD",
     "src": "ar"},
]

# ================================================================ 渠道定位
# 用于看板第十二章的「渠道特征对比」——只陈述公开可核实的事实，不做份额推测。
# excluded=True 的三家已整体移出对标（站内不可直抓，并列进来会伪造可比性），
# 数据保留在此仅作存档，看板与小程序都不会渲染。
CHANNELS = [
    {"key": "amazon", "name_zh": "Amazon", "name_en": "Amazon",
     "data_tier_zh": "一手直抓", "data_tier_en": "First-party scrape",
     "strength_zh": "公开畅销榜与评分数据最完整，长尾第三方品牌密集，"
                    "价格透明、比价压力最大",
     "strength_en": "Most complete public leaderboards and ratings data; dense long tail of "
                    "third-party brands; fully transparent pricing",
     "brand_zh": "以第三方品牌与白牌为主（Zevo、TERRO、POLYWOOD、GCI 等）",
     "brand_en": "Mainly third-party and white-label brands",
     "access_zh": "8 个畅销榜 / 新品榜可直抓；商品详情页有 captcha，主图取不到，"
                  "所以配图统一用沃尔玛侧",
     "access_en": "Eight best-seller / new-release boards scrape cleanly; product detail pages "
                  "serve a captcha and main images are unavailable, so photos come from Walmart",
     "src": "fetch_buzz.py"},
    {"key": "walmart", "name_zh": "Walmart", "name_en": "Walmart",
     "data_tier_zh": "一手直抓", "data_tier_en": "First-party scrape",
     "strength_zh": "大件家具与遮阳的铺货厚度全场最高，中端自有品牌密集，"
                    "价格带整体低于亚马逊；但评价水位明显更浅"
                    "（中位评价数 122 条 vs 亚马逊 5,528 条），口碑样本更薄",
     "strength_en": "Deepest assortment in bulky furniture and shade, dense mid-tier private "
                    "labels and a lower price band than Amazon — but far shallower review "
                    "coverage (median 122 ratings vs Amazon's 5,528), so sentiment samples are thinner",
     "brand_zh": "Better Homes & Gardens / Mainstays / Ozark Trail / Expert Grill / Hyper Tough",
     "brand_en": "Better Homes & Gardens / Mainstays / Ozark Trail / Expert Grill / Hyper Tough",
     "access_zh": "7 个 patio 品类页直抓（296 件）；评论页支持「最低分优先」排序，"
                  "是负评归纳的数据源。⚠️ 站内有速率风控，页间隔需 12–16 秒",
     "access_en": "Seven patio category pages scrape cleanly (296 items); the review pages "
                  "support a lowest-rating-first sort, which powers the complaint analysis. "
                  "Rate-limited: 12–16s between pages",
     "src": "fetch_walmart.py"},
    {"key": "hd", "name_zh": "Home Depot", "name_en": "Home Depot", "excluded": True,
     "data_tier_zh": "受限（站内不可直抓）", "data_tier_en": "Restricted (on-site not scrapable)",
     "strength_zh": "自有品牌主导户外线，线下门店可现场试坐验货，"
                    "大件配送与门店自提形成便利性优势",
     "strength_en": "Private labels lead outdoor; physical stores allow try-before-buy; "
                    "delivery and curbside pickup are the convenience edge",
     "brand_zh": "Hampton Bay / Stylewell / Home Decorators Collection / Martha Stewart",
     "brand_en": "Hampton Bay / Stylewell / Home Decorators Collection / Martha Stewart",
     "access_zh": "站内被 Akamai 拦截，robots.txt 亦返回 403；只有 IR / 新闻稿等"
                  "公开披露材料可读",
     "access_en": "On-site pages are blocked by Akamai and even robots.txt returns 403; only "
                  "public disclosures (IR, press releases) are readable",
     "src": "config_buzz.HD_ITEMS"},
    {"key": "low", "name_zh": "Lowe's", "name_en": "Lowe's", "excluded": True,
     "data_tier_zh": "受限（站内不可直抓）", "data_tier_en": "Restricted (on-site not scrapable)",
     "strength_zh": "allen + roth 一个品牌覆盖绝大部分户外品类，"
                    "风格跨度大、促销折扣力度常高于同业",
     "strength_en": "A single allen + roth label spans most outdoor categories, with wide style "
                    "range and frequently deeper promotions",
     "brand_zh": "allen + roth（主力）/ Style Selections / 联名 POLYWOOD",
     "brand_en": "allen + roth (core) / Style Selections / POLYWOOD collab",
     "access_zh": "整站返回 403（含 robots.txt），无头浏览器与多个代理通道同样被拒",
     "access_en": "The whole site returns 403 (robots.txt included); headless browsers and "
                  "several proxy routes were refused as well",
     "src": "config_buzz.LOW_ITEMS"},
    {"key": "costco", "name_zh": "Costco", "name_en": "Costco", "excluded": True,
     "data_tier_zh": "受限（客户端渲染，无服务端数据）",
     "data_tier_en": "Restricted (client-side rendered, no server payload)",
     "strength_zh": "SKU 极窄、季节性上架，走仓店大包装与限时特价；单款议价能力强，"
                    "但可选款式与尺寸远少于专业家居建材渠道，复购与配件生态也弱",
     "strength_en": "Extremely narrow SKU count, seasonal listings, warehouse bulk packs and "
                    "time-limited deals. Strong bargaining power per item, but far fewer styles "
                    "and sizes than home-improvement specialists, with a weak accessory ecosystem",
     "brand_zh": "Sunvilla / Agio / Lifetime 等仓店专供与联名款",
     "brand_en": "Warehouse-exclusive and collab labels such as Sunvilla / Agio / Lifetime",
     "access_zh": "页面为纯客户端渲染，HTML 里只有约 350 处 Skeleton 占位、无任何商品数据；"
                  "三个内部接口均返回 404。本节只做定性描述，不填任何数字",
     "access_en": "Pages are purely client-side rendered — the HTML carries roughly 350 skeleton "
                  "placeholders and no product data at all, and three internal endpoints return "
                  "404. This entry stays qualitative and contributes no numbers",
     "src": "—（仅定性，无一手数据）"},
]

# ================================================================ 品类洞察
# 由 Amazon 榜单数据算出的事实性观察（数字在 analyze_buzz.py 中动态计算，此处只放定性结论与来源）
NOTES = {
    "consumable_zh": "亚马逊「庭院与户外」总榜前六名全部是杀虫类耗材（Zevo、TERRO、Ortho）。"
                     "这不是数据错误 —— 该榜按销售件数排，低单价、高复购、全年刚需的耗材"
                     "天然压过单价高、一次性购买的大件家具。看家具要看子类榜，别看总榜。",
    "consumable_en": "The top six of Amazon's overall Patio, Lawn & Garden board are all "
                     "insect-control consumables (Zevo, TERRO, Ortho). This is not a data error: "
                     "the board ranks by units, so cheap, repeat-purchase, year-round essentials "
                     "structurally outrank one-off big-ticket furniture. Read the sub-category "
                     "boards for furniture, not the overall board.",
    "category_zh": "Amazon 的「Patio Furniture & Accessories」节点并非纯家具 —— "
                   "它把冷藏箱、保温冰袋、露营椅也算进来了。因此本页在做家具分析时"
                   "按标题关键词重新归了类，并单独列出分类结果，避免把冷藏箱当成户外家具。",
    "category_en": "Amazon's 'Patio Furniture & Accessories' node is not purely furniture — it "
                   "also contains coolers, ice packs and camping chairs. Products are therefore "
                   "re-categorised by title keywords here, and the resulting split is shown "
                   "explicitly so coolers are not mistaken for outdoor furniture.",
}
