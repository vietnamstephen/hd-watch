# -*- coding: utf-8 -*-
"""
明星产品配图采集（看板 + 小程序共用）。

为什么要单独做一步
--------------------------------------------------
用户需求：「明星类产放个照片」。看板与小程序都要内嵌图片，因此必须把图片**压到很小**
再 base64 内联（两个产物都是自包含 HTML/JS，不放外链，微信里也不会加载外部图片）。

图片来源的取舍（实测结论，别无选择）
--------------------------------------------------
  · Amazon 商品页  → 3.7KB captcha，取不到主图
  · Amazon 榜单页  → 图片是 JS 懒加载，HTML 里只有 3 张，配对失败
  · Amazon 遗留图片端点 images.amazon.com/images/P/<ASIN>.01.jpg → 403
  · Walmart 图 CDN i5.walmartimages.com → ✅ 公开可下载，且支持 odnHeight/odnWidth 参数

所以配图统一取自 **Walmart 侧真实商品图**（六个 patio 品类全覆盖，且成套家具/遮阳伞
这些 Amazon 几乎不上榜的品类，恰好是 Walmart 图库最强的地方）。

「明星」的判定
--------------------------------------------------
score = log10(评论数 + 1) × (评分 / 5)
    —— 既看销量体量（评论数是销量的代理），也看口碑；纯看评论数会让 3.8 星的老品霸榜。
每个 patio 品类取 Top N，输出 JPEG（200×200，白底 letterbox，q=72，约 8–14KB/张）。

产物：
  data/star_images.json          —— 含 base64，供看板自包含 HTML 内联（看板零外链）
  miniprogram/images/star/*.jpg  —— 供小程序 <image src="/images/star/xx.jpg">
                                    （小程序里放真实文件比把 base64 塞进 wxml 快得多）
"""
import base64
import io
import json
import math
import os
import ssl
import time
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
MP_IMG_DIR = os.path.join(BASE_DIR, "miniprogram", "images", "star")

UA = "Mozilla/5.0"
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE

PICK_TOP = 2        # 每个品类取前 N 名配图
SIZE = 200          # 输出边长
QUALITY = 72
MAX_BYTES = 60_000  # 单图上限，超过就降质量重压


def _big(url, w=400):
    """把 Walmart CDN 缩略图参数换成大图（原 URL 自带 odnHeight/odnWidth）。"""
    if not url:
        return url
    base = url.split("?")[0]
    return "%s?odnHeight=%d&odnWidth=%d&odnBg=FFFFFF" % (base, w, w)


def _download(url, tries=3, timeout=30):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
                return r.read()
        except Exception as e:
            last = e
            time.sleep(1.2 * (i + 1))
    raise RuntimeError("下载失败 %s: %s" % (url[:70], last))


