# Making an Agent Land Precisely in REAPER

> Your Agent can write the **right** notes. It just can't write them in the **right** place.
>
> This isn't the model being dumb.
> **It's that your interface speaks in "seconds" while the model is thinking in "bars."**

---

## 1. The Symptom

You hand the Agent a task:

> "Write a C4 at bar 5, beat 1, one beat long."

It's done. You hit play.

**The note is there, but not quite there.**

- Sometimes it's off by a whole **bar**
- Sometimes it's off by just a few dozen milliseconds and you say "close enough"
- Sometimes it can't make up its mind, flip-flopping between 5.1 and 5.2

You tune the prompt, swap models, add few-shot — it gets better, but it **never reaches "exact."**

You start to wonder: is this just something models can't do?

---

## 2. It's Not That the Model Is Dumb

One sentence says it all:

> **Generative models are reliable at formal reasoning like `1+1=2`.
> Their failure here shows exactly one thing — the input representation itself lacks computable precision.**

The model isn't unable to compute it. **You didn't give it something computable.**

Think about it: if its task were "change the 3rd element of array A to 5," it would nail it.
But if the task is "convert bar 5, beat 1 into seconds" — it needs to know:

- What's the time signature of this project?
- Did the time signature change mid-piece?
- When it changed, did the physical length of `one beat` change?
- How many times did it change?

**None of that is in your interface.** The model can only guess.

---

## 3. The Cause: The Interface Has the Wrong Shape

Look at a typical DAW MCP server interface (this one is real):

```lua
-- the interface for writing notes
notes.add({ start_position = 12.48, end_position = 13.02, pitch = 60 })
--                        ↑ seconds                 ↑ seconds
```

**Nothing anywhere in this interface accepts a "bar" or a "beat."**

So the Agent has to do this itself:

```
"bar 5, beat 1"  ──[ ??? ]──▶  12.48 seconds
                  ↑
        it can only do this step in its head
```

**And that conversion needs a time-signature map — which the model doesn't have.**

### The right interface should look like this

```lua
notes.add({ bar = 5, beat = 1, pitch = 60, length_beats = 1 })
```

**The model says what it means; the machine does the converting.**

---

## 4. What the Correct Conversion Actually Is

There's only one core fact: **the length of "one beat" is determined by the time signature — and the time signature changes.**

### 4.1 The Conventional Formula (Wrong)

```
AbsTick = ((M − 1) · BPI + (T − 1)) · TPB         TPB = PPQ × 4 / Denom
```

`M` = measure number, `T` = beat number (both 1-based).

**It assumes there's a single ruler for the whole piece.** The moment the time signature changes mid-piece, it collapses.

### 4.2 A Counterexample

Say the project is:

| Segment | Bars | Time signature | BPI | Denom | ticks per bar |
|---|---|---|---|---|---|
| 1 | 1–4 | 4/4 | 4 | 4 | **3840** |
| 2 | 5–10 | 3/4 | 3 | 4 | **2880** |
| 3 | 11–18 | 6/8 | 6 | 8 | **2880** |

PPQ = 960. Question: what's the absolute tick of bar 5, beat 1 (`5.1.00`)?

```
The formula above (hard-multiplying from bar 1 using segment 2's BPI):
    ((5 − 1) × 3 + 0) × 960 = 11520     ❌

The true value (segmented accumulation):
    4 bars × 3840 = 15360                ✅

Error = 3840 = exactly one 4/4 bar
```

**This is the root cause of "notes drift systematically after a time-signature change."**

> In other words: the original formula thinks the function is **a straight line**, when it's actually **a polyline**.
> For a straight line, one multiplication handles everything; for a polyline you can only **sum segment by segment**.

### 4.3 General Form

```
abs_tick(B, T) = Σ_{s < k} [ (eb_s − sb_s + 1) · BPI_s · TPB_s ]
               + ( (B − sb_k) · BPI_k + (T − 1) ) · TPB_k
```

where `k` is the segment containing bar `B`.

**There's exactly one key change:**

> **The "minus one" didn't change — but it dropped from a "global minus one" to a "within-segment minus one."**

### 4.4 Degenerate Property

