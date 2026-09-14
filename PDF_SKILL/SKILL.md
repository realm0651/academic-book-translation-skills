---
name: academic-book-pdf
description: Build and verify a polished B5 Chinese academic-book PDF from the final master Markdown produced by the translation workflow. Treat master.md as the only authoritative body source; normalize only in a temporary build directory; infer and validate book structure before typesetting; generate a restrained TOC/bookmark hierarchy, correct Roman-to-Arabic page labels, readable tables, non-upscaled images, native-size mathematics with shrink-only overflow handling, and bidirectional book-end notes; then run structural, typography, link, font, log, and rendered-page QA before delivery.
---

# Academic Book PDF

## Scope and authority

Use this skill only after translation and whole-book Markdown assembly are complete. The authoritative input is the final book-specific `<BOOK_STEM>_master.md` produced by the Translation Skill. It is the **only正文 source of truth** for PDF generation.

Never promote a temporary file such as `_build_master.md`, `_build_master_fixed.md`, `normalized_master.md`, `book_annotated.md`, generated TeX, or a debugging copy into a second正文 source. Every build starts again from the authoritative master. Temporary normalization exists only inside an ephemeral build directory and must not survive as workflow state.

Do not retranslate, rewrite, polish, summarize, silently correct, or reorder正文 in the PDF stage. Do not change stable footnote IDs, formulas, numbers, tables, quotations, glossary decisions, or image content merely to satisfy typesetting. If a genuine source/content error is discovered, report it separately; do not silently repair it in the PDF build.

Bundled files:

```text
build_pdf.py
book_filter.lua
preamble.tex
template.tex
```

`build_pdf.py` performs normalization, Pandoc AST preflight, structure inference, build, and automated QA. `book_filter.lua` turns the inferred H1 structure into explicit Part/Chapter/front-matter/Notes LaTeX commands and builds reciprocal endnote links. The TeX files provide the generic B5 layout.

## 1. Normal workflow

When the user asks to generate the PDF:

1. Read this Skill.
2. Locate the final `<BOOK_STEM>_master.md` and `assets/` if present.
3. Confirm the file is the assembled master, not an individual Part and not a prior temporary build input.
4. Inspect the master structure before compiling. Do not assume Pandoc will interpret raw Markdown correctly merely because `#` characters are visible in the source.
5. Adjust only necessary book-specific settings near the top of `build_pdf.py`, or use CLI overrides.
6. Run `build_pdf.py`.
7. Require the automated QA to pass.
8. Render representative pages and visually inspect them. Automated compilation success is not publication QA.
9. Only after both structural and visual QA pass, deliver the final PDF.

If the build fails, fix the narrowest build defect. Do not rewrite正文 as a workaround.

## 2. Book-specific settings

Normally edit only the `USER SETTINGS` block in `build_pdf.py`:

```python
INPUT_MD = "<BOOK_STEM>_master.md"
OUTPUT_PDF = ""          # blank -> input stem + .pdf

TITLE = "中文书名"
SHORT_TITLE = "短书名"
AUTHORS = ["作者"]
LANG = "zh-CN"
EDITION_NOTE = "中文翻译稿"

TOC_TITLE = "目录"
NOTES_TITLE = "注释"
SOURCE_TOC_TITLES = ("目录", "原书目录")
MAINMATTER_START = ""     # exact H1 only when auto-detection is unsuitable
SUPPRESS_FIRST_H1 = True  # assembled master normally begins with book-title H1
TOC_EXCLUDE_H1 = ()       # exact H1 titles to render but omit from TOC/bookmarks
OPENRIGHT = False         # digital-reading default
ASSETS_DIR = "assets"
MAX_OVERFULL_PT = 8.0
```

`OPENRIGHT = False` is the default because the project primarily produces digital-reading PDFs and should not create avoidable blank verso pages. Set it to `True` only when the user explicitly wants print-style right-hand Part/Chapter openings.

CLI overrides may be used, for example:

