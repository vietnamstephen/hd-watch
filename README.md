# Home Depot (HD) 专项研究看板

为 HD 员工定制的单一公司研究看板：**股价波动、季度财报归纳、管理层讲话、扩店计划、
中美贸易（关税）、公司战略与长期情景**，每月自动更新一次并存入 WorkBuddy 资料库。

## 快速使用

```bash
# 一键跑完（九步：抓数据 → 双渠道打分 → 重建看板 → 重建小程序数据 → 自检）
# 耗时约 12–15 分钟（Walmart 两步占约 11 分钟，都有页间隔退避防风控）
cd hd-watch/scripts && /Users/xuyousheng/.workbuddy/binaries/python/envs/default/bin/python -u run_cycle.py

# 需要分步时（run_cycle 内部就是按这个顺序调的）
python -u fetch_hd.py                # ① 行情 / SEC / IR 财报材料 / 新闻
python -u fetch_buzz.py              # ② Amazon 8 个声量榜单
python -u fetch_walmart.py           # ③ Walmart 7 个 patio 品类页（一手供给）
python -u fetch_walmart_reviews.py   # ④ Walmart「最低分优先」评论页（负评归纳）
python -u fetch_star_images.py       # ⑤ 明星产品配图（Walmart 图 CDN，双产物）
python -u analyze_buzz.py            # ⑥ 双渠道打分 / 档次阶梯 / 差评主题 / 跨渠道冠军
python -c "import build_hd; build_hd.build()"   # ⑦ 重建看板
python build_miniprogram.py          # ⑧ 重建小程序数据
python check_miniprogram.py          # ⑨ 小程序自检
```

`run_cycle.py` 的开关：`--no-buzz`（跳过 Amazon 榜单）、`--no-walmart`（跳过 Walmart 三步，
赶时间时用）、`--no-build`（只抓数据）、`--no-check`。
退出码 0 = 无硬失败，1 = 有硬失败。汇总里 `✅` 成功 / `⚠️` 软失败（不阻断，如 Walmart 评论）
/ `❌` 硬失败 —— 软失败步骤也会如实标出，不要只看退出码。

- **在线版本**：`https://www.workbuddy.cn/space/d/GXXyK0U3j89dHVG2JEAhgN`（资料库节点，覆盖更新，链接恒定）
- **本地版本**：`hd-watch/dashboard/index.html`（自包含单文件，约 1.45 MB，ECharts 与 7 张配图均已内联、零外部请求，手机可直接打开）
- **小程序**：`hd-watch/miniprogram/`（4 个 tab，数据内置随包发布；本轮新增「品类对标」tab）
- **自动化**：每月 18 日 09:00 自动执行并覆盖资料库节点（含新财报的归纳更新）

## 数据源（全部免密钥、可回溯）

| 数据 | 来源 | 说明 |
|---|---|---|
| 行情与波动 | Yahoo Finance（yfinance） | 2 年日线、均线、52 周区间、波动率、最大回撤 |
| 基本面 | yfinance `.info` | 市值、PE、股息率、分析师目标价 |
| 监管文件 | SEC EDGAR submissions API | 10-K / 10-Q / 8-K / DEF 14A 列表与原文链接 |
| 财报原文 | ir.homedepot.com（PDF） | 新闻稿 + 电话会记录，pypdf 提取文本后人工核对入库 |
| 新闻 | yfinance news + Yahoo RSS | 标题级列表 |

**静态事实的口径**：`scripts/config.py` 中所有静态事实（战略、门店、指引、关税明细、
管理层履历）都标了 `src` 字段，对应 `data/docs/` 里的原始 PDF 或 SEC 链接，看板上一并展示。

## 目录

