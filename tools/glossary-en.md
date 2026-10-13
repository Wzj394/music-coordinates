# 英译术语对照表 · Translation Glossary

> **用途**：本仓库中译英时的**强制术语约定**。
> 所有译者（无论人还是 AI）必须遵循本表，以保证两篇论文与工程文档用词一致。
>
> **规则**：
> 1. 本表未收录的术语，**先在此表补一条再使用**，不要各自发明译法。
> 2. `\label{}`、`\ref{}`、`\cite{}` 的**内部名字一律不改**（改了引用就断）。
> 3. 代码块内的变量名、函数名、API 名、字符串常量**一律不改**。

---

## 一、核心概念

| 中文 | English | 备注 |
|---|---|---|
| 绝对时空坐标系 | Absolute Spatiotemporal Coordinate System | 缩写 **MATCS**，全篇首次出现时给全称 |
| 绝对 tick / 绝对 Tick | absolute tick | 统一小写 tick |
| 相对坐标 | relative coordinate | |
| 绝对坐标 | absolute coordinate | |
| 坐标系 | coordinate system | |
| 小节 | measure / bar | ⚠️ **见下方「小节 vs bar 规则」** |
| 拍 | beat | |
| 拍号 | time signature | |
| 小节:拍 / bar:beat | bar:beat | 代码与接口名用 `bar:beat` 原样 |
| 变拍号 / 变拍子 | variable time signature | 首次出现加注 mid-piece meter change |
| 单拍子 | simple meter | |
| 复拍子 | compound meter | |
| **混合拍子** | **irregular meter** | ⚠️ **不要译成 mixed meter** —— 论文专门澄清过这个概念 |
| 分段线性 | piecewise linear | |
| 分段求和 | piecewise summation | |
| 闭式 | closed form | |
| 通式 | general form | |
| 原式 | the original formula | 首次出现可作 the naive formula，之后统一 the original formula |
| 退化定理 | degeneracy theorem | |
| 退化性质 | degenerate property | |
| 退化等价 | degenerate equivalence | |
| 定义域扩充 | domain extension | |
| 段 / 段表 | segment / segment table | |
| 累计边界 | cumulative boundary | 符号记作 S_s |
| 双向映射 | bidirectional mapping | |
| 反向映射 | reverse mapping | |
| 正向映射 | forward mapping | |
| 分片线性 | piecewise linear | 与「分段线性」同义，统一用 piecewise linear |
| 严格单调 | strictly monotonic | |
| 双射 | bijection | |

---

## 一·补、小节一律译 bar（**终版规则，2026-10-13**）

`小节` 有 `bar` 和 `measure` 两个都能用的英文词。**本仓库全篇统一用 `bar`。**

**理由不是偏好，是符号系统决定的** —— 本仓库的记号本身就建立在 bar 上：

```
BPI   = Beats Per Bar        ← 论文自己的符号
barLen                       ← 论文自己的符号
bar:beat                     ← 接口名
from_bar / to_bar            ← 代码接口
```

用 `measure` 会立刻和 `BPI`、`barLen` 割裂，读者要在两套词之间来回翻译。

| 场景 | 用词 |
|---|---|
| 全部文档（工程 + 论文 + README） | **bar** |
| 代码、接口名、参数名 | **bar**（`bar:beat`、`{ bar = 5, beat = 1 }` 原样） |
| 直接引用他人原文时 | 保留原文用词，可加 `\term{measure}` 并括注 |

> **修订记录：**
> - 初版只写「推荐 measure」，与已完成的 `engineering/README.en.md`（全篇 bar）冲突。
> - 二版按文档类型分工（工程 bar / 论文 measure）。
> - **三版（现行）：全部用 bar。** 论文二翻译时发现 `BPI`（Beats Per Bar）、`barLen`、
>   `from_bar`/`to_bar` 都是 bar —— 论文里用 measure 才是真的割裂。此前二版规则作废。
> - **已完成的 `engineering/README.en.md`、`README.en.md` 不需要任何回改。**

---

## 二、事件与技法

