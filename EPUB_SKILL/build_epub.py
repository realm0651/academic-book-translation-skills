#!/usr/bin/env python3
"""Build an EPUB3 from an already assembled book Markdown file.

Normal use: edit only the USER SETTINGS block below, then run:
    python build_epub.py

The script expects Pandoc in PATH. It uses the CSS and Lua filter shipped beside
this file, generates temporary metadata automatically, builds the EPUB, and runs
a small structural sanity check.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


# ============================ USER SETTINGS ============================
# Paths are relative to the directory from which this script is run
# (normally the book project directory containing book_master.md/assets/).
INPUT_MD = "book_master.md"
OUTPUT_EPUB = ""  # blank -> same stem as INPUT_MD with .epub

TITLE = ""        # recommended: Chinese book title
AUTHORS = []       # e.g. ["P. K. Edwards"]
LANG = "zh-CN"

TOC_TITLE = "目录"
TOC_DEPTH = 3
SPLIT_LEVEL = 1    # TRANSLATION_SKILL makes major book units H1, so 1 is the default
NOTES_TITLE = "注释"
UNGROUPED_NOTES_TITLE = "其他"

ASSETS_DIR = "assets"
COVER_IMAGE = ""  # optional, e.g. "assets/cover.jpg"
# ======================================================================


SKILL_DIR = Path(__file__).resolve().parent
CSS_FILE = SKILL_DIR / "epub_generic.css"
LUA_FILTER = SKILL_DIR / "epub_endnotes.lua"


def q(value: str) -> str:
    """Return a YAML-safe double-quoted scalar using JSON escaping."""
    return json.dumps(value, ensure_ascii=False)


def write_metadata(path: Path, title: str, authors: list[str]) -> None:
    lines = [
        f"title: {q(title)}",
        f"lang: {q(LANG)}",
        f"toc-title: {q(TOC_TITLE)}",
        f"notes-title: {q(NOTES_TITLE)}",
        f"ungrouped-notes-title: {q(UNGROUPED_NOTES_TITLE)}",
    ]
    if authors:
        lines.append("author:")
        lines.extend(f"  - {q(a)}" for a in authors)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_command(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"Required command not found in PATH: {name}")


def structural_check(epub: Path) -> None:
    with zipfile.ZipFile(epub) as zf:
        names = zf.namelist()
        required_signals = {
            "mimetype": any(n == "mimetype" for n in names),
            "package": any(n.endswith(".opf") for n in names),
            "navigation": any("nav" in n.lower() and n.endswith((".xhtml", ".html")) for n in names),
            "content": any(n.endswith((".xhtml", ".html")) for n in names),
        }
        missing = [k for k, ok in required_signals.items() if not ok]
        if missing:
            raise RuntimeError(f"EPUB structural check failed; missing: {', '.join(missing)}")

        # Notes title should normally be present when source footnotes exist.
        html_names = [n for n in names if n.endswith((".xhtml", ".html"))]
        joined = ""
        for n in html_names:
            try:
                joined += zf.read(n).decode("utf-8", errors="ignore")
            except KeyError:
                pass
        if NOTES_TITLE and NOTES_TITLE not in joined:
            print(f"[warning] Could not confirm '{NOTES_TITLE}' in EPUB XHTML. "
                  "This is harmless if the book has no notes.")


def build(args: argparse.Namespace) -> Path:
    project_dir = Path.cwd()
    input_md = (project_dir / args.input).resolve()
    if not input_md.exists():
        raise FileNotFoundError(f"Input Markdown not found: {input_md}")

    output = Path(args.output) if args.output else Path(input_md.stem + ".epub")
    if not output.is_absolute():
        output = (project_dir / output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    ensure_command("pandoc")
    for f in (CSS_FILE, LUA_FILTER):
        if not f.exists():
            raise FileNotFoundError(f"Missing skill file: {f}")

    title = args.title or TITLE or input_md.stem
    authors = args.author if args.author else list(AUTHORS)

    build_dir = project_dir / ".epub_build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)
    metadata = build_dir / "metadata.yaml"
    write_metadata(metadata, title, authors)

    resource_paths = [str(project_dir)]
    assets = project_dir / ASSETS_DIR
    if assets.exists():
        resource_paths.append(str(assets.resolve()))

    cmd = [
        "pandoc",
        str(input_md),
        "--from=markdown+smart",
        "--to=epub3",
        "--toc",
        f"--toc-depth={TOC_DEPTH}",
        f"--split-level={SPLIT_LEVEL}",
        f"--css={CSS_FILE}",
        f"--metadata-file={metadata}",
        f"--lua-filter={LUA_FILTER}",
        f"--resource-path={os.pathsep.join(resource_paths)}",
        "-o",
        str(output),
    ]

    cover = args.cover or COVER_IMAGE
    if cover:
        cover_path = Path(cover)
        if not cover_path.is_absolute():
            cover_path = project_dir / cover_path
        if not cover_path.exists():
            raise FileNotFoundError(f"Cover image not found: {cover_path}")
        cmd.insert(-2, f"--epub-cover-image={cover_path.resolve()}")

    print("=== EPUB build ===")
    print(f"Input : {input_md}")
    print(f"Output: {output}")
    print(f"Title : {title}")
    subprocess.run(cmd, cwd=project_dir, check=True)

    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError("Pandoc returned successfully but no EPUB was created.")

    structural_check(output)
    print(f"Done: {output} ({output.stat().st_size / 1024 / 1024:.2f} MB)")
    return output


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build EPUB3 from assembled Markdown.")
    p.add_argument("--input", default=INPUT_MD, help="Input master Markdown")
    p.add_argument("--output", default=OUTPUT_EPUB, help="Output EPUB path")
    p.add_argument("--title", default="", help="Override TITLE")
    p.add_argument("--author", action="append", default=[], help="Author; repeat as needed")
    p.add_argument("--cover", default="", help="Optional cover image")
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
