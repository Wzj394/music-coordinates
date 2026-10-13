#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_figures.py —— 生成论文插图（矢量 PDF）

设计规范（参照 SSCI-Plots 等期刊绘图实践）：
  · 只用 Noto Sans SC 单一字体族：同时覆盖拉丁与 CJK，绕开 matplotlib 的字体回退
  · 图宽按期刊栏宽精确设定（0.78\\textwidth），使图内字号与正文严格 1:1
  · 不使用 bbox='tight'，改由 constrained_layout 在固定画布内排版，
    保证输出尺寸 == 设计尺寸，插图时不被缩放
  · 去上/右框线、无网格、无 chartjunk；图号与图注一律留在 LaTeX 侧，不烧进图里
  · 统一取色：强调色（深蓝）+ 中性灰；仅"错误/关键"用红
  · 引线短、不跨数据线；标注分层错开，避免拥挤

用法：
    python tools/make_figures.py
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import patches

# ---- 版面常量：图宽 = 0.78 \textwidth，与 main.tex 中的 width= 严格一致 ----
TEXTW_CM = 16.09
FIGFRAC  = 0.78
FIGW     = TEXTW_CM * FIGFRAC / 2.54          # ≈ 4.94 in

plt.rcParams.update({
    "font.family":        "sans-serif",
    "font.sans-serif":    ["Noto Sans SC"],
    "axes.unicode_minus": False,
    "font.size":          8.5,
    "axes.labelsize":     8.5,
    "axes.titlesize":     9,
    "xtick.labelsize":    8,
    "ytick.labelsize":    8,
    "legend.fontsize":    8,
    "axes.linewidth":     0.7,
    "xtick.major.width":  0.7,
    "ytick.major.width":  0.7,
    "xtick.major.size":   3.0,
    "ytick.major.size":   3.0,
    "xtick.direction":    "out",
    "ytick.direction":    "out",
    "pdf.fonttype":       42,
    "figure.constrained_layout.use": True,
    "savefig.pad_inches": 0.02,
})

BLUE  = "#1F4E79"      # 强调色
GREY  = "#8C8C8C"      # 中性灰（对照）
LGREY = "#C9C9C9"
RED   = "#A6321E"      # 仅用于"错误 / 关键"
GREEN = "#3E6B52"

HERE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(os.path.dirname(HERE), "figures")
os.makedirs(OUT, exist_ok=True)


def save(fig, name):
    p = os.path.join(OUT, name)
    fig.savefig(p)
    plt.close(fig)
    print(f"  {name:20s} {os.path.getsize(p)/1024:6.1f} KB")


def bare(ax):
    """去上/右框线——期刊图的标准做法。"""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


# ===========================================================================
# 图 1：分段线性 vs 直线
# ===========================================================================
def fig_pwl():
    segs = [(1, 4, 3840, "4/4"), (5, 10, 2880, "3/4"), (11, 18, 2880, "6/8")]
    xs, ys, acc = [], [], 0
    for (a, b, ln, _) in segs:
        xs += [a]; ys += [acc]
        acc += (b - a + 1) * ln
        xs += [b + 1]; ys += [acc]

    bars  = np.arange(1, 20)
    wrong = (bars - 1) * 2880

    fig, ax = plt.subplots(figsize=(FIGW, 2.55))
    ax.plot(xs, ys, color=BLUE, lw=1.6, zorder=3, label="真实：分段求和")
    ax.plot(bars, wrong, color=GREY, lw=1.4, ls=(0, (4, 2)), zorder=2,
            label="原式：单一线性（斜率取段 2）")

    for xb in (5, 11):
        ax.axvline(xb, color=LGREY, lw=0.7, ls=":", zorder=1)

    # 段标签：贴顶排列，置于各自段中心
    for (a, b, _, nm) in segs:
        ax.text((a + b) / 2, 61000, nm, ha="center", va="bottom",
                fontsize=8.5, color=BLUE)

    # 误差标注：竖直双箭头 + 左上角短引线
    ax.annotate("", xy=(5, 15360), xytext=(5, 11520),
                arrowprops=dict(arrowstyle="<->", color=RED, lw=1.0))
    ax.annotate("偏差 3840 tick\n（恰为一个 4/4 小节）",
                xy=(5, 13440), xytext=(1.4, 29500), color=RED,
                fontsize=8, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=RED, lw=0.7))

    ax.set_xlabel("小节序号")
    ax.set_ylabel("绝对 Tick")
    ax.set_xlim(1, 19)
    ax.set_ylim(-3000, 67000)
    ax.set_xticks([1, 5, 10, 15, 18])
    ax.set_yticks([0, 15360, 32640, 55680])
    ax.set_yticklabels(["0", "15360", "32640", "55680"])
    bare(ax)
    ax.legend(loc="lower right", frameon=False, handlelength=1.8)
    save(fig, "fig-pwl.pdf")