| 中文 | English | 备注 |
|---|---|---|
| 事件判据 | event criterion | |
| 事件坐标化 | event coordinatization | 章节标题可用 The Coordinate of Events |
| 空事件 | empty event | |
| 未定义区间 | undefined interval | |
| 音符起始 | note onset | |
| 连奏 | legato | |
| 断奏 | staccato | |
| 休止 | rest | |
| 休止结束 | rest end / end of rest | |
| 纵向值 | vertical value | 指音高轴的取值；首次出现加注 (the pitch value) |
| 事件链递推 | event-chain recursion | |
| 全量扫描算法 | full-scan algorithm | |
| 大跳 | large leap | |
| 二维联动 | two-dimensional coupling | |
| 声部分离 | voice separation | |
| 旋律线追踪 | melody line tracking | |
| 音区 | register | |
| 等距排除法 | equidistance exclusion method | |
| 虚拟桥 | virtual bridge | |
| 连线法 | linking method | |
| 递归细分 | recursive subdivision | |
| 音区粗分 | coarse register partition | |

## 三、结构与语义

| 中文 | English | 备注 |
|---|---|---|
| 结构层 | structural layer | |
| 生成层 | generative layer | |
| 过滤层 | filtering layer | |
| 三条公理 | three axioms | |
| 时间守恒 | temporal conservation | |
| 递归划分 | recursive division | |
| 动机 | motif | |
| 几何变换 | geometric transformation | |
| 闭环 | closed loop | |
| 结构边界对齐 | structural boundary alignment | |
| 算例 | worked example | |
| 语义层 | semantic layer | |
| 双坐标系对照 | dual-coordinate-system comparison | |
| 映射引擎 | mapping engine | |
| 语义指令 | semantic instruction | |
| 可执行指令 | executable instruction | |

## 四、精度与适用域

| 中文 | English | 备注 |
|---|---|---|
| 精度分析 | precision analysis | |
| 取整误差 | rounding error | |
| 适用域 | applicability domain | |
| 失效机理 / 失效边界 | failure mechanism / failure boundary | |
| 拍号变化密度 | time-signature change density | |
| 参数复杂度 | parameter complexity | |
| 杠杆 | leverage | 「公式的杠杆归零」→ the formula's leverage drops to zero |
| 范式切换 | paradigm shift | |
| 拍号事件表 | time-signature event table | |
| 二分查找 | binary search | |
| 硬前提 / 硬边界 | hard precondition / hard boundary | |
| 计算器，不是审计员 | a calculator, not an auditor | 固定译法，全篇一致 |

## 五、工程与实现

| 中文 | English | 备注 |
|---|---|---|
| 宿主软件 / 宿主 | DAW / host software | 首次出现用 DAW (digital audio workstation) |
| 数字音频工作站 | digital audio workstation (DAW) | |
| 符号音乐 | symbolic music | |
| 音乐信息检索 | Music Information Retrieval (MIR) | |
| 记号 | notation | |
| 乐谱 | score | |
| 谱面 | the score itself | 「参数量趋近谱面本身」→ parameter count approaches that of the score itself |
| 人机协作 | human–AI collaboration | 用 en dash |
| 生成模型 | generative model | |
| 时间签名映射表 | time signature map | |
| 区间查找 | interval lookup | |
| 计数约定 | counting convention | |
| 先有技术 | prior art | |
| 显式化 | making explicit / explicitization | 论文语境取 "making explicit" |
| 闭环验证 | closed-loop verification | |
| 交叉验证 | cross-validation | |
| 跨实现验证 | cross-implementation validation | |

## 六、教学与教育

| 中文 | English | 备注 |
|---|---|---|
| 教学链路 | teaching pipeline | |
| 苏格拉底产婆术 | Socratic method | |
| 脚手架理论 | scaffolding | |
| 认知学徒制 | cognitive apprenticeship | |
| 基于问题的学习 | problem-based learning (PBL) | |
| 做中学 | learning by doing | |
| 生成学习理论 | generative learning theory | |
| 引导文教学法 | guided-text method | |
| 九层框架 | nine-layer framework | |
| 考评体系 | assessment system | |
| 主观逻辑权重 | weight of subjective judgement | |

## 七、LaTeX 环境名对照

论文正文里用中文环境名，英文版 `.tex` 必须改用右列。