```
hd-watch/
├── scripts/
│   ├── config.py              # 元数据 + 已核实事实库（每条带 src）
│   ├── config_buzz.py         # 渠道口径（只对标 Amazon·Walmart）/ HD·Lowe's 公开单品存档
│   ├── patio_taxonomy.py      # ★ 品类口径单一事实来源（7 类规则 + 61 条回归用例）
│   ├── fetch_hd.py            # 动态数据抓取（行情 / SEC / IR PDF / 新闻）
│   ├── fetch_buzz.py          # Amazon 8 个声量榜单
│   ├── fetch_walmart.py       # Walmart 7 个 patio 品类页
│   ├── fetch_walmart_reviews.py  # Walmart「最低分优先」评论页（负评归纳）
│   ├── fetch_star_images.py   # 明星产品配图（看板 base64 + 小程序文件，双产物）
│   ├── analyze_buzz.py        # 打分 / 渠道对比 / 档次阶梯 / 差评主题 / 跨渠道冠军
│   ├── build_hd.py            # 看板生成器（自包含单文件，13 章）
│   ├── build_miniprogram.py   # 小程序数据压缩（mini.js）
│   ├── check_miniprogram.py   # 小程序自检（17 项）
│   ├── make_tabbar_icons.py   # 生成 tabBar 图标（4 个）
│   └── run_cycle.py           # 九步统一入口
├── data/
│   ├── quote.json / filings.json / ir.json / news.json
│   ├── buzz.json / buzz_analysis.json          # Amazon + 双渠道分析结果
│   ├── walmart.json / walmart_reviews.json     # Walmart 一手供给与差评
│   ├── star_images.json                        # 配图（base64）
│   └── docs/                                   # 财报 PDF 原文与提取文本、IR 文档缓存
├── dashboard/
│   ├── index.html             # 生成的看板（约 1.45 MB）
│   └── vendor/echarts.min.js  # 内联用图表库副本
└── miniprogram/               # 「HD 户外周报」小程序（4 tab）
    ├── data/mini.js           # 随包数据（由 build_miniprogram.py 生成）
    └── images/star/           # 明星产品配图（小程序专用副本）
```

## 关键口径（避免误读）

1. **量价拆分**：HD 的增长常由客单价（含关税成本传导）驱动，交易量可能在下滑 ——
   两者必须并排看，只看销售额会误判需求。
2. **关税退款**：IEEPA 退款是一次性现金流收益（Q2 $7.30 亿，其中 $6.85 亿流入销货成本，
   对毛利率净改善约 +25bp），不是经营性改善；公司明确表示全年成本上行将完全抵消该收益。
3. **情景框架**：HD 不公布逐年 5 年数字目标，而是给出基准 / 市场复苏 / 加速复苏三种情景；
   看板如实呈现三种情景，不替公司发明"5 年计划"数字。
4. **季度数据**：本板 Q1 FY2026 数字由半年报减 Q2 得出（与原文一致），单位为百万美元。

## 已知限制

- 财报电话会记录（transcript）由 IR 网站提供，通常滞后 1–2 周；新季度发布后约两周内材料齐全。
- 分析师目标价、PE 等为第三方聚合数据（yfinance），仅做算术展示（如"较现价 +33%"），不构成评级。
- 自动化若在某月检测到新财报，会先备份 `config.py` 再更新归纳要点，语法校验失败自动回滚。

## 双语与主题切换（2026-10-05 追加）

看板支持两个可切换维度，右上角控件即时生效，选择写入 localStorage 下次自动沿用：

| 维度 | 选项 | 说明 |
|---|---|---|
| 语言 | 中文 / EN | 全站 257 处文案 + 9 张图表内文字全部双语 |
| 主题 | ☀ 浅色 / ☾ 深色 | CSS 变量两套，图表颜色重绘时从 CSS 变量读取，与页面永远一致 |

也支持 URL 参数直达（优先级最高，便于分享指定形态）：
`index.html?theme=dark&lang=en`

**双语实现**（`scripts/i18n.py`，162 组词条）：
- HTML 静态/动态文案 → `<span class="i18n" data-zh="…" data-en="…">`，切换时 JS 换 `textContent`
- 图表内文字（canvas 画不了 DOM）→ 随 payload 注入 `L: {zh:{…}, en:{…}}` 字典，切换后整套图表重绘
- 中文事实的**权威源仍是 `config.py`**；`i18n.py` 里的 `FACT_*` 只是英文译文，按位置一一对应，
  改 config 结构时必须同步维护

**一个刻意的设计**：涨跌颜色跟随所选语言的地区惯例——中文模式涨红跌绿，
英文模式自动切换为国际惯例（绿涨红跌，CSS 变量覆盖 + 图表重绘自动生效），
口径说明会随语言同步改写，避免读者误解。