```text
python PDF_SKILL/build_pdf.py \
  --input <BOOK_STEM>_master.md \
  --output <BOOK_STEM>.pdf \
  --title "中文书名" \
  --short-title "短书名" \
  --author "作者"
```

Repeat `--author` for multiple authors.

## 3. Master Markdown preflight: mandatory

Before typesetting, the build must perform a temporary normalization and then inspect the Pandoc AST.

### 3.1 Temporary normalization

The authoritative master is never edited. A temporary `normalized_master.md` may be created only inside the build directory to:

- normalize CRLF/LF and remove a UTF-8 BOM;
- ensure every ATX heading has a legal block boundary before and after it;
- prevent `# 第一章 ...` or similar headings from being swallowed into a preceding list item or paragraph;
- annotate named footnote references so their source IDs survive Pandoc and can be used for reciprocal note links;
- remove duplicate automatic figure captions only when an image already has a separate immediately following `图...` / `表...` caption paragraph;
- perform narrowly defined transcription-level repairs to known control-character corruption when the visible intended TeX token is unambiguous.

Normalization must not modify visible正文 wording, mathematical meaning, note IDs, table data, image paths, or section order.

### 3.2 AST validation

Do not trust line-based Markdown inspection alone. Run Pandoc to JSON and verify that all intended H1 units are genuine AST `Header` nodes.

The build infers a structural manifest from the H1 sequence:

- first source title H1: normally suppressed as a duplicate of the generated title page;
- source `# 目录` / `# 原书目录`: used only as a placement marker, with its printed source contents skipped;
- front-matter H1s before main matter: top-level front units;
- `第X部分` / `Part X`: Part units;
- `第X章` / `Chapter N`: Chapter units;
- `附录` / `Appendix`: top-level back/main units;
- `# 注释`: source Notes shell, skipped and rebuilt from native notes.

The first Part or Chapter H1 is normally the main-matter start. If this cannot be detected safely, the build must stop and require `MAINMATTER_START` rather than guess.

Unknown H1s must **never be silently discarded**. After main matter starts, an unclassified H1 is preserved as a top-level unit and reported as a QA warning so the structure can be reviewed.

The same inferred manifest must drive both rendering and QA. Do not hard-code a specific book's chapter count, Part count, titles, or outline into the generic Skill scripts.

## 4. TOC and PDF bookmarks

The PDF should contain one generated TOC only. If the master contains a source-side `# 目录` / `# 原书目录`, keep it in the master but skip its printed entries during PDF generation.

Default hierarchy:

- front-matter H1: TOC/bookmark level 1;
- Chapter before any Part: level 1;
- Part: level 1;
- Chapter within a Part: level 2;
- Appendix: level 1 unless the book-specific structure clearly requires otherwise;
- Notes: level 1;
- H2/H3/H4正文 headings: visible in the book but **not** in the main TOC or PDF bookmarks.

Do not solve TOC problems merely by changing `tocdepth`. The book-level hierarchy must be explicit and validated against the inferred structural manifest.

Front-matter minor headings such as `编者`, `出版信息`, acknowledgments subheads, methodological subheads, chapter internal sections, and Notes group headings should not leak into the main TOC/bookmarks unless explicitly requested.

## 5. Page numbering and page labels

Page numbering is a publication invariant, not a cosmetic detail.

Front matter uses lowercase Roman numerals. The title page may hide the printed number while still belonging to front matter.

At the exact main-matter start, issue a real `\mainmatter` so the visible page number resets to Arabic `1`. Part/Chapter/Appendix/Notes after this point continue in one Arabic sequence and do not reset again.

The PDF must also contain logical page labels (`pdfpagelabels`) so readers such as Acrobat and Preview display `iii`, `iv`, `1`, `2`, `3` rather than only physical page indices.

Automated QA must verify:

- front matter has lowercase-Roman labels;
- the inferred main-matter opening has logical label `1`;
- a printed footer `1` is visible on that opening page unless the book-specific design intentionally suppresses it;
- Arabic labels remain continuous through the last page.

A build that compiles but leaves the entire book in Roman numerals is a failed build.

## 6. Typography defaults