| 中文（`musepaper.sty`） | English（`musepaper-en.sty`） |
|---|---|
| `\begin{定理}` | `\begin{theorem}` |
| `\begin{引理}` | `\begin{lemma}` |
| `\begin{推论}` | `\begin{corollary}` |
| `\begin{命题}` | `\begin{proposition}` |
| `\begin{定义}` | `\begin{definition}` |
| `\begin{例}` | `\begin{example}` |
| `\begin{注记}` | `\begin{remark}` |
| `\begin{观察}` | `\begin{observation}` |
| `\begin{摘要}` | `\begin{abstracten}` | ⚠️ 实际环境名是 **`abstracten`**（`musepaper-en.sty` 提供，自带 "Abstract." 行内标签），**不是 `abstract`** |
| `\begin{英文摘要}` | （英文版无需，删去或合并） |
| `\begin{示意图}` | `\begin{schematic}` |
| `\关键词{...}` | `\keywords{...}` |
| `\页眉{...}` | `\runninghead{...}` |
| `\作者块{...}{...}` | `\authorblock{...}{...}` |
| `\作者单位{...}` | `\affiliation{...}` |
| `\英文题名{...}` | （英文版即正题名，删去） |
| `\英文作者{...}` | （同上） |
| `\英文单位{...}` | （同上） |
| `\中图分类号` / `\文献标识码` | （中文期刊要件，英文版删去） |
| `\thd{...}` | `\thd{...}`（保留同名，表格表头加粗） |
| `\term{...}` | `\term{...}`（保留同名，斜体术语） |

## 八、格式约定

| 项 | 约定 |
|---|---|
| 引号 | 用 LaTeX 的 `` `` '' ``；不要用直引号 |
| 破折号 | 用 `---`（em dash），前后不加空格 |
| 连接号 | 数字/概念范围用 `--`（en dash），如 `1--4`、`human--AI` |
| 数字 | 正文叙述用英文数词（one, two, twelve），表格与公式保留阿拉伯数字 |
| 章节编号 | 用阿拉伯数字 `1.` `2.`，不用 `一、二、` |
| 时态 | 描述本文工作用一般现在时（"This paper presents"） |
| 人称 | 用 "this paper" / "we"，不用 "I" |
| 术语斜体 | 首次出现的关键术语用 `\term{...}` 标出 |
| 中文专名 | 人名、机构名首次出现给拼音 + 英文意译 |
| **拼写变体** | ⚠️ **全篇用美式英语**（见下） |

### 拼写变体：一律美式（2026-10-13 定）

同一篇英文论文里混用英式与美式拼写会显得没打磨过。本仓库统一用**美式**：

| 美式（用） | 英式（不用） |
|---|---|
| meter | metre |
| behavior | behaviour |
| labeled | labelled |
| organize | organise |
| analyze | analyse |
| centered | centred |
| color | colour |
| modeling | modelling |
| recognize | recognise |

> **典型症状**：论文二初稿里 `metre` 与 `meter` **各出现 13 次** —— 因为一部分章节按
> glossary 用了 `irregular meter`，另一部分顺手写了 `metre change`。
> 已用脚本统一（20 处），并断言 `\label` / `\ref` 集合在替换前后完全一致。
> 脚本做法：先把 `\label{}` / `\ref{}` / `\cite{}` / `\includegraphics{}` 整体抠成占位符，
> 替换完再放回 —— 否则改到 `\label{tab:meter}` 这种名字上，引用就断了。

> 注意 `center` 的统计会被 LaTeX 命令污染（`\begin{center}`、`\centering`），
> 排查时不要按出现的次数下结论，要看具体行。

---

## 九、译者须知

1. **不要改写论证**。翻译不是重写。中文里啰嗦但完整的地方，英文也保持完整；不要为了"更像英文论文"而删减。
2. **不要动数据**。所有数字、公式、表格数值逐字保留。
3. **不要动标签**。`\label{sec:counter}` 这类内部名字原样保留。
4. **遇到本表没有的术语**，先加到本表里，再在文中使用。
5. **`musepaper-en.sty` 提供英文环境**，不要改回中文环境名。

---

## 十、论文一补译词条（Paper I supplement：音乐非量化工作的错位与反思）

> 翻译《论文一_音乐非量化工作的错位与反思/paper.tex》时按 §九.4 的规则**先补后译**的词条。
> 论文一全篇用 **measure**（其正文不出现 `bar:beat`，故不触发 §1 补的例外规则）。

### 10.1 量化理论（判据与结构）