# ===========================================================================
# 图 2：拍号变化密度与参数量
# ===========================================================================
def fig_density():
    total_bars, notes_per_bar = 500, 2
    score_size = total_bars * notes_per_bar
    # 参数量按「连续值」绘制：段数实际须取整，但取整会在对数轴上把曲线
    # 变成步宽不规则的阶梯（N=32→64 区间为 64,64,60,60,56,56,56,52,…），
    # 视觉上像"抖动"而非"台阶"。趋势图只需趋势，故略去取整并在图注中说明。
    N = np.arange(1, 65)
    params = 4 * total_bars / N

    fig, ax = plt.subplots(figsize=(FIGW, 2.6))
    ax.plot(N, params, color=BLUE, lw=1.6, zorder=3,
            label="段表参数量（闭式方案）")
    ax.axhline(score_size, color=GREY, lw=1.2, ls=(0, (4, 2)), zorder=2,
               label="谱面本身的事件规模（$500\\times 2$）")
    ax.axvspan(1, 4, color=RED, alpha=0.08, lw=0, zorder=1)

    ax.text(2.6, 210, "杠杆归零区", color=RED, fontsize=8,
            ha="center", va="center")

    # 交叉点：短引线，标注置于曲线右上方空档（该处无任何曲线经过）
    ax.plot([2], [1000], "o", color=RED, ms=3.6, zorder=4)
    ax.annotate("每 2 小节一变时\n参数量已超过谱面",
                xy=(2, 1000), xytext=(2.9, 2600), color=RED, fontsize=8,
                ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=RED, lw=0.7))

    ax.set_xlabel("拍号变化间隔（每 $N$ 小节一变）")
    ax.set_ylabel("参数量")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(1, 64); ax.set_ylim(20, 5000)
    ax.set_xticks([1, 2, 4, 8, 16, 32, 64])
    ax.set_xticklabels(["1", "2", "4", "8", "16", "32", "64"])
    bare(ax)
    ax.legend(loc="lower left", frameon=False, handlelength=1.8)
    save(fig, "fig-density.pdf")


