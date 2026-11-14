# -*- coding: utf-8 -*-
"""
patio 品类口径 —— 单一事实来源。

口径按用户指定，对齐 Home Depot 的 patio 类目体系：

    Patio set       成套出售的户外家具（3/4/5 件套、餐桌椅套装、会客套装）
    Mix & Match     可自由搭配的单件家具（单椅、沙发、模块、单桌）
    Umbrella        遮阳伞
    Canopy & Gazebo 篷房、凉亭、车棚、派对帐篷、遮阳棚
    Camping         露营与便携户外（露营椅、折叠床、吊床、沙滩椅）
    Patio Accessories 配件与耗材（罩、坐垫、照明、装饰、储物、冷藏箱）
    Grills & Fire   烤炉、火炉、取暖器

另有一类 `off_topic`：Amazon 的「Patio, Lawn & Garden」总榜里混着**园艺养护 / 虫害防治 /
泳池化学**——这些不属于 HD patio 口径，单独统计并在看板里说明，不进任何 patio 榜单。

⚠️ 五条必须遵守的规则（每一条都是踩过的坑）
--------------------------------------------------
1. **顺序即优先级，命中即停。** 关键的先后关系：
   · cover 最先        —— 「Fire Pit Cover」是配件不是火炉
   · patio_set 早于 umbrella —— 「Dining Set with Umbrella Hole」是家具不是伞
   · patio_set 早于 fire     —— 「8 Piece Set with Fire Pit Table」主体是套装
   · camping 晚于 canopy     —— 「Canopy Tent ... for Camping」是篷房
   · camping 早于 cooler     —— 「Camping Chair with Cooler」是露营椅
   · cushion 早于 seating    —— 「Chair Cushion」是坐垫不是椅子
2. **off_topic 放在最后。** 这是最关键的一条：早先把它放在最前，结果
   「Solar Patio Umbrella **for Pool**」被判成泳池用品、
   「Canopy with **Mosquito** Netting」被判成虫害、
   「Camping Chair ... Folding **Lawn** Chairs」被判成园艺——全部掉出 patio 榜。
   只有 patio 规则一个都没命中时，才轮到它判非 patio。
3. **别用裸词。** 「storage」「garden」「cabinet」「carry bag」这类词会大量误伤：
   「Adirondack Side Table, 2-Tier Storage」不是储物箱；
   「Prefab Tiny Home with L-Shaped Cabin」不是户外柜；
   「Camping Chair **with Carry Bag**」不是袋子。一律用短语或明确词。
4. **词边界 + 规则复数。** 用 `(?<![a-z0-9])kw(?:s|es)?(?![a-z0-9])`：
   否则「table」会命中「tablets」（泳池氯片跑进家具类），
   「Chair Covers」会漏掉 cover 被 chair 抢走。
5. **负面词表。** 命中即跳过该规则。两处必需：
   · fire 要排除 flameless（电子蜡烛不是火炉）
   · patio_set 要排除 grill set / tool set / cushion set（否则「Cushion Set」变套装）

改任何规则前后都要跑 `python patio_taxonomy.py`，内建回归用例必须全绿；
再用 `python -c "import audit_rules"` 之类的真实数据审计脚本扫一遍分布。
"""
import re

# ---------------------------------------------------------------- 品类元数据
# order 决定展示顺序（看板/小程序的图表与列表都按这个排）
CATS = {
    "patio_set":   {"zh": "成套家具",    "en": "Patio Sets",          "order": 1},
    "mix_match":   {"zh": "单件组合家具", "en": "Mix & Match",         "order": 2},
    "umbrella":    {"zh": "遮阳伞",      "en": "Umbrellas",            "order": 3},
    "canopy":      {"zh": "篷房与凉亭",   "en": "Canopies & Gazebos",   "order": 4},
    "camping":     {"zh": "露营与便携",   "en": "Camping",              "order": 5},
    "accessories": {"zh": "配件与耗材",   "en": "Patio Accessories",    "order": 6},
    "grill_fire":  {"zh": "烧烤与火炉",   "en": "Grills & Fire",        "order": 7},
    "other":       {"zh": "其他",        "en": "Other",                "order": 8},
    "off_topic":   {"zh": "非户外生活类",  "en": "Outside patio scope",  "order": 9},
}

