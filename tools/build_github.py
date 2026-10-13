#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_github.py —— 把 LaTeX 论文转成 GitHub 原生 Markdown

【为什么不能直接用 pandoc】
pandoc 的 gfm 输出对 GitHub 有几处不兼容，必须后处理：

  1. \\includegraphics  →  <embed src="x.pdf">      GitHub 不渲染 <embed>
  2. \\begin{equation}  →  ```math 围栏内仍保留 \\begin{equation}  KaTeX 报错
  3. \\(x\\)             →  <span class="math inline">\\(x\\)</span>  GitHub 只认 $x$
  4. 交叉引用           →  <a data-reference="eq:tpb">[eq:tpb]</a>   应显示编号
  5. 图表题注           →  跑到对象**后面**，且丢了「图 N / 表 N」编号
  6. 自定义环境         →  <div class="定义">…</div>               丢失编号

本脚本按论文自身的排版约定做定向后处理，并把图片导出为 PNG（GitHub 只渲染
位图，PDF 放在 ![]() 里不会显示）。

用法：
    python tools/build_github.py <论文目录> <输出目录>
"""
import os
import re
import subprocess
import sys

# ---------------------------------------------------------------------------
# 一、从 LaTeX 源抽取题名块
# ---------------------------------------------------------------------------
def grab(tex, pat, default=""):
    m = re.search(pat, tex, re.S)
    return m.group(1).strip() if m else default


def extract_front(tex):
    f = {}
    f["title"] = grab(tex, r"\\页眉\{(.*?)\}")
    f["author"] = grab(tex, r"\{\\normalsize\s*(.*?)\\par\}")
    f["unit"] = grab(tex, r"\{\\small（(.*?)）\\par\}")
    f["email"] = grab(tex, r"通信邮箱：(.*?)\\par")
    f["abstract"] = grab(tex, r"\\begin\{摘要\}(.*?)\\end\{摘要\}")
    f["keywords"] = grab(tex, r"\\关键词\{(.*?)\}\s*\n")
    f["clc"] = grab(tex, r"\\中图分类号\{(.*?)\}")
    f["doccode"] = grab(tex, r"\\文献标识码\{(.*?)\}")
    f["entitle"] = grab(tex, r"\\英文题名\{(.*?)\}")
    f["enauthor"] = grab(tex, r"\\英文作者\{(.*?)\}")
    f["enunit"] = grab(tex, r"\\英文单位\{(.*?)\}")
    f["enabstract"] = grab(tex, r"\\begin\{英文摘要\}(.*?)\\end\{英文摘要\}")
    f["enkeywords"] = grab(tex, r"\\英文关键词\{(.*?)\}\s*\n")
    return f


# ---------------------------------------------------------------------------
# 二、后处理 pandoc 的 gfm 输出
# ---------------------------------------------------------------------------
DIV_LABEL = {
    "定义": "定义", "观察": "观察", "注记": "注记", "定理": "定理",
    "引理": "引理", "推论": "推论", "命题": "命题", "例": "例",
    "证明": "证明", "引述": "引述",
}

#  Div 标签后面那个标点。中文用全角句点，英文用半角句点 + 空格。
#  单独抽出来是为了让 build_github_en.py 能复用同一条流水线，
#  否则英文版会渲染成 "**theorem．**"（小写 + 中文标点）。
DIV_PUNCT = "．"

#  图表题注前缀。同样是为了让英文构建器复用本流水线：
#  否则英文 README 里的表题会印成 "**表 1** ..."。
FIG_LABEL = "图"
TAB_LABEL = "表"


def preprocess_latex(t):
    """在交给 pandoc 之前，把「pandoc 不认得 / 会转出畸形结果」的写法规范化。

    这样做的收益大于事后打补丁：
      · \\begin{equation}  pandoc 会输出 ```math 围栏，且开合处理不一致，
        本文件里就因此产生过一个落单的 ``` 围栏（会毁掉其后全部渲染）；
        改成 \\[ ... \\] 后 pandoc 输出标准 display math。
      · museCode / 示意图 是本项目自定义环境，pandoc 不认识，
        换成 lstlisting / verbatim 后即可正常转为代码块。
    """
    #  公式环境 → \[ ... \]
    #  ⚠️ \label 只能在**公式环境内部**剥离！图与表的 \label 是 pandoc 生成
    #     锚点（<figure id=…> / {#tab:…}）的依据，一旦被全局删掉，
    #     所有图表编号与交叉引用都会失效。
    def eq_repl(m):
        inner = re.sub(r"\\label\{[^}]*\}", "", m.group(2))
        inner = re.sub(r"\\tag\{[^}]*\}", "", inner)
        return "\\[\n" + inner.strip() + "\n\\]"
    t = re.sub(r"\\begin\{(equation\*?|align\*?|gather\*?|eqnarray\*?)\}(.*?)"
               r"\\end\{\1\}", eq_repl, t, flags=re.S)
    #  自定义代码环境 → verbatim，并注入哨兵行
    #  为什么用哨兵而不是"事后识别 4 空格缩进"：pandoc 也会把**列表续行**等
    #  散文缩进 4 格，纯靠缩进识别会把大量正文误封成代码块（实测 20 个块里
    #  只有 2 个是真代码）。哨兵由源文件注入，精确无误。
    t = re.sub(r"\\begin\{museCode\}(?:\[language=(\w+)\])?",
               lambda m: "\\begin{verbatim}\n@@MUSECODE:" + (m.group(1) or "") + "@@", t)
    t = t.replace(r"\end{museCode}", "@@ENDCODE@@\n\\end{verbatim}")
    t = t.replace(r"\begin{示意图}", "\\begin{verbatim}\n@@MUSECODE:@@")
    t = t.replace(r"\end{示意图}", "@@ENDCODE@@\n\\end{verbatim}")
    return t


def sentinel_to_fence(md):
    """把哨兵包起来的区域转成围栏代码块，并剥掉 pandoc 加的 4 格缩进。"""
    lines = md.split("\n")
    out, i = [], 0
    while i < len(lines):
        m = re.match(r"^\s*@@MUSECODE:(\w*)@@\s*$", lines[i])
        if not m:
            out.append(lines[i]); i += 1
            continue
        lang = m.group(1)
        i += 1
        body = []
        while i < len(lines) and not re.match(r"^\s*@@ENDCODE@@\s*$", lines[i]):
            body.append(re.sub(r"^    ", "", lines[i]))
            i += 1
        i += 1                                   # 跳过 @@ENDCODE@@
        while body and not body[-1].strip():
            body.pop()
        out.append("```" + lang)
        out.extend(body)
        out.append("```")
    return "\n".join(out)


