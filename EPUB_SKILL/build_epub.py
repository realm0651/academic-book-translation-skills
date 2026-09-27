#!/usr/bin/env python3
"""Build and structurally verify an EPUB3 from assembled book Markdown.

Normal use: edit only the USER SETTINGS block below, then run:
    python build_epub.py

The source master remains authoritative. The Lua filter removes only the printed
source TOC / assembled source Notes shell and leaves Pandoc native Note nodes intact.
Pandoc therefore emits EPUB3-native, same-XHTML chapter-end footnotes with backlinks.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET


# ============================ USER SETTINGS ============================
# Paths are relative to the directory from which this script is run
# (normally the book project directory containing book_master.md/assets/).
INPUT_MD = "book_master.md"
OUTPUT_EPUB = ""  # blank -> filename-safe Chinese TITLE + .epub; fallback to input stem

TITLE = ""         # recommended: finalized Chinese book title
AUTHORS = []       # e.g. ["P. K. Edwards"]
LANG = "zh-CN"

TOC_TITLE = "目录"
TOC_DEPTH = 2      # current TRANSLATION_SKILL: H1 book units, H2 main in-unit sections
SPLIT_LEVEL = 1    # current TRANSLATION_SKILL: major book units are H1
NOTES_TITLE = "注释"

# Keep matching source headings in the reading flow but omit them from navigation.
# The script automatically adds TITLE and its colon-separated main/subtitle parts.
TOC_OMIT_HEADINGS = []
AUTO_OMIT_METADATA_TITLE_HEADINGS = True

ASSETS_DIR = "assets"
COVER_IMAGE = ""  # optional, e.g. "assets/cover.jpg"
# ======================================================================


SKILL_DIR = Path(__file__).resolve().parent
CSS_FILE = SKILL_DIR / "epub_generic.css"
LUA_FILTER = SKILL_DIR / "epub_chapter_notes.lua"

UNSAFE_FILENAME_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
EPUB_NS = "http://www.idpf.org/2007/ops"
XHTML_NS = "http://www.w3.org/1999/xhtml"
NCX_NS = "http://www.daisy.org/z3986/2005/ncx/"
OPF_NS = "http://www.idpf.org/2007/opf"
DC_NS = "http://purl.org/dc/elements/1.1/"


def safe_filename_stem(value: str) -> str:
    """Normalize a user-facing filename stem; never emit spaces or literal %20."""
    value = value.replace("%20", " ").replace("：", "_").replace(":", "_")
    value = re.sub(r"\s+", "_", value.strip())
    value = UNSAFE_FILENAME_RE.sub("_", value)
    value = re.sub(r"_+", "_", value).strip("._ ")
    return value or "book"


def q(value: str) -> str:
    """Return a YAML-safe double-quoted scalar using JSON escaping."""
    return json.dumps(value, ensure_ascii=False)


def title_heading_candidates(title: str) -> list[str]:
    """Exact headings commonly duplicated by a generated EPUB title page."""
    candidates: list[str] = []
    for item in [title, *re.split(r"\s*[：:]\s*", title)]:
        item = item.strip()
        if item and item not in candidates:
            candidates.append(item)
    return candidates


def write_metadata(path: Path, title: str, authors: list[str], toc_omit: list[str]) -> None:
    lines = [
        f"title: {q(title)}",
        f"lang: {q(LANG)}",
        f"toc-title: {q(TOC_TITLE)}",
        f"notes-title: {q(NOTES_TITLE)}",
    ]
    if authors:
        lines.append("author:")
        lines.extend(f"  - {q(a)}" for a in authors)
    if toc_omit:
        lines.append("toc-omit-headings:")
        lines.extend(f"  - {q(h)}" for h in toc_omit)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_command(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"Required command not found in PATH: {name}")


def _decode_xml(zf: zipfile.ZipFile, name: str) -> ET.Element:
    try:
        return ET.fromstring(zf.read(name))
    except ET.ParseError as e:
        raise RuntimeError(f"Invalid XML/XHTML in EPUB member {name}: {e}") from e


def _all_text(el: ET.Element) -> str:
    return "".join(el.itertext()).strip()


def _resolve_member(base_name: str, href: str) -> tuple[str, str]:
    """Resolve an EPUB-internal href against a member path; return member, fragment."""
    href = href.strip()
    if not href:
        return base_name, ""
    if "://" in href or href.startswith("mailto:"):
        return "", ""
    path_part, sep, frag = href.partition("#")
    if not path_part:
        return base_name, frag
    base_dir = PurePosixPath(base_name).parent
    resolved = str(PurePosixPath(os.path.normpath(str(base_dir / path_part)).replace("\\", "/")))
    return resolved, frag if sep else ""


def _ids_in(root: ET.Element) -> set[str]:
    return {el.attrib["id"] for el in root.iter() if el.attrib.get("id")}


def _anchor_elements(root: ET.Element) -> list[ET.Element]:
    return [el for el in root.iter() if el.tag.endswith("}a") or el.tag == "a"]


def _epub_type(el: ET.Element) -> str:
    return el.attrib.get(f"{{{EPUB_NS}}}type", "")


def _classes(el: ET.Element) -> set[str]:
    return set(el.attrib.get("class", "").split())


def structural_check(
    epub: Path,
    *,
    title: str,
    authors: list[str],
    expected_toc_omissions: list[str],
) -> None:
    """Fail on broken chapter-note links / navigation; warn on suspicious TOC labels."""
    with zipfile.ZipFile(epub) as zf:
        bad_member = zf.testzip()
        if bad_member:
            raise RuntimeError(f"EPUB ZIP integrity check failed at: {bad_member}")

        names = zf.namelist()
        name_set = set(names)
        required_signals = {
            "mimetype": "mimetype" in name_set,
            "package": any(n.endswith(".opf") for n in names),
            "navigation": any(n.endswith("nav.xhtml") for n in names),
            "content": any(n.endswith((".xhtml", ".html")) for n in names),
        }
        missing = [k for k, ok in required_signals.items() if not ok]
        if missing:
            raise RuntimeError(f"EPUB structural check failed; missing: {', '.join(missing)}")

        xhtml_names = [n for n in names if n.endswith((".xhtml", ".html"))]
        roots: dict[str, ET.Element] = {n: _decode_xml(zf, n) for n in xhtml_names}
        ids_by_file = {n: _ids_in(root) for n, root in roots.items()}

        # --- Metadata ---
        opf_name = next((n for n in names if n.endswith(".opf")), None)
        if opf_name:
            opf = _decode_xml(zf, opf_name)
            ns = {"dc": DC_NS}
            found_title = (opf.findtext(".//dc:title", default="", namespaces=ns) or "").strip()
            if title and found_title != title:
                raise RuntimeError(f"EPUB metadata title mismatch: expected {title!r}, got {found_title!r}")
            found_authors = [(_all_text(e)) for e in opf.findall(".//dc:creator", ns)]
            for author in authors:
                if author not in found_authors:
                    raise RuntimeError(f"EPUB metadata is missing author: {author}")

        # --- Native footnotes: same XHTML, visible number, target and backlink ---
        total_refs = 0
        total_notes = 0
        for name, root in roots.items():
            if name.endswith("nav.xhtml") or name.endswith("title_page.xhtml"):
                continue
            ids = ids_by_file[name]
            anchors = _anchor_elements(root)
            refs = [
                a for a in anchors
                if "noteref" in _epub_type(a).split() or "footnote-ref" in _classes(a)
            ]
            if not refs:
                continue

            total_refs += len(refs)
            ref_numbers: list[int] = []
            for a in refs:
                href = a.attrib.get("href", "")
                if not href.startswith("#"):
                    raise RuntimeError(
                        f"Footnote reference is not same-XHTML in {name}: href={href!r}. "
                        "Chapter notes must use local fragment links."
                    )
                target = href[1:]
                if target not in ids:
                    raise RuntimeError(f"Broken footnote target in {name}: #{target}")
                visible = _all_text(a)
                m = re.fullmatch(r"\[?(\d+)\]?", visible)
                if not m:
                    raise RuntimeError(
                        f"Footnote reference in {name} has no clear visible numeric marker: {visible!r}"
                    )
                ref_numbers.append(int(m.group(1)))

            unique_ref_numbers = []
            for n in ref_numbers:
                if not unique_ref_numbers or unique_ref_numbers[-1] != n:
                    unique_ref_numbers.append(n)
            if unique_ref_numbers and unique_ref_numbers[0] != 1:
                raise RuntimeError(f"Footnote numbering in {name} does not restart at 1")
            if unique_ref_numbers and unique_ref_numbers != list(range(1, max(unique_ref_numbers) + 1)):
                raise RuntimeError(f"Footnote numbering in {name} is not contiguous: {unique_ref_numbers[:20]}")

            note_els = [
                el for el in root.iter()
                if "footnote" in _epub_type(el).split() and el.attrib.get("id")
            ]
            total_notes += len(note_els)
            if len(note_els) < len(set(ref_numbers)):
                raise RuntimeError(
                    f"Too few native footnote targets in {name}: refs={len(set(ref_numbers))}, notes={len(note_els)}"
                )

            for note in note_els:
                backlinks = [
                    a for a in _anchor_elements(note)
                    if a.attrib.get("role") == "doc-backlink" or "footnote-back" in _classes(a)
                ]
                if not backlinks:
                    raise RuntimeError(f"Footnote {note.attrib.get('id')} in {name} has no backlink")
                backlink = backlinks[0]
                href = backlink.attrib.get("href", "")
                if not href.startswith("#") or href[1:] not in ids:
                    raise RuntimeError(
                        f"Broken footnote backlink in {name} note {note.attrib.get('id')}: {href!r}"
                    )
                if not _all_text(backlink):
                    raise RuntimeError(
                        f"Footnote {note.attrib.get('id')} in {name} has no visible note number/backlink text"
                    )

        # --- Navigation TOC: all targets reachable, no source Notes chapter ---
        nav_name = next((n for n in names if n.endswith("nav.xhtml")), None)
        if not nav_name:
            raise RuntimeError("EPUB navigation document nav.xhtml not found")
        nav_root = roots[nav_name]
        nav_anchors = _anchor_elements(nav_root)
        toc_labels: list[str] = []
        for a in nav_anchors:
            href = a.attrib.get("href", "")
            label = _all_text(a)
            if href and not href.startswith("#") and not href.startswith("http"):
                target_file, frag = _resolve_member(nav_name, href)
                if target_file not in name_set:
                    raise RuntimeError(f"Broken nav target: {href!r} -> missing {target_file}")
                if frag and frag not in ids_by_file.get(target_file, set()):
                    raise RuntimeError(f"Broken nav fragment: {href!r}")
            if label and a.attrib.get(f"{{{EPUB_NS}}}type") not in {"titlepage", "toc"}:
                toc_labels.append(label)

        if NOTES_TITLE in toc_labels:
            raise RuntimeError(
                f"Generated navigation still contains a standalone '{NOTES_TITLE}' chapter; "
                "chapter-end native footnotes were expected."
            )
        for omitted in expected_toc_omissions:
            if omitted and omitted in toc_labels:
                raise RuntimeError(f"TOC omission failed; navigation still contains heading: {omitted}")

        suspicious = [x for x in toc_labels if re.match(r"^(表|图)\s*\d", x)]
        if suspicious:
            print("[warning] TOC contains possible table/figure headings: " + "; ".join(suspicious[:8]))

        # --- Legacy NCX compatibility: targets must also be reachable ---
        ncx_name = next((n for n in names if n.endswith("toc.ncx")), None)
        if ncx_name:
            ncx_root = _decode_xml(zf, ncx_name)
            for content in ncx_root.findall(f".//{{{NCX_NS}}}content"):
                src = content.attrib.get("src", "")
                if not src:
                    continue
                target_file, frag = _resolve_member(ncx_name, src)
                if target_file not in name_set:
                    raise RuntimeError(f"Broken NCX target: {src!r} -> missing {target_file}")
                if frag and frag not in ids_by_file.get(target_file, set()):
                    raise RuntimeError(f"Broken NCX fragment: {src!r}")

        print(f"QA: {total_refs} native note refs, {total_notes} native note targets; navigation links valid.")


def build(args: argparse.Namespace) -> Path:
    project_dir = Path.cwd()
    input_md = (project_dir / args.input).resolve()
    if not input_md.exists():
        raise FileNotFoundError(f"Input Markdown not found: {input_md}")

    title = args.title or TITLE or input_md.stem.removesuffix("_master")
    output = Path(args.output) if args.output else Path(safe_filename_stem(title) + ".epub")
    if not output.is_absolute():
        output = (project_dir / output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    ensure_command("pandoc")
    for f in (CSS_FILE, LUA_FILTER):
        if not f.exists():
            raise FileNotFoundError(f"Missing skill file: {f}")

    authors = args.author if args.author else list(AUTHORS)
    toc_omit = list(TOC_OMIT_HEADINGS)
    if AUTO_OMIT_METADATA_TITLE_HEADINGS and title:
        for h in title_heading_candidates(title):
            if h not in toc_omit:
                toc_omit.append(h)

    build_dir = project_dir / ".epub_build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)
    metadata = build_dir / "metadata.yaml"
    write_metadata(metadata, title, authors, toc_omit)

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
    print(f"TOC   : depth={TOC_DEPTH}, split-level={SPLIT_LEVEL}")
    subprocess.run(cmd, cwd=project_dir, check=True)

    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError("Pandoc returned successfully but no EPUB was created.")

    structural_check(
        output,
        title=title,
        authors=authors,
        expected_toc_omissions=toc_omit,
    )
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