When `n = 1` (a single time signature for the whole piece), the general form **degenerates exactly into the original formula**.

Which means: **swapping in this implementation changes nothing about the behavior of any single-time-signature project**, so it's safe to deploy.

### 4.5 A Commonly Overlooked Point: Reverse Mapping

```
Forward  bar.beat → tick  : one formula, you can even do it by hand
Reverse  tick → bar.beat  : must rely on the accumulated boundary S_s of each segment
```

`bar.beat ↔ tick` is a **piecewise-linear, strictly monotonic bijection**, so the reverse has a unique solution —
**but the reverse lands on that string of accumulated boundaries `S_s`, not on a formula.**

**Forward you can do by hand; reverse you cannot.** This is the one thing in this whole concept that you'll get wrong if you don't know it.

---

## 5. Evidence: This Isn't Paper Derivation

That 3840-tick counterexample above, and the general form itself, **were both measured on a real DAW.**

### 5.1 How It Was Measured

In a test project with `4/4 (1–4) → 3/4 (5–10) → 6/8 (11–18)`,
for **every beat of every bar**, we resolved the position through three independent paths at once:

| Path | Source |
|---|---|
| **A** | The general form in this document (pure arithmetic) |
| **B** | REAPER `TimeMap_GetMeasureInfo()` (table lookup) |
| **C** | REAPER `TimeMap2_beatsToTime()` → `TimeMap2_timeToQN()` (conversion) |

**The three paths are independent of each other. Only full agreement counts as verification.**

### 5.2 Measured Results

```
REAPER version : 7.73/x64
Test PPQ       : 960
Total compared : 82     matched : 82     mismatched : 0
```

Samples:

| Bar | Beat | General form (QN) | REAPER-Info | REAPER-B2T | |
|---|---|---|---|---|---|
| 1 | 1 | 0.000000 | 0.000000 | 0.000000 | ✅ |
| 5 | 1 | 16.000000 | 16.000000 | 16.000000 | ✅ |
| 11 | 1 | 34.000000 | 34.000000 | 34.000000 | ✅ |
| 18 | 6 | 57.500000 | 57.500000 | 57.500000 | ✅ |

Counterexample reproduction:

| Position | General form (tick) | Original formula (tick) | Error |
|---|---|---|---|
| `5.1.00` | 15360 | 11520 | **3840** ✅ |
| `9.2.00` | 27840 | 24000 | **3840** ✅ |
| `11.1.00` | 32640 | 28800 | **3840** ✅ |

### 5.3 How to Run It Yourself

```
REAPER → Actions → Show action list
       → New action → Load ReaScript
       → select code/matcs_verify_reaper.lua  → Run
```

The script will:

1. Back up your current tempo map
2. Build its own standard test project (`4/4 → 3/4 → 6/8`)
3. Probe the API's indexing convention (measure it, don't guess)
4. Run the three-way comparison bar by bar, beat by beat
5. Reproduce that 3840-tick counterexample above
6. **Automatically restore** your tempo map (the whole run is wrapped in Undo)

Output goes to the REAPER console and is also written to `REAPER resource directory/MATCS-verify-result.txt`.

> ⚠️ **Run it in an empty project the first time.**
> 💡 Want to verify against a real project? Set `USE_CURRENT_MAP` at the top of the script to `true` and it won't write anything at all.

---

## 6. The Fix: Add a bar:beat Interface to Your MCP Server

No rewrite needed — **add a layer**.

### 6.1 The Write Path

```lua
-- before: the Agent has to work out "bar 5, beat 1" = 12.48 seconds by itself
-- notes.add({ start_position = 12.48, pitch = 60 })

-- after: the Agent says what it means
-- notes.add({ bar = 5, beat = 1, pitch = 60, length_qn = 1 })
```

Core implementation (**full runnable version in [`code/matcs_agent_helpers.lua`](code/matcs_agent_helpers.lua)**):

