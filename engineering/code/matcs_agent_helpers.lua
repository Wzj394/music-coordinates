--[[
================================================================================
  matcs_agent_helpers.lua
  「音乐坐标 ↔ 绝对位置」参考实现
================================================================================

  用途
  ----
  给 DAW 的 MCP server / Agent 工具层加一层「说人话」的接口。

  Agent（LLM）想的是：      「第 5 小节第 1 拍」
  底层 API 要的是：          「12.48 秒」

  本文件把这一步换算封起来，让 Agent 直接说音乐坐标。

  为什么需要它
  ------------
  传统写法把「bar:beat → 秒」的换算推给了 LLM 心算。而这一步需要
  时间签名映射表 —— 模型手里没有，只能猜。落点误差就是这么来的。

  设计要点
  --------
  1. 「时值」用 QN（四分音符）而不是「拍」表达。
     原因：拍号一变，「一拍」的物理长度就变了。一个跨过变拍号点的时值，
     说「两拍」是不明确的 —— 是起始小节的两拍，还是终点小节的两拍？
     用 QN 表达则无歧义（QN 不随拍号变化）。
     如果你确实要用「拍」，本文件也提供了显式策略的版本，见 §3。

  2. 位置一律用 (bar, beat)，两者均自 1 起计（与乐理和 DAW 界面一致）。

  3. 全部换算交给 REAPER 的 time map，本文件不实现任何公式。
     （公式的正确性证明见 ../README.md §4，验证脚本见 matcs_verify_reaper.lua）

  依赖
  ----
  REAPER 7.x 的以下 API：
      TimeMap_GetMeasureInfo      小节信息（含拍号）
      TimeMap2_QNToTime           QN → 时间
      TimeMap2_timeToBeats        时间 → 小节/拍
      MIDI_GetPPQPosFromProjTime  时间 → take 内 PPQ
      MIDI_GetProjTimeFromPPQPos  take 内 PPQ → 时间
      MIDI_InsertNote             写音符

  作者：MOZUN（王子健）· 核心理论项目组
  许可：CC BY 4.0
================================================================================
--]]

local M = {}

-- 便于在 REAPER 之外做静态检查
local reaper = reaper

-- QN 单位下，一个四分音符 = 1 QN。
-- 拍号分母为 D 时，每「拍」占 4/D 个 QN。
local function qn_per_beat(denom)
    return 4 / denom
end

-- ============================================================================
-- 1. 位置：音乐坐标 → 绝对位置
-- ============================================================================

--- (小节, 拍) → 绝对 QN
-- @param bar   小节号，自 1 起计
-- @param beat  拍号，自 1 起计
-- @param proj  工程（默认 0 = 当前工程）
-- @return qn | nil, err
function M.bar_beat_to_qn(bar, beat, proj)
    proj = proj or 0
    if not bar or not beat or bar < 1 or beat < 1 then
        return nil, "bar 与 beat 均须 >= 1"
    end

    -- TimeMap_GetMeasureInfo 的小节索引是 0-based
    local retval, qn_start, _qn_end, _tnum, tdenom =
        reaper.TimeMap_GetMeasureInfo(proj, bar - 1)

    if not retval or qn_start == nil then
        return nil, string.format("无法读取第 %d 小节的信息", bar)
    end

    return qn_start + (beat - 1) * qn_per_beat(tdenom)
end

--- (小节, 拍) → 时间（秒）
function M.bar_beat_to_time(bar, beat, proj)
    local qn, err = M.bar_beat_to_qn(bar, beat, proj)
    if not qn then return nil, err end
    return reaper.TimeMap2_QNToTime(proj or 0, qn)
end

--- (小节, 拍) → take 内的 PPQ 位置（写 MIDI 用这个）
function M.bar_beat_to_ppq(take, bar, beat, proj)
    local t, err = M.bar_beat_to_time(bar, beat, proj)
    if not t then return nil, err end
    return reaper.MIDI_GetPPQPosFromProjTime(take, t)
end

-- ============================================================================
-- 2. 位置：绝对位置 → 音乐坐标
--    这一步比正向更重要 —— Agent 写得进去，还得读得出来
-- ============================================================================

--- 时间（秒）→ (小节, 拍)
-- @return bar, beat, measure_len_beats, denom
function M.time_to_bar_beat(t, proj)
    proj = proj or 0
    if not t then return nil, "t 为空" end

    -- Lua 侧返回：beats_in_measure(0-based), measure(0-based), cml, fullbeats, cdenom
    local beats_in_measure, measure, cml, _fullbeats, cdenom =
        reaper.TimeMap2_timeToBeats(proj, t)

    if measure == nil then return nil, "TimeMap2_timeToBeats 未能反解" end

    return measure + 1, beats_in_measure + 1, cml, cdenom
end

--- take 内的 PPQ → (小节, 拍)
function M.ppq_to_bar_beat(take, ppq, proj)
    local t = reaper.MIDI_GetProjTimeFromPPQPos(take, ppq)
    return M.time_to_bar_beat(t, proj)
end

-- ============================================================================
-- 3. 写入：在音乐坐标处放一个音符
-- ============================================================================

