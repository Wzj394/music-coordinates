#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_github_en.py —— 从英文版 paper.en.tex 生成 README.en.md

为什么需要这个文件
------------------
build_github.py 是中文专用的：它抓的是 `\\页眉{}`、`\\begin{摘要}`、`\\关键词{}`
这些中文宏，输出组装的标签也全是中文。

但那条流水线里**最值钱的部分是语言无关的**——公式归一化、`museCode`/示意图
转代码块、图表自动编号与交叉引用解析（`number_and_resolve`）。重写一遍是浪费，
而且两边一定会漂移。

所以这里**复用整条流水线**，只替换三处语言相关的东西：

    1. 输入文件名    paper.tex      → paper.en.tex
    2. front matter 提取  中文宏名    → 英文宏名（见 extract_front_en）
    3. 输出组装标签  中文标签    → 英文标签
       （另外把 bg.DIV_LABEL / bg.DIV_PUNCT 切成英文，让定理环境渲染成
         `**Theorem.**` 而不是 `**Theorem．**`）

用法
----
    python tools/build_github_en.py <论文目录> <输出目录>

输出 <输出目录>/README.en.md
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_github as bg          # noqa: E402

TEX_NAME = "paper.en.tex"
OUT_NAME = "README.en.md"

# ---------------------------------------------------------------------------
# 1. 把流水线切到英文模式
#    注意：是**原地改** bg 模块的全局量，这样 bg.postprocess 内部读到的就是新值。
#    （bg 的 fix_div 里是 `DIV_LABEL.get(env, env)`，未知环境会兜底成环境名本身；
#      若不覆盖，英文的 \begin{theorem} 会渲染成小写的 "**theorem．**"。）
# ---------------------------------------------------------------------------
bg.DIV_LABEL.clear()
bg.DIV_LABEL.update({
    "theorem":     "Theorem",
    "lemma":       "Lemma",
    "corollary":   "Corollary",
    "proposition": "Proposition",
    "definition":  "Definition",
    "example":     "Example",
    "remark":      "Remark",
    "observation": "Observation",
    "proof":       "Proof",
    "schematic":   "Schematic",
})
bg.DIV_PUNCT = "."

#  图表题注前缀（否则英文 README 的表题会印成 "**表 1**"）
bg.FIG_LABEL = "Figure"
bg.TAB_LABEL = "Table"


def grab(tex, pattern):
    """抓第一个捕获组；抓不到返回空串。"""
    m = re.search(pattern, tex, re.S)
    return m.group(1).strip() if m else ""


def extract_front_en(tex):
    """从英文 .tex 里取题名块。对应中文版的 extract_front()。"""
    f = {}
    #  题名：优先 \runninghead{}（英文版用它），退回 \title{}
    f["title"] = grab(tex, r"\\runninghead\{(.*?)\}") or grab(tex, r"\\title\{(.*?)\}")
    #  作者：题名页里 {\normalsize WANG Zijian\par}
    f["author"] = grab(tex, r"\{\\normalsize\s*(.*?)\\par\}")
    #  单位：题名页里 {\small (MozunStudio, ...)\par}  ← 半角括号
    f["unit"] = grab(tex, r"\{\\small\s*\((.*?)\)\\par\}")
    #  邮箱：题名页里 {\small Correspondence: ...\par}
    f["email"] = grab(tex, r"\{\\small\s*Correspondence:\s*(.*?)\\par\}")
    #  摘要 / 关键词
    f["abstract"] = grab(tex, r"\\begin\{abstracten\}(.*?)\\end\{abstracten\}")
    f["keywords"] = grab(tex, r"\\keywords\{(.*?)\}")
    return f


