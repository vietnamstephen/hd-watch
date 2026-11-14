# -*- coding: utf-8 -*-
"""
hd-watch 一轮完整更新的统一入口。

流程（九步）：
  ① fetch_hd             —— 行情 / SEC 表单 / IR 财报材料（含 PDF 解析出时间与标题）/ 新闻
  ② fetch_buzz           —— Amazon 庭院户外 8 个榜单（含防串榜校验）
  ③ fetch_walmart        —— Walmart 7 个 patio 品类页（一手供给，含图与评分）
  ④ fetch_walmart_reviews —— Walmart「最低分优先」评论页（负评归纳，依赖③）
  ⑤ fetch_star_images    —— 明星产品配图（Walmart 图 CDN，压缩后供看板内联 + 小程序文件）
  ⑥ analyze_buzz         —— 双渠道打分 + 品类档次阶梯 + 差评主题 + 跨渠道冠军
  ⑦ build_hd             —— 重建看板 dashboard/index.html（双语双主题、零外部请求）
  ⑧ build_miniprogram    —— 重建小程序数据 miniprogram/data/mini.js
  ⑨ check_miniprogram    —— 小程序自检（页面/语法/数据/体积/零外部资源）

耗时提示：③ 约 4 分钟、④ 约 7 分钟（都有页间隔退避，防被风控），整轮约 12–15 分钟。

设计原则：
  - 抓取步骤失败不阻断后续构建（沿用上一份数据重建，但如实报错并以非零码退出）。
  - 各步独立捕获异常，最后统一汇总，退出码 0 = 全成功、1 = 有失败步骤。

用法：
  python run_cycle.py                 # 全流程
  python run_cycle.py --no-buzz       # 跳过 Amazon 榜单抓取（网络受限时）
  python run_cycle.py --no-walmart    # 跳过 Walmart 两步 + 配图（赶时间时）
  python run_cycle.py --no-build      # 只抓数据，不重建产物
  python run_cycle.py --no-check      # 跳过小程序自检
"""
from __future__ import annotations

import argparse
import importlib
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _check_miniprogram():
    """调用自检模块并把非零返回码转成异常，便于统一汇总。"""
    m = importlib.import_module("check_miniprogram")
    code = m.main()
    if code != 0:
        raise RuntimeError("自检未通过（返回码 %s）" % code)
    return code


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-buzz", action="store_true", help="跳过 Amazon 榜单抓取与打分")
    ap.add_argument("--no-walmart", action="store_true",
                    help="跳过 Walmart 品类页 / 评论 / 配图（这三步最慢）")
    ap.add_argument("--no-build", action="store_true", help="跳过看板与小程序数据重建")
    ap.add_argument("--no-check", action="store_true", help="跳过小程序自检")
    args = ap.parse_args()

    t0 = time.time()
    results = []

    def step(label, fn, soft=False):
        """soft=True：失败只记录、不算流程失败（用于可选增强数据）。

        记录用「状态字」而不是布尔 —— 早期写成 `results.append((label, soft))`，
        软失败（soft=True）会被汇总打印成 ✅，跟上面那行 ⚠️ 自相矛盾，
        看汇总的人会误以为步骤成功了。退出码仍然按「硬失败」判。
        """
        print("\n" + "=" * 60)
        print("  " + label)
        print("=" * 60)
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            print("  %s：%s: %s" % ("⚠️ 失败（不阻断）" if soft else "❌ 失败",
                                   type(e).__name__, e))
            traceback.print_exc()
            results.append((label, "warn" if soft else "bad"))
            return False
        print("  ✅ 完成")
        results.append((label, "ok"))
        return True

    print("[%s] hd-watch 一轮更新开始…" % time.strftime("%Y-%m-%d %H:%M:%S"))

    # ---- 数据层 ----
    import fetch_hd
    step("① 抓取 HD 动态数据（行情 / SEC / IR / 新闻）", fetch_hd.run)

    ok_amz = True
    if not args.no_buzz:
        import fetch_buzz
        ok_amz = step("② 抓取 Amazon 声量榜单", fetch_buzz.run)

    if not args.no_walmart:
        import fetch_walmart
        import fetch_walmart_reviews
        import fetch_star_images
        ok_wm = step("③ 抓取 Walmart 品类页（7 个 patio 品类）", fetch_walmart.run)
        if ok_wm:
            step("④ 抓取 Walmart 评论（负评归纳）", fetch_walmart_reviews.run, soft=True)
        else:
            results.append(("④ Walmart 评论（因③失败而跳过）", "warn"))
        # 配图只依赖 walmart.json，与评论无关
        step("⑤ 下载明星产品配图", fetch_star_images.run, soft=True)

    # ⑥ 打分：只要 Amazon 侧没抓失败就跑（Walmart 缺失时脚本内部会自行降级并报错）
    if ok_amz:
        import analyze_buzz
        step("⑥ buzz 打分 + 双渠道对比 + 品类档次阶梯", analyze_buzz.analyze,
             soft=args.no_walmart)
    else:
        results.append(("⑥ buzz 打分（因②失败而跳过）", "bad"))

    # ---- 产物层 ----
    if not args.no_build:
        import build_hd
        import build_miniprogram
        step("⑦ 重建 HD 看板 HTML", build_hd.build)
        step("⑧ 重建小程序数据 mini.js", build_miniprogram.main)

    # ---- 校验层 ----
    if not args.no_check:
        step("⑨ 小程序自检", _check_miniprogram)

    # ---- 汇总 ----
    bad = [n for n, st in results if st == "bad"]
    warn = [n for n, st in results if st == "warn"]
    print("\n" + "=" * 60)
    mark = {"ok": "✅", "warn": "⚠️", "bad": "❌"}
    for name, st in results:
        print("  %s  %s" % (mark[st], name))
    print("-" * 60)
    tail = "｜全部成功"
    if bad or warn:
        tail = "｜失败 %d 步" % len(bad) + ("、不阻断失败 %d 步" % len(warn) if warn else "")
    print("[%s] 结束，用时 %.1fs%s"
          % (time.strftime("%Y-%m-%d %H:%M:%S"), time.time() - t0, tail))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
