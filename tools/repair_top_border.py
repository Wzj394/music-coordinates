#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
repair_top_border.py —— 补回被 drawio 导出裁掉的白底方框顶边

【问题】
某些 drawio 导出把画布边界精确裁在图形最顶端方框的顶边上，
那条水平描边整体落在画布之外，于是被裁掉；
而竖直描边因向下延伸得以保留，导致方框「顶部敞开」。

本例中 fig4-hitl 的两个方框（human / llm）即如此：
  · 绘图初稿版（人机交互实现图（4）.drawio.png）里方框是闭合的
  · 开发日志配图版与合规图片版里顶边已丢失
  · 经像素级比对，本项目的清洗流程未丢失任何深色像素（各阈值下丢失均为 0）

【做法】
  1. 在顶部增加若干像素白边，使画面不紧贴裁切边缘
  2. 探测前若干行中的竖直边框 x 位置
  3. 按方框成对连接，绘制与其它边框同粗的黑色顶边

用法：
    python tools/repair_top_border.py            # 就地修复 figures/fig4-hitl.png
"""
import os
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(os.path.dirname(HERE), "figures", "fig4-hitl.png")

MARGIN   = 16      # 顶部新增白边（像素）
PROBE    = 30      # 探测竖直边框所用的行数
PAIR_TOL = 40      # 同一方框左右边框的间距下限，用于配对
LINE_RGB = (0, 0, 0)


def vertical_borders(dark, probe):
    """返回前 probe 行中竖直边框的 (x_min, x_max, width) 列表"""
    proj = dark[:probe].sum(axis=0)
    cols = np.where(proj >= probe * 0.6)[0]
    groups, s, p = [], None, None
    for c in cols:
        if s is None:
            s = p = c
        elif c <= p + 3:
            p = c
        else:
            groups.append((s, p)); s = p = c
    if s is not None:
        groups.append((s, p))
    return [(s, e, e - s + 1) for (s, e) in groups]


def main():
    im = Image.open(FIG).convert("RGB")
    a = np.array(im).astype(int)
    dark = a.sum(axis=2) < 400

    verts = vertical_borders(dark, PROBE)
    if len(verts) < 2:
        raise SystemExit("未能在顶部探测到竖直边框，放弃修复")
    print("探测到的竖直边框:")
    for s, e, w in verts:
        print(f"   x {s:5d}..{e:<5d}  宽 {w}")

    # 竖直边框宽度 -> 顶边粗细（取中位数）
    thick = int(np.median([w for _, _, w in verts]))

    # 成对：第 0-1 个是左框的左右边，第 2-3 个是右框的左右边
    if len(verts) % 2:
        raise SystemExit(f"竖直边框数为奇数（{len(verts)}），无法成对，放弃修复")
    pairs = [(verts[i][0], verts[i + 1][1]) for i in range(0, len(verts), 2)]
    print(f"\n顶边粗细 {thick} px，待补方框 {len(pairs)} 个:")
    for x0, x1 in pairs:
        print(f"   x {x0}..{x1}  （宽 {x1 - x0 + 1}）")

    # 1) 顶部加白边
    w, h = im.size
    canvas = Image.new("RGB", (w, h + MARGIN), "white")
    canvas.paste(im, (0, MARGIN))

    # 2) 画顶边：紧贴新白边下方，与竖直边框自然衔接
    arr = np.array(canvas)
    y0, y1 = MARGIN - thick, MARGIN - 1
    for x0, x1 in pairs:
        if x1 <= x0:
            continue
        arr[y0:y1 + 1, x0:x1 + 1] = LINE_RGB
        print(f"   已补顶边 y {y0}..{y1}  x {x0}..{x1}")

    Image.fromarray(arr).save(FIG)
    print(f"\n已写回 {FIG}（高度 {h} -> {h + MARGIN}）")


if __name__ == "__main__":
    main()
