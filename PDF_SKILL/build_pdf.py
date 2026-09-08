#!/usr/bin/env python3
"""Build a B5 Chinese book PDF from an already assembled master Markdown.

Normal use: edit only the USER SETTINGS block below, then run:
    python build_pdf.py

Pipeline:
    Markdown -> Pandoc/Lua -> LaTeX -> XeLaTeX x3 -> XDV -> xdvipdfmx -> PDF

Required commands in PATH: pandoc, xelatex, xdvipdfmx.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


# ============================ USER SETTINGS ============================
# Paths are relative to the directory from which this script is run
# (normally the book project directory containing book_master.md/assets/).
INPUT_MD = "book_master.md"
OUTPUT_PDF = ""  # blank -> same stem as INPUT_MD with .pdf

TITLE = ""        # recommended: Chinese book title
SHORT_TITLE = ""  # blank -> TITLE; used in running heads
AUTHORS = []       # e.g. ["P. K. Edwards"]
LANG = "zh-CN"
EDITION_NOTE = "中文翻译稿"

TOC_TITLE = "目录"
TOC_DEPTH = 1
NOTES_TITLE = "注释"
UNGROUPED_NOTES_TITLE = "其他"

# Leave blank to auto-detect the first numbered chapter as main matter.
# Set an exact H1 only for unusual books.
MAINMATTER_START = ""

ASSETS_DIR = "assets"
# ======================================================================


SKILL_DIR = Path(__file__).resolve().parent
TEMPLATE_FILE = SKILL_DIR / "template.tex"
PREAMBLE_FILE = SKILL_DIR / "preamble.tex"
LUA_FILTER = SKILL_DIR / "endnotes.lua"


def q(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def write_metadata(path: Path, title: str, short_title: str, authors: list[str]) -> None:
    lines = [
        f"title: {q(title)}",
        f"short-title: {q(short_title or title)}",
        f"lang: {q(LANG)}",
        f"edition-note: {q(EDITION_NOTE)}",
        f"toc-title: {q(TOC_TITLE)}",
        f"toc-depth: {TOC_DEPTH}",
        f"notes-title: {q(NOTES_TITLE)}",
        f"ungrouped-notes-title: {q(UNGROUPED_NOTES_TITLE)}",
        f"preamble-path: {q(PREAMBLE_FILE.resolve().as_posix())}",
    ]
    if MAINMATTER_START:
        lines.append(f"mainmatter-start: {q(MAINMATTER_START)}")
    if authors:
        lines.append("author:")
        lines.extend(f"  - {q(a)}" for a in authors)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_command(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"Required command not found in PATH: {name}")


_NOTES_HEADING_RE = re.compile(r"(?m)^#\s+注释\s*$")
_NAMED_FOOTNOTE_REF_RE = re.compile(r"(?<!\\)\[\^([^\]\r\n]+)\]")


def annotate_named_footnote_refs(source: Path, dest: Path) -> int:
    """Write a temporary Markdown copy with invisible note-reference annotations.

    Pandoc resolves named footnotes into native Note nodes but discards the source
    footnote ID. We preserve that identity without touching book_master.md by
    inserting an empty Span immediately before each正文 reference. endnotes.lua
    consumes the Span and can therefore produce exact backlinks, including multiple
    return targets if a source footnote is cited more than once.
    """
    text = source.read_text(encoding="utf-8")
    m = _NOTES_HEADING_RE.search(text)
    if m:
        body, notes = text[:m.start()], text[m.start():]
    else:
        body, notes = text, ""

    counts: dict[str, int] = {}

    def repl(match: re.Match[str]) -> str:
        note_id = match.group(1)
        counts[note_id] = counts.get(note_id, 0) + 1
        stable_key = hashlib.sha1(note_id.encode("utf-8")).hexdigest()
        annotation = (
            '[]{.pdf-noteref '
            f'data-note-key="{stable_key}" '
            f'data-note-occ="{counts[note_id]}"}}'
        )
        return annotation + match.group(0)

    annotated = _NAMED_FOOTNOTE_REF_RE.sub(repl, body) + notes
    dest.write_text(annotated, encoding="utf-8")
    return sum(counts.values())


def run(cmd: list[str], cwd: Path, label: str) -> None:
    print(label)
    subprocess.run(cmd, cwd=cwd, check=True)


def _matching_brace(text: str, open_index: int) -> int:
    if open_index >= len(text) or text[open_index] != "{":
        raise ValueError("Expected opening brace")
    depth = 0
    i = open_index
    while i < len(text):
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError("Unbalanced braces in generated LaTeX")


def add_short_titles_for_linked_headings(tex_path: Path) -> int:
    """Keep note anchors out of TOC/running heads for footnoted headings.

    Pandoc places RawInline note markers inside a heading's long title. Without an
    explicit LaTeX short title, that marker is also written to the .toc / marks and
    can define the same PDF destination a second time. Pandoc already emits a plain
    second argument in ``\\texorpdfstring{long}{plain}``; reuse that plain title as
    the optional short title. Visible heading text is unchanged.
    """
    text = tex_path.read_text(encoding="utf-8")
    pat = re.compile(r"\\(chapter|section|subsection|subsubsection)\{")
    edits: list[tuple[int, int, str]] = []

    for m in pat.finditer(text):
        open_index = m.end() - 1
        try:
            close_index = _matching_brace(text, open_index)
        except ValueError:
            continue
        arg = text[open_index + 1:close_index]
        if "\\booknoteref" not in arg or "\\texorpdfstring" not in arg:
            continue

        t = arg.find("\\texorpdfstring")
        first_open = arg.find("{", t + len("\\texorpdfstring"))
        if first_open < 0:
            continue
        try:
            first_close = _matching_brace(arg, first_open)
        except ValueError:
            continue
        j = first_close + 1
        while j < len(arg) and arg[j].isspace():
            j += 1
        if j >= len(arg) or arg[j] != "{":
            continue
        try:
            second_close = _matching_brace(arg, j)
        except ValueError:
            continue
        short = arg[j + 1:second_close]
        if not short:
            continue

        cmd = m.group(1)
        replacement = f"\\{cmd}[{short}]{{{arg}}}"
        edits.append((m.start(), close_index + 1, replacement))

    if not edits:
        return 0

    for start, end, replacement in reversed(edits):
        text = text[:start] + replacement + text[end:]
    tex_path.write_text(text, encoding="utf-8")
    return len(edits)


def strip_redundant_terminal_list_breaks(tex_path: Path) -> int:
    """Remove redundant hard line breaks at the ends of list items.

    A Markdown list item that ends with two trailing spaces can reach Pandoc as
    ``\\`` immediately before the next ``\\item``.  At the end of a list item
    that hard break carries no semantic information, but in book typography it
    adds roughly one extra baseline of vertical white space.  This is especially
    noticeable in front-matter directories such as a List of Illustrations.

    Normalize only breaks that occur immediately before a new item or the end of
    an enumerate/itemize environment.  Explicit line breaks *within* an item are
    left untouched, and the authoritative Markdown is never modified.
    """
    text = tex_path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"\\\\[ \t]*\n(?=[ \t]*\\(?:item\b|end\{(?:enumerate|itemize)\}))"
    )
    text, count = pattern.subn("\n", text)
    if count:
        tex_path.write_text(text, encoding="utf-8")
    return count


def print_latex_error(log_path: Path) -> None:
    if not log_path.exists():
        return
    text = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    patterns = [
        re.compile(r"Undefined control sequence"),
        re.compile(r"LaTeX Error"),
        re.compile(r"Package .* Error"),
        re.compile(r"Missing .* inserted"),
        re.compile(r"Extra alignment tab"),
        re.compile(r"Emergency stop"),
        re.compile(r"Fatal error"),
        re.compile(r"^!"),
    ]
    idx = None
    for i, line in enumerate(text):
        if any(p.search(line) for p in patterns):
            idx = i
            break
    if idx is None:
        start = max(0, len(text) - 50)
    else:
        start = max(0, idx - 5)
    print("\n=== XeLaTeX log excerpt ===", file=sys.stderr)
    for line in text[start:start + 30]:
        print(line, file=sys.stderr)
    print(f"Full log: {log_path}", file=sys.stderr)


def build(args: argparse.Namespace) -> Path:
    project_dir = Path.cwd()
    input_md = (project_dir / args.input).resolve()
    if not input_md.exists():
        raise FileNotFoundError(f"Input Markdown not found: {input_md}")

    output = Path(args.output) if args.output else Path(input_md.stem + ".pdf")
    if not output.is_absolute():
        output = (project_dir / output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    for command in ("pandoc", "xelatex", "xdvipdfmx"):
        ensure_command(command)
    for f in (TEMPLATE_FILE, PREAMBLE_FILE, LUA_FILTER):
        if not f.exists():
            raise FileNotFoundError(f"Missing skill file: {f}")

    title = args.title or TITLE or input_md.stem
    authors = args.author if args.author else list(AUTHORS)
    short_title = SHORT_TITLE or title

    build_dir = SKILL_DIR / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)

    metadata = build_dir / "metadata.yaml"
    tex_file = build_dir / "book.tex"
    annotated_md = build_dir / "book_annotated.md"
    write_metadata(metadata, title, short_title, authors)
    annotated_refs = annotate_named_footnote_refs(input_md, annotated_md)

    resource_paths = [str(project_dir)]
    assets = project_dir / ASSETS_DIR
    if assets.exists():
        resource_paths.append(str(assets.resolve()))

    pandoc_cmd = [
        "pandoc",
        str(annotated_md),
        "--from=markdown+smart",
        "--to=latex",
        "--standalone",
        "--top-level-division=chapter",
        f"--template={TEMPLATE_FILE}",
        f"--metadata-file={metadata}",
        f"--lua-filter={LUA_FILTER}",
        f"--resource-path={os.pathsep.join(resource_paths)}",
        "-o",
        str(tex_file),
    ]

    print("=== PDF build ===")
    print(f"Input : {input_md}")
    print(f"Output: {output}")
    print(f"Title : {title}")
    print(f"Notes : {annotated_refs} annotated正文 references")
    run(pandoc_cmd, project_dir, "[1/5] Pandoc -> LaTeX")
    linked_headings = add_short_titles_for_linked_headings(tex_file)
    if linked_headings:
        print(f"Headings: {linked_headings} footnoted heading(s) normalized for TOC/marks")
    stripped_breaks = strip_redundant_terminal_list_breaks(tex_file)
    if stripped_breaks:
        print(f"Lists: {stripped_breaks} redundant terminal hard break(s) removed")

    xelatex_cmd = [
        "xelatex",
        "-no-pdf",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        f"-output-directory={build_dir}",
        str(tex_file),
    ]

    log_path = build_dir / "book.log"
    try:
        for i in range(1, 4):
            run(xelatex_cmd, project_dir, f"[{i + 1}/5] XeLaTeX pass {i}/3")
    except subprocess.CalledProcessError:
        print_latex_error(log_path)
        raise

    xdv = build_dir / "book.xdv"
    built_pdf = build_dir / "book.pdf"
    if not xdv.exists():
        raise RuntimeError(f"XDV was not created: {xdv}")

    run(["xdvipdfmx", "-E", "-o", str(built_pdf), str(xdv)], project_dir, "[5/5] XDV -> PDF")
    if not built_pdf.exists() or built_pdf.stat().st_size == 0:
        raise RuntimeError("xdvipdfmx returned successfully but no PDF was created.")

    shutil.copy2(built_pdf, output)
    print(f"Done: {output} ({output.stat().st_size / 1024 / 1024:.2f} MB)")
    return output


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build PDF from assembled Markdown.")
    p.add_argument("--input", default=INPUT_MD, help="Input master Markdown")
    p.add_argument("--output", default=OUTPUT_PDF, help="Output PDF path")
    p.add_argument("--title", default="", help="Override TITLE")
    p.add_argument("--author", action="append", default=[], help="Author; repeat as needed")
    return p.parse_args()


if __name__ == "__main__":
    try:
        build(parse_args())
    except subprocess.CalledProcessError as e:
        print(f"Build failed: command exited with code {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode or 1)
    except Exception as e:
        print(f"Build failed: {e}", file=sys.stderr)
        sys.exit(1)