```lua
-- position: (bar, beat) → absolute QN
local function bar_beat_to_qn(bar, beat)
    local _, qn_start, _, _, tdenom = reaper.TimeMap_GetMeasureInfo(0, bar - 1)
    return qn_start + (beat - 1) * (4 / tdenom)   -- each "beat" = 4/denominator QN
end

-- write a note at a musical coordinate
local function add_note_at(take, bar, beat, pitch, length_qn)
    local qn = bar_beat_to_qn(bar, beat)

    local t0 = reaper.TimeMap2_QNToTime(0, qn)
    local t1 = reaper.TimeMap2_QNToTime(0, qn + length_qn)

    return reaper.MIDI_InsertNote(take, false, false,
        reaper.MIDI_GetPPQPosFromProjTime(take, t0),
        reaper.MIDI_GetPPQPosFromProjTime(take, t1),
        0, pitch, 96, true)
end
```

### ⚠️ For durations, don't use "beats" — use QN

This is the easiest place to trip up:

```
With a 4/4 time signature, "one beat" = one quarter note
With a 6/8 time signature, "one beat" = one eighth note      ← it changed
```

**If a duration crosses a time-signature change point, saying "two beats" is ambiguous** —
is it two beats in the starting bar, or two beats in the ending bar?

**Expressed in QN there's no such problem** (QN doesn't change with the time signature), which is why the interface above takes `length_qn`.

> If you really do want to use "beats", `code/matcs_agent_helpers.lua` also ships
> `add_note_at_beats()`, which **explicitly adopts "the beat length of the starting bar"** as its interpretation policy.
> The policy is explicit, but it still fights your intuition when you cross a time-signature change — so we don't use it by default.

### 6.2 The Read Path (Just as Important)

Fixing only the write path is useless — the Agent can write notes in, but **it can't read back where it put them.**

```lua
-- convert PPQ back to "bar.beat"
local function ppq_to_bar_beat(take, ppq)
    local t = reaper.MIDI_GetProjTimeFromPPQPos(take, ppq)
    local beats_in_bar, measure, cml, fullbeats, cdenom =
        reaper.TimeMap2_timeToBeats(0, t)
    --  beats_in_bar : which beat within the bar (0-based)
    --  measure      : bar number (0-based)
    --  cml          : current beats per bar (= time signature numerator)
    --  cdenom       : current time signature denominator
    return measure + 1, math.floor(beats_in_bar) + 1
end
```

**Only after both changes does the Agent's loop actually close:**

```
say "bar 5, beat 1" → write it in → read it back → still "bar 5, beat 1"
```

---

## 7. The Limits of This Approach

**Don't treat this as a cure-all.** These are the hard limits:

| Limit | Explanation |
|---|---|
| **The segment table must come from outside** | This method **does not infer time signatures from audio**. That's a probabilistic estimation problem in MIR |
| **No premise validation** | It computes whatever you hand it. If the segment table is wrong, the result is wrong |
| **It fails under dense time-signature changes** | When the time signature changes "once per bar," the formula's leverage goes to zero — and there the right answer isn't a better formula, it's a **time-signature event table + binary search** |
| **No strict upper bound on rounding error** | Under variable time signatures we only have empirical observations, no proof |
| **Verified on only one host application** | Only REAPER 7.73 so far. Other DAWs are unverified |

**In one line: this method is a calculator, not an auditor.**

---

## 8. Where This Comes From

The full derivations, the degeneracy theorem, the event criterion, and the applicability-domain analysis are in the papers:

| Document | Contents |
|---|---|
| [Paper II · Absolute Spatiotemporal Coordinate System](../论文二_绝对时空坐标系/README.md) (Chinese) | Coordinate system, closed form, reverse mapping, event criterion, precision analysis · [PDF](../论文二_绝对时空坐标系/paper.pdf) |
| [Paper I · Dislocation and Reflection on "Non-Quantized" Musical Work](../论文一_音乐非量化工作的错位与反思/README.md) (Chinese) | Why music is quantifiable, and down to which layer quantization holds · [PDF](../论文一_音乐非量化工作的错位与反思/paper.pdf) |

**Want theory → read the papers. Want to build → stay in this document.**

---

## 9. Citation

See [`CITATION.cff`](../CITATION.cff) in the repository root.

---

## License

Text and figures are under [CC BY 4.0](../LICENSE). Please keep the attribution and source when reposting or citing.

---

*Author: MOZUN (Wang Zijian) · Core Theory Project Group · 368164331@qq.com*
