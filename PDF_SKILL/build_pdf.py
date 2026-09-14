#!/usr/bin/env python3
"""Build and QA a structured B5 Chinese academic book PDF.

Pipeline:
  authoritative Markdown
    -> temporary normalized_master.md
    -> Pandoc AST validation
    -> Pandoc + book_filter.lua
    -> XeLaTeX (XDV) + xdvipdfmx
    -> structural/link/font/log QA
    -> final PDF + qa_report.txt

The input Markdown is hashed before and after the build and is never modified.
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
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    import fitz  # PyMuPDF
except ImportError as exc:  # pragma: no cover - dependency error path
    raise SystemExit("Missing Python dependency: PyMuPDF (import name: fitz)") from exc


TOOLKIT_DIR = Path(__file__).resolve().parent
FILTER_FILE = TOOLKIT_DIR / "book_filter.lua"
TEMPLATE_FILE = TOOLKIT_DIR / "template.tex"
PREAMBLE_FILE = TOOLKIT_DIR / "preamble.tex"

# ============================ USER SETTINGS ============================
# The authoritative input must be the final <BOOK_STEM>_master.md.
INPUT_MD = "book_master.md"
OUTPUT_PDF = ""  # blank -> same stem as INPUT_MD with .pdf

TITLE = ""
SHORT_TITLE = ""
AUTHORS: list[str] = []
LANG = "zh-CN"
EDITION_NOTE = "中文翻译稿"

TOC_TITLE = "目录"
NOTES_TITLE = "注释"
SOURCE_TOC_TITLES = ("目录", "原书目录")
MAINMATTER_START = ""  # blank -> first Part/Chapter H1; set exact H1 if unusual
SUPPRESS_FIRST_H1 = True  # assembled masters normally begin with the book-title H1
TOC_EXCLUDE_H1: tuple[str, ...] = ()
OPENRIGHT = False  # False is the digital-reading default; True is print-style odd-page opening
ASSETS_DIR = "assets"
MAX_OVERFULL_PT = 8.0
# ======================================================================

CN_NUM = "一二三四五六七八九十百零〇0-9"
CHAPTER_RE = re.compile(rf"^(?:第[{CN_NUM}]+章|[Cc]hapter\s+\d+\b)")
PART_RE = re.compile(rf"^(?:第[{CN_NUM}]+部分|[Pp]art\s+(?:[{CN_NUM}]+|\d+)\b)")
APPENDIX_RE = re.compile(r"^(?:附录|[Aa]ppendix\b)")
ATX_RE = re.compile(r"^( {0,3})(#{1,6})[ \t]+(.+?)\s*$")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
IMAGE_LINE_RE = re.compile(r"^(\s*)!\[([^\]]*)\](\([^\n)]+\)(?:\{[^\n}]*\})?\s*)$")
CAPTION_LINE_RE = re.compile(r"^\s*(?:\*\*(?:图|表)\s*.*\*\*|\*(?:图|表)\s*.*\*)\s*$")
NOTE_REF_RE = re.compile(r"(?<!\\)\[\^([^\]\r\n]+)\](?!:)")
NOTE_DEF_RE = re.compile(r"(?m)^\[\^([^\]\r\n]+)\]:")



class BuildError(RuntimeError):
    """A deterministic build or QA failure."""


@dataclass
class SourceStats:
    refs: list[str]
    defs: list[str]
    duplicate_defs: list[str]
    missing_defs: list[str]
    orphan_defs: list[str]
    multi_ref_ids: dict[str, int]


@dataclass
class NormalizeStats:
    headings_seen: int = 0
    blank_lines_inserted: int = 0
    captions_deduped: int = 0
    refs_annotated: int = 0
    control_sequences_repaired: int = 0


@dataclass
class LogStats:
    fatal_errors: list[str]
    missing_glyphs: list[str]
    duplicate_destinations: list[str]
    overfull: list[tuple[float, str]]
    underfull_count: int


@dataclass
class NoteLinkStats:
    refs: int
    note_entries: int
    backlinks: int
    duplicate_anchors: list[str]
    missing_forward_targets: list[str]
    missing_back_targets: list[str]


@dataclass
class PdfStats:
    pages: int
    outline: list[list[Any]]
    page_labels: list[dict[str, Any]]
    mainmatter_page: int
    mainmatter_label: str
    mainmatter_printed: bool
    font_rows: list[tuple[str, str, bool]]
    image_occurrences: int
    image_xrefs: int
    link_count: int
    warnings: list[str]


@dataclass
class StructuralManifest:
    h1_titles: list[str]
    h1_types: list[str]
    expected_outline: list[tuple[int, str]]
    mainmatter_index: int
    mainmatter_title: str
    notes_present: bool
    warnings: list[str]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_dependencies() -> None:
    missing = [name for name in ("pandoc", "xelatex", "xdvipdfmx") if shutil.which(name) is None]
    if missing:
        raise BuildError(f"Missing required command(s): {', '.join(missing)}")
    for path in (FILTER_FILE, TEMPLATE_FILE, PREAMBLE_FILE):
        if not path.is_file():
            raise BuildError(f"Missing toolkit file: {path}")


def run(cmd: list[str], cwd: Path, label: str, capture: bool = False) -> subprocess.CompletedProcess[bytes]:
    print(label, flush=True)
    try:
        return subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
        )
    except subprocess.CalledProcessError as exc:
        if capture:
            stdout = (exc.stdout or b"").decode("utf-8", errors="replace")
            stderr = (exc.stderr or b"").decode("utf-8", errors="replace")
            if stdout:
                print(stdout[-4000:], file=sys.stderr)
            if stderr:
                print(stderr[-4000:], file=sys.stderr)
        raise BuildError(f"Command failed ({exc.returncode}): {' '.join(cmd)}") from exc


def analyze_source_notes(text: str, notes_title: str) -> SourceStats:
    notes_re = re.compile(rf"(?m)^#\s+{re.escape(notes_title)}\s*$")
    notes_match = notes_re.search(text)
    body = text[: notes_match.start()] if notes_match else text
    refs = NOTE_REF_RE.findall(body)
    defs = NOTE_DEF_RE.findall(text)
    ref_counts = Counter(refs)
    def_counts = Counter(defs)
    return SourceStats(
        refs=refs,
        defs=defs,
        duplicate_defs=sorted(key for key, count in def_counts.items() if count > 1),
        missing_defs=sorted(set(ref_counts) - set(def_counts)),
        orphan_defs=sorted(set(def_counts) - set(ref_counts)),
        multi_ref_ids={key: count for key, count in ref_counts.items() if count > 1},
    )


def validate_source_notes(stats: SourceStats) -> None:
    problems = []
    if stats.duplicate_defs:
        problems.append(f"duplicate definitions: {stats.duplicate_defs}")
    if stats.missing_defs:
        problems.append(f"references without definitions: {stats.missing_defs}")
    if stats.orphan_defs:
        problems.append(f"orphan definitions: {stats.orphan_defs}")
    if problems:
        raise BuildError("Footnote source QA failed: " + "; ".join(problems))


def _is_fence(line: str) -> re.Match[str] | None:
    return FENCE_RE.match(line)


def _dedupe_image_alt(lines: list[str]) -> tuple[list[str], int]:
    result = list(lines)
    in_fence = False
    fence_char = ""
    count = 0
    for i, line in enumerate(lines):
        fence = _is_fence(line)
        if fence:
            token = fence.group(1)
            if not in_fence:
                in_fence, fence_char = True, token[0]
            elif token[0] == fence_char:
                in_fence, fence_char = False, ""
            continue
        if in_fence:
            continue
        match = IMAGE_LINE_RE.match(line)
        if not match or not match.group(2):
            continue
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        if j < len(lines) and CAPTION_LINE_RE.match(lines[j]):
            result[i] = f"{match.group(1)}![]{match.group(3)}"
            count += 1
    return result, count


def _normalize_heading_spacing(lines: list[str]) -> tuple[list[str], int, int]:
    out: list[str] = []
    in_fence = False
    fence_char = ""
    inserted = 0
    headings = 0

    for line in lines:
        fence = _is_fence(line)
        if fence:
            token = fence.group(1)
            if not in_fence:
                in_fence, fence_char = True, token[0]
            elif token[0] == fence_char:
                in_fence, fence_char = False, ""
            out.append(line)
            continue

        if not in_fence and ATX_RE.match(line):
            headings += 1
            if out and out[-1].strip():
                out.append("")
                inserted += 1
            out.append(line)
            # Always establish a legal block boundary. An existing blank input
            # line is coalesced by the next iteration.
            out.append("")
            inserted += 1
        else:
            if not (not line.strip() and out and not out[-1].strip()):
                out.append(line)

    while out and not out[-1].strip():
        out.pop()
    out.append("")
    return out, headings, inserted


def _annotate_note_refs(text: str, notes_title: str) -> tuple[str, int]:
    notes_re = re.compile(rf"(?m)^#\s+{re.escape(notes_title)}\s*$")
    notes_match = notes_re.search(text)
    if notes_match:
        body, notes = text[: notes_match.start()], text[notes_match.start() :]
    else:
        body, notes = text, ""
    counts: Counter[str] = Counter()

    def replace(match: re.Match[str]) -> str:
        note_id = match.group(1)
        counts[note_id] += 1
        key = hashlib.sha1(note_id.encode("utf-8")).hexdigest()
        annotation = (
            "[]{.pdf-noteref "
            f'data-note-key="{key}" data-note-occ="{counts[note_id]}"'
            "}"
        )
        return annotation + match.group(0)

    annotated = NOTE_REF_RE.sub(replace, body) + notes
    return annotated, sum(counts.values())


def normalize_markdown(source_text: str, notes_title: str) -> tuple[str, NormalizeStats]:
    # One known class of copy/extraction damage is a form-feed byte where the
    # source visibly intends TeX's \frac. Repair only that exact token in the
    # temporary input; reject any other unexplained control character.
    control_repairs = source_text.count("\x0crac")
    source_text = source_text.replace("\x0crac", r"\frac")
    unexpected_controls = sorted(
        {ord(char) for char in source_text if ord(char) < 32 and char not in "\n\r\t"}
    )
    if unexpected_controls:
        raise BuildError(f"Unsupported control characters in source: {unexpected_controls}")
    lines = source_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[0].startswith("\ufeff"):
        lines[0] = lines[0].lstrip("\ufeff")
    lines, captions_deduped = _dedupe_image_alt(lines)
    lines, headings_seen, blanks = _normalize_heading_spacing(lines)
    normalized = "\n".join(lines)
    normalized, refs_annotated = _annotate_note_refs(normalized, notes_title)
    return normalized, NormalizeStats(
        headings_seen, blanks, captions_deduped, refs_annotated, control_repairs
    )


def _inline_text(items: Iterable[Any]) -> str:
    pieces: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            kind = value.get("t")
            content = value.get("c")
            if kind in {"Str", "Code", "Math"}:
                if kind == "Str":
                    pieces.append(str(content))
                elif isinstance(content, list):
                    pieces.append(str(content[-1]))
            elif kind in {"Space", "SoftBreak", "LineBreak"}:
                pieces.append(" ")
            elif content is not None:
                walk(content)

    walk(list(items))
    return "".join(pieces).strip()


def load_ast(markdown: Path, cwd: Path) -> dict[str, Any]:
    completed = run(
        [
            "pandoc", str(markdown),
            "--from=markdown+smart+tex_math_single_backslash", "--to=json",
        ],
        cwd,
        "[2/8] Pandoc AST validation",
        capture=True,
    )
    return json.loads(completed.stdout.decode("utf-8"))



def normalize_structural_title(title: str) -> str:
    match = re.match(rf"^(第[{CN_NUM}]+(?:章|部分))", title)
    if not match:
        return title
    prefix = match.group(1)
    rest = title[len(prefix):].lstrip(" \t　")
    return prefix if not rest else prefix + "　" + rest

def validate_ast(
    ast: dict[str, Any],
    *,
    title: str,
    mainmatter_start: str,
    notes_title: str,
    source_toc_titles: tuple[str, ...],
    suppress_first_h1: bool,
    toc_exclude_h1: tuple[str, ...],
) -> StructuralManifest:
    headers: list[tuple[int, str]] = []
    for block in ast.get("blocks", []):
        if block.get("t") == "Header":
            level, _attr, inlines = block["c"]
            headers.append((int(level), _inline_text(inlines)))
    h1 = [value for level, value in headers if level == 1]
    if not h1:
        raise BuildError("Pandoc AST contains no H1 headings")

    notes_indexes = [i for i, value in enumerate(h1) if value == notes_title]
    if len(notes_indexes) > 1:
        raise BuildError(f"Multiple H1 headings named {notes_title!r}")
    notes_idx = notes_indexes[0] if notes_indexes else None

    if mainmatter_start:
        candidates = [i for i, value in enumerate(h1) if value == mainmatter_start]
        if len(candidates) != 1:
            raise BuildError(
                f"MAINMATTER_START must match exactly one H1: {mainmatter_start!r}; matches={len(candidates)}"
            )
        main_idx = candidates[0]
    else:
        candidates = [
            i for i, value in enumerate(h1)
            if (PART_RE.match(value) or CHAPTER_RE.match(value))
            and (notes_idx is None or i < notes_idx)
        ]
        if not candidates:
            raise BuildError(
                "Could not auto-detect main matter. Set MAINMATTER_START to the exact first body H1."
            )
        main_idx = candidates[0]

    h1_types: list[str] = []
    expected: list[tuple[int, str]] = []
    warnings: list[str] = []
    part_active = False
    toc_set = set(source_toc_titles)
    excluded = set(toc_exclude_h1)

    for i, value in enumerate(h1):
        if i == 0 and suppress_first_h1 and value not in toc_set and value != notes_title:
            kind = "source-title"
        elif value in toc_set:
            kind = "source-toc"
        elif value == notes_title:
            kind = "notes"
        elif i < main_idx:
            kind = "front"
        elif PART_RE.match(value):
            kind = "part"
            part_active = True
        elif APPENDIX_RE.match(value):
            kind = "chapter-top"
            part_active = False
        elif CHAPTER_RE.match(value):
            kind = "chapter-sub" if part_active else "chapter-top"
        else:
            kind = "chapter-top"
            part_active = False
            warnings.append(
                f"Unclassified main-matter H1 rendered as top-level unit: {value!r}. "
                "Set MAINMATTER_START / adjust the source structure if this is not intended."
            )

        if value in excluded and kind in {"front", "part", "chapter-top", "chapter-sub"}:
            kind += "-unlisted"

        h1_types.append(kind)
        display_value = normalize_structural_title(value)
        if kind == "front" or kind == "chapter-top" or kind == "part" or kind == "notes":
            expected.append((1, display_value))
        elif kind == "chapter-sub":
            expected.append((2, display_value))

    if h1_types[main_idx] in {"source-title", "source-toc", "front", "notes"}:
        raise BuildError(
            f"Main-matter start {h1[main_idx]!r} was classified as {h1_types[main_idx]!r}"
        )

    return StructuralManifest(
        h1_titles=h1,
        h1_types=h1_types,
        expected_outline=expected,
        mainmatter_index=main_idx + 1,
        mainmatter_title=normalize_structural_title(h1[main_idx]),
        notes_present=notes_idx is not None,
        warnings=warnings,
    )


def ast_image_targets(ast: dict[str, Any]) -> list[str]:
    targets: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            if value.get("t") == "Image":
                content = value.get("c", [])
                if len(content) >= 3 and isinstance(content[2], list):
                    targets.append(str(content[2][0]))
            for child in value.values():
                walk(child)

    walk(ast.get("blocks", []))
    return targets


def validate_images(targets: list[str], source_dir: Path) -> None:
    missing = []
    remote = []
    for target in targets:
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", target):
            remote.append(target)
            continue
        candidate = (source_dir / target).resolve()
        if not candidate.is_file():
            missing.append(target)
    if remote:
        raise BuildError(f"Remote images are not permitted in an offline build: {remote}")
    if missing:
        raise BuildError(f"Missing image assets: {missing}")


def write_metadata(
    path: Path,
    *,
    title: str,
    short_title: str,
    authors: list[str],
    lang: str,
    edition_note: str,
    toc_title: str,
    notes_title: str,
    openright: bool,
    manifest: StructuralManifest,
) -> None:
    data = {
        "title": title,
        "short-title": short_title,
        "author": authors,
        "lang": lang,
        "edition-note": edition_note,
        "toc-title": toc_title,
        "notes-title": notes_title,
        "openright": openright,
        "preamble-path": PREAMBLE_FILE.resolve().as_posix(),
        "book-h1-types": manifest.h1_types,
        "book-mainmatter-index": manifest.mainmatter_index,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_tagged_display_math_text(text: str) -> tuple[str, int]:
    pattern = re.compile(r"\\\[(?P<body>.*?)\\\]", re.S)
    count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal count
        body = match.group("body")
        tags = re.findall(r"\\tag\{([^{}]+)\}", body)
        if not tags:
            return match.group(0)
        clean = re.sub(r"\\tag\{[^{}]+\}", "", body).strip()
        count += 1
        return "\\begin{equation*}\n" + clean + f"\n\\tag{{{tags[-1]}}}\n\\end{{equation*}}"

    return pattern.sub(replace, text), count


def normalize_tagged_display_math(tex_path: Path) -> int:
    # Built-in regression check: only tagged display blocks may change.
    sample = r"before \[x=1\tag{A}\] middle \[y=2\] after"
    checked, sample_count = normalize_tagged_display_math_text(sample)
    if sample_count != 1 or r"\begin{equation*}" not in checked or r"\[y=2\]" not in checked:
        raise BuildError("Internal tagged-display-math regression check failed")
    text = tex_path.read_text(encoding="utf-8")
    text, count = normalize_tagged_display_math_text(text)
    if count:
        tex_path.write_text(text, encoding="utf-8")
    return count


def bound_display_math_text(text: str) -> tuple[str, int]:
    """Apply a *conditional* width cap to display math without enlarging it.

    Every display is measured at the book's normal math size by ``\\bookfitmath``.
    The TeX macro shrinks only a formula whose natural width exceeds 92% of the
    text block. Short equations retain their native size.
    """
    count = 0
    equation_pattern = re.compile(
        r"\\begin\{equation\*\}\s*(?P<body>.*?)\s*(?P<tag>\\tag\{[^{}]+\})?\s*"
        r"\\end\{equation\*\}",
        re.S,
    )

    def repl_equation(match: re.Match[str]) -> str:
        nonlocal count
        body = match.group("body").strip()
        tag = match.group("tag") or ""
        count += 1
        tag_line = f"\n{tag}" if tag else ""
        return (
            "\\begin{equation*}\n"
            "\\bookfitmath{%\n" + body + "\n}%" + tag_line +
            "\n\\end{equation*}"
        )

    text = equation_pattern.sub(repl_equation, text)
    display_pattern = re.compile(r"\\\[(?P<body>.*?)\\\]", re.S)

    def repl_display(match: re.Match[str]) -> str:
        nonlocal count
        body = match.group("body").strip()
        count += 1
        return (
            "\\begin{equation*}\n"
            "\\bookfitmath{%\n" + body + "\n}%\n"
            "\\end{equation*}"
        )

    return display_pattern.sub(repl_display, text), count


def bound_display_math(tex_path: Path) -> int:
    sample = r"a \[x=1\] b \begin{equation*}y=2\tag{B}\end{equation*}"
    checked, sample_count = bound_display_math_text(sample)
    if sample_count != 2 or checked.count(r"\bookfitmath") != 2 or r"\tag{B}" not in checked:
        raise BuildError("Internal conditional display-math fit regression check failed")
    text = tex_path.read_text(encoding="utf-8")
    text, count = bound_display_math_text(text)
    tex_path.write_text(text, encoding="utf-8")
    return count


def normalize_image_tex(tex_path: Path) -> int:
    """Route Pandoc images through the book image macro and style standalone captions.

    This prevents small raster figures from being enlarged to full text width,
    removes paragraph indentation before bare images, and gives captions a
    consistent centered book style.  Figure environments created by Pandoc are
    preserved; only the image command itself is replaced.
    """
    text = tex_path.read_text(encoding="utf-8")

    # Pandoc's LaTeX image syntax changed across releases.  Older versions
    # emit bare ``\includegraphics{...}``; newer versions may add options
    # and wrap the command in ``\pandocbounded{...}``.  Match all of these
    # forms so the build is reproducible across Windows/macOS/Linux Pandoc
    # installations instead of depending on one exact Pandoc release.
    image_pattern = re.compile(
        r"""(?mx)
        ^(?P<indent>[ \t]*)
        (?P<wrapped>\\pandocbounded\{)?
        \\includegraphics
        (?:\[[^\]\n]*\])?
        \{(?P<target>[^{}\n]+)\}
        (?(wrapped)\})
        [ \t]*$
        """
    )

    # Fail early if a future edit makes the compatibility regexp regress.
    image_samples = "\n".join([
        r"\includegraphics{assets/a.png}",
        r"\includegraphics[keepaspectratio,width=0.9\linewidth]{assets/b.png}",
        r"\pandocbounded{\includegraphics[keepaspectratio]{assets/c.png}}",
    ])
    if len(list(image_pattern.finditer(image_samples))) != 3:
        raise BuildError("Internal Pandoc image-syntax compatibility regression check failed")

    def image_repl(match: re.Match[str]) -> str:
        target = match.group("target")
        macro = "bookincludetableimage" if "_table" in target.lower() else "bookincludegraphics"
        return f"{match.group('indent')}\\{macro}{{{target}}}"

    text, count = image_pattern.subn(image_repl, text)

    # Independent captions occur only where the Markdown normalizer already
    # recognized a dedicated *图...* / **图...** or table-caption paragraph.
    cap_pattern = re.compile(
        r"(?m)^\\(?:textbf|emph)\{((?:图|表)[^\n{}]*(?:\\[{}%&#_$^~\\][^\n{}]*)?)\}\s*$"
    )
    text = cap_pattern.sub(r"\\bookfigurecaption{\1}", text)
    tex_path.write_text(text, encoding="utf-8")
    return count


def qa_note_links(tex: str, source: SourceStats) -> NoteLinkStats:
    refs = re.findall(r"\\booknoteref\{([^{}]+)\}\{([^{}]+)\}\{(\d+)\}", tex)
    note_anchors = re.findall(r"\\booknoteanchor\{([^{}]+)\}", tex)
    single_backs = re.findall(r"\\booknotebacklink\{([^{}]+)\}", tex)
    multi_backs = re.findall(r"\\booknotebacklinkmulti\{([^{}]+)\}\{\d+\}", tex)
    back_targets = single_backs + multi_backs

    ref_anchors = [row[0] for row in refs]
    forward_targets = [row[1] for row in refs]
    all_anchors = ref_anchors + note_anchors
    counts = Counter(all_anchors)
    duplicate_anchors = sorted(key for key, count in counts.items() if count > 1)
    missing_forward = sorted(set(forward_targets) - set(note_anchors))
    missing_back = sorted(set(back_targets) - set(ref_anchors))

    stats = NoteLinkStats(
        refs=len(refs),
        note_entries=len(note_anchors),
        backlinks=len(back_targets),
        duplicate_anchors=duplicate_anchors,
        missing_forward_targets=missing_forward,
        missing_back_targets=missing_back,
    )
    expected_refs = len(source.refs)
    expected_notes = len(set(source.defs))
    if (
        stats.refs != expected_refs
        or stats.note_entries != expected_notes
        or stats.backlinks != expected_refs
        or duplicate_anchors
        or missing_forward
        or missing_back
    ):
        raise BuildError(
            "Generated TeX endnote-link QA failed: "
            f"refs={stats.refs}/{expected_refs}, notes={stats.note_entries}/{expected_notes}, "
            f"backlinks={stats.backlinks}/{expected_refs}, duplicate_anchors={duplicate_anchors}, "
            f"missing_forward={missing_forward}, missing_back={missing_back}"
        )
    return stats


def parse_latex_log(log_path: Path) -> LogStats:
    if not log_path.is_file():
        raise BuildError(f"XeLaTeX log was not created: {log_path}")
    text = log_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    fatal_patterns = (
        re.compile(r"^! "),
        re.compile(r"LaTeX Error:"),
        re.compile(r"Package .* Error:"),
        re.compile(r"Emergency stop"),
        re.compile(r"Fatal error", re.I),
    )
    fatal = [line for line in lines if any(pattern.search(line) for pattern in fatal_patterns)]
    missing = [line for line in lines if "Missing character:" in line]
    duplicate = [
        line for line in lines
        if re.search(r"destination with the same identifier|duplicate destination", line, re.I)
    ]
    overfull: list[tuple[float, str]] = []
    for line in lines:
        match = re.search(r"Overfull \\hbox \(([-0-9.]+)pt too wide\)", line)
        if match:
            overfull.append((float(match.group(1)), line))
    underfull = sum("Underfull \\hbox" in line or "Underfull \\vbox" in line for line in lines)
    return LogStats(fatal, missing, duplicate, overfull, underfull)


def _page_has_printed_one(page: fitz.Page) -> bool:
    threshold = page.rect.height * 0.84
    for x0, y0, x1, y1, word, *_rest in page.get_text("words"):
        if y0 >= threshold and word.strip() == "1":
            return True
    return False


def _font_inventory(doc: fitz.Document) -> list[tuple[str, str, bool]]:
    rows: dict[int, tuple[str, str, bool]] = {}
    for page_number in range(doc.page_count):
        for font in doc.get_page_fonts(page_number, full=True):
            xref = int(font[0])
            if xref <= 0 or xref in rows:
                continue
            basefont = str(font[3]) if len(font) > 3 else f"xref-{xref}"
            try:
                name, ext, _font_type, content = doc.extract_font(xref)
                rows[xref] = (str(name or basefont), str(ext or "unknown"), bool(content))
            except Exception:
                rows[xref] = (basefont, "unknown", False)
    return sorted(rows.values(), key=lambda row: row[0].lower())


def qa_pdf(
    pdf_path: Path,
    *,
    manifest: StructuralManifest,
    expected_images: int,
    expected_internal_links: int,
    log_stats: LogStats,
    max_overfull_pt: float,
) -> PdfStats:
    warnings: list[str] = list(manifest.warnings)
    with fitz.open(pdf_path) as doc:
        if doc.page_count <= 0:
            raise BuildError("PDF has no pages")
        outline = doc.get_toc(simple=True)
        actual_pairs = [(int(row[0]), str(row[1])) for row in outline]
        if actual_pairs != manifest.expected_outline:
            raise BuildError(
                "PDF outline does not match the structure inferred from master.md.\n"
                f"Expected: {manifest.expected_outline}\nActual: {actual_pairs}"
            )

        main_rows = [row for row in outline if str(row[1]) == manifest.mainmatter_title]
        if len(main_rows) != 1:
            raise BuildError(
                f"Could not locate unique main-matter outline entry: {manifest.mainmatter_title!r}"
            )
        main_page = int(main_rows[0][2])
        main_pdf_page = doc[main_page - 1]
        main_label = main_pdf_page.get_label()
        printed_one = _page_has_printed_one(main_pdf_page)
        if main_label != "1":
            raise BuildError(f"Main-matter logical page label is {main_label!r}, expected '1'")
        if not printed_one:
            raise BuildError("Could not verify printed footer page number 1 on main-matter opening page")

        labels = doc.get_page_labels()
        if not labels or labels[0].get("style") != "r" or labels[0].get("startpage") != 0:
            raise BuildError(f"Front-matter lowercase-Roman page labels are missing: {labels}")
        arabic = [row for row in labels if row.get("style") == "D"]
        if len(arabic) != 1 or arabic[0].get("startpage") != main_page - 1 or arabic[0].get("firstpagenum") != 1:
            raise BuildError(f"Arabic page-label transition does not coincide with main matter: {labels}")
        if main_page > 1:
            previous = doc[main_page - 2].get_label()
            if not re.fullmatch(r"[ivxlcdm]+", previous):
                raise BuildError(f"Page before main matter is not lowercase Roman: {previous!r}")
        expected_last_label = str(doc.page_count - (main_page - 1))
        if doc[-1].get_label() != expected_last_label:
            raise BuildError(
                "Arabic page labels are not continuous through the last page: "
                f"{doc[-1].get_label()!r} != {expected_last_label!r}"
            )

        full_text = "\n".join(doc[i].get_text() for i in range(doc.page_count))
        leaked = re.findall(r"(?m)^\s*#\s*(?:第|附录|前言|序言|注释|Part\b|Chapter\b|Appendix\b)[^\n]*", full_text)
        if leaked:
            raise BuildError(f"Visible Markdown heading markers leaked into PDF text: {leaked[:10]}")
        caption_hits = [
            pattern for pattern in (
                r"图\s*\d+(?:\.\d+)?\s*[:：]\s*图\s*\d+",
                r"Figure\s*\d+\s*[:：]\s*图\s*\d+",
            ) if re.search(pattern, full_text, re.I)
        ]
        if caption_hits:
            raise BuildError(f"Duplicate caption pattern found in PDF text: {caption_hits}")

        image_occurrences = 0
        image_xrefs: set[int] = set()
        link_count = 0
        for page in doc:
            images = page.get_images(full=True)
            image_occurrences += len(images)
            image_xrefs.update(int(row[0]) for row in images if int(row[0]) > 0)
            links = page.get_links()
            link_count += len(links)
            internal = [link for link in links if link.get("kind") == fitz.LINK_GOTO]
            invalid = [link for link in internal if link.get("page", -1) < 0]
            if invalid:
                raise BuildError(f"Invalid internal PDF links found on page {page.number + 1}")
        if image_occurrences < expected_images:
            raise BuildError(
                f"PDF image occurrence count is too small: {image_occurrences} < {expected_images}"
            )
        if link_count < expected_internal_links:
            raise BuildError(
                f"PDF link count is too small: {link_count} < {expected_internal_links}"
            )

        fonts = _font_inventory(doc)
        unembedded = [name for name, _ext, embedded in fonts if not embedded]
        if unembedded:
            raise BuildError(f"Unembedded PDF fonts detected: {unembedded}")

        if log_stats.fatal_errors:
            raise BuildError(f"Fatal LaTeX log entries: {log_stats.fatal_errors[:10]}")
        if log_stats.missing_glyphs:
            raise BuildError(f"Missing-glyph warnings: {log_stats.missing_glyphs[:10]}")
        if log_stats.duplicate_destinations:
            raise BuildError(f"Duplicate PDF destinations: {log_stats.duplicate_destinations[:10]}")
        max_overfull = max((amount for amount, _line in log_stats.overfull), default=0.0)
        if max_overfull > max_overfull_pt:
            raise BuildError(f"Unacceptable overfull hbox: {max_overfull:.2f}pt")
        if log_stats.overfull:
            warnings.append(
                f"LaTeX reported {len(log_stats.overfull)} overfull hbox(es); maximum {max_overfull:.2f}pt."
            )
        if log_stats.underfull_count:
            warnings.append(f"LaTeX reported {log_stats.underfull_count} underfull box warning(s).")

        return PdfStats(
            pages=doc.page_count,
            outline=outline,
            page_labels=labels,
            mainmatter_page=main_page,
            mainmatter_label=main_label,
            mainmatter_printed=printed_one,
            font_rows=fonts,
            image_occurrences=image_occurrences,
            image_xrefs=len(image_xrefs),
            link_count=link_count,
            warnings=warnings,
        )


def write_qa_report(
    path: Path,
    pdf_path: Path,
    source_hash: str,
    normalize_stats: NormalizeStats,
    source_notes: SourceStats,
    note_links: NoteLinkStats,
    image_refs: int,
    log_stats: LogStats,
    pdf_stats: PdfStats,
    tagged_math_count: int,
    bounded_math_count: int,
) -> None:
    overfull_max = max((amount for amount, _line in log_stats.overfull), default=0.0)
    lines = [
        "Academic-book PDF build QA report",
        "=" * 36,
        f"PDF: {pdf_path.name}",
        f"Source SHA-256: {source_hash}",
        f"Pages: {pdf_stats.pages}",
        f"Outline items: {len(pdf_stats.outline)}",
        "Outline:",
    ]
    for level, title, page in pdf_stats.outline:
        lines.append(f"  {'  ' * (int(level) - 1)}- L{level} p.{page}: {title}")
    lines.extend([
        "",
        f"Page labels: {json.dumps(pdf_stats.page_labels, ensure_ascii=False)}",
        f"Main-matter physical page: {pdf_stats.mainmatter_page}",
        f"Main-matter logical label: {pdf_stats.mainmatter_label}",
        f"Main-matter printed footer verified as 1: {pdf_stats.mainmatter_printed}",
        "",
        "Fonts (all must be embedded):",
    ])
    for name, ext, embedded in pdf_stats.font_rows:
        lines.append(f"  - {name} [{ext}] embedded={embedded}")
    lines.extend([
        "",
        f"Markdown image references: {image_refs}",
        f"PDF image occurrences: {pdf_stats.image_occurrences}",
        f"PDF unique image xrefs: {pdf_stats.image_xrefs}",
        f"Image captions deduplicated in temporary input: {normalize_stats.captions_deduped}",
        "Duplicate caption pattern found: False",
        f"PDF annotation/link count: {pdf_stats.link_count}",
        "",
        "Note QA:",
        f"  source references: {len(source_notes.refs)}",
        f"  source definitions: {len(source_notes.defs)}",
        f"  unique definitions: {len(set(source_notes.defs))}",
        f"  repeated-reference IDs: {len(source_notes.multi_ref_ids)}",
        f"  forward links emitted: {note_links.refs}",
        f"  note anchors emitted: {note_links.note_entries}",
        f"  backlinks emitted: {note_links.backlinks}",
        f"  orphan notes: {len(source_notes.orphan_defs)}",
        f"  missing definitions: {len(source_notes.missing_defs)}",
        f"  duplicate anchors: {len(note_links.duplicate_anchors)}",
        f"  missing forward targets: {len(note_links.missing_forward_targets)}",
        f"  missing backlink targets: {len(note_links.missing_back_targets)}",
        "",
        f"ATX headings normalized: {normalize_stats.headings_seen}",
        f"Boundary blank lines inserted/coalesced in temporary input: {normalize_stats.blank_lines_inserted}",
        f"Named note references annotated: {normalize_stats.refs_annotated}",
        f"Temporary TeX control-sequence repairs: {normalize_stats.control_sequences_repaired}",
        f"Tagged display-math blocks normalized in temporary TeX: {tagged_math_count}",
        f"Display-math blocks conditionally width-capped (no enlargement): {bounded_math_count}",
        "",
        "LaTeX log:",
        f"  fatal errors: {len(log_stats.fatal_errors)}",
        f"  missing glyphs: {len(log_stats.missing_glyphs)}",
        f"  duplicate destinations: {len(log_stats.duplicate_destinations)}",
        f"  overfull hboxes: {len(log_stats.overfull)} (max {overfull_max:.2f}pt)",
        f"  underfull boxes: {log_stats.underfull_count}",
        "",
        "Warnings requiring attention:",
    ])
    if pdf_stats.warnings:
        lines.extend(f"  - {warning}" for warning in pdf_stats.warnings)
    else:
        lines.append("  - None")
    lines.extend([
        "",
        "Automated QA status: PASS",
        "Visual QA status: pending manual review of rendered representative pages",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build(args: argparse.Namespace) -> tuple[Path, Path, PdfStats]:
    ensure_dependencies()
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.is_file():
        raise BuildError(f"Input Markdown not found: {input_path}")
    output_value = args.output or (input_path.stem + ".pdf")
    output_path = Path(output_value).expanduser()
    if not output_path.is_absolute():
        output_path = (Path.cwd() / output_path).resolve()
    qa_path = Path(args.qa_report).expanduser() if args.qa_report else output_path.with_name("qa_report.txt")
    if not qa_path.is_absolute():
        qa_path = (Path.cwd() / qa_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    qa_path.parent.mkdir(parents=True, exist_ok=True)

    title = args.title or TITLE or input_path.stem.removesuffix("_master")
    short_title = args.short_title or SHORT_TITLE or title
    authors = list(args.author or AUTHORS)
    mainmatter_start = args.mainmatter_start or MAINMATTER_START
    openright = bool(args.openright if args.openright is not None else OPENRIGHT)

    source_hash_before = sha256_file(input_path)
    source_text = input_path.read_text(encoding="utf-8-sig")
    source_notes = analyze_source_notes(source_text, NOTES_TITLE)
    validate_source_notes(source_notes)
    normalized_text, normalize_stats = normalize_markdown(source_text, NOTES_TITLE)
    if normalize_stats.refs_annotated != len(source_notes.refs):
        raise BuildError(
            f"Note annotation count mismatch: {normalize_stats.refs_annotated} != {len(source_notes.refs)}"
        )

    build_dir = Path(tempfile.mkdtemp(prefix=".pdf-build-", dir=input_path.parent))
    success = False
    try:
        normalized_path = build_dir / "normalized_master.md"
        metadata_path = build_dir / "metadata.json"
        tex_path = build_dir / "book.tex"
        xdv_path = build_dir / "book.xdv"
        built_pdf = build_dir / "book.pdf"
        normalized_path.write_text(normalized_text, encoding="utf-8")

        print("[1/8] Source, note, and temporary-normalization QA", flush=True)
        ast = load_ast(normalized_path, input_path.parent)
        manifest = validate_ast(
            ast,
            title=title,
            mainmatter_start=mainmatter_start,
            notes_title=NOTES_TITLE,
            source_toc_titles=tuple(SOURCE_TOC_TITLES),
            suppress_first_h1=SUPPRESS_FIRST_H1,
            toc_exclude_h1=tuple(TOC_EXCLUDE_H1),
        )
        image_targets = ast_image_targets(ast)
        validate_images(image_targets, input_path.parent)
        write_metadata(
            metadata_path,
            title=title,
            short_title=short_title,
            authors=authors,
            lang=LANG,
            edition_note=EDITION_NOTE,
            toc_title=TOC_TITLE,
            notes_title=NOTES_TITLE,
            openright=openright,
            manifest=manifest,
        )

        resource_paths = [str(input_path.parent)]
        assets_path = input_path.parent / ASSETS_DIR
        if assets_path.exists():
            resource_paths.append(str(assets_path))
        run(
            [
                "pandoc", str(normalized_path),
                "--from=markdown+smart+tex_math_single_backslash",
                "--to=latex", "--standalone",
                "--top-level-division=chapter",
                f"--template={TEMPLATE_FILE}",
                f"--metadata-file={metadata_path}",
                f"--lua-filter={FILTER_FILE}",
                f"--resource-path={os.pathsep.join(resource_paths)}",
                "--output", str(tex_path),
            ],
            input_path.parent,
            "[3/8] Pandoc + book structure/endnotes filter -> LaTeX",
        )
        tagged_math_count = normalize_tagged_display_math(tex_path)
        bounded_math_count = bound_display_math(tex_path)
        normalize_image_tex(tex_path)
        tex_text = tex_path.read_text(encoding="utf-8")
        note_links = qa_note_links(tex_text, source_notes)
        includegraphics_count = (
            tex_text.count("\\bookincludegraphics{")
            + tex_text.count("\\bookincludetableimage{")
        )
        if includegraphics_count != len(image_targets):
            raise BuildError(
                "Generated TeX image count mismatch after Pandoc compatibility normalization: "
                f"{includegraphics_count} != {len(image_targets)}. "
                "Rerun with --keep-temp and inspect book.tex; the installed Pandoc may use a new image syntax."
            )

        xelatex = [
            "xelatex", "-no-pdf", "-interaction=nonstopmode", "-halt-on-error",
            "-file-line-error", f"-output-directory={build_dir}", str(tex_path),
        ]
        for pass_no in range(1, 4):
            run(xelatex, input_path.parent, f"[{3 + pass_no}/8] XeLaTeX pass {pass_no}/3", capture=True)
        if not xdv_path.is_file():
            raise BuildError(f"XeLaTeX did not create XDV: {xdv_path}")
        run(
            ["xdvipdfmx", "-E", "-o", str(built_pdf), str(xdv_path)],
            input_path.parent,
            "[7/8] xdvipdfmx -> PDF",
            capture=True,
        )
        if not built_pdf.is_file() or built_pdf.stat().st_size == 0:
            raise BuildError("xdvipdfmx returned without creating a non-empty PDF")

        log_stats = parse_latex_log(build_dir / "book.log")
        expected_internal_links = note_links.refs + note_links.backlinks + len(manifest.expected_outline)
        pdf_stats = qa_pdf(
            built_pdf,
            manifest=manifest,
            expected_images=len(image_targets),
            expected_internal_links=expected_internal_links,
            log_stats=log_stats,
            max_overfull_pt=MAX_OVERFULL_PT,
        )
        if source_hash_before != sha256_file(input_path):
            raise BuildError("Authoritative input Markdown changed during the build")

        print("[8/8] PDF structure, page-label, font, image, log, and note-link QA", flush=True)
        shutil.copy2(built_pdf, output_path)
        write_qa_report(
            qa_path, output_path, source_hash_before, normalize_stats, source_notes,
            note_links, len(image_targets), log_stats, pdf_stats, tagged_math_count,
            bounded_math_count,
        )
        success = True
        print(f"PASS: {output_path}", flush=True)
        print(f"QA:   {qa_path}", flush=True)
        return output_path, qa_path, pdf_stats
    finally:
        if args.keep_temp:
            print(f"Temporary build directory retained: {build_dir}", flush=True)
        else:
            shutil.rmtree(build_dir, ignore_errors=True)
        if not success:
            print("Build did not publish a final PDF.", file=sys.stderr)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and QA a B5 Chinese academic-book PDF")
    parser.add_argument("--input", default=INPUT_MD, help="authoritative master Markdown")
    parser.add_argument("--output", default=OUTPUT_PDF, help="final PDF path")
    parser.add_argument("--qa-report", default="", help="QA report path (default: beside PDF)")
    parser.add_argument("--title", default="")
    parser.add_argument("--short-title", default="")
    parser.add_argument("--author", action="append", default=[], help="author; repeat as needed")
    parser.add_argument("--mainmatter-start", default="", help="exact first body H1 if auto-detection is unsuitable")
    parser.add_argument("--openright", action=argparse.BooleanOptionalAction, default=None, help="force Part/Chapter to odd pages")
    parser.add_argument("--keep-temp", action="store_true", help="retain temporary build files for diagnosis")
    return parser.parse_args()


def main() -> int:
    try:
        _output, _qa, stats = build(parse_args())
        print(
            f"Summary: pages={stats.pages}, outline={len(stats.outline)}, "
            f"mainmatter label={stats.mainmatter_label}, images={stats.image_occurrences}, "
            f"links={stats.link_count}"
        )
        return 0
    except BuildError as exc:
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("BUILD INTERRUPTED", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
