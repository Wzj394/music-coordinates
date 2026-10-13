#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
matcs.py —— 绝对时空坐标系（MATCS）的最小参考实现

论文：《绝对时空坐标系：音乐事件的精确量化与全局定位》
      https://github.com/  （见仓库 README）

为什么给代码：论文里的关键断言（「原式在 5.1.00 处误差 3840 tick」「正确值为
15360」）**只靠读论文无法验证**。这里把判据与算法落成可执行的断言，
`python matcs.py` 即可复现论文第 9 节的验证表。

约定（与论文一致）：
    小节号 M 自 1 起计，拍号 T 自 1 起计，tick 自 0 起计。
    「第 1 小节第 1 拍」= 绝对 tick 0。
"""

from typing import Dict, List, Sequence, Tuple

Segment = Tuple[int, int, int, int]      # (起小节, 止小节, BPI, Denom) —— 均含端点


# ---------------------------------------------------------------------------
# 一、坐标换算
# ---------------------------------------------------------------------------
def tpb_of(ppq: int, denom: int) -> int:
    """每拍的 tick 数：TPB = PPQ × 4 / Denom"""
    return ppq * 4 // denom


def bar_len(ppq: int, bpi: int, denom: int) -> int:
    """一小节的 tick 数：BPI × TPB"""
    return bpi * tpb_of(ppq, denom)


def abs_tick_naive(bar: int, beat: int, bpi: int, ppq: int, denom: int) -> int:
    """**原式**：单一线性。只在全曲单一拍号时正确。

    这就是论文要推广掉的那个式子——它的前提是「尺子全程不变」。
    """
    return ((bar - 1) * bpi + (beat - 1)) * tpb_of(ppq, denom)


def abs_tick(bar: int, beat: int, segments: Sequence[Segment], ppq: int) -> int:
    """**通式**：分段求和。变拍号下的正确解。

    segments 须按起小节升序、彼此不相交且覆盖整部作品。
    """
    if bar < 1 or beat < 1:
        raise ValueError("小节号与拍号均自 1 起计")
    total = 0
    for (sb, eb, bpi, denom) in segments:
        tpb = tpb_of(ppq, denom)
        if bar < sb:
            break
        if bar <= eb:
            return total + ((bar - sb) * bpi + (beat - 1)) * tpb
        total += (eb - sb + 1) * bpi * tpb        # 整段累加
    raise ValueError(f"小节 {bar} 超出段表范围 {segments}")


def total_ticks(segments: Sequence[Segment], ppq: int) -> int:
    """全曲总时长（tick）。用于骨架实验的 T 值核对。"""
    return sum((eb - sb + 1) * bpi * tpb_of(ppq, denom)
               for (sb, eb, bpi, denom) in segments)


# ---------------------------------------------------------------------------
# 二、事件判据：事件 = 纵向值发生改变的瞬间
# ---------------------------------------------------------------------------
def scan_events(states: Sequence[int]) -> List[Tuple[int, int, int]]:
    """states[t] = 第 t 个绝对 tick 上的纵向值（0 表示休止）。

    返回 [(时刻, 旧值, 新值), ...]。音符起始 / 连奏 / 断奏 / 休止结束
    四类边界由此**同一条件**给出，无需分别处理。
    """
    return [(t, states[t - 1], states[t])
            for t in range(1, len(states)) if states[t] != states[t - 1]]


# ---------------------------------------------------------------------------
# 三、论文第 9 节的验证表（可执行）
# ---------------------------------------------------------------------------
#  500 小节工程所用的反例段表：4/4 → 3/4 → 6/8
SEGMENTS: List[Segment] = [
    (1, 4, 4, 4),        # 段1  4/4  BPI=4  Denom=4
    (5, 10, 3, 4),       # 段2  3/4  BPI=3  Denom=4
    (11, 18, 6, 8),      # 段3  6/8  BPI=6  Denom=8
]
PPQ = 960

#  论文给出的验证表：(小节, 拍, 位置记法, 通式结果, 原式结果)
CASES = [
    (5, 1, "5.1.00", 15360, 11520),
    (9, 2, "9.2.00", 27840, 24000),
    (11, 1, "11.1.00", 32640, 28800),
]


def main() -> int:
    print("=" * 66)
    print("段表（PPQ = %d）" % PPQ)
    print("=" * 66)
    for (sb, eb, bpi, denom) in SEGMENTS:
        print(f"  小节 {sb:>3}—{eb:<3}  BPI={bpi}  Denom={denom}"
              f"   TPB={tpb_of(PPQ, denom):>4}   小节长={bar_len(PPQ, bpi, denom):>5} tick")
    print(f"  全曲总时长 T = {total_ticks(SEGMENTS, PPQ)} tick\n")

    print("=" * 66)
    print("验证表：通式 vs 原式")
    print("=" * 66)
    print(f"  {'位置':<10}{'通式(正确)':>12}{'原式':>10}{'误差':>10}")
    ok = True
    for (bar, beat, label, want, want_naive) in CASES:
        got = abs_tick(bar, beat, SEGMENTS, PPQ)
        naive = abs_tick_naive(bar, beat, SEGMENTS[1][2], PPQ, SEGMENTS[1][3])
        err = want - want_naive
        mark = "✅" if (got == want and naive == want_naive) else "❌"
        if got != want or naive != want_naive:
            ok = False
        print(f"  {label:<10}{got:>12}{naive:>10}{err:>10}   {mark}")

    print()
    print("=" * 66)
    print("事件判据：四类边界同一条件")
    print("=" * 66)
    #  论文图 4 的阶梯：60 → 休止 → 67 → 64 → 休止 → 64
    states = [60] * 960 + [0] * 480 + [67] * 960 + [64] * 960 + [0] * 480 + [64] * 480
    for (t, old, new) in scan_events(states):
        kind = {(0, 60): "音符起始", (60, 0): "断奏/休止开始",
                (0, 67): "休止结束", (67, 64): "连奏（音高改变）",
                (64, 0): "断奏", (0, 64): "休止结束"}.get((old, new), "？")
        print(f"  t={t:>5}  {old:>3} → {new:<3}   {kind}")
    print(f"  共 {len(scan_events(states))} 个事件")

    print()
    print("=" * 66)
    print("结论：" + ("全部断言通过 ✅" if ok else "存在不符 ❌"))
    print("=" * 66)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