def fence_indented_code(md):
    """把 4 空格缩进式代码块 → 围栏式代码块。

    pandoc 对 lstlisting / verbatim 默认输出缩进块：GitHub 能渲染，但
    缩进块一旦被任何后续处理打乱缩进就会静默失效；围栏块更稳妥，且能加语言标签
    以获得语法高亮。正文散文没有字面缩进（缩进由 LaTeX 的 \\parindent 产生），
    故此处不会误伤。
    """
    lines = md.split("\n")
    out, i = [], 0
    while i < len(lines):
        if lines[i].startswith("    ") and lines[i].strip():
            j, block = i, []
            while j < len(lines):
                if lines[j].startswith("    "):
                    block.append(lines[j]); j += 1
                elif not lines[j].strip() and j + 1 < len(lines) and lines[j + 1].startswith("    "):
                    block.append(lines[j]); j += 1
                else:
                    break
            while block and not block[-1].strip():
                block.pop()
            body = [l[4:] if l.startswith("    ") else l for l in block]
            joined = "\n".join(body)
            lang = "python" if re.search(r"\b(def |import |class |return )", joined) else ""
            out.append("```" + lang)
            out.extend(body)
            out.append("```")
            i = j
            continue
        out.append(lines[i]); i += 1
    return "\n".join(out)