The bundled design is a restrained B5 Chinese academic-book layout:

- B5: 176 × 250 mm;
- two-sided text block;
- inner margin about 22 mm, outer about 18 mm, top about 21 mm, bottom about 24 mm;
-正文 about 10.7 pt with approximately 15.5 pt leading;
- 2em first-line indent;
- moderate Chapter opening space rather than half-page blank bands;
- H2/H3/H4 sized clearly but conservatively;
- odd-page running head: current Chapter/unit title;
- even-page running head: short book title;
- centered footer page number;
- Chapter/Part opening pages suppress running heads.

Do not insert manual page-specific `\vspace` patches unless there is a reproducible local defect. Prefer semantic macros and stable layout parameters.

## 7. Mathematics: native size, shrink only

This is a hard rule learned from formula-heavy political-economy books.

**Never globally resize every display equation to a target width. Never use a transformation that can enlarge short equations.** A short equation such as `m^* = ρ/ν` must remain at normal display-math size.

The bundled pipeline wraps ordinary display equations in `\bookfitmath`, which:

1. typesets the equation at the book's normal display size;
2. measures its natural width;
3. leaves it unchanged if it fits;
4. shrinks it only if its natural width exceeds the configured fraction of the text block.

Long aligned equations may be reduced locally. Short equations must never be expanded to fill the line.

Tagged display equations may require a narrow temporary TeX normalization so `\tag{...}` remains valid. Preserve the formula and tag exactly.

After build, inspect formula-heavy representative pages. Log cleanliness alone cannot prove acceptable mathematical typography.

## 8. Images and captions

Images must never be cropped by the PDF build.

Ordinary figures should remain at natural size when they already fit. The build may shrink an oversized figure to fit the text block and page height, but it must not automatically enlarge a small raster image to `\linewidth`.

Image-based tables follow the same principle: fit down when necessary, never upscale merely to fill the line.

If the master contains both:

```markdown
![图1](assets/x.png)

*图1*
```

or another separate caption paragraph immediately after the image, suppress Pandoc's automatic image-alt caption in the temporary input so the final PDF shows the caption once. Do not produce `图 1: 图 1`, `Figure 1: 图 1`, or duplicate captions.

All image targets discovered in the Pandoc AST must exist. Remote images are not acceptable for an offline final-book build. Missing assets block the build.

If a supplied source PNG/JPEG is already cropped, blurred, or missing edge content, the build script cannot reconstruct absent pixels. Report that as an asset problem; do not conceal it by further cropping.

## 9. Tables

Readable Markdown tables should remain tables. Do not convert them into images merely because PDF layout is difficult.

Do not shrink **all** tables to a tiny global size just to make the widest table fit. The default table size should remain reasonably close to正文. If one or two tables are too wide, fix those tables locally through column spacing, local font reduction, landscape handling if explicitly approved, or another targeted solution.

Long tables may span pages. Wide tables must not be clipped beyond the text block. Table data and numeric values are immutable during typesetting.

Inspect at least one ordinary table and one dense/wide table in rendered output when the book contains tables.

## 10. Notes and reciprocal navigation

The Translation Skill assembles the source notes at the end of `master.md`; the PDF build converts正文 native Markdown notes into a book-end Notes chapter grouped by source H1 unit.

Requirements:

- one visible Notes entry per unique source note within its group;
-正文 note marker links to the correct Notes entry;
- each Notes entry has an exact backlink to the正文 citation point;
- repeated references to one source note produce multiple compact return links rather than duplicate Notes entries;
- Notes group headings remain visible but do not enter the main TOC/bookmarks;
- no duplicate PDF destination IDs;
- no orphan note definitions or references without definitions.

The master note IDs are stable workflow data and must not be renumbered in the source.

## 11. Build dependencies and portability

Standard dependencies:

```text
Python 3
PyMuPDF (import name: fitz)
Pandoc
XeLaTeX
xdvipdfmx
```

Use `ctexbook` and TeX Live fonts such as Fandol as the reliable fallback. Do not package or redistribute font files.