def build_en(paper_dir, out_dir):
    tex_path = os.path.join(paper_dir, TEX_NAME)
    if not os.path.exists(tex_path):
        raise SystemExit(f"找不到 {tex_path}")

    tex = open(tex_path, encoding="utf-8").read()

    front = extract_front_en(tex)
    for k in ("title", "author", "unit", "email", "abstract", "keywords"):
        front[k] = bg.inline_md(front.get(k, ""))

    # ---- 正文切片 ----
    #  锚在**最后一个** \begin{document} 之后，再找第一个 \section{。
    #  比中文版直接 index(r"\section{") 更稳：文件头注释里出现同名标记也不会误命中。
    doc_start = tex.rindex(r"\begin{document}")
    i = tex.index(r"\section{", doc_start)

    cuts = []
    for marker in (r"\appendix", r"\begin{thebibliography}", r"\end{document}"):
        p = tex.find(marker, doc_start)
        if p != -1 and p > i:
            cuts.append(p)
    j = min(cuts) if cuts else len(tex)
    body_tex = bg.preprocess_latex(tex[i:j])

    # ---- 附录切片（与正文共享 refmap）----
    app_tex = ""
    p = tex.find(r"\appendix", doc_start)
    if p != -1 and p > i:
        app_tex = re.split(r"\\end\{document\}", tex[p + len(r"\appendix"):])[0]
        if app_tex.strip():
            app_tex = bg.preprocess_latex(app_tex)

    os.makedirs(out_dir, exist_ok=True)

    # ---- 正文 → pandoc ----
    tmp = os.path.join(out_dir, "_body.tex")
    open(tmp, "w", encoding="utf-8").write(body_tex)
    r = subprocess.run(["pandoc", tmp, "-f", "latex", "-t", "gfm+attributes",
                        "--mathjax", "-o", os.path.join(out_dir, "_body.md")],
                       capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        print("  pandoc warning:", (r.stderr or "")[:200])
    md = open(os.path.join(out_dir, "_body.md"), encoding="utf-8").read()
    md = bg.postprocess(md)
    md, refmap = bg.number_and_resolve(md)

    # ---- 附录 → pandoc ----
    app_md = ""
    if app_tex.strip():
        atmp = os.path.join(out_dir, "_app.tex")
        open(atmp, "w", encoding="utf-8").write(app_tex)
        subprocess.run(["pandoc", atmp, "-f", "latex", "-t", "gfm+attributes",
                        "--mathjax", "-o", os.path.join(out_dir, "_app.md")],
                       capture_output=True, text=True, errors="replace")
        app_md = open(os.path.join(out_dir, "_app.md"), encoding="utf-8").read()
        app_md = bg.postprocess(app_md)
        app_md, _ = bg.number_and_resolve(app_md, refmap)
        os.remove(atmp)
        os.remove(os.path.join(out_dir, "_app.md"))

    # ---- 组装（英文标签）----
    parts = []
    parts.append(f"# {front['title']}\n")
    parts.append(f"**{front['author']}**　　{front['unit']}\n")
    parts.append(f"Correspondence: {front['email']}\n")
    parts.append("---\n")
    parts.append(f"**Abstract.** {front['abstract']}\n")
    parts.append(f"**Keywords:** {front['keywords']}\n")
    parts.append("---\n")
    parts.append(md)
    if app_md.strip():
        parts.append("\n---\n\n# Appendix\n")
        parts.append(app_md)
    parts.append(f"\n---\n\n> PDF: [`paper.en.pdf`](paper.en.pdf)　"
                 f"LaTeX source: [`paper.en.tex`](paper.en.tex)\n")

    out = "\n".join(parts)
    out_path = os.path.join(out_dir, OUT_NAME)
    open(out_path, "w", encoding="utf-8").write(out)

    os.remove(tmp)
    os.remove(os.path.join(out_dir, "_body.md"))

    nfig = sum(1 for k in refmap if k.startswith("fig"))
    ntab = sum(1 for k in refmap if k.startswith("tab"))
    print(f"  figures {nfig} / tables {ntab}")
    print(f"  wrote {out_path}  ({len(out)} chars)")
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit("usage: build_github_en.py <paper_dir> <out_dir>")
    build_en(sys.argv[1], sys.argv[2])