def inline_md(s):
    """把题名块里的行内 LaTeX 转成 Markdown。

    ⚠️ 题名块（摘要 / 关键词 / 英文摘要…）是用正则从源码里抽出来的，
    并不经过正文那条 pandoc 管线。若不单独转换，\\textbf{}、\\texttt{}、\\\\
    这些标记会**原样漏进 Markdown**，在 GitHub 上显示成裸 LaTeX。
    """
    if not s or not s.strip():
        return ""
    r = subprocess.run(["pandoc", "-f", "latex", "-t", "gfm+attributes", "--mathjax"],
                       input=s, capture_output=True, text=True, errors="replace")
    out = r.stdout
    out = re.sub(r"\$`([^`\n]+?)`\$", lambda m: "$" + m.group(1) + "$", out)
    out = re.sub(r"\\\((.*?)\\\)", lambda m: "$" + m.group(1).strip() + "$",
                 out, flags=re.S)
    out = re.sub(r"\\\[(.*?)\\\]", lambda m: "$$\n" + m.group(1).strip() + "\n$$",
                 out, flags=re.S)
    out = re.sub(r"[ \t]+\n", "\n", out)
    return out.strip()


def postprocess(md):
    # --- 1. ```math 围栏：剥掉 \begin{equation} / \label，改成 $$ ---
    def fix_math(m):
        body = m.group(1)
        body = re.sub(r"\\begin\{(equation\*?|align\*?|gather\*?|eqnarray\*?)\}", "", body)
        body = re.sub(r"\\end\{(equation\*?|align\*?|gather\*?|eqnarray\*?)\}", "", body)
        body = re.sub(r"\\label\{[^}]*\}", "", body)
        body = re.sub(r"\\tag\{[^}]*\}", "", body)
        lines = [l.rstrip() for l in body.strip().split("\n")]
        return "$$\n" + "\n".join(lines) + "\n$$"

    md = re.sub(r"```\s*math\s*\n(.*?)\n```", fix_math, md, flags=re.S)

    # --- 2. \[ ... \] → $$ ... $$ ---
    md = re.sub(r"\\\[\s*(.*?)\s*\\\]", lambda m: "$$\n" + m.group(1).strip() + "\n$$",
                md, flags=re.S)

    # --- 3. 行内公式包装 → $...$ ---
    md = re.sub(r'<span class="math inline">\\\((.*?)\\\)</span>',
                lambda m: "$" + m.group(1).strip() + "$", md, flags=re.S)
    md = re.sub(r'<span class="math display">\\\[(.*?)\\\]</span>',
                lambda m: "$$\n" + m.group(1).strip() + "\n$$", md, flags=re.S)
    # pandoc 的 $`x`$ → $x$（GitHub 两种都认，去反引号更易读）
    md = re.sub(r"\$`([^`\n]+?)`\$", lambda m: "$" + m.group(1) + "$", md)

    # --- 4. 自定义环境 Div → 加粗标签段落 ---
    def fix_div(m):
        env, inner = m.group(1), m.group(2).strip()
        label = DIV_LABEL.get(env, env)
        return f"\n**{label}{DIV_PUNCT}** {inner}\n"
    md = re.sub(r'<div class="([^"]+)">\s*(.*?)\s*</div>', fix_div, md, flags=re.S)

    # --- 5. <figure> → Markdown 图片（编号在下一步统一处理） ---
    #  注意 pandoc 对矢量图输出 <embed>、对位图输出 <img>，两者都要接；
    #  多子图（minipage）会在同一 <figure> 内出现多个 <img> 与 <span> 子题注。
    def fix_figure(m):
        anchor = m.group(1)
        inner = m.group(2)

        # 先把 <figcaption> 摘出去 —— 它内部**也含** <span class="math inline">，
        # 若不摘除会被下面的子题注正则误当成子图标签。
        capm = re.search(r"<figcaption>(.*?)</figcaption>", inner, re.S)
        if capm:
            cap = re.sub(r"<[^>]+>", "", capm.group(1))
            cap = re.sub(r"\s+", " ", cap).strip()
            inner = inner[:capm.start()] + inner[capm.end():]
        else:
            cap = ""

        imgs = re.findall(r'<(?:embed|img)\s[^>]*?src="([^"]+)"', inner)
        subs = [re.sub(r"<[^>]+>", "", s).strip()
                for s in re.findall(r"<span[^>]*>(.*?)</span>", inner, re.S)]
        if not imgs:
            return ""
        short = (cap[:28] + "…") if len(cap) > 28 else cap
        parts = []
        for k, img in enumerate(imgs):
            base = os.path.splitext(os.path.basename(img))[0]
            alt = subs[k] if k < len(subs) and subs[k] else (short or base)
            parts.append(f"![{alt}](figures/{base}.png)")
        # 子图同行并列 → GitHub 会并排渲染
        return (f"\n{{{{FIG:{anchor}}}}}\n\n" + " ".join(parts) + "\n\n"
                f"{{{{FIGCAP:{anchor}}}}}|{cap}\n")
    md = re.sub(r'<figure id="([^"]+)"[^>]*>(.*?)</figure>',
                fix_figure, md, flags=re.S)

    # --- 6. 表格题注：pandoc 放在表后，改为标记，稍后移到表前 ---
    md = re.sub(r"^([^\n|].*?)\s*\{#(tab:[^}]+)\}\s*$",
                lambda m: f"{{{{TABCAP:{m.group(2)}}}}}|{m.group(1).strip()}",
                md, flags=re.M)

    # --- 7. 交叉引用：解析成编号链接 ---
    #  ⚠️ 必须用 `-t gfm+attributes`：默认的 `gfm` 会**丢掉标题锚点**，
    #     于是所有 \ref{sec:…} 都无从解析（实测残留 44 处）。
    #     代价是引用形式变成 Markdown 链接带属性，故这里两种形式都接。
    md = re.sub(
        r'\[\\?\[([^\]]+?)\\?\]\(#([^)]+?)\)\{[^}]*?reference[^}]*?\}',
        lambda m: f"{{{{REF:{m.group(2)}}}}}", md, flags=re.S)
    md = re.sub(
        r'<a href="#([^"]+)" data-reference-type="[^"]*"\s*\n?\s*data-reference="[^"]*">[^<]*</a>',
        lambda m: f"{{{{REF:{m.group(1)}}}}}", md, flags=re.S)
    md = re.sub(
        r'<a href="#([^"]+)" data-reference-type="[^"]*" data-reference="[^"]*">[^<]*</a>',
        lambda m: f"{{{{REF:{m.group(1)}}}}}", md)

    # --- 8. 兜底清理 ---
    #  个别公式块 pandoc 会输出成 `$$ math` 这种畸形开头（围栏没走到正则），
    #  这里做一次无条件清理：凡残留的 LaTeX 数学环境与标签一律剥掉。
    md = re.sub(r"^\s*\$\$\s*math\s*$", "$$", md, flags=re.M)
    md = re.sub(r"\\begin\{(equation\*?|align\*?|gather\*?|eqnarray\*?|split)\}", "", md)
    md = re.sub(r"\\end\{(equation\*?|align\*?|gather\*?|eqnarray\*?|split)\}", "", md)
    md = re.sub(r"\\label\{[^}]*\}", "", md)
    md = re.sub(r"\\tag\{[^}]*\}", "", md)
    #  行内 / 行间数学分隔符统一成 GitHub 认的 $ 与 $$
    md = re.sub(r"\\\((.*?)\\\)", lambda m: "$" + m.group(1).strip() + "$", md, flags=re.S)
    md = re.sub(r"\\\[(.*?)\\\]", lambda m: "$$\n" + m.group(1).strip() + "\n$$", md, flags=re.S)
    #  ``` math 围栏清完后可能留下孤立的 ```，成对删除
    md = re.sub(r"```\s*math\s*\n\s*```", "", md)

    #  围栏配对兜底：若 $$ 块内出现落单的裸 ```，按 $$ 处理；
    #  末尾若仍有落单围栏，直接删掉（宁少一个代码块，也不能让其后全文错乱）。
    lines = md.split("\n")
    inside = False
    for i, l in enumerate(lines):
        s = l.strip()
        if s == "$$":
            inside = not inside
        elif s == "```" and inside:
            lines[i] = "$$"
            inside = False
    md = "\n".join(lines)
    if sum(1 for l in md.split("\n") if l.startswith("```")) % 2:
        md = "\n".join(l for l in md.split("\n") if l.strip() != "```")

    md = sentinel_to_fence(md)

    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