**代码层面的健壮性**：任何词条缺失都退化为中文不白屏；localStorage 被沙箱禁用时静默降级；
切换时全部 ECharts 实例 dispose 后重建，不留旧色残留。

## 网评分 / 畅销榜 / Patio buzz 分析（2026-10-05 第二次追加）

看板从 9 章扩到 12 章，新增「网评分与畅销榜」「Patio 明星产品 buzz 分析」「三渠道对标」。

### 数据管道

```
fetch_buzz.py   → data/buzz.json          （Amazon 8 个榜单 × 30 条原始数据）
analyze_buzz.py → data/buzz_analysis.json （打分、三层分组、品类聚合）
config_buzz.py  → HD / Lowe's 公开披露数据  （每条带 src 与可靠性等级）
```

### 为什么 HD / Lowe's 的站内评分不是直抓的

两站的商品数据被 Akamai 指纹级防护：urllib 直连（含 .com/.com.mx/.ca 与 robots.txt）、
无头 Chrome（含自动化特征屏蔽）、5 个公开 CORS 代理、r.jina.ai、Google Shopping、
Bing 富片段——全部实测被拒（403/522/429 或无结构化字段）。
因此 Amazon 做一手数据源（8 榜单 × 30 条，含排名/评分/评论数），
HD / Lowe's 用公开渠道披露的单品信息（可靠性三级：搜索索引快照 / 媒体引用 / 品牌官方站），
**每条标注来源，拿不到的绝不推测**。

### buzz 打分

`buzz = 0.45×声量 + 0.30×口碑 + 0.25×动能`，三个分量各自归一化：
- 声量 = log10(累计评论数)，**在同一榜单内**做 min-max 归一化（评论数跨三个数量级）
- 口碑 = (评分 − 3.5)/1.5，截断到 [0,1]
- 动能 = 1 − (名次−1)/(条数−1)

**为什么必须在榜内打分**：畅销榜中位评论上万、新品榜只有一百，跨榜比较
等于在比上架时间。所以新品榜单独输出为「新星」，不与长销明星混排。

**为什么家具/设备/配件要分层**：配件（防尘罩、冷藏箱）的评论量天然碾压大件家具
（低单价、高频、易复购），混排的榜单会被配件永久霸占。

### 三个写进看板的重要事实

1. Amazon 庭院户外**总榜前六名全是杀虫耗材**——榜单按件数排，低价高复购商品结构性占优。
   看家具要看子类榜。
2. Amazon 的「Patio Furniture & Accessories」节点**并不纯是家具**（含冷藏箱、露营椅），
   已按标题关键词重新归类并展示口径。
3. Amazon 上真正的桌椅家具极少上榜，家具类头部全是**遮阳设备**——大件家具走线下渠道，
   这是渠道结构性差异，不是数据缺失。

### 踩坑记录（fetch_buzz.py 注释里也有）

- **URL 形式决定拿到什么榜单**：`/Best-Sellers-Patio-Lawn-Garden/zgbs/lawn-garden`
  在限流后可能返回 3.7KB 空壳，若只按长度重试会**静默拿到别的榜单内容**
  （实测「总榜」被写成了「虫害榜」）。现在统一用 `/gp/bestsellers/lawn-garden`，
  解析后强制校验页面 title，并做跨榜单 ASIN 重复检测。
- **品类关键词必须按词边界 + 复数匹配**：子串匹配会让 "table" 命中 "tablets"
  （泳池氯片进家具榜）；只匹配单数会让 "Chair Covers" 漏掉 cover（椅子套霸榜家具榜）。
  现有 18 条回归用例固化在开发过程中，每次改 CATS 都要重跑。
- **Amazon 有速率限制**：请求间隔 2.2s 起 + 指数退避；空壳页（<30KB 且无 gridItemRoot）
  必须重试而不是直接解析。

## 品类档次对标 + 五渠道 + 负评归纳（2026-10-13 第三次追加）

看板从 12 章扩到 13 章，小程序从 3 个 tab 扩到 4 个 tab（新增「品类对标」）。
一轮改造同时补齐了用户提的 7 条需求，落点是新增章节 + 新增 tab。

