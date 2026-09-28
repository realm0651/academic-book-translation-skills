from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# Pandoc / Markdown footnote forms used by this workflow.
REF_RE = re.compile(r"\[\^([^\]\s]+)\]")
DEF_RE = re.compile(r"^\[\^([^\]\s]+)\]:(?:[ \t]*(.*))?$")

# Recommended stable IDs for this translation workflow.
RECOMMENDED_ID_RE = re.compile(
    r"^(?:"
    r"pr-\d{3}|"                 # Preface: [^pr-001]
    r"intro-\d{3}|"              # Introduction: [^intro-001]
    r"ch\d{2,}-\d{3}|"           # Chapters: [^ch01-001]
    r"conclusion-\d{3}|"         # Conclusion
    r"ap-\d{3}"                 # Appendix: [^ap-001]
    r")$"
)

SEQUENCE_RE = re.compile(r"^(?P<prefix>.+)-(?P<number>\d{3})$")


@dataclass(frozen=True)
class Occurrence:
    path: Path
    line: int


@dataclass
class FileReport:
    path: Path
    refs: list[tuple[str, int]]
    defs: list[tuple[str, int]]
    end_layout_errors: list[tuple[int, str]]


def iter_markdown_files(inputs: Iterable[str]) -> list[Path]:
    files: list[Path] = []
    for raw in inputs:
        path = Path(raw)
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")
        if path.is_file():
            if path.suffix.lower() != ".md":
                raise ValueError(f"Not a Markdown file: {path}")
            files.append(path.resolve())
        else:
            files.extend(sorted(p.resolve() for p in path.rglob("*.md") if p.is_file()))

    # Stable de-duplication.
    result: list[Path] = []
    seen: set[Path] = set()
    for path in files:
        if path not in seen:
            seen.add(path)
            result.append(path)
    if not result:
        raise ValueError("No Markdown files found.")
    return result


def analyze_file(path: Path, check_definitions_at_end: bool) -> FileReport:
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()

    refs: list[tuple[str, int]] = []
    defs: list[tuple[str, int]] = []
    end_layout_errors: list[tuple[int, str]] = []

    # Final assembled master files use a top-level ``# 注释`` chapter and may contain
    # second-level group headings (``## 序言``, ``## 第三章``, ``## 附录``) between
    # definition groups. Working Part files do not. Detect the final layout automatically.
    notes_heading_lines = [
        lineno
        for lineno, line in enumerate(lines, start=1)
        if line.strip() == "# 注释"
    ]
    notes_heading_line = notes_heading_lines[0] if notes_heading_lines else None

    if check_definitions_at_end and len(notes_heading_lines) > 1:
        for lineno in notes_heading_lines[1:]:
            end_layout_errors.append(
                (lineno, "duplicate top-level # 注释 heading")
            )

    first_definition_line: int | None = None
    inside_definition_block = False

    for lineno, line in enumerate(lines, start=1):
        def_match = DEF_RE.match(line)
        if def_match:
            footnote_id = def_match.group(1)
            defs.append((footnote_id, lineno))
            if first_definition_line is None:
                first_definition_line = lineno
            inside_definition_block = True

            if (
                check_definitions_at_end
                and notes_heading_line is not None
                and lineno < notes_heading_line
            ):
                end_layout_errors.append(
                    (lineno, "footnote definition appears before the final # 注释 chapter")
                )

            # A definition body may itself contain a reference to another footnote.
            body = def_match.group(2) or ""
            for ref_match in REF_RE.finditer(body):
                refs.append((ref_match.group(1), lineno))
            continue

        # Scan ordinary lines for references.
        for ref_match in REF_RE.finditer(line):
            refs.append((ref_match.group(1), lineno))

        if not check_definitions_at_end:
            continue

        # Final whole-book layout: after ``# 注释`` begins, only blank lines, ``##``
        # group headings, footnote definitions, and indented definition continuations are
        # valid. This permits multiple groups while still preventing正文 from leaking into
        # the endnotes chapter.
        if notes_heading_line is not None:
            if lineno < notes_heading_line:
                continue
            if lineno == notes_heading_line:
                inside_definition_block = False
                continue
            if line.strip() == "":
                continue
            if line.startswith("## ") and not line.startswith("### "):
                inside_definition_block = False
                continue
            if (line.startswith("    ") or line.startswith("\t")) and inside_definition_block:
                continue

            inside_definition_block = False
            end_layout_errors.append(
                (lineno, "ordinary content appears inside the final # 注释 chapter: " + line[:100])
            )
            continue

        # Working Part layout: after the first definition begins, only blank lines,
        # indented continuation lines, and subsequent definitions are allowed. This
        # enforces the rule that each Part's definitions are collected at file end.
        if first_definition_line is None:
            continue
        if line.strip() == "":
            continue
        if (line.startswith("    ") or line.startswith("\t")) and inside_definition_block:
            continue

        inside_definition_block = False
        end_layout_errors.append(
            (lineno, "ordinary content appears after Part footnote definitions begin: " + line[:100])
        )

    return FileReport(path, refs, defs, end_layout_errors)