Pandoc's LaTeX image syntax changes between releases. The build must tolerate at least:

```text
\includegraphics{...}
\includegraphics[...]{...}
\pandocbounded{\includegraphics[...]{...}}
```

Do not make the final build depend on one exact Pandoc minor version without an explicit reason.

If a PowerShell launcher is supplied for Windows, save it as UTF-8 with BOM or keep it ASCII-only so Windows PowerShell 5.1 does not misparse non-ASCII strings. The Skill itself does not require PowerShell; `build_pdf.py` remains the canonical entry point.

## 12. Automated QA: required before publication

A successful XeLaTeX exit code is only the beginning. `build_pdf.py` must fail or warn on the following conditions.

### 12.1 Source/structure QA

- authoritative master hash changes during the build;
- missing/duplicate/orphan footnotes;
- intended H1s are not recognized by Pandoc;
- main matter cannot be safely detected;
- source TOC is duplicated in visible output;
- a structural H1 is silently lost;
- generated outline differs from the inferred manifest.

### 12.2 PDF QA

Verify:

- PDF exists and has pages;
- outline hierarchy exactly matches the inferred structural manifest;
- ordinary H2/H3/H4 do not leak into the main outline;
- Roman-to-Arabic page-label transition is correct;
- no visible Markdown `#` structural markers leak into PDF text;
- all referenced images appear;
- no duplicate caption patterns;
- all fonts are embedded;
- no fatal LaTeX errors;
- no missing-glyph warnings;
- no duplicate PDF destinations;
- overfull boxes remain below the configured tolerance or are explicitly investigated;
- note forward links, note anchors, and backlinks match the source note counts;
- internal destinations are valid.

The QA report must include the source SHA-256 so a report from an older/different master cannot be mistaken for proof that the current source built successfully.

## 13. Visual QA: mandatory

After automated QA passes, render representative pages to images and inspect them. This is not optional for a final publishing build.

At minimum inspect:

- title page;
- TOC first page and last page if multi-page;
- one front-matter page;
- main-matter opening page (`1`);
- one Part page if Parts exist;
- at least one Chapter opening;
- a formula-heavy page;
- a dense table page if tables exist;
- a figure + caption page if figures exist;
- a later-book Chapter opening;
- Notes first page if notes exist;
- final PDF page.

Check for:

- clipped or overlapping text;
- black boxes or missing glyphs;
- absurdly oversized or undersized formulas;
- tables with unreadably small type;
- image upscaling, cropping, or caption duplication;
- excessive chapter-title whitespace;
- isolated headings with poor page breaks;
- incorrect running heads;
- incorrect page numbers;
- avoidable nearly blank pages.

If a defect is visible, revise the generic template or make the narrowest book-specific change, rebuild from `master.md`, and repeat QA. Never declare completion solely because `qa_report.txt` says PASS.

## 14. Failure handling

When a build fails:

1. identify the exact stage: source QA, AST, Pandoc, Lua, TeX, XDV/PDF conversion, structural QA, note-link QA, or visual QA;
2. preserve the authoritative master unchanged;
3. if diagnosis requires intermediates, rerun with `--keep-temp` and inspect the temporary normalized Markdown / TeX / logs;
4. fix the narrowest generic-script or book-specific configuration problem;
5. rerun the full build from the authoritative master.

Do not patch a previously generated `book.tex` and treat it as the next build source. Do not reuse a stale `normalized_master.md` from a prior build.

## 15. Deliverables

Primary deliverables for the PDF stage:

```text
<BOOK_STEM>.pdf
qa_report.txt
```

Do not normally deliver temporary normalized Markdown, generated TeX, `.aux`, `.log`, `.toc`, `.xdv`, rendered PNGs, or debugging files.

When the whole publishing workflow is complete and `zlibrary_metadata.md` has also been generated, create `<BOOK_STEM>_final.zip` according to the project instruction. Include only the final master, final PDF, EPUB if applicable, glossary, metadata, and `assets/` if present; exclude Part working files, build intermediates, and `book_plan.md` unless the user explicitly requests them.