### 七类 patio 口径（`patio_taxonomy.py` 是唯一事实来源）

`PATIO_KEYS` = 成套家具 / 单件组合家具 / 遮阳伞 / 篷房与凉亭 / 露营与便携 / 配件与耗材 / 烧烤与火炉。
四条铁律：① 规则顺序即优先级，命中即停；② `off_topic` 必须放最后；
③ 别用裸词（`storage` / `garden` / `cabinet` / `cover`）；④ 词边界 + 规则复数
（注意 `chlorin` 匹配不到 `chlorine`，必须写 `chlor`）。
`CASES` 有 **61 条回归用例**，改规则必须重跑 `python patio_taxonomy.py`。

### 档次阶梯的口径修正（重要）

早期用「在架件数」当需求体量轴，结果把「成套家具」打到末位并标成「机会/利基」——
件数反映的是**渠道招商策略**，不是品类需求规模：大件家具走线下，本来就不在 Amazon 榜上。
现在体量轴改为 `log10(两渠道累计评论数 + 1)`。

定位分 = `0.40×体量 + 0.35×口碑 + 0.25×(-差评率)`（各自 z 分后加权）。
梯队（第一/二/三）**只按排名分档**，抱怨压力（低/中/高）单独成列 —— 不要把两件事混读。

本期结果：

| # | 品类 | 定位分 | WM 件 | 加权星 | 差评率 | 梯队 |
|---|---|---|---|---|---|---|
| 1 | 烧烤与火炉 | +1.280 | 49 | 4.64 | 4.1% | 第一 |
| 2 | 配件与耗材 | +0.793 | 79 | 4.45 | 8.0% | 第一 |
| 3 | 露营与便携 | +0.462 | 39 | 4.55 | 7.1% | 第二 |
| 4 | 遮阳伞 | −0.162 | 46 | 4.42 | 8.5% | 第二 |
| 5 | 单件组合家具 | −0.229 | 16 | 4.46 | 7.3% | 第三（评论样本 947 条，置信度低）|
| 6 | 成套家具 | −0.789 | 27 | 4.30 | 13.1% | 第三 |
| 7 | 篷房与凉亭 | −1.356 | 40 | 4.07 | 21.1% | 第三 |

### 渠道可得性（实测结论）

⚠️ **2026-10-15 口径收敛**：下表五家的探测结论仍然有效，但**只有 Amazon 与 Walmart 进入对标**
（详见文末「第四次追加」）。

| 渠道 | 结论 | 证据 |
|---|---|---|
| Amazon | 一手直抓 | 8 个畅销榜；商品详情页有 captcha，**主图三路全封** |
| Walmart | 一手直抓 | 7 个品类页（296 件）+ 评论页支持「最低分优先」排序 |
| Home Depot | 受限 | 站内 Akamai 403，连 robots.txt 也是 403；只有 IR / 新闻稿可读 |
| Lowe's | 受限 | 整站 403（含 robots.txt），无头浏览器与多个代理通道同样被拒 |
| Costco | 受限 | 纯客户端渲染：HTML 里约 350 处 Skeleton 占位、零商品数据，三个内部接口全 404 |

**配图统一取 Walmart 公开 CDN**（`i5.walmartimages.com`）——Amazon 三路皆封已实证排除。

### 负评归纳怎么做的（这里踩过一个坑）

`props.pageProps.initialData.data.reviews.aspects[]` **只有 `snippetCount`（提及数），没有正负极性** ——
早期方案基于「aspects 带正负计数」的假设，实测全空。
`bulletReviewSummary.bulletSummaryAspects[].aspectPolarity` 有极性，但只给 6 条、样本里常常全是 Positive。
**可靠做法**：`?sort=rating-asc&page=N` 直接拉最低分优先页（实测前 10 条全 1 星），
再对自定义的 12 项痛点词表做命中统计。本期 14 款商品 / 242 条差评 / 0 错误。

**引语去重**：一段差评常同时吐槽 4–5 个点，按 `helpful` 挑会让同一段话出现在多个主题下。
现在用「专属性」打分：`helpful*100 − (命中主题数−1)*10 − |len−200|*0.05`。