# 进 patio 榜单的品类（off_topic 与 other 除外）
PATIO_KEYS = [k for k, v in sorted(CATS.items(), key=lambda x: x[1]["order"])
              if k not in ("other", "off_topic")]


# ---------------------------------------------------------------- 规则表
# (规则名, 目标品类, 关键词列表)  —— 顺序即优先级，命中即停
RULES = [
    # ===== 1. 罩类与遮蔽配件（必须最先，否则「Fire Pit Cover」「Grill Cover」会被火炉/烤炉抢走）
    ("cover", "accessories", [
        "fire pit cover", "grill cover", "griddle cover", "smoker cover",
        "umbrella cover", "parasol cover", "furniture cover", "chair cover",
        "table cover", "sofa cover", "loveseat cover", "patio cover",
        "bench cover", "recliner cover", "swing cover", "replacement cover",
        "cover only", "covers only", "protective cover", "dust cover",
        "cover for", "canopy weight", "weight bag", "tarp",
    ]),

    # ===== 2. 成套家具（必须早于 umbrella / fire，见文件头说明）
    ("patio_set", "patio_set", [
        "patio set", "furniture set", "conversation set", "dining set",
        "sofa set", "seating set", "table and chair set", "bistro set",
        "chat set", "piece set", "sectional set", "deep seating set",
        "furniture collection", "patio collection",
    ]),

    # ===== 3. 烧烤与火炉
    ("fire", "grill_fire", [
        "fire pit", "firepit", "fire bowl", "chiminea", "fireplace", "firewood",
        "fire log", "fire starter", "kindling", "fire glass", "fire table",
        "fire color", "flame color", "magical flames", "magic flames",
        "smokeless fire", "bonfire", "s'mores", "smores",
    ]),
    ("grill", "grill_fire", [
        "grill", "griddle", "smoker", "bbq", "barbecue", "pellet", "charcoal",
        "briquette", "skewer", "grilling", "flat top", "hibachi", "propane",
        "meat thermometer", "burger press", "pizza oven", "outdoor cooking",
        "grease cup", "chimney starter",
    ]),
    ("heating", "grill_fire", [
        "patio heater", "outdoor heater", "space heater", "infrared heater",
        "heat lamp", "heater", "misting fan", "patio fan",
    ]),

    # ===== 4. 遮阳：伞
    ("umbrella", "umbrella", [
        "umbrella", "parasol", "cantilever",
    ]),

    # ===== 5. 遮阳：篷房与凉亭
    ("canopy", "canopy", [
        "canopy", "gazebo", "pergola", "awning", "carport", "car port",
        "party tent", "screen house", "sun shelter", "pop up tent",
        "shelterlogic", "canopies",
    ]),

    # ===== 6. 露营与便携（晚于 canopy，早于 cooler）
    ("camping", "camping", [
        "camping chair", "camp chair", "camping loveseat", "camp cot",
        "sleeping bag", "hammock", "beach chair", "folding chair",
        "folding cot", "picnic blanket", "camp kitchen", "rv patio",
        "stadium seat", "bleacher seat",
    ]),

    # ===== 7. 配件与耗材
    ("cushion", "accessories", [
        "cushion", "pillow", "seat pad", "chair pad", "bench pad", "chaise pad",
        "throw pillow",
    ]),
    ("storage", "accessories", [
        "storage box", "deck box", "storage bench", "storage cabinet",
        "storage shed", "outdoor storage", "storage container", "trash can",
        "snackle box",
    ]),
    ("cooler", "accessories", [
        "cooler", "ice chest", "cooler bag", "cooler backpack", "beverage tub",
    ]),
    ("lighting", "accessories", [
        "light", "lights", "lantern", "lamp", "candle", "floodlight",
        "spotlight", "pathway light", "path light", "solar light", "torch light",
        "light bulb", "light strip", "string light", "fairy light",
    ]),
    ("decor", "accessories", [
        "decor", "decoration", "flag", "wind chime", "statue", "fountain",
        "rug", "doormat", "door mat", "floor mat", "tablecloth", "placemat",
        "gnome", "birdbath", "stepping stone", "wreath", "planter", "urn",
        "spider web", "creepy cloth", "banner", "wall art",
    ]),

    # ===== 8. 单件家具（兜底）
    ("seating", "mix_match", [
        "patio chair", "patio seating", "sofa", "loveseat", "sectional",
        "ottoman", "recliner", "bench", "stool", "swing", "adirondack",
        "chaise", "lounge chair", "glider", "rocking chair", "armchair",
        "club chair", "egg chair", "muskoka", "seating",
    ]),
    ("table", "mix_match", [
        "table",
    ]),

    # ===== 9. 非 patio（放最后！见文件头第 2 条：前面命中过就不再判断）
    ("pest", "off_topic", [
        "insect", "ant", "roach", "rodent", "mouse", "rat", "mole", "gopher",
        "wasp", "hornet", "mosquito", "fly trap", "bug", "pest", "repellent",
        "termite", "flea", "tick", "glue trap", "bait station",
    ]),
    ("pool", "off_topic", [
        # ⚠️ 用 "chlor" 而不是 "chlorin"：规则复数只补 s/es，
        # "chlorin" 匹配不到 "chlorine"（结尾是 e），会让泳池氯片漏到 other。
        "pool", "spa", "hot tub", "chlor", "algaecide", "alkalinity",
        "shock treatment", "pool shock", "skimmer", "winterizing",
        "jetted tub", "whirlpool", "water test strip", "test strips",
    ]),
    ("garden", "off_topic", [
        "lawn", "garden hose", "seed", "fertilizer", "plant food", "potting",
        "soil", "mulch", "weed", "sprinkler", "mower", "hedge", "trimmer",
        "leaf rake", "leaf sweeper", "bird feed", "bird food", "suet",
        "hummingbird", "compost", "herb kit", "irrigation",
    ]),
]

