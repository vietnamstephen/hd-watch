# -*- coding: utf-8 -*-
"""资料库页面覆盖导入（带长超时）。

背景：WorkBuddy 自带的 library/page/import_html.py 把 COS PUT 超时写死为 60s。
本机上行带宽下，1.2MB 的看板 HTML 需要 90s 左右，用默认值必报
「文件上传到 COS 失败」。这里导入其模块后把 PUT_TIMEOUT 调大再执行，
其余参数与官方脚本完全一致（--file-name / --space-id / --node-block-id）。

用法：
    python3 scripts/import_library_page.py <html 路径> --file-name ... \
        --space-id ... --node-block-id ...
"""
import importlib.util
import os
import sys

HELPER = ("/Applications/WorkBuddy.app/Contents/Resources/app.asar.unpacked/resources/"
          "plugins/workbuddy-builtin/skills/library/page/import_html.py")


def main() -> None:
    if not os.path.exists(HELPER):
        sys.exit("找不到 import_html.py，检查 WorkBuddy 安装路径")
    sys.path.insert(0, os.path.dirname(HELPER))
    spec = importlib.util.spec_from_file_location("import_html", HELPER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.PUT_TIMEOUT = 300
    sys.argv = [HELPER] + sys.argv[1:]
    mod.main()


if __name__ == "__main__":
    main()