def _shrink(raw):
    """居中 letterbox 到 SIZE×SIZE 白底 JPEG，返回 (bytes_blob, w, h)。"""
    from PIL import Image
    im = Image.open(io.BytesIO(raw))
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")

    canvas = Image.new("RGB", (SIZE, SIZE), (255, 255, 255))
    c = im.copy()
    c.thumbnail((SIZE, SIZE), Image.LANCZOS)
    canvas.paste(c, ((SIZE - c.width) // 2, (SIZE - c.height) // 2))

    for q in (QUALITY, 62, 52, 44):
        buf = io.BytesIO()
        canvas.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        if buf.tell() <= MAX_BYTES or q == 44:
            return (buf.getvalue(), SIZE, SIZE)
    raise RuntimeError("压缩失败")


def _star_score(it):
    r = it.get("rating") or 0
    n = it.get("reviews") or 0
    return math.log10(n + 1) * (r / 5.0)


def _dedupe_key(title):
    """用前 3 个词做近似去重键：Blackstone Griddle 28in / 36in 视为同一款。"""
    import re
    w = re.findall(r"[A-Za-z0-9]+", (title or "").lower())
    return " ".join(w[:3])


def pick_stars(wm, per_cat=PICK_TOP):
    import patio_taxonomy as TX
    out = []
    for cat in TX.PATIO_KEYS:
        rows = [x for x in (wm.get("items") or [])
                if TX.guess_cat(x.get("title", "")) == cat
                and (x.get("reviews") or 0) > 0 and x.get("image")]
        rows.sort(key=_star_score, reverse=True)
        seen, picked = set(), []
        for r in rows:
            k = _dedupe_key(r.get("title"))
            if k in seen:
                continue
            seen.add(k)
            picked.append(r)
            if len(picked) >= per_cat:
                break
        for r in picked:
            out.append((cat, r))
    return out


def run(verbose=True):
    import patio_taxonomy as TX
    wm_path = os.path.join(DATA_DIR, "walmart.json")
    if not os.path.exists(wm_path):
        raise SystemExit("缺少 data/walmart.json，请先运行 fetch_walmart.py")
    wm = json.load(open(wm_path, encoding="utf-8"))
    picks = pick_stars(wm)

    if verbose:
        print("明星产品配图：每品类 Top %d，共 %d 张（源：Walmart 图 CDN）"
              % (PICK_TOP, len(picks)))

    items, errors = {}, []
    os.makedirs(MP_IMG_DIR, exist_ok=True)
    for i, (cat, it) in enumerate(picks):
        if i:
            time.sleep(0.6)
        try:
            raw = _download(_big(it["image"]))
            blob, w, h = _shrink(raw)
            n = len(blob)
            # 小程序侧：写真实文件（比把 base64 塞进 wxml 快得多）
            fname = "%s.jpg" % it["id"]
            with open(os.path.join(MP_IMG_DIR, fname), "wb") as f:
                f.write(blob)
            items[it["id"]] = {
                "id": it["id"],
                "title": it["title"],
                "short": it["title"][:70],
                "brand": it.get("brand") or "",
                "rating": it.get("rating"),
                "reviews": it.get("reviews") or 0,
                "price": it.get("price"),
                "cat": cat,
                "cat_label_zh": TX.label(cat),
                "cat_label_en": TX.label(cat, "en"),
                "star_score": round(_star_score(it), 3),
                "channel": "Walmart",
                "url": it.get("url") or "",
                "src": it["image"].split("?")[0],
                "w": w, "h": h, "bytes": n,
                "mp": "/images/star/" + fname,
                "b64": base64.b64encode(blob).decode("ascii"),
            }
            if verbose:
                print("  ✅ %-13s %-40s %5d B" % (TX.label(cat), it["title"][:40], n))
        except Exception as e:
            errors.append({"id": it.get("id"), "title": it.get("title", "")[:60],
                           "error": str(e)})
            if verbose:
                print("  ❌ %-13s %-40s %s" % (TX.label(cat), it["title"][:40], str(e)[:50]))

    out = {
        "source": "i5.walmartimages.com (Walmart product images)",
        "source_zh": "沃尔玛商品图 CDN",
        "captured_at": time.strftime("%Y-%m-%d"),
        "note": "Amazon 侧主图实测三路皆封（商品页 captcha / 榜单页懒加载 / 遗留端点 403），"
                "配图统一取 Walmart 公开商品图；JPEG 200×200 白底，已 base64 供内联。",
        "size": SIZE, "quality": QUALITY,
        "items": items,
        "errors": errors,
    }
    path = os.path.join(DATA_DIR, "star_images.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    total = sum(v["bytes"] for v in items.values())
    if verbose:
        print("-" * 66)
        print("  落盘 %s：%d 张 / 合计 %.0f KB / 平均 %.1f KB / 错误 %d"
              % (path, len(items), total / 1024.0,
                 total / 1024.0 / max(1, len(items)), len(errors)))
        print("  小程序图片 → %s" % MP_IMG_DIR)
    return out


if __name__ == "__main__":
    run()