# ===========================================================================
# 图 3：事件判据 —— 纵向状态改变
# ===========================================================================
def fig_event():
    # 纵向值改用等距行呈现：60/64/67 在数值轴上会挤成一团
    LEVELS = [0, 60, 64, 67]
    ROW = {v: i for i, v in enumerate(LEVELS)}

    seq = [(0, 960, 60), (960, 1440, 0), (1440, 2400, 67),
           (2400, 3360, 64), (3360, 3840, 0), (3840, 4320, 64)]

    fig, ax = plt.subplots(figsize=(FIGW, 2.6))

    for (s, e, v) in seq:
        if v == 0:
            ax.axvspan(s, e, color="#EDEDED", lw=0, zorder=0)

    # 阶梯：每一段都画水平线；**只要纵向值改变就画竖直线**，
    # 与前后段是否首尾相接无关（旧版把竖线写在 s > prev_x 里，漏画了全部跳变）
    prev_x, prev_v = 0, 0
    for (s, e, v) in seq:
        if s > prev_x:                                    # 段间空隙：补水平线
            ax.plot([prev_x, s], [ROW[prev_v]] * 2, color=BLUE, lw=1.8, zorder=3)
        if ROW[v] != ROW[prev_v]:                         # 纵向值改变：画跳变
            ax.plot([s, s], [ROW[prev_v], ROW[v]], color=BLUE, lw=1.8, zorder=3)
        ax.plot([s, e], [ROW[v]] * 2, color=BLUE, lw=1.8, zorder=3)
        prev_x, prev_v = e, v

    # 事件点与竖直虚线
    for (t, v) in [(0, 60), (960, 0), (1440, 67), (2400, 64), (3360, 0), (3840, 64)]:
        ax.axvline(t, color=RED, lw=0.7, ls=":", zorder=2)
        ax.plot([t], [ROW[v]], "o", color=RED, ms=3.4, zorder=4)

    # 标注分两行错开，水平位置避开彼此的包围盒
    ax.text(0,    4.42, "音符起始\n$0\\to N$", color=RED, fontsize=8,
            ha="left", va="bottom")
    ax.text(1440, 4.42, "休止结束\n$0\\to N$", color=RED, fontsize=8,
            ha="center", va="bottom")
    ax.text(2400, 4.42, "连奏起始\n$N\\to M$", color=RED, fontsize=8,
            ha="center", va="bottom")
    ax.text(3500, 3.55, "断奏起始\n$N\\to 0$", color=RED, fontsize=8,
            ha="right", va="bottom")

    ax.text(1200, 0.34, "空事件（休止）", fontsize=8, color=GREY, ha="center")

    ax.set_xlabel("绝对 Tick")
    ax.set_ylabel("纵向值（MIDI 音高）")
    ax.set_xlim(-140, 4560)
    ax.set_ylim(-0.35, 6.0)
    ax.set_yticks([ROW[v] for v in LEVELS])
    ax.set_yticklabels(["0\n（休止）", "60", "64", "67"])
    ax.set_xticks([0, 960, 1440, 2400, 3360, 3840, 4320])
    bare(ax)
    save(fig, "fig-event.pdf")


# ===========================================================================
# 图 4：声部分离 —— 连线法与虚拟桥
# ===========================================================================
def fig_voice():
    fig, ax = plt.subplots(figsize=(FIGW, 2.9))

    voices = [
        ("高声部", [(0, 960, 72), (960, 1920, 74), (2880, 3840, 76), (3840, 4800, 77)], BLUE),
        ("中声部", [(0, 1200, 65), (1200, 2400, 67), (2400, 3840, 65)], GREEN),
        ("低声部", [(0, 1920, 53), (1920, 3840, 55)], GREY),
    ]
    for name, notes, c in voices:
        for (s, e, p) in notes:
            ax.plot([s, e], [p, p], color=c, lw=4.0,
                    solid_capstyle="butt", zorder=3)

    # 同声部的相邻音符：音尾—音头的竖直连线
    for (_n, notes, c) in voices:
        for i in range(len(notes) - 1):
            xe, pe = notes[i][1], notes[i][2]
            xs2, ps2 = notes[i + 1][0], notes[i + 1][2]
            if xe == xs2:
                ax.plot([xe, xs2], [pe, ps2], color=c, lw=0.9,
                        ls=(0, (3, 2)), zorder=2)

    # 虚拟桥：高声部 1920–2880 的休止缺口，用偏移半音的虚拟音填满
    ax.plot([1920, 2880], [75, 75], color=RED, lw=3.0,
            ls=(0, (2.4, 1.6)), zorder=4)
    ax.plot([1920, 2880], [74, 76], color=RED, lw=0.9,
            ls=(0, (3, 2)), zorder=2)

    ax.annotate("虚拟桥：半音偏移 $74\\to 75$",
                xy=(2400, 75), xytext=(2400, 81.5), ha="center", va="bottom",
                fontsize=8, color=RED,
                arrowprops=dict(arrowstyle="-", color=RED, lw=0.7))

    ax.text(1900, 71.6, "音尾", fontsize=7.5, color=GREY, ha="right", va="center")
    ax.text(2900, 77.6, "音头", fontsize=7.5, color=GREY, ha="left", va="center")

    for name, notes, c in voices:
        ax.text(-170, notes[0][2], name, fontsize=8.5, color=c,
                ha="right", va="center")

    ax.set_xlabel("绝对 Tick")
    ax.set_xlim(-1750, 5000)
    ax.set_ylim(49, 85)
    ax.set_yticks([53, 65, 72, 76])
    ax.set_yticklabels(["53", "65", "72", "76"])
    ax.set_xticks([0, 960, 1920, 2880, 3840, 4800])
    bare(ax)
    save(fig, "fig-voice.pdf")