# 负面词：命中即跳过该规则（防止「有该词但不是那类」）
NEG = {
    "fire": ["flameless", "flame-less", "flame less", "fake flame"],
    # ⚠️ 这里**不能**放 "furniture set"：「Furniture Set Covers」是套装罩，
    # 会被这条 NEG 挡掉 cover 规则、误判成套家具。套装罩必须是 accessories。
    "cover": ["piece set", "conversation set", "dining set", "sofa set",
              "seating set", "chat set", "bistro set"],
    "patio_set": ["grill set", "tool set", "accessory set", "cushion set",
                  "cover set", "light set", "socket set", "wrench set",
                  "knife set", "screwdriver set",
                  # 坐垫商品常写成「3 Piece … Cushions for Large Wicker Sets」，
                  # 会被 "piece set" 误判成套家具
                  "chair cushion", "seat cushion", "bench cushion",
                  "settee cushion", "cushion seating"],
}

# 整词/短语 + 规则复数匹配，带缓存
_cache = {}


def _kw_hit(text, kw):
    key = (text, kw)
    hit = _cache.get(key)
    if hit is None:
        pat = re.compile(r"(?<![a-z0-9])" + re.escape(kw.strip()) + r"(?:s|es)?(?![a-z0-9])")
        hit = bool(pat.search(text))
        _cache[key] = hit
    return hit


# 「3-Piece Patio Furniture」这类没写 set 的套装
_PIECE = re.compile(r"\b\d+\s*[- ]?\s*(?:piece|pc|pcs)\b", re.I)


def guess_cat(title):
    """从标题推断品类，返回 CATS 的 key。"""
    t = (title or "").lower()
    for rule, cat, kws in RULES:
        if any(_kw_hit(t, n) for n in NEG.get(rule, [])):
            continue
        if any(_kw_hit(t, k) for k in kws):
            return cat
    if _PIECE.search(t) and any(_kw_hit(t, k) for k in
                                ["patio", "furniture", "chair", "table", "sofa", "seating"]):
        return "patio_set"
    return "other"


def why(title):
    """调试用：返回 (品类, 命中的规则名, 命中的关键词)。命中兜底时规则名为 None。"""
    t = (title or "").lower()
    for rule, cat, kws in RULES:
        if any(_kw_hit(t, n) for n in NEG.get(rule, [])):
            continue
        for k in kws:
            if _kw_hit(t, k):
                return cat, rule, k
    if _PIECE.search(t) and any(_kw_hit(t, k) for k in
                                ["patio", "furniture", "chair", "table", "sofa", "seating"]):
        return "patio_set", "_piece", ""
    return "other", None, None


