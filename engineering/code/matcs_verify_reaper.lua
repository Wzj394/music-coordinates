--[[
================================================================================
  MATCS 交叉验证脚本  ·  REAPER ReaScript (Lua)
================================================================================

  用途
  ----
  在 REAPER 里逐小节比对两套「小节:拍 → 绝对位置」的换算：

      A. REAPER 原生时间映射（事实标准，经年验证）
           · TimeMap_GetMeasureInfo()
           · TimeMap2_beatsToTime()

      B. MATCS 论文的分段求和闭式
           《绝对时空坐标系：音乐事件的精确量化与全局定位》

  为什么做这件事
  --------------
  论文的核心断言是「变拍号下原线性式失效、分段求和式才是正确解」。
  但**这一断言无法靠读论文验证** —— 必须拿一个已知正确的实现来对照。

  REAPER 的 time map 就是那个「已知正确的实现」：它内部处理变拍号、变速，
  是 DAW 里跑了多年的路径。

  三种可能的结果，每种都有意义：

      1. 三者完全一致
         → 论文闭式是 REAPER 行为的正确重述（可发表为「按此闭式可实现」）

      2. MATCS 与 REAPER 有偏差
         → 说明两者约定不同，需查清是哪一方（这是真发现）

      3. REAPER 内部两条路径互相不一致
         → 更严重，说明该 API 有未文档化的行为

  怎么用
  ------
  1. REAPER 里：Actions → Show action list → New action → Load ReaScript
     选中本文件
  2. 运行
  3. 结果输出到两个地方：
       · REAPER 控制台（View → Show console）
       · 资源目录下的 MATCS-verify-result.txt

  安全性
  ------
  本脚本会临时改写工程的 tempo/time-signature map，**用完后自动还原**。
  同时全程包在 Undo Block 里，即使还原失败也能 Ctrl+Z 撤销。

  如果你不想让它动任何东西，把下面的 USE_CURRENT_MAP 改成 true ——
  那样它只读当前工程，不写任何标记。

  作者：MOZUN（王子健）· 核心理论项目组
  许可：CC BY 4.0
================================================================================
--]]

-- ============================================================================
-- 配置
-- ============================================================================

-- false = 自建标准测试工程（推荐，结果可复现、可对比）
-- true  = 只读当前工程的 tempo map（不写任何东西，但结果依赖你打开的工程）
local USE_CURRENT_MAP = false

-- 标准测试段表：4/4 (1-4) → 3/4 (5-10) → 6/8 (11-18)
-- 与论文第 9 节的反例一致
local TEST_SEGMENTS = {
    { sb = 1,  eb = 4,  bpi = 4, denom = 4 },
    { sb = 5,  eb = 10, bpi = 3, denom = 4 },
    { sb = 11, eb = 18, bpi = 6, denom = 8 },
}
local TEST_BPM    = 120
local TEST_PPQ    = 960      -- 仅用于论文闭式的 tick 计算

-- 浮点比较容差（QN 单位）。1e-9 太严，重采样/浮点累加会有微小误差
local EPS = 1e-6