# ===========================================================================
# 图 5：结构—生成—过滤 三层闭环
# ===========================================================================
def fig_arch():
    fig, ax = plt.subplots(figsize=(FIGW, 2.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.2)
    ax.axis("off")

    w, h, y0, gap = 2.72, 1.95, 1.15, 0.92
    x0 = 0.0
    boxes = [
        ("结构层", "时间总守恒与递归划分", "$T=\\sum_i S_i$"),
        ("生成层", "动机的几何变换",       "平移 / 倒影 / 逆行 / 缩放"),
        ("过滤层", "音乐约束的可计算判定", "$F=F_1\\wedge\\cdots\\wedge F_k$"),
    ]
    xs = [x0 + i * (w + gap) for i in range(3)]

    for x, (name, sub, formula) in zip(xs, boxes):
        ax.add_patch(patches.FancyBboxPatch(
            (x, y0), w, h, boxstyle="round,pad=0.0,rounding_size=0.10",
            linewidth=0.9, edgecolor=BLUE, facecolor="#EDF3FA", zorder=2))
        ax.text(x + w / 2, y0 + h - 0.40, name, ha="center", va="center",
                fontsize=9.5, color=BLUE, zorder=3)
        ax.text(x + w / 2, y0 + h - 0.92, sub, ha="center", va="center",
                fontsize=7.2, color="#333333", zorder=3)
        ax.text(x + w / 2, y0 + h - 1.48, formula, ha="center", va="center",
                fontsize=7.8, color=GREY, zorder=3)

    # 正向箭头：走在方框之间的空隙里
    for i in range(2):
        xa = xs[i] + w
        ax.annotate("", xy=(xa + gap - 0.10, y0 + h / 2),
                    xytext=(xa + 0.08, y0 + h / 2),
                    arrowprops=dict(arrowstyle="-|>", color=BLUE, lw=1.1,
                                    mutation_scale=9))

    # 反馈箭头：正交折线走高，绝不与方框文字相交
    ytop = y0 + h + 0.55
    xf, xg = xs[1] + w / 2, xs[2] + w / 2
    ax.plot([xg, xg], [y0 + h, ytop], color=RED, lw=1.0, zorder=3)
    ax.plot([xg, xf], [ytop, ytop], color=RED, lw=1.0, zorder=3)
    ax.annotate("", xy=(xf, y0 + h), xytext=(xf, ytop),
                arrowprops=dict(arrowstyle="-|>", color=RED, lw=1.0,
                                mutation_scale=9))
    ax.text((xf + xg) / 2, ytop + 0.16, "被拒绝 → 重新变换",
            fontsize=7.8, color=RED, ha="center", va="bottom")

    # 底部：守恒恒不变
    ax.plot([xs[0], xs[2] + w], [y0 - 0.42, y0 - 0.42], color=GREY, lw=0.7,
            ls=(0, (3, 2)), zorder=1)
    ax.text(5.0, y0 - 0.62,
            "总时长约束 $T_{\\mathrm{total}}$ 在全过程中保持不变",
            fontsize=7.8, color=GREY, ha="center", va="top")

    save(fig, "fig-arch.pdf")


if __name__ == "__main__":
    print("生成插图 ->", OUT)
    fig_pwl(); fig_density(); fig_event(); fig_voice(); fig_arch()
    print("完成。")
