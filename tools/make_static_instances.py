#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_static_instances.py —— 从「思源宋体变量字体」抽取静态字重

【为什么需要】
本机只装了 `NotoSerifSC-VF.ttf` 一个文件（变量字体，wght 轴 200–900）。
XeLaTeX 不支持变量轴，只能取默认实例（Regular），因此正文中文的粗体
过去只能靠 `AutoFakeBold` 合成——那是**伪粗**，在学术排版里是个破绽。

【做法】
用 fontTools 把 wght=400 与 wght=700 抽成两个静态 ttf，放进项目 fonts/，
再由 musepaper.sty 作为 Regular / Bold 引用。这样既拿到**真粗体**，
又不必从 XeLaTeX 换到 LuaLaTeX（换引擎会让编译从 14 秒涨到几分钟）。

用法：
    python tools/make_static_instances.py
"""
import os
import sys

try:
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer
except ImportError:
    sys.exit("需要 fontTools：pip install fonttools")

SRC = r"C:\Windows\Fonts\NotoSerifSC-VF.ttf"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "fonts")
os.makedirs(OUT, exist_ok=True)

INSTANCES = [(400, "Regular"), (700, "Bold")]

if not os.path.exists(SRC):
    sys.exit(f"未找到变量字体：{SRC}")

for wght, name in INSTANCES:
    dst = os.path.join(OUT, f"NotoSerifSC-{name}.ttf")
    if os.path.exists(dst):
        print(f"已存在，跳过：{dst}")
        continue
    print(f"抽取 wght={wght} -> {name} …")
    f = TTFont(SRC)
    try:
        inst = instancer.instantiateVariableFont(
            f, {"wght": wght}, inplace=False, updateFontNames=True)
    except Exception as e:
        print(f"   updateFontNames 失败（{e}），退回不更新字体名")
        f = TTFont(SRC)
        inst = instancer.instantiateVariableFont(f, {"wght": wght}, inplace=False)
    inst.save(dst)
    print(f"   {os.path.getsize(dst)/1024/1024:.1f} MB")

print("\n完成，输出目录:", OUT)
for n in sorted(os.listdir(OUT)):
    print("  ", n, f"{os.path.getsize(os.path.join(OUT,n))/1024/1024:.1f} MB")