# ---------------------------------------------------------------------------
# 三、编号：按出现顺序给图 / 表 / 式编号，并解析引用
# ---------------------------------------------------------------------------
def number_and_resolve(md, refmap=None):
    counters = {"fig": 0, "tab": 0, "eq": 0}
    if refmap is None:
        refmap = {}

    # ---- 小节编号：pandoc 把 \label 放在标题锚点上，形如 `## 标题 {#subsec:x}` ----
    sec = {"sec": 0, "subsec": 0, "subsubsec": 0}
    for m in re.finditer(r"^(#{1,4})\s+.*?\{#((?:sub)*sec:[^}]+)\}\s*$", md, flags=re.M):
        lvl = len(m.group(1))
        anchor = m.group(2)
        if lvl <= 1:
            sec["sec"] += 1; sec["subsec"] = 0; sec["subsubsec"] = 0
            refmap[anchor] = str(sec["sec"])
        elif lvl == 2:
            sec["subsec"] += 1; sec["subsubsec"] = 0
            refmap[anchor] = f"{sec['sec']}.{sec['subsec']}"
        else:
            sec["subsubsec"] += 1
            refmap[anchor] = f"{sec['sec']}.{sec['subsec']}.{sec['subsubsec']}"
    # 去掉标题行上的锚点标记（GitHub 自动生成锚点，留着会显示在标题里）
    md = re.sub(r"^(#{1,4}\s+.*?)\s*\{#(?:sub)*sec:[^}]+\}\s*$", r"\1", md, flags=re.M)

    # 题注标记（图 / 表）——决定编号
    def take_cap(kind):
        def rep(m):
            counters[kind] += 1
            anchor, cap = m.group(1), m.group(2)
            refmap[anchor] = counters[kind]
            return (anchor, counters[kind], cap)
        return rep

    # 逐个处理 FIGCAP / TABCAP，先建 refmap
    for m in re.finditer(r"\{\{FIGCAP:([^}]+)\}\}\|(.*)", md):
        counters["fig"] += 1
        refmap[m.group(1)] = counters["fig"]
    for m in re.finditer(r"\{\{TABCAP:([^}]+)\}\}\|(.*)", md):
        counters["tab"] += 1
        refmap[m.group(1)] = counters["tab"]
    # 公式：按 \label 在源中的顺序，pandoc 的 $$ 块内已无 label，
    # 改由 REF 首次出现的顺序兜底编号
    for m in re.finditer(r"\{\{REF:(eq:[^}]+)\}\}", md):
        if m.group(1) not in refmap:
            counters["eq"] += 1
            refmap[m.group(1)] = counters["eq"]

    # 替换图片题注
    def figcap(m):
        anchor, cap = m.group(1), m.group(2).strip()
        return f"\n**{FIG_LABEL} {refmap[anchor]}**　{cap}\n"
    md = re.sub(r"\{\{FIGCAP:([^}]+)\}\}\|(.*)", figcap, md)

    # 表格题注：从表后移到表前
    lines = md.split("\n")
    out, pending = [], []
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("{{TABCAP:"):
            m = re.match(r"\{\{TABCAP:([^}]+)\}\}\|(.*)", lines[i].strip())
            anchor, cap = m.group(1), m.group(2).strip()
            pending.append((anchor, cap))
            i += 1
            continue
        # 找到该题注对应的表格块，插到它前面
        if pending and lines[i].lstrip().startswith("|"):
            j = i
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                j += 1
            for anchor, cap in pending:
                out.append(f"**{TAB_LABEL} {refmap[anchor]}**　{cap}")
                out.append("")
            pending = []
            out.extend(lines[i:j])
            i = j
            continue
        out.append(lines[i])
        i += 1
    for anchor, cap in pending:
        out.append("")
        out.append(f"**{TAB_LABEL} {refmap[anchor]}**　{cap}")
    md = "\n".join(out)

    # 解析引用
    def ref(m):
        key = m.group(1)
        n = refmap.get(key)
        if n is None:
            return f"〔{key}〕"
        return f"**{n}**"
    md = re.sub(r"\{\{REF:([^}]+)\}\}", ref, md)

    # 删掉遗留的图片占位
    md = re.sub(r"\{\{FIG:[^}]+\}\}\n*", "", md)
    # 确保 $$ 成对（落单的会破坏 GitHub 的 KaTeX 渲染）
    if md.count("$$") % 2:
        md += "\n$$"
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md, refmap