--- 在 (bar, beat) 处写入一个音符
--
-- 时值策略（重要）：
--   本函数用 length_qn 表达时值，单位是「四分音符个数」。
--   为什么不用「拍」：拍号一变，「一拍」的物理长度就变了，跨变拍号点的
--   时值用「拍」表达是有歧义的（见文件头 §设计要点 1）。
--
--   如果你一定要用「拍」，用 M.length_beats_policy_start() ，
--   它明确采用「起始小节的拍长」作为解释策略。
--
-- @param take         目标 MIDI take
-- @param bar, beat    位置（均自 1 起计）
-- @param pitch        MIDI 音高 0-127
-- @param length_qn    时值（QN 个数）。1 = 四分音符，0.5 = 八分音符
-- @param chan         通道 0-15（默认 0）
-- @param vel          力度 1-127（默认 96）
-- @param selected     写入后是否选中（默认 false）
-- @return true | nil, err
function M.add_note_at(take, bar, beat, pitch, length_qn, chan, vel, selected)
    if not take then return nil, "take 为空" end
    if not reaper.TakeIsMIDI(take) then return nil, "不是 MIDI take" end

    length_qn = length_qn or 1.0

    local qn, err = M.bar_beat_to_qn(bar, beat)
    if not qn then return nil, err end

    -- 时值直接加在 QN 上 —— QN 不随拍号变化，无歧义
    local t0 = reaper.TimeMap2_QNToTime(0, qn)
    local t1 = reaper.TimeMap2_QNToTime(0, qn + length_qn)

    local p0 = reaper.MIDI_GetPPQPosFromProjTime(take, t0)
    local p1 = reaper.MIDI_GetPPQPosFromProjTime(take, t1)

    if p1 <= p0 then
        return nil, string.format("时值无效：起 %d 止 %d", p0, p1)
    end

    local ok = reaper.MIDI_InsertNote(
        take, selected or false, false,
        p0, p1,
        math.floor(chan or 0), math.floor(pitch),
        math.floor(vel or 96), true)

    if not ok then return nil, "MIDI_InsertNote 失败" end
    return true
end

--- 用「拍」表达时值，显式采用**起始小节的拍长**作为解释策略
--
-- ⚠️ 该策略在时值跨过变拍号点时会与「终点小节的拍长」不一致。
--    需要精确控制时，请改用 length_qn 版本。
function M.add_note_at_beats(take, bar, beat, pitch, length_beats, chan, vel, selected)
    local _ret, _qn_start, _qn_end, _tn, tdenom =
        reaper.TimeMap_GetMeasureInfo(0, bar - 1)
    if tdenom == nil then return nil, "无法读取拍号分母" end

    -- 把「拍」折算成 QN，用起始小节的拍长
    local length_qn = length_beats * qn_per_beat(tdenom)
    return M.add_note_at(take, bar, beat, pitch, length_qn, chan, vel, selected)
end

-- ============================================================================
-- 4. 自检：在 REAPER 里跑一遍，确认这套换算闭环成立
-- ============================================================================

--- 往返自检：(bar, beat) → QN → (bar, beat) 是否回到原点
-- @param cases  可选，{ {bar, beat}, ... }；省略则用默认用例
-- @return ok_count, fail_count, report(string)
function M.self_test(cases)
    cases = cases or {
        { 1, 1 }, { 1, 4 },
        { 5, 1 }, { 5, 3 },          -- 变拍号后的第一小节
        { 10, 3 }, { 11, 1 }, { 11, 6 },
        { 18, 6 },
    }

    local ok_n, fail_n = 0, 0
    local lines = {}

    lines[#lines + 1] = string.format("%-12s %-14s %-14s %s",
        "输入", "QN", "反解", "结果")
    lines[#lines + 1] = string.rep("-", 60)

    for _, c in ipairs(cases) do
        local bar, beat = c[1], c[2]

        local qn, err = M.bar_beat_to_qn(bar, beat)
        if not qn then
            fail_n = fail_n + 1
            lines[#lines + 1] = string.format("%d.%d        ERROR: %s", bar, beat, tostring(err))
        else
            local t = reaper.TimeMap2_QNToTime(0, qn)
            local rbar, rbeat = M.time_to_bar_beat(t)

            local ok = (rbar == bar) and (math.abs(rbeat - beat) < 1e-6)
            if ok then ok_n = ok_n + 1 else fail_n = fail_n + 1 end

            lines[#lines + 1] = string.format("%-12s %-14.6f %-14s %s",
                string.format("%d.%d", bar, beat),
                qn,
                string.format("%d.%.4f", rbar or -1, rbeat or -1),
                ok and "✅" or "❌")
        end
    end

    lines[#lines + 1] = string.rep("-", 60)
    lines[#lines + 1] = string.format("通过 %d，失败 %d", ok_n, fail_n)
    lines[#lines + 1] = fail_n == 0
        and "✅ 往返闭环成立：音乐坐标 → 绝对位置 → 音乐坐标"
        or  "❌ 存在不闭环的用例"

    return ok_n, fail_n, table.concat(lines, "\n")
end

--- 在 REAPER 控制台跑自检
function M.run_self_test()
    local ok_n, fail_n, report = M.self_test()
    reaper.ClearConsole()
    reaper.ShowConsoleMsg("=== matcs_agent_helpers 自检 ===\n\n")
    reaper.ShowConsoleMsg(report .. "\n")
    return fail_n == 0
end

return M