def label(key, lang="zh"):
    m = CATS.get(key) or CATS["other"]
    return m["zh"] if lang == "zh" else m["en"]


def order_of(key):
    return CATS.get(key, CATS["other"])["order"]


# ---------------------------------------------------------------- 回归用例
# 每条都是实际抓到的标题或历史上踩过的坑。格式：(标题, 期望品类)
CASES = [
    # —— 顺序陷阱：cover 必须先于 fire / grill / seating
    ("ULTCOVER Waterproof Patio Furniture Cover 111L x 74W in", "accessories"),
    ("Vailge Patio Chair Covers & Outdoor Furniture Covers Heavy-Duty", "accessories"),
    ("Kipiea Patio Furniture Covers Waterproof Winter Set Covers", "accessories"),
    ("Fire Pit Cover Square Waterproof", "accessories"),
    ("Grill Cover Heavy Duty BBQ Cover", "accessories"),
    ("ULTCOVER Waterproof Patio Cantilever Offset Umbrella Cover", "accessories"),
    ("Utopia Bedding Waterproof Outdoor Chair Cover, Patio Furniture Cover", "accessories"),
    # —— 裸词陷阱：附带件不能改变主体品类
    ("Blackstone Original Outdoor Griddle, 28 inch 2-Burner Flat Top Grill with Hard Cover", "grill_fire"),
    ("Duck Covers Water-Resistant Indoor/Outdoor Seat Cushions, 19 x 19 x 5 Inch", "accessories"),
    ("Kimunuk Outdoor Bench Cushions 60 x 18 x 3.5 Inch, High Density Foam", "accessories"),
    ("Ozark Trail Oversized Mesh Camping Chair with Carry Bag and Cup Holders", "camping"),
    ("AORAN 2-Pack Foldable Moon Chairs, portable camping chairs with carry bag", "camping"),
    ("DuraYu 19x20ft Expandable Prefab Tiny Home, Steel Frame Foldable Modular Cabin", "other"),
    # —— off_topic 必须后置：带 Pool/Mosquito/Lawn 字样的 patio 商品不能被排除
    ("Autlaycil 10 ft Solar Patio Umbrellas with 32 Lights for Market Outdoor Pool", "umbrella"),
    ("GVDV 10ft x 10ft Pop-Up Canopy, Outdoor Canopy tent with Mosquito Netting", "canopy"),
    ("Sophia & William 2 Pack Oversized Camping Chairs Heavy-Duty Steel Frame", "camping"),
    ("Folding Camping Chair, Portable High Back Folding Lawn Chairs for Adults", "camping"),
    ("Eurhowing Waterproof Patio Rocking Chair Cushions 1-Piece, 3 Inch Thick", "accessories"),
    # —— 真正的非 patio 必须仍被排除
    ("Clorox Pool&Spa XTRABLUE 3” Chlorinating Tablets 5 lbs", "off_topic"),
    ("HTH 52037R, Pool Care Shock Advanced, 12 Pack", "off_topic"),
    ("FROG @Ease Floating Sanitizing System for Hot Tubs", "off_topic"),
    ("Oh Yuk Jetted Tub Cleaner for Jacuzzis", "off_topic"),
    ("TERRO Drain Insect Killer, Foam Treatment for Indoor Infestations", "off_topic"),
    ("Catchmaster Max-Catch Glue Traps 36pk, Sticky Mouse Traps", "off_topic"),
    ("Flexzilla Garden Hose 5/8 in. x 50 ft.", "off_topic"),
    ("Wagner's Farmer's Delight Wild Bird Food, 10-Pound Bag", "off_topic"),
    ("New Ohio Steel 42 inch / 22 CF Lawn Sweeper", "off_topic"),
    ("Miracle-Gro Potting Mix, For Indoor or Outdoor Potted Plants, 25 qt.", "off_topic"),
    # —— 顺序陷阱：Storage Bench 归 storage 而非 seating
    ("EFU Outdoor Bench Storage Deck Box, 120 Gallon Waterproof Wicker", "accessories"),
    ("Keter City 30 Gal Outdoor Storage Box and Patio Side Table", "accessories"),
    ("Quictent 100 Gallon Heavy Duty Resin Deck Box Weatherproof", "accessories"),
    ("NBYSGO Adirondack Square Outdoor Side Table, 2-Tier Storage", "mix_match"),
    # —— 负面词陷阱
    ("Homemory 24Pcs Flickering Flameless Candle Battery Operated", "accessories"),
    ("Better Homes & Gardens 2-Piece Deep Seat Outdoor Cushion Set, 45 in", "accessories"),
    ("Indoor Outdoor 3 Piece Tufted Wicker Settee Cushions for Large Wicker Sets", "accessories"),
    ("High Back Outdoor Chair Cushions, Non-Slip Patio Chair Cushions Seating", "accessories"),
    # —— 顺序陷阱：成套家具带 Umbrella / Fire Pit 字样仍是成套家具
    ("5 Piece Outdoor Dining Set with Umbrella Hole", "patio_set"),
    ("8 Piece Outdoor Patio Furniture Set with 45 inch 50000 BTU Propane Fire Pit Table", "patio_set"),
    ("Better Homes & Gardens River Oaks Outdoor Sofa Set with 2 Nesting Tables and Patio Cover", "patio_set"),
    ("Better Homes & Gardens Juliet Outdoor Sectional Set", "patio_set"),
    ("Better Homes & Gardens River Oaks Outdoor Swivel Gliders Steel Frame 2 Piece Set", "patio_set"),
    ("Muphyers 10 Pcs Aluminum Swivel Rocking Chair Set, Patio Furniture Set with 55000 BTU", "patio_set"),
    # —— 遮阳：伞 vs 篷
    ("CROWN SHADES 10x10 Pop Up Canopy Tent with One Push Setup", "canopy"),
    ("Quictent 10x20FT Pop Up Canopy Tent with Sidewalls Party Tent", "canopy"),
    ("Ktaxon 10ft x 10ft Ez Pop Up Canopy Tent with Lights,LED Frame Canopy", "canopy"),
    ("COBIZI 10x10 Pop up Gazebo Screen Tent Screen House for Camping", "canopy"),
    ("Abba Patio 9FT Lyon Outdoor Patio Umbrella with Push Button Tilt", "umbrella"),
    ("HaiNova 10 ft Offset Patio Umbrella, All-Weather UV Protection Cantilever", "umbrella"),
    # —— 火炉 vs 烤炉
    ("Solo Stove Bonfire Smokeless Fire Pit Bundle", "grill_fire"),
    ("OutVue 42 Inch Fire Pit with 2 Grills, Lid, Poker", "grill_fire"),
    ("Magical Flames Fire Color Packets (25 Pack)", "grill_fire"),
    ("Traeger Signature Blend Wood Pellets for Pellet Grills & Smokers", "grill_fire"),
    ("Kingsford Original Charcoal Briquettes, BBQ Charcoal, 16 Pounds", "grill_fire"),
    ("DR. INFRARED HEATER 1500W Portable Indoor and Outdoor Space Heater", "grill_fire"),
    # —— 成套 vs 单件
    ("DUMOS 8 FT Folding Picnic Table, Portable Plastic Table", "mix_match"),
    ("Ozark Trail Quad Folding Camp Chair with Cup Holder, Dark Blue", "camping"),
    ("Coleman Camping Chair with Built-in 4 Can Cooler", "camping"),
    # —— 配件兜底
    ("YETI Roadie 15 Hard Cooler with DoubleDuty Shoulder Strap", "accessories"),
    ("American flag 3x5 FT for Outside, Heavy Duty Polyester USA Flag", "accessories"),
    ("GORILLA GRIP WeatherMAX Door Mat, Indoor and Outdoor Use", "accessories"),
    ("Tuffenough Solar Outdoor Lights 2500LM 210 LED Security Lights", "accessories"),
]


def _selftest():
    bad = []
    for t, want in CASES:
        got = guess_cat(t)
        if got != want:
            bad.append((t, want, got))
    n = len(CASES)
    if not bad:
        print("✅ 品类回归 %d/%d 通过" % (n, n))
        return 0
    print("❌ 品类回归 %d/%d 通过，失败项：" % (n - len(bad), n))
    for t, want, got in bad:
        print("   「%s」\n      期望 %s(%s)  实际 %s(%s)"
              % (t[:70], want, label(want), got, label(got)))
    return 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
