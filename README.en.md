# MATCS · The Absolute Spatiotemporal Coordinate System for Musical Events

> **In one line**: turn "bar *m*, beat *t*" into a globally unique absolute tick — and keep it correct under **variable time signatures** (mid-piece meter changes).

The positional expression of musical notation is **relative** — its unit of measure, "one beat," is defined by the time signature. Change the time signature and the ruler changes with it: the same expression then points at a different physical duration. This repository gives you the coordinate system for that problem, the closed form, the failure boundary, and **a runnable reference implementation**.

---

## What Do You Want to Do?

| What you want to do | Where to go |
|---|---|
| **Make an Agent write notes precisely in a DAW** | 👉 [`engineering/`](engineering/README.en.md) (English) · [中文](engineering/README.md) |
| Read the theory / the coordinate system / the event criterion | 👉 [Paper II · Absolute Spatiotemporal Coordinate System](论文二_绝对时空坐标系/README.en.md) (English) · [中文](论文二_绝对时空坐标系/README.md) |
| Figure out why music can be quantized at all | 👉 [Paper I · Dislocation and Reflection on "Non-Quantized" Musical Work](论文一_音乐非量化工作的错位与反思/README.en.md) (English) · [中文](论文一_音乐非量化工作的错位与反思/README.md) |
| Just want the conclusion | Read on — 60 seconds |

**This repository ships two things at once**: read the papers if you want the papers, go straight to the engineering if you want to build. Both share the same mathematics.

---

## The Problem in 30 Seconds

The conversion that is standard in DAWs and symbolic-music libraries is:

```
AbsTick = ((M − 1) · BPI + (T − 1)) · TPB        TPB = PPQ × 4 / Denom
```

It assumes **there is a single ruler for the whole piece**. The moment the time signature changes mid-piece, this formula is wrong:

| Segment | Bars | Time signature | BPI | Denom | TPB | Bar length |
|---|---|---|---|---|---|---|
| 1 | 1–4 | 4/4 | 4 | 4 | 960 | **3840** |
| 2 | 5–10 | 3/4 | 3 | 4 | 960 | **2880** |
| 3 | 11–18 | 6/8 | 6 | 8 | 480 | **2880** |

At "5.1.00" (bar 5, beat 1):

```
Original formula (hard-multiplying from bar 1 with segment 2's BPI)   ((5−1)·3 + 0)·960 = 11520
True value (piecewise summation)                                     4 × 3840         = 15360
                                                                     Error            = 3840  ← exactly one 4/4 bar
```

**This is the root cause of "notes drift systematically after a time-signature change" in a DAW.**

> Put another way: the original formula thinks the function is **a straight line**, when it is actually **a polyline**.
> For a straight line, one multiplication handles everything; for a polyline you can only **sum segment by segment**.

---

## Run It and See

```bash
python engineering/code/matcs.py
```

The output is the verification table from §9 of the paper:

```
Position     General form (correct)   Original formula   Error
5.1.00       15360      11520     3840   ✅
9.2.00       27840      24000     3840   ✅
11.1.00      32640      28800     3840   ✅
all assertions passed ✅
```

The same script also reproduces the event criterion — **note onset / legato / staccato / rest end: four boundary types given by one and the same condition**:

```python
scan_events([60]*960 + [0]*480 + [67]*960 + ...)
# t= 960  60 → 0    staccato / start of rest
# t=1440   0 → 67   end of rest
# t=2400  67 → 64   legato (pitch changes)
```

### Verify It on a Real DAW

The above is pure arithmetic. **To check it against real host software**, use this ReaScript:

```
REAPER → Actions → Show action list
       → New action → Load ReaScript
       → engineering/code/matcs_verify_reaper.lua → Run
```

In a `4/4 → 3/4 → 6/8` test project, it resolves the position of **every beat of every bar** through three independent paths at once, and compares them one by one.

**Measured results (REAPER 7.73, PPQ 960):**

```
Total compared: 82     matched: 82     mismatched: 0
```

| Path | Source |
|---|---|
| A | The piecewise-summation general form in this document (pure arithmetic) |
| B | REAPER `TimeMap_GetMeasureInfo()` (table lookup) |
| C | REAPER `TimeMap2_beatsToTime()` → `TimeMap2_timeToQN()` (conversion) |

---

## Three Things

1. **A unified, symbol-level event criterion** —— an event = the instant the vertical value (the pitch value) changes. Note onset, legato, staccato and rest end are thereby reduced to one and the same condition; a rest is redefined as an **empty event** (empty pitch, explicit start and end), so there are no more undefined intervals on the timeline.
2. **A closed form under variable time signatures, and its degenerate property** —— generalize the original formula into a piecewise summation, and prove that the original formula is the degenerate special case of it when the number of segments *n* = 1.
3. **A quantitative characterization of the applicability domain** —— the parameter count grows linearly with time-signature change density. As that density approaches "one change per bar," the parameter count approaches that of the score itself and the formula's leverage drops to zero — **at that point the right answer is not a better formula but a paradigm shift** (time-signature event table + binary search).

---