-- ============================================================================
-- 输出收集
-- ============================================================================
local OUT = {}
local function log(fmt, ...)
    local s = select("#", ...) > 0 and string.format(fmt, ...) or fmt
    OUT[#OUT + 1] = s
end

local pass, fail = 0, 0
local function verdict(ok, fmt, ...)
    local s = select("#", ...) > 0 and string.format(fmt, ...) or fmt
    if ok then pass = pass + 1 else fail = fail + 1 end
    return s
end

-- ============================================================================
-- MATCS 闭式（严格移植自论文附录的参考实现）
--   返回：给定 (bar, beat) 的绝对 tick（PPQ 单位）
-- ============================================================================
local function tpb_of(ppq, denom)
    return math.floor(ppq * 4 / denom)
end

local function matcs_abs_tick(bar, beat, segments, ppq)
    local total = 0
    for _, s in ipairs(segments) do
        local tpb = tpb_of(ppq, s.denom)
        if bar < s.sb then break end
        if bar <= s.eb then
            return total + ((bar - s.sb) * s.bpi + (beat - 1)) * tpb
        end
        total = total + (s.eb - s.sb + 1) * s.bpi * tpb
    end
    return nil, ("小节 %d 超出段表范围"):format(bar)
end

-- 论文闭式换算成 QN（四分音符）单位，便于与 REAPER 对照
--     1 个四分音符 = PPQ 个 tick
local function matcs_qn(bar, beat, segments, ppq)
    local t = matcs_abs_tick(bar, beat, segments, ppq)
    if not t then return nil end
    return t / ppq
end

-- ============================================================================
-- 论文里的「原式」（单一线性）—— 用来复现那个 3840 tick 的误差
-- ============================================================================
local function naive_abs_tick(bar, beat, bpi, ppq, denom)
    return ((bar - 1) * bpi + (beat - 1)) * tpb_of(ppq, denom)
end

-- ============================================================================
-- 主流程
-- ============================================================================
local function main()
    local proj = 0

    log("================================================================================")
    log("  MATCS 交叉验证 · REAPER 原生时间映射  vs  论文分段求和闭式")
    log("================================================================================")
    log("  REAPER 版本 : %s", reaper.GetAppVersion and reaper.GetAppVersion() or "?")
    log("  测试 PPQ    : %d", TEST_PPQ)
    log("  浮点容差    : %g", EPS)
    log("  模式        : %s", USE_CURRENT_MAP and "只读当前工程" or "自建标准测试工程")
    log("")

    -- ------------------------------------------------------------------
    -- 1. 备份现有 tempo map
    -- ------------------------------------------------------------------
    local backup = {}
    local n0 = reaper.CountTempoTimeSigMarkers(proj)
    for i = 0, n0 - 1 do
        local ok, tp, mp, bp, bpm, tn, td, lin = reaper.GetTempoTimeSigMarker(proj, i)
        if ok then
            backup[#backup + 1] = { tp, mp, bp, bpm, tn, td, lin }
        end
    end
    log("【1】备份现有 tempo map：%d 个标记", #backup)
    for i, m in ipairs(backup) do
        log("      [%d] timepos=%.6f  measurepos=%d  beatpos=%.3f  bpm=%.3f  %d/%d",
            i - 1, m[1], m[2], m[3], m[4], m[5], m[6])
    end
    log("")

    local restore_needed = false

    if not USE_CURRENT_MAP then
        -- --------------------------------------------------------------
        -- 2. 建立标准测试 map
        -- --------------------------------------------------------------
        reaper.Undo_BeginBlock()
        restore_needed = true

        -- 先清掉 index >= 1 的标记（index 0 是工程必有的一根，用 Set 改写）
        local n = reaper.CountTempoTimeSigMarkers(proj)
        for i = n - 1, 1, -1 do
            reaper.DeleteTempoTimeSigMarker(proj, i)
        end

        -- 第一根：measurepos = 0（0-based，即第 1 小节），4/4
        reaper.SetTempoTimeSigMarker(proj, 0, -1, 0, 0, TEST_BPM, 4, 4, false)

        -- 变拍号点：用 measurepos（0-based）+ beatpos 指定
        --   第 5 小节（1-based）= measurepos 4
        --   第 11 小节（1-based）= measurepos 10
        local ok1 = reaper.SetTempoTimeSigMarker(proj, -1, -1, 4,  0, TEST_BPM, 3, 4, false)
        local ok2 = reaper.SetTempoTimeSigMarker(proj, -1, -1, 10, 0, TEST_BPM, 6, 8, false)

        reaper.UpdateTimeline()

        log("【2】建立测试 map")
        log("      4/4 @ measurepos=0   (第 1 小节)")
        log("      3/4 @ measurepos=4   (第 5 小节)   返回=%s", tostring(ok1))
        log("      6/8 @ measurepos=10  (第 11 小节)  返回=%s", tostring(ok2))
        log("")

        -- 回读，确认 REAPER 真的这么存了
        log("      回读确认：")
        local nc = reaper.CountTempoTimeSigMarkers(proj)
        for i = 0, nc - 1 do
            local ok, tp, mp, bp, bpm, tn, td = reaper.GetTempoTimeSigMarker(proj, i)
            log("        [%d] measurepos=%d  beatpos=%.2f  timepos=%.6f  bpm=%.2f  %d/%d",
                i, mp, bp, tp, bpm, tn, td)
        end

        -- 若回读的 measurepos 与预期不符，说明 0-based 假设不成立，立刻报告
        local _, mp_ok0 = reaper.GetTempoTimeSigMarker(proj, 0)
        if mp_ok0 ~= 0 then
            log("      ⚠️ 警告：measurepos 约定可能不是 0-based（读到 %d）", mp_ok0)
        end
        log("")
    else
        log("【2】跳过（只读模式）")
        log("")
    end

    -- ------------------------------------------------------------------
    -- 3. 探测 TimeMap_GetMeasureInfo 的索引约定
    -- ------------------------------------------------------------------
    log("【3】索引约定探测（TimeMap_GetMeasureInfo）")
    local probe0 = { reaper.TimeMap_GetMeasureInfo(proj, 0) }
    local probe1 = { reaper.TimeMap_GetMeasureInfo(proj, 1) }
    log("      measure=0 → retval=%s  qn_start=%.6f  qn_end=%.6f  %d/%d",
        tostring(probe0[1]), probe0[2] or -1, probe0[3] or -1, probe0[4] or 0, probe0[5] or 0)
    log("      measure=1 → retval=%s  qn_start=%.6f  qn_end=%.6f  %d/%d",
        tostring(probe1[1]), probe1[2] or -1, probe1[3] or -1, probe1[4] or 0, probe1[5] or 0)

    local zero_based
    if probe0[2] and math.abs(probe0[2]) < EPS then
        zero_based = true
        log("      → 判定：**0-based**（measure=0 的 qn_start 为 0）")
    elseif probe1[2] and math.abs(probe1[2]) < EPS then
        zero_based = false
        log("      → 判定：**1-based**（measure=1 的 qn_start 为 0）")
    else
        log("      → ⚠️ 无法判定（两者 qn_start 都不为 0），后续按 0-based 处理")
        zero_based = true
    end
    local function to_index(bar)   -- 1-based 小节号 → API 索引
        return zero_based and (bar - 1) or bar
    end
    log("")

    -- ------------------------------------------------------------------
    -- 4. 逐小节逐拍对照
    -- ------------------------------------------------------------------
    log("【4】逐小节逐拍对照（QN 单位）")
    log("      列说明：")
    log("        MATCS = 论文分段求和闭式")
    log("        REAPER-Info  = TimeMap_GetMeasureInfo 的 qn_start + (拍-1)×4/分母")
    log("        REAPER-B2T   = TimeMap2_beatsToTime → TimeMap2_timeToQN")
    log("")
    log("      小节  拍  MATCS        REAPER-Info  REAPER-B2T   一致")
    log("      ----------------------------------------------------------------")

    local mismatch = {}
    local total = 0

    for _, seg in ipairs(TEST_SEGMENTS) do
        for bar = seg.sb, seg.eb do
            -- 取 REAPER 的小节信息
            local info = { reaper.TimeMap_GetMeasureInfo(proj, to_index(bar)) }
            local qn_start = info[2]
            local tn, td   = info[4], info[5]

            for beat = 1, seg.bpi do
                total = total + 1

                local a  = matcs_qn(bar, beat, TEST_SEGMENTS, TEST_PPQ)

                local b  = nil
                if qn_start then
                    b = qn_start + (beat - 1) * (4 / seg.denom)
                end

                -- REAPER 第二条路径
                local c = nil
                local t = reaper.TimeMap2_beatsToTime(proj, beat - 1, to_index(bar))
                if t then
                    c = reaper.TimeMap2_timeToQN(proj, t)
                end

                local ok = (a and b and c
                            and math.abs(a - b) < EPS
                            and math.abs(a - c) < EPS
                            and math.abs(b - c) < EPS)

                if not ok then
                    mismatch[#mismatch + 1] = {
                        bar = bar, beat = beat, a = a, b = b, c = c,
                        tn = tn, td = td,
                    }
                end

                log("      %4d %3d  %-12s  %-12s  %-12s %s",
                    bar, beat,
                    a and string.format("%.6f", a) or "nil",
                    b and string.format("%.6f", b) or "nil",
                    c and string.format("%.6f", c) or "nil",
                    verdict(ok, "") .. (ok and "✅" or "❌"))
            end
        end
    end

    log("")
    log("      对照总数：%d    一致：%d    不一致：%d", total, total - #mismatch, #mismatch)
    log("")

    -- ------------------------------------------------------------------
    -- 5. 不一致明细
    -- ------------------------------------------------------------------
    if #mismatch > 0 then
        log("【5】❌ 不一致明细")
        log("      小节  拍   MATCS        REAPER-Info  REAPER-B2T   差值(A-B)")
        log("      ----------------------------------------------------------------")
        for _, m in ipairs(mismatch) do
            log("      %4d %3d  %-12s  %-12s  %-12s  %s",
                m.bar, m.beat,
                m.a and string.format("%.6f", m.a) or "nil",
                m.b and string.format("%.6f", m.b) or "nil",
                m.c and string.format("%.6f", m.c) or "nil",
                (m.a and m.b) and string.format("%.9f", m.a - m.b) or "-")
        end
        log("")
    else
        log("【5】无不一致项 ✅")
        log("")
    end

    -- ------------------------------------------------------------------
    -- 6. 复现论文的反例（原式误差 = 3840 tick）
    -- ------------------------------------------------------------------
    log("【6】复现论文反例：原式在变拍号下的误差")
    log("      论文声称：位置 5.1.00 处，原式误差 = 3840 tick（恰为一个 4/4 小节）")
    log("")
    log("      位置      通式(tick)   原式(tick)   误差(tick)")
    log("      --------------------------------------------------")
    local naive_cases = { {5,1,"5.1.00"}, {9,2,"9.2.00"}, {11,1,"11.1.00"} }
    for _, cs in ipairs(naive_cases) do
        local bar, beat, label = cs[1], cs[2], cs[3]
        local correct = matcs_abs_tick(bar, beat, TEST_SEGMENTS, TEST_PPQ)
        -- 原式用「段 2」的尺子从第 1 小节硬乘 —— 与论文一致
        local seg2 = TEST_SEGMENTS[2]
        local naive = naive_abs_tick(bar, beat, seg2.bpi, TEST_PPQ, seg2.denom)
        log("      %-9s %-12d %-12d %-12d  %s",
            label, correct, naive, correct - naive,
            verdict(correct - naive == 3840, "") .. ((correct - naive == 3840) and "✅" or "❌"))
    end
    log("")

    -- ------------------------------------------------------------------
    -- 7. 还原
    -- ------------------------------------------------------------------
    if restore_needed then
        log("【7】还原原 tempo map")

        -- 全部删除（包含 index 0）。
        -- 实测（REAPER 7.73）：工程可以存在 0 个显式 tempo marker，
        -- 此时用 REAPER 的默认 120bpm 4/4。所以 index 0 也必须删。
        local n = reaper.CountTempoTimeSigMarkers(proj)
        for i = n - 1, 0, -1 do
            reaper.DeleteTempoTimeSigMarker(proj, i)
        end

        -- 按备份重建。
        -- API 文档要求 timepos 与 measurepos/beatpos「二选一」，
        -- 所以这里只给 timepos，其余传 -1。
        for _, m in ipairs(backup) do
            reaper.SetTempoTimeSigMarker(proj, -1, m[1], -1, -1, m[4], m[5], m[6], m[7])
        end

        reaper.UpdateTimeline()
        reaper.Undo_EndBlock("MATCS 交叉验证（已自动还原）", -1)

        local nc = reaper.CountTempoTimeSigMarkers(proj)
        log("      还原后标记数：%d（原本 %d）%s",
            nc, #backup, (nc == #backup) and "✅" or "⚠️ 未完全还原，可 Ctrl+Z")
        if #backup == 0 then
            log("      说明：原工程没有显式 tempo marker（用 REAPER 默认 120bpm 4/4）")
        end
        log("")
    end

    -- ------------------------------------------------------------------
    -- 8. 结论
    -- ------------------------------------------------------------------
    log("================================================================================")
    log("  结论")
    log("================================================================================")
    if #mismatch == 0 then
        log("  ✅ 三条路径完全一致（%d / %d）", total, total)
        log("")
        log("  这意味着：")
        log("    · MATCS 的分段求和闭式，与 REAPER 原生时间映射**行为一致**")
        log("    · 即论文的闭式是既有实现的**正确重述**，而非另一种约定")
        log("    · 在 REAPER 上，用闭式或用 TimeMap2_beatsToTime 结果等价")
    else
        log("  ⚠️ 存在 %d 处不一致（共 %d 处）", #mismatch, total)
        log("")
        log("  这是**有价值的发现**：说明 MATCS 与 REAPER 在某些情形下约定不同。")
        log("  请把上面的明细贴出来，逐条定位是取整、边界归属，还是索引约定。")
    end
    log("")
    log("  断言统计：通过 %d，失败 %d", pass, fail)
    log("================================================================================")

    return #mismatch == 0 and fail == 0
end

-- ============================================================================
-- 执行 + 输出
-- ============================================================================
local ok, err = pcall(main)

if not ok then
    log("")
    log("❌ 脚本异常终止：%s", tostring(err))
end

local text = table.concat(OUT, "\n")

-- 输出 1：REAPER 控制台
reaper.ShowConsoleMsg(text .. "\n")

-- 输出 2：资源目录下的文件（便于贴 issue / 附进论文）
local path = reaper.GetResourcePath() .. "/MATCS-verify-result.txt"
local f = io.open(path, "w")
if f then
    f:write(text, "\n")
    f:close()
    reaper.ShowConsoleMsg("\n[结果已保存] " .. path .. "\n")
end
