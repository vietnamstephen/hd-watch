#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成小程序 tabBar 图标（81×81 PNG，透明底）。

为什么不直接引用现成图标：保持小程序零外部资源 —— 所有素材本地生成，不依赖网络。
画法：在 4 倍画布上绘制再降采样，得到平滑边缘（PIL 的 draw 本身不抗锯齿）。

用法：python make_tabbar_icons.py
产物：miniprogram/images/{tab-home,tab-star,tab-compare}{,-on}.png
"""

import math
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(os.path.dirname(HERE), "miniprogram", "images")

SIZE = 81          # 微信建议的 tabBar 图标尺寸
SS = 4             # 超采样倍数
N = SIZE * SS

GRAY = (138, 138, 148, 255)   # 普通态
RED = (200, 16, 46, 255)      # 选中态（品牌红）


def new_canvas():
    img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def draw_bars(d):
    """概览：三根递增的柱状图"""
    bw = N * 0.16
    gap = N * 0.10
    total = bw * 3 + gap * 2
    x0 = (N - total) / 2
    heights = [0.40, 0.62, 0.85]
    base = N * 0.78
    for i, h in enumerate(heights):
        x = x0 + i * (bw + gap)
        top = base - N * 0.64 * h
        d.rounded_rectangle([x, top, x + bw, base], radius=bw / 2.6, fill=GRAY)


def draw_star(d):
    """明星产品：五角星"""
    cx = cy = N / 2
    r_out = N * 0.40
    r_in = r_out * 0.44
    pts = []
    for i in range(10):
        r = r_out if i % 2 == 0 else r_in
        a = -math.pi / 2 + i * math.pi / 5
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d.polygon(pts, fill=GRAY)


def draw_compare(d):
    """渠道对标：两条长度不同的横条（对比）"""
    bh = N * 0.15
    x0 = N * 0.16
    widths = [0.68, 0.40]
    ys = [0.33, 0.55]
    for w, y in zip(widths, ys):
        top = N * y
        d.rounded_rectangle(
            [x0, top, x0 + N * w, top + bh], radius=bh / 2, fill=GRAY
        )


def draw_cats(d):
    """品类对标：2×2 分类格（右下格缩小，暗示「档次有高低」）"""
    s = N * 0.32          # 单格边长
    gap = N * 0.10
    x0 = (N - (s * 2 + gap)) / 2
    y0 = x0
    r = s / 4.0
    # 左上 / 右上 / 左下 三格实心
    for gx, gy in ((0, 0), (1, 0), (0, 1)):
        x = x0 + gx * (s + gap)
        y = y0 + gy * (s + gap)
        d.rounded_rectangle([x, y, x + s, y + s], radius=r, fill=GRAY)
    # 右下格：缩到 60% 并右对齐底对齐，视觉上「矮一档」
    k = 0.58
    sw = s * k
    x = x0 + (s + gap) + (s - sw)
    y = y0 + (s + gap) + (s - sw)
    d.rounded_rectangle([x, y, x + sw, y + sw], radius=sw / 4.0, fill=GRAY)


TABS = {
    "tab-home": draw_bars,
    "tab-star": draw_star,
    "tab-compare": draw_compare,
    "tab-cats": draw_cats,
}


def tint(img, color):
    """把非透明像素整体换色（图标是单色的，直接替换）"""
    px = img.load()
    for y in range(img.size[1]):
        for x in range(img.size[0]):
            r, g, b, a = px[x, y]
            if a:
                px[x, y] = (color[0], color[1], color[2], a)
    return img


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    made = []
    for name, fn in TABS.items():
        for suffix, color in (("", GRAY), ("-on", RED)):
            img, d = new_canvas()
            fn(d)
            img = tint(img, color)
            img = img.resize((SIZE, SIZE), Image.LANCZOS)
            p = os.path.join(OUT_DIR, "%s%s.png" % (name, suffix))
            img.save(p, "PNG", optimize=True)
            made.append((p, os.path.getsize(p)))

    total = sum(s for _, s in made)
    print("生成 %d 个图标，共 %.1f KB" % (len(made), total / 1024.0))
    for p, s in made:
        print("  %-46s %5d B" % (os.path.relpath(p, os.path.dirname(HERE)), s))


if __name__ == "__main__":
    main()