**别再设总数上限**：`MAX_PRODUCTS` 早期写成 12，而 7 品类 × 2 = 14，
会把排在最后的「烧烤与火炉」整类截掉、导致该品类差评率恒为空。现在是 `MAX_PRODUCTS = 0`（不设上限）。

### 小程序侧

第 4 个 tab「品类对标」：口径折叠卡 → 档次阶梯（含自动解读）→ 渠道供给厚度（蓝=Amazon / 紫=Walmart）
→ 各品类明星产品（实物图，Amazon 侧设计上无图）→ 负评归纳（含引语）→ 品类×痛点热力矩阵。
首页顶部新增「数据要点」7 条 bullet，每条都能追溯到下方某个卡片。

自检从 16 项扩到 **17 项**；`check_miniprogram.py` 现在会收集 `wx:for-item` 自定义的循环变量名，
避免把 `{{c.x}}` 这类合法局部引用误报成「未声明的 data 变量」。

## 渠道口径收敛为双渠道（2026-10-15 第四次追加）

**需求原话**：「既然 homedepot 和沃尔玛网站防爬虫，就去掉，把重点集中在 amazon 和 lows 头上」，
追问后确认为「**那个不能抓的就去掉，保留容易抓的**」。

⚠️ 需求里的前提与实际相反，这里立此存照：**能抓的是 Amazon 与 Walmart**，
不能抓的是 **Home Depot 与 Lowe's（都是 Akamai 全站 403，Lowe's 连首页都是 Access Denied）
以及 Costco（纯客户端渲染）**。所以按「去掉不能抓的」执行的结果是
**只对标 Amazon + Walmart**，而不是「Amazon + Lowe's」——后者的 Lowe's 侧会是空的。

### 改了什么

| 位置 | 改动 |
|---|---|
| `config_buzz.py` | `CHANNELS` 三条受限渠道加 `excluded: True`；模块 docstring 重写；`METHOD.limits` 第 4 条由「仅覆盖 Amazon」改为「只覆盖 Amazon 与 Walmart」 |
| `build_hd.py` | `_bz_chan_table` 只渲染非 `excluded` 的渠道，表下留一块「未纳入本节的三家渠道」口径说明；`_bz_sources_html` 去掉 HD·Lowe's 来源清单；模板删掉 `{{c.hditems}}` / `{{c.lowitems}}` 两张卡与 `__BZHD__` / `__BZLOW__` 两个占位 |
| 看板第十二章 | 章节名 →「双渠道对标：Amazon vs Walmart（均为一手直抓）」；表由 5 行 → **2 行** |
| `build_miniprogram.py` | `pick_channels` 改为返回 `(live, dropped)`；删掉 `pick_item` / `pick_sources`；`mini["channels_excluded"]` 记录被移出的三家名 |
| 小程序 compare 页 | 删掉「HD 关键单品」「Lowe's 关键单品」「来源与可靠性」三块；数据边界文案改写 |
| `check_miniprogram.py` | 必备字段由 `items,sources` 改为 `cats,brief` |

### 明确没动的

- **Home Depot 仍是研究主体** —— 行情、财报、SEC、IR、新闻（第一至第十一章）全部保留，
  被移出的只是「渠道对比」这一个维度。
- `HD_ITEMS` / `LOW_ITEMS` / `HD_SRC` / `LOW_SRC` **保留在 `config_buzz.py` 里作存档**，
  只是不再渲染。日后要恢复对比，把 `excluded` 标记去掉即可。
- Walmart 采集链路（`fetch_walmart.py` / `fetch_walmart_reviews.py`）**完全保留** ——
  它是 242 条差评、7 品类档次阶梯、14 张配图的唯一数据源。

### 复验证据（2026-10-15 实时探测）

```
Home Depot  商品页      HTTP 403  Forbidden
Home Depot  robots      HTTP 403  Forbidden
Lowe's      商品页      HTTP 403  Forbidden
Lowe's      robots      HTTP 403  Forbidden   （首页亦为 Akamai Access Denied）
Walmart     品类页      HTTP 200    561227 B  有 __NEXT_DATA__ + itemStacks
Amazon      榜单页      HTTP 200    462762 B  + gridItemRoot
```