| 中文 | English | 备注 |
|---|---|---|
| 量化 | quantization | 论文一中心词；动词 to quantize |
| 有损压缩 | lossy compression | 量化的本质定义 |
| 离散化 / 符号化 | discretization / symbolization | 「切」与「命名」两件事 |
| 源集合 | source set | |
| 划分 | partition | |
| 桶 | bin | 划分后的单元 |
| 代表符号 | representative symbol | 通常为桶的中心或质心 |
| 质心 | centroid | |
| 差异结构 | structure of difference | 判据一 |
| 拓扑/相邻性 | topology/adjacency | 判据二 |
| 容差 | tolerance | 判据三；「对象×用途×容差」三元关系 |
| 稳定可复现 | stable and reproducible | 判据四 |
| 可量化性 | quantifiability | |
| 天然可量化 | naturally quantifiable | |
| 用途 | purpose | 三元关系中的一项 |
| 错位 | dislocation | 论文一标题与关键词；四种错位见 `tab:cuowei` |
| 定义错位 | definitional dislocation | |
| 美学错位 | aesthetic dislocation | |
| 技术错位 | technical dislocation | |
| 制度错位 | institutional dislocation | |
| 命题层面 | propositional layer | |
| 本体层面 | ontological layer | |
| 方法层面 | methodological layer | |
| 教育与社会层面 | educational and social layer | |
| 分层量化 | layered quantization | |
| 审美层 / 结构层 | aesthetic layer / structural layer | 论文一的分层主张 |

### 10.2 音乐、美学与中国文论

| 中文 | English | 备注 |
|---|---|---|
| 静止 / 运动 | stasis / motion | 论文一「静止与运动」分层 |
| 人为的相对动态 | human-made relative dynamics | 论文一固定译法，全篇一致 |
| 人性化 | humanization | |
| 偏移 / 微差 | deviation / minute difference | |
| 滑音 | portamento | |
| 渐强 | crescendo | |
| 弹性速度 | rubato | |
| 连续性 / 连续统 | continuity / continuum | |
| 无外力干扰 | free of external interference | |
| 思想实验 | thought experiment | |
| 极值 | extreme value | |
| 声无哀乐论 | Sheng Wu Ai Yue Lun (On the Absence of Sorrow and Joy in Sound) | 嵇康；保留拼音并给意译 |
| 嵇康 | Ji Kang | 三国魏 |
| 自律论 / 他律论 | autonomy / heteronomy | 汉斯立克 vs 浪漫主义情感美学 |
| 论音乐的美 | On the Musically Beautiful | 汉斯立克 1854 |
| 十二平均律 | twelve-tone equal temperament | 朱载堉 |
| 平均律钢琴曲集 | The Well-Tempered Clavier | 巴赫 BWV 846—869 |
| 减字谱 | jianzipu (abbreviated-character tablature) | |
| 纽姆谱 / 四线谱 / 五线谱 | neumes / four-line staff / five-line staff | |
| 口传心授 | oral transmission and heart-to-heart instruction | 论文一制度根源之一 |
| 灵光乍现 | flash of inspiration | |
| 序列主义 | serialism | |
| 十二音技法 | twelve-tone technique | 勋伯格 |
| 总序列主义 | integral serialism | 布列兹 |
| 四大件 | the ``four pillars'' of composition | 和声、曲式、复调、配器 |
| 和声 | harmony | |
| 复调 | counterpoint | |
| 配器 | orchestration | |
| 粉刷匠 | The Little Painter | 中国儿童歌曲 |

---

## 十一、论文二补译词条（Paper II supplement：绝对时空坐标系）

> 翻译《论文二_绝对时空坐标系/paper.tex》时按 §九.4 的规则**先补后译**的词条。

### 10.1 正文新增术语