## ⚠️ When Not to Use It

- **It does not infer time signatures from audio waveforms** —— the segment table must come from outside (project data or score annotations); that assumption is unavoidable
- **It gives no strict upper bound on rounding error**
- **No cross-implementation validation has been done** —— so far only one host, REAPER
- **The closed form fails under dense time-signature changes** —— see item 3 above: that case degenerates to an event table + binary search
- **It makes no claim about musicality whatsoever**
- **This method is a calculator, not an auditor** —— it computes whatever you hand it; it does not validate your premises

---

## This Conversion Is Not New in Itself

Converting between bar–beat–tick and absolute tick is already standard practice in DAWs, symbolic-music libraries and game audio engines — Unreal's `FBarMap` interface, MusPy and mido all provide equivalent implementations. **This repository does not claim it as new.**

What it does claim is the three things built on top of it (see §2.8 and §1.4 of the papers), and the **cross-implementation, measured validation** this repository adds.

---

## Documents

| | Document | Format | Language | Notes |
|---|---|---|---|---|
| **Engineering** | [Making an Agent Land Precisely in REAPER](engineering/README.en.md) | Markdown | English | Symptom, cause, measured evidence, MCP server fix, reference code |
| | [让 Agent 在 REAPER 里精确落点](engineering/README.md) | Markdown | Chinese | 症状、病因、实测证据、MCP server 改法、参考代码 |
| **Technical spec** | [Absolute Spatiotemporal Coordinate System: Precise Quantization and Global Localization of Musical Events](论文二_绝对时空坐标系/README.en.md) | Markdown / [PDF](论文二_绝对时空坐标系/paper.pdf) | English | Coordinate system, closed form, event criterion, voice separation, precision analysis |
| | [绝对时空坐标系：音乐事件的精确量化与全局定位](论文二_绝对时空坐标系/README.md) | Markdown / [PDF](论文二_绝对时空坐标系/paper.pdf) | Chinese | 坐标系统、闭式、事件判据、声部分离、精度分析 |
| **Theoretical background** | [Dislocation and Reflection on "Non-Quantized" Musical Work](论文一_音乐非量化工作的错位与反思/README.en.md) | Markdown / [PDF](论文一_音乐非量化工作的错位与反思/paper.pdf) | English | Why music is quantifiable, and down to which layer quantization holds |
| | [对于音乐"非量化"工作的错位与反思](论文一_音乐非量化工作的错位与反思/README.md) | Markdown / [PDF](论文一_音乐非量化工作的错位与反思/paper.pdf) | Chinese | 音乐为何可量化、量化到哪一层为止 |

Paper I supplies the ontological foundation, Paper II the engineering implementation.
If you only care about coordinate conversion, read Paper II §3 directly; if you want to know "why can this be quantized at all," read Paper I.

---

## Repository Layout

```
├── engineering/                      ← Engineering (go here if you want to build)
│   ├── README.md                       Symptom → Cause → Evidence → Fix
│   └── code/
│       ├── matcs.py                    Python reference implementation (runnable as-is)
│       ├── matcs_agent_helpers.lua     Agent tool layer: musical coordinates ↔ absolute position
│       └── matcs_verify_reaper.lua     REAPER cross-validation script
├── tools/                            ← Paper build pipeline
│   ├── build_github.py                 LaTeX → Markdown converter
│   ├── make_figures.py                 generate vector figures
│   ├── make_static_instances.py        extract static weights from a variable font
│   └── repair_top_border.py            repair the clipped top edge of a white-background box
├── 论文二_绝对时空坐标系/              ← Main body (the technical spec)
│   ├── README.md / paper.pdf / paper.tex / figures/
└── 论文一_音乐非量化工作的错位与反思/    ← Theoretical background
    └── README.md / paper.pdf / paper.tex
```

---

## Tech Stack and Two Pitfalls

XeLaTeX + `ctex` + a hand-rolled layout; the Markdown is generated by pandoc with `gfm+attributes`.
Two pitfalls we stepped in are recorded here so nobody else has to:

- **A variable font's default instance is not necessarily Regular.** The `wght` axis of
  `NotoSerifSC-VF.ttf` is `200 .. 200 .. 900` — **the default instance is ExtraLight**. XeLaTeX
  doesn't support variation axes and takes only the default instance, so the body text was briefly
  all hairline weight, and `AutoFakeBold` merely thickened the hairline face and papered the problem
  over. Fix: `tools/make_static_instances.py` extracts static weights.
- **pandoc's `-t gfm` drops heading anchors**, so every `\ref{sec:…}` fails to resolve (44 leftover
  occurrences, measured). You have to use `-t gfm+attributes`.

---

## Citation

See [`CITATION.cff`](CITATION.cff). If you cite only one paper: for coordinate conversion and the event criterion → cite Paper II; for whether music can be quantized → cite Paper I.

---

## License

Text and figures are under [CC BY 4.0](LICENSE). Please keep the attribution and source when reposting or citing.

---

## Author

**MOZUN** (Wang Zijian) · Core Theory Project Group · 368164331@qq.com
