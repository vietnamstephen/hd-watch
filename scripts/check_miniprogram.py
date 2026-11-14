#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信小程序项目自检（每周数据刷新后跑一遍）。

检查项：
  1. 必需文件齐全
  2. 所有 .json 可解析
  3. 所有 .js 通过 node --check（语法）
  4. app.json 声明的每个页面都齐 .js/.json/.wxml
  5. tabBar 的 pagePath 都在 pages 里
  6. data/mini.js 可被 node 加载，且关键字段非空
  7. 每个页面 WXML 用到的顶层变量都在该页 data 里声明
  8. 无外部网络资源（图片/字体/脚本）
  9. 主包体积 < 2MB

用法：python check_miniprogram.py
"""

import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MP = os.path.join(ROOT, "miniprogram")
def _find_node() -> str:
    """自动定位托管 node 可执行文件。

    版本目录名会随升级变化（曾写死 22.22.2-3，升级到 22.22.2-6 后自检直接崩），
    所以这里每次扫目录取最新版本，扫不到再退回 PATH 里的 node。
    """
    cands = sorted(glob.glob(
        "/Users/xuyousheng/.workbuddy/binaries/node/versions/*/bin/node"))
    return cands[-1] if cands else "node"


NODE = _find_node()

REQUIRED = [
    "app.json", "app.js", "app.wxss", "project.config.json",
    "sitemap.json", "data/mini.js",
]

# WXML 里这些是 wx:for 的局部变量，不算页面 data
LOOP_VARS = {"item", "index", "true", "false", "null", "undefined", "wx"}

PKG_LIMIT = 2 * 1024 * 1024

errors = []
warns = []
oks = []


def rel(p):
    return os.path.relpath(p, ROOT)


def walk(ext):
    out = []
    for dp, _dn, fns in os.walk(MP):
        for fn in fns:
            if fn.endswith(ext):
                out.append(os.path.join(dp, fn))
    return sorted(out)


def balance_block(text, start):
    """从 text[start] 处的 '{' 开始做括号配平，返回块内文本"""
    depth = 0
    i = start
    while i < len(text):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:i]
        i += 1
    return ""


def data_keys(js_src):
    """提取 Page({... data: {...} ...}) 里的 data 键名"""
    m = re.search(r"\bdata\s*:\s*\{", js_src)
    if not m:
        return set()
    block = balance_block(js_src, m.end() - 1)
    return set(re.findall(r"[{,]\s*([A-Za-z_$][\w$]*)\s*:", block)) | \
        set(re.findall(r"^\s*([A-Za-z_$][\w$]*)\s*:", block, re.M))


def loop_locals(wxml):
    """收集 wxml 里用 `wx:for-item` / `wx:for-index` 自定义的循环变量名。

    小程序允许把循环变量改名（`wx:for-item="c"`），改名后 `{{c.x}}` 是合法的局部引用，
    并不是「未声明的 data 变量」。早期校验器只认默认的 item / index，
    于是把改名后的写法误报成错误 —— 这是校验器的问题，不是页面的问题。
    """
    out = set()
    for m in re.finditer(r'wx:for-(?:item|index)\s*=\s*"([^"]+)"', wxml):
        name = m.group(1).strip()
        if re.match(r"^[A-Za-z_$][\w$]*$", name):
            out.add(name)
    return out


def mustache_vars(wxml):
    """提取 {{...}} 里引用的顶层变量名（排除 item.xxx 的属性名）"""
    out = set()
    for expr in re.findall(r"\{\{(.*?)\}\}", wxml, re.S):
        # 去掉字符串字面量，避免把字符串里的词当变量
        e = re.sub(r"'[^']*'", " ", expr)
        e = re.sub(r'"[^"]*"', " ", e)
        for m in re.finditer(r"([A-Za-z_$][\w$]*)", e):
            name = m.group(1)
            pre = e[:m.start()].rstrip()
            if pre.endswith("."):        # 是 xxx.name 的属性
                continue
            out.add(name)
    return out - LOOP_VARS


def main():
    print("=== 小程序自检 ===")

    # 1. 必需文件
    for f in REQUIRED:
        p = os.path.join(MP, f)
        if os.path.exists(p):
            oks.append("存在 %s" % f)
        else:
            errors.append("缺少必需文件 %s" % f)

    # 2. JSON
    for p in walk(".json"):
        try:
            with open(p, encoding="utf-8") as fh:
                json.load(fh)
        except Exception as e:  # noqa: BLE001
            errors.append("%s JSON 解析失败：%s" % (rel(p), e))
    oks.append("JSON 全部可解析（%d 个）" % len(walk(".json")))

    # 3. JS 语法
    js_files = walk(".js")
    bad_js = 0
    for p in js_files:
        r = subprocess.run([NODE, "--check", p], capture_output=True, text=True)
        if r.returncode != 0:
            bad_js += 1
            errors.append("%s 语法错误：%s" % (rel(p), (r.stderr or "").strip()[:200]))
    if not bad_js:
        oks.append("JS 语法全部通过（%d 个）" % len(js_files))

    # 4/5. app.json 页面与 tabBar
    app_json_path = os.path.join(MP, "app.json")
    pages = []
    if os.path.exists(app_json_path):
        with open(app_json_path, encoding="utf-8") as fh:
            app_json = json.load(fh)
        pages = app_json.get("pages") or []
        for pg in pages:
            base = os.path.join(MP, pg)
            for ext in (".js", ".json", ".wxml"):
                if not os.path.exists(base + ext):
                    errors.append("页面 %s 缺少 %s" % (pg, ext))
        if not errors:
            oks.append("页面文件齐全（%d 个页面）" % len(pages))

        tb = app_json.get("tabBar") or {}
        for it in (tb.get("list") or []):
            pp = it.get("pagePath")
            if pp not in pages:
                errors.append("tabBar 的 pagePath「%s」不在 pages 里" % pp)
            for k in ("iconPath", "selectedIconPath"):
                icon = it.get(k)
                if icon and not os.path.exists(os.path.join(MP, icon)):
                    errors.append("tabBar 图标缺失：%s" % icon)
        if tb:
            oks.append("tabBar 配置正常（%d 项）" % len(tb.get("list") or []))

    # 6. mini.js 内容
    mini_js = os.path.join(MP, "data", "mini.js")
    if os.path.exists(mini_js):
        probe = (
            "const m=require(process.argv[1]);"
            "const req=['meta','quote','fund','bench','news','patio','channels','cats','brief'];"
            "const miss=req.filter(k=>!m[k]);"
            "if(miss.length){console.error('缺少字段: '+miss.join(','));process.exit(1);}"
            "const p=m.patio||{};"
            "if(!(p.groups&&p.groups.length)){console.error('patio.groups 为空');process.exit(1);}"
            "if(!(p.stars&&p.stars.length)){console.error('patio.stars 为空');process.exit(1);}"
            "if(!(m.news&&m.news.length)){console.error('news 为空');process.exit(1);}"
            "const n=(m.quote&&m.quote.spark||[]).length;"
            "if(n<20){console.error('spark 点数不足: '+n);process.exit(1);}"
            "console.log('ok meta='+m.meta.week+' spark='+n+' groups='+p.groups.length+' stars='+p.stars.length);"
        )
        r = subprocess.run([NODE, "-e", probe, mini_js], capture_output=True, text=True)
        if r.returncode == 0:
            oks.append("mini.js 数据完整：%s" % (r.stdout or "").strip())
        else:
            errors.append("mini.js 数据异常：%s" % (r.stderr or "").strip()[:300])

    # 7. WXML 变量覆盖
    for pg in pages:
        wxml = os.path.join(MP, pg + ".wxml")
        js = os.path.join(MP, pg + ".js")
        if not (os.path.exists(wxml) and os.path.exists(js)):
            continue
        with open(wxml, encoding="utf-8") as fh:
            w = fh.read()
        with open(js, encoding="utf-8") as fh:
            j = fh.read()
        keys = data_keys(j) | {"item", "index"} | loop_locals(w)
        used = mustache_vars(w)
        unknown = sorted(v for v in used if v not in keys)
        if unknown:
            errors.append("%s 引用了未在 data 里声明的变量：%s"
                          % (rel(wxml), ", ".join(unknown)))
        else:
            oks.append("%s 变量覆盖完整（%d 个顶层变量）" % (os.path.basename(wxml), len(used)))

    # 8. 外部资源
    ext_pat = re.compile(r'(?:src|url|href|@import)\s*[=(]?\s*["\']?(https?:)?//', re.I)
    for p in walk(".wxml") + walk(".wxss"):
        with open(p, encoding="utf-8") as fh:
            t = fh.read()
        if ext_pat.search(t):
            errors.append("%s 出现外部资源引用" % rel(p))
    oks.append("无外部网络资源引用")

    # 9. 体积
    total = 0
    n_files = 0
    for dp, _dn, fns in os.walk(MP):
        if "node_modules" in dp:
            continue
        for fn in fns:
            total += os.path.getsize(os.path.join(dp, fn))
            n_files += 1
    if total > PKG_LIMIT:
        errors.append("主包体积 %.2f MB 超过 2MB 上限" % (total / 1024 / 1024))
    else:
        oks.append("主包体积 %.1f KB（%d 个文件，上限 2MB）" % (total / 1024.0, n_files))

    # 输出
    print()
    for s in oks:
        print("  [OK]   %s" % s)
    for s in warns:
        print("  [警告] %s" % s)
    for s in errors:
        print("  [错误] %s" % s)
    print()
    if errors:
        print("结果：%d 项错误，%d 项通过" % (len(errors), len(oks)))
        return 1
    print("结果：全部通过（%d 项）" % len(oks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