def format_occurrences(items: list[Occurrence], limit: int = 6) -> str:
    shown = items[:limit]
    text = ", ".join(f"{o.path.name}:{o.line}" for o in shown)
    if len(items) > limit:
        text += f", ... (+{len(items) - limit})"
    return text


def check_sequence(ids: Iterable[str]) -> list[str]:
    grouped: dict[str, set[int]] = defaultdict(set)
    warnings: list[str] = []

    for footnote_id in ids:
        match = SEQUENCE_RE.match(footnote_id)
        if not match:
            continue
        prefix = match.group("prefix")
        number = int(match.group("number"))
        grouped[prefix].add(number)

    for prefix, numbers in sorted(grouped.items()):
        if not numbers:
            continue
        low, high = min(numbers), max(numbers)
        expected = set(range(low, high + 1))
        missing = sorted(expected - numbers)
        if missing:
            formatted = ", ".join(f"{n:03d}" for n in missing[:20])
            suffix = " ..." if len(missing) > 20 else ""
            warnings.append(
                f"Sequence gap for prefix {prefix!r}: missing {formatted}{suffix}"
            )

    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Check Pandoc/Markdown footnotes across one or more translated Markdown files. "
            "Directories are searched recursively for *.md files."
        )
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Markdown file(s) and/or directories to check together as one book/project.",
    )
    parser.add_argument(
        "--strict-ids",
        action="store_true",
        help=(
            "Treat non-standard IDs as errors. Standard IDs include pr-001, intro-001, "
            "ch01-001, conclusion-001, ap-001. Without this flag they are warnings."
        ),
    )
    parser.add_argument(
        "--no-end-check",
        action="store_true",
        help=(
            "Do not enforce Part-end / assembled-endnotes layout. The translation workflow "
            "normally keeps this check enabled."
        ),
    )
    parser.add_argument(
        "--no-sequence-check",
        action="store_true",
        help="Do not warn about numbering gaps within the same footnote prefix.",
    )
    args = parser.parse_args()

    try:
        files = iter_markdown_files(args.paths)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    reports = [
        analyze_file(path, check_definitions_at_end=not args.no_end_check)
        for path in files
    ]

    ref_occ: dict[str, list[Occurrence]] = defaultdict(list)
    def_occ: dict[str, list[Occurrence]] = defaultdict(list)

    for report in reports:
        for footnote_id, line in report.refs:
            ref_occ[footnote_id].append(Occurrence(report.path, line))
        for footnote_id, line in report.defs:
            def_occ[footnote_id].append(Occurrence(report.path, line))

    errors: list[str] = []
    warnings: list[str] = []

    all_ids = sorted(set(ref_occ) | set(def_occ))

    # Duplicate definitions are always errors. Multiple references to one definition are valid.
    for footnote_id, occurrences in sorted(def_occ.items()):
        if len(occurrences) > 1:
            errors.append(
                f"Duplicate definition [^{footnote_id}]: {format_occurrences(occurrences)}"
            )

    # Missing and orphan definitions.
    for footnote_id in sorted(set(ref_occ) - set(def_occ)):
        errors.append(
            f"Missing definition for [^{footnote_id}] referenced at "
            f"{format_occurrences(ref_occ[footnote_id])}"
        )

    for footnote_id in sorted(set(def_occ) - set(ref_occ)):
        warnings.append(
            f"Orphan definition [^{footnote_id}] at {format_occurrences(def_occ[footnote_id])}"
        )

    # Recommended ID convention.
    for footnote_id in all_ids:
        if not RECOMMENDED_ID_RE.fullmatch(footnote_id):
            message = (
                f"Non-standard footnote ID [^{footnote_id}]. Recommended forms: "
                "[^pr-001], [^intro-001], [^ch01-001], "
                "[^conclusion-001], [^ap-001]."
            )
            if args.strict_ids:
                errors.append(message)
            else:
                warnings.append(message)

    # Layout rule: working Part files keep definitions at file end; an assembled master
    # keeps all definitions inside one final top-level # 注释 chapter with ## group headings.
    if not args.no_end_check:
        for report in reports:
            for lineno, preview in report.end_layout_errors:
                errors.append(
                    f"Footnote layout error in {report.path.name} at line {lineno}: {preview}"
                )

    # Sequence gaps are warnings, because source books can legitimately skip a number after
    # an extraction correction or when a non-note marker is involved.
    if not args.no_sequence_check:
        warnings.extend(check_sequence(all_ids))

    total_refs = sum(len(v) for v in ref_occ.values())
    total_defs = sum(len(v) for v in def_occ.values())

    print("Footnote check")
    print("==============")
    print(f"Files checked: {len(files)}")
    print(f"Reference occurrences: {total_refs}")
    print(f"Unique referenced IDs: {len(ref_occ)}")
    print(f"Definition occurrences: {total_defs}")
    print(f"Unique defined IDs: {len(def_occ)}")

    if warnings:
        print("\nWarnings")
        print("--------")
        for item in warnings:
            print(f"- {item}")

    if errors:
        print("\nErrors")
        print("------")
        for item in errors:
            print(f"- {item}")
        print(f"\nFAILED: {len(errors)} error(s), {len(warnings)} warning(s).")
        return 1

    print(f"\nOK: 0 errors, {len(warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
