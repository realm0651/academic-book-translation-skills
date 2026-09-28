#!/usr/bin/env python3
"""Validate a final translation master for Pandoc-based publishing handoff.

The check is intentionally non-destructive. It validates:
- raw ATX H1/H2 headings have safe blank-line boundaries;
- those headings survive a Pandoc structural parse at the same levels;
- a unified top-level Notes heading is not duplicated;
- local Markdown image references resolve relative to the master file.

To keep whole-book checks fast, Pandoc receives a structural projection of the
Markdown rather than the full prose/footnote payload. The projection preserves
block boundaries, headings, lists, fenced code, and footnote-definition shapes,
which is enough to catch the heading-recognition failures this check targets.
Book-specific semantic order still comes from book_plan.md and is checked by the
workflow.
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Iterable
from urllib.parse import unquote

ATX_RE = re.compile(r"^(#{1,2})[ \t]+(.+?)[ \t]*#*[ \t]*$")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\((?:<([^>]+)>|([^\s)]+))(?:\s+[\"'][^\"']*[\"'])?\)")
LIST_RE = re.compile(r"^(\s*)([-+*]|\d+[.)])\s+")
FOOTNOTE_RE = re.compile(r"^(\s*)\[\^[^\]]+\]:")


def normalize_heading_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def strip_inline_markdown(text: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[*_~]", "", text)
    return normalize_heading_text(text)


def raw_headings(lines: list[str]) -> list[tuple[int, str, int]]:
    out: list[tuple[int, str, int]] = []
    in_fence = False
    fence = None
    for lineno, line in enumerate(lines, 1):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            mark = stripped[:3]
            if not in_fence:
                in_fence = True
                fence = mark
            elif mark == fence:
                in_fence = False
                fence = None
            continue
        if in_fence:
            continue
        m = ATX_RE.match(line)
        if m:
            out.append((len(m.group(1)), strip_inline_markdown(m.group(2)), lineno))
    return out


def structural_projection(lines: list[str]) -> str:
    out: list[str] = []
    in_fence = False
    fence = None
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            mark = stripped[:3]
            if not in_fence:
                in_fence = True
                fence = mark
                out.append(mark)
            elif mark == fence:
                in_fence = False
                fence = None
                out.append(mark)
            else:
                out.append("x")
            continue
        if in_fence:
            out.append("x")
            continue
        if not line.strip():
            out.append("")
            continue
        if re.match(r"^#{1,6}[ \t]+", line):
            out.append(line)
            continue
        fm = FOOTNOTE_RE.match(line)
        if fm:
            out.append(f"{fm.group(1)}[^x]: x")
            continue
        lm = LIST_RE.match(line)
        if lm:
            out.append(f"{lm.group(1)}{lm.group(2)} x")
            continue
        if line.startswith("    ") or line.startswith("\t"):
            out.append("    x")
            continue
        if stripped.startswith(">"):
            indent = line[: len(line) - len(stripped)]
            out.append(indent + "> x")
            continue
        out.append("x")
    return "\n".join(out) + "\n"


def stringify_inlines(nodes: Iterable[dict[str, Any]]) -> str:
    parts: list[str] = []
    for node in nodes:
        t = node.get("t")
        c = node.get("c")
        if t == "Str":
            parts.append(str(c))
        elif t in {"Space", "SoftBreak", "LineBreak"}:
            parts.append(" ")
        elif t in {"Code", "Math"} and isinstance(c, list) and len(c) >= 2:
            parts.append(str(c[1]))
        elif t in {"Emph", "Strong", "Strikeout", "SmallCaps", "Superscript", "Subscript"}:
            parts.append(stringify_inlines(c or []))
        elif t == "Quoted" and isinstance(c, list) and len(c) == 2:
            parts.append(stringify_inlines(c[1]))
        elif t in {"Link", "Image"} and isinstance(c, list) and len(c) >= 2:
            parts.append(stringify_inlines(c[1]))
        elif isinstance(c, list):
            children = [x for x in c if isinstance(x, dict)]
            if children:
                parts.append(stringify_inlines(children))
    return normalize_heading_text("".join(parts))


def walk(node: Any):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from walk(item)


def pandoc_ast(projection: str, timeout: int) -> dict[str, Any]:
    pandoc = shutil.which("pandoc")
    if not pandoc:
        raise RuntimeError("pandoc not found in PATH")
    try:
        proc = subprocess.run(
            [pandoc, "--from=markdown", "--to=json"],
            input=projection,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"pandoc structural parse timed out after {timeout}s") from e
    if proc.returncode != 0:
        raise RuntimeError(f"pandoc failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def ast_headings(ast: dict[str, Any]) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for node in walk(ast.get("blocks", [])):
        if node.get("t") == "Header":
            c = node.get("c", [])
            if isinstance(c, list) and len(c) >= 3:
                level = int(c[0])
                if level in (1, 2):
                    out.append((level, stringify_inlines(c[2])))
    return out


def image_targets(text: str) -> list[str]:
    out: list[str] = []
    for m in IMAGE_RE.finditer(text):
        target = m.group(1) or m.group(2) or ""
        if target:
            out.append(unquote(target))
    return out


def is_external(target: str) -> bool:
    return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", target)) or target.startswith("data:")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("master", type=Path)
    ap.add_argument("--pandoc-timeout", type=int, default=30)
    args = ap.parse_args()

    master = args.master.resolve()
    if not master.is_file():
        print(f"ERROR: master not found: {master}", file=sys.stderr)
        return 2

    text = master.read_text(encoding="utf-8")
    lines = text.splitlines()
    raw = raw_headings(lines)
    errors: list[str] = []

    # Safe boundaries: final masters should keep H1/H2 isolated from adjacent blocks.
    for level, title, lineno in raw:
        if lineno > 1 and lines[lineno - 2].strip():
            errors.append(f"H{level} {title!r} at line {lineno} lacks a blank line before it")
        if lineno < len(lines) and lines[lineno].strip():
            errors.append(f"H{level} {title!r} at line {lineno} lacks a blank line after it")

    try:
        ast = pandoc_ast(structural_projection(lines), args.pandoc_timeout)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    ast_h = ast_headings(ast)
    raw_counter = collections.Counter((lvl, title) for lvl, title, _ in raw)
    ast_counter = collections.Counter(ast_h)
    if raw_counter != ast_counter:
        missing = raw_counter - ast_counter
        extra = ast_counter - raw_counter
        for (lvl, title), count in missing.items():
            src_lines = [str(n) for l, t, n in raw if l == lvl and t == title]
            errors.append(
                f"Pandoc did not recognize raw H{lvl} {title!r} the expected {count} time(s); raw line(s): {', '.join(src_lines)}"
            )
        for (lvl, title), count in extra.items():
            errors.append(f"Pandoc produced unexpected H{lvl} {title!r} {count} time(s)")

    notes_count = sum(1 for lvl, title in ast_h if lvl == 1 and title == "注释")
    if notes_count > 1:
        errors.append(f"Top-level '# 注释' appears {notes_count} times; expected at most one")

    targets = image_targets(text)
    missing_images: list[str] = []
    for target in targets:
        if not target or is_external(target) or target.startswith("#"):
            continue
        if not (master.parent / target).is_file():
            missing_images.append(target)
    for target in sorted(set(missing_images)):
        errors.append(f"Missing local image: {target}")

    h1 = [title for lvl, title in ast_h if lvl == 1]
    h2_count = sum(1 for lvl, _ in ast_h if lvl == 2)
    local_images = [p for p in targets if p and not is_external(p)]
    print(f"master: {master.name}")
    print(f"Pandoc H1: {len(h1)}")
    print(f"Pandoc H2: {h2_count}")
    print(f"local images: {len(local_images)}")
    if h1:
        print("H1 sequence:")
        for i, title in enumerate(h1, 1):
            print(f"  {i:02d}. {title}")

    if errors:
        print("FAIL", file=sys.stderr)
        for e in errors:
            print(f"- {e}", file=sys.stderr)
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