# ---------------------------------------------------------------------------
# 四、参考文献
# ---------------------------------------------------------------------------
def extract_bib(tex):
    m = re.search(r"\\begin\{thebibliography\}\{[^}]*\}(.*?)\\end\{thebibliography\}",
                  tex, re.S)
    if not m:
        return []
    items = re.findall(r"\\bibitem\{[^}]*\}\s*(.*?)(?=\\bibitem|$)", m.group(1), re.S)
    out = []
    for it in items:
        t = re.sub(r"\s+", " ", it).strip()
        t = t.rstrip(".")
        out.append(t)
    return out


# ---------------------------------------------------------------------------
# 五、主流程
# ---------------------------------------------------------------------------
def build(paper_dir, out_dir, ordinal):
    tex_path = None
    for name in ("paper.tex", "main.tex"):
        cand = os.path.join(paper_dir, name)
        if os.path.exists(cand):
            tex_path = cand
            break
    if tex_path is None:
        raise SystemExit(f"{paper_dir} 下找不到 paper.tex / main.tex")
    tex = open(tex_path, encoding="utf-8").read()
    front = extract_front(tex)
    #  题名块的每个字段都要单独过一遍 pandoc，否则 LaTeX 标记会漏进 Markdown
    for k in ("title", "author", "unit", "abstract", "keywords", "clc", "doccode",
              "entitle", "enauthor", "enunit", "enabstract", "enkeywords"):
        front[k] = inline_md(front.get(k, ""))
    bib = extract_bib(tex)

    # ---- 正文切片 ----
    #  ⚠️ 两个坑，都踩过：
    #   1) 引用改成页下脚注后，文献表环境不复存在，正文须以 \appendix 为界；
    #   2) 用 str.index/find 找标记时，**文件头注释里的同名字样也会命中**——
    #      本文件头部说明就写过那个环境名，位置在 \section{引言} 之前，
    #      于是 tex[i:j] 里 i > j，静默切出空串（实测输出只剩 3000 字符）。
    #      故这里只认真正位于正文之后的边界，并加下界保护。
    i = tex.index(r"\section{引言") if r"\section{引言" in tex else tex.index(r"\section{")
    cuts = []
    for marker in (r"\appendix", r"\begin{thebibliography}", r"\end{document}"):
        p = tex.find(marker)
        while p != -1:
            if p > i:                      # 必须在正文起点之后才算数
                cuts.append(p)
                break
            p = tex.find(marker, p + 1)
    j = min(cuts) if cuts else len(tex)
    body_tex = preprocess_latex(tex[i:j])

    # ---- 附录切片 ----
    k = -1
    p = tex.find(r"\appendix")
    while p != -1:
        if p > i:
            k = p
            break
        p = tex.find(r"\appendix", p + 1)
    app_tex = ""
    if k >= 0:
        app_tex = tex[k + len(r"\appendix"):]
        app_tex = re.split(r"\\end\{document\}", app_tex)[0]
        if app_tex.strip():
            app_tex = preprocess_latex(app_tex)

    tmp = os.path.join(out_dir, "_body.tex")
    os.makedirs(out_dir, exist_ok=True)
    open(tmp, "w", encoding="utf-8").write(body_tex)

    r = subprocess.run(["pandoc", tmp, "-f", "latex", "-t", "gfm+attributes",
                        "--mathjax",
                        "-o", os.path.join(out_dir, "_body.md")],
                       capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        print("  pandoc 警告:", (r.stderr or "")[:200])
    md = open(os.path.join(out_dir, "_body.md"), encoding="utf-8").read()
    md = postprocess(md)
    md, refmap = number_and_resolve(md)

    # 附录：同样走一遍 pandoc，但**共享同一套 refmap**，
    #  否则附录里引正文的 \ref 会解析不出来。
    app_md = ""
    if app_tex.strip():
        atmp = os.path.join(out_dir, "_app.tex")
        open(atmp, "w", encoding="utf-8").write(app_tex)
        subprocess.run(["pandoc", atmp, "-f", "latex", "-t", "gfm+attributes",
                        "--mathjax", "-o", os.path.join(out_dir, "_app.md")],
                       capture_output=True, text=True, errors="replace")
        app_md = open(os.path.join(out_dir, "_app.md"), encoding="utf-8").read()
        app_md = postprocess(app_md)
        app_md, _ = number_and_resolve(app_md, refmap)
        os.remove(atmp)
        os.remove(os.path.join(out_dir, "_app.md"))

    # 组装
    parts = []
    parts.append(f"# {front['title']}\n")
    parts.append(f"**{front['author']}**　　{front['unit']}\n")
    parts.append(f"通信邮箱：{front['email']}\n")
    parts.append("---\n")
    parts.append(f"**摘　要：**{front['abstract']}\n")
    parts.append(f"**关键词：**{front['keywords']}\n")
    parts.append(f"**中图分类号：**{front['clc']}　　**文献标识码：**{front['doccode']}\n")
    parts.append("---\n")
    parts.append(f"### {front['entitle']}\n")
    parts.append(f"{front['enauthor']}　　{front['enunit']}\n")
    parts.append(f"**Abstract:** {front['enabstract']}\n")
    parts.append(f"**Key words:** {front['enkeywords']}\n")
    parts.append("---\n")
    parts.append(md)
    if bib:
        parts.append("\n---\n\n## 参考文献\n")
        for k, b in enumerate(bib, 1):
            parts.append(f"[{k}] {b}.\n")
    if app_md.strip():
        parts.append("\n---\n\n# 附录\n")
        parts.append(app_md)
    parts.append(f"\n---\n\n> 本文 PDF 版：[`paper.pdf`](paper.pdf)　"
                 f"LaTeX 源码：[`paper.tex`](paper.tex)\n")

    out = "\n".join(parts)
    open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8").write(out)
    os.remove(tmp)
    os.remove(os.path.join(out_dir, "_body.md"))
    print(f"  图 {refmap and sum(1 for k in refmap if k.startswith('fig'))} 个 / "
          f"表 {sum(1 for k in refmap if k.startswith('tab'))} 个 / "
          f"参考文献 {len(bib)} 条")
    print(f"  已写出 {os.path.join(out_dir, 'README.md')}  ({len(out)} 字符)")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "1")