| 中文 | English | 备注 |
|---|---|---|
| 小节 | bar | ⚠️ 本表 §1 原推荐 `measure`；论文二须与既有英文摘要、符号 `barLen`、`BPI`（Beats Per Bar）及代码接口 `from_bar`/`to_bar` 一致，故全篇统一用 **bar**，不再混用 measure |
| 事件链 | event chain | |
| 事件绘制 | event drawing | 图 `fig2-event-draw` |
| 引述 | quoted passage | LaTeX 环境 `引述` → 英文版自定义 `quotedpassage` |
| 术语表 | glossary of terms | 附录 B.3 |
| 段起点 | segment start | 符号 $S_s$ |
| 累计量 | cumulative quantity | |
| 锚点 | anchor | |
| 记谱 | notation / notational | |
| 小节线 | barline | |
| 工程 | project | DAW 工程 |
| 工程元数据 | project metadata | |
| 读数 | read-out | |
| 刻度 | scale | 拍号一变，刻度随之改变 → change the signature and the scale changes |
| 时值刻度 | duration scale | |
| 标尺 / 尺子 | ruler | 绝对标尺 → absolute ruler |
| 度量单位 | unit of measurement | |
| 计数起点 | counting origin | |
| 进位 | carry | 进位序列 → carry sequence |
| 位值记数制 | positional numeral system | |
| 时值 | duration | |
| 音高 | pitch | |
| 音程 | interval | |
| 半音 | semitone | |
| 级进 | stepwise motion | |
| 变化音 | chromatic note | |
| 自然音 | diatonic note | |
| 乐句 | phrase | |
| 乐句感 | sense of phrasing | |
| 曲式 | musical form | |
| 段落 | section / passage | 视上下文 |
| 直线 | straight line | |
| 折线 | polyline | |
| 斜率 | slope | |
| 反例 | counterexample | |
| 不适定 | ill-posed | |
| 上界 | upper bound | |
| 参数量 | parameter count | |
| 落点 | landing point | |
| 网格 / 标准网格 | grid / standard grid | |
| 拱形 | arch shape | |
| 呼吸感 | sense of breathing | |
| 律动训练 | groove training | |
| 单例观察 | single-case observation | |
| 对照组 | control group | |
| 评分者 | rater | |
| 受控实验 | controlled experiment | |
| 听感评估 | listening evaluation | |
| 监督式微调 | supervised fine-tuning | |
| 语言模型 | language model | |
| 语义封装层 | semantic encapsulation layer | |
| 双向映射引擎 | bidirectional mapping engine | |
| 声部交叉 | voice crossing | |
| 音尾 / 音头 | note offset / note onset | |
| 延留音 | suspension | |
| 四声部合唱（SATB） | four-part choir (SATB) | |
| 无监督聚类 | unsupervised clustering | |
| 等高线切分 | contour slicing | |
| 调性 | tonality | |
| 音域 | range | 乐器音域 → instrument range |
| 和弦模板 | chord template | |
| 板式变化 | ban-shi (metrical-pattern) change | 戏曲术语，保留拼音 |
| 散板 | free metre (sanban) | 戏曲术语，保留拼音 |
| 密集变拍 | dense metre change | |
| 被训侧 / 反馈方 | the trainee / the feedback provider | 教学法语境 |
| 教学侧 / 模型侧 | teacher side / model side | |
| 干预方式 | intervention mode | |
| 引导式提问 | guided questioning | |
| 脚手架撤除 | withdrawal of scaffolding | |
| 示范 / 模仿 | demonstration / imitation | |

### 10.2 音符时值与音程

| 中文 | English |
|---|---|
| 全音符 | whole note |
| 二分音符 | half note |
| 四分音符 | quarter note |
| 附点四分音符 | dotted quarter note |
| 八分音符 | eighth note |
| 十六分音符 | sixteenth note |
| 纯四度 | perfect fourth |
| 增四度 | augmented fourth |
| 减五度 | diminished fifth |
| 纯五度 | perfect fifth |
| 小六度 | minor sixth |
| 八度 | octave |

### 10.3 动机发展技法（几何变换）

| 中文 | English | 数学名 |
|---|---|---|
| 重复 | repetition | temporal translation |
| 倒影 | inversion | vertical reflection |
| 逆行 | retrograde | sequence reversal |
| 扩大 | augmentation | temporal scaling, $\lambda>1$ |
| 缩小 | diminution | temporal scaling, $0<\lambda<1$ |

### 10.4 LaTeX 环境名补充（接 §七）

| 中文（`musepaper.sty`） | English（论文二英文版） | 说明 |
|---|---|---|
| `\begin{引述}` | `\begin{quotedpassage}` | 英文版在导言区自定义（`quote` 基座，无框线） |
| `\begin{museCode}` | `\begin{museCode}` | 同名保留；英文版导言区用 `listings` 自定义 |
| 中文注释 / 代码中的中文字符串 | 译为英文 | 英文版不含 CJK 字体；代码注释与字符串必须英文化，标识符、函数名、数字一律不动 |
