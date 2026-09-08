---
name: academic-book-pdf
description: >
  Build and verify a polished B5 Chinese academic-book PDF from a completed book-specific master
  Markdown file produced by the translation workflow. Use when translation and final Markdown
  assembly are finished and the user wants a PDF, with optional assets. Perform structural
  preflight, adjust only necessary book-specific build settings, reuse the bundled TeX and Lua
  resources, run the build, verify typography and endnote links, and deliver it without
  retranslating or substantially editing the book.
---

# Academic Book PDF

## Scope

Use this skill after the translation/assembly stage is complete. The expected master Markdown normally contains peer-level H1 units such as:

```text
# 目录                     (optional source-side printed TOC)
# 序言 / # 编者前言 / ...
# 第一章 ...
# 第二章 ...
...
# 附录                     (optional)
# 注释
## 序言
[^pr-001]: ...
## 第三章
[^ch03-001]: ...
## 附录
[^ap-001]: ...
```

Images and image-based complex tables normally live in `assets/` and are referenced using relative Markdown paths.

The assembled master is book-specific: use the stable `BOOK_STEM` established by the translation workflow, normally `<BOOK_STEM>_master.md`. The literal `book` is only the stem for a source actually named `book.pdf`; do not reuse it as a fixed prefix across different books.

This skill is for **PDF typesetting only**. The integrated Markdown master is authoritative. In normal cases the book should not need textual editing before building.

Supporting files shipped with this skill:

```text
build_pdf.py
template.tex
preamble.tex
endnotes.lua
```

The build script may generate a temporary annotated Markdown copy inside `PDF_SKILL/build/`. This copy exists only so named Markdown footnote IDs survive the Pandoc conversion long enough to build reciprocal PDF links. The authoritative book-specific master Markdown is never modified.

## 1. Normal workflow

When the user provides an assembled master Markdown and requests a PDF:

1. locate the final master Markdown and `assets/` if present;
2. confirm that the file has already been assembled and is not merely one translation Part;
3. modify only the small `USER SETTINGS` block near the top of `build_pdf.py`;
4. run `build_pdf.py` from the book project directory;
5. inspect the generated PDF and build log if necessary;
6. deliver the final `.pdf`.

For a correctly assembled book, running the script should normally be sufficient.

## 2. Parameters GPT normally changes

Edit only these values unless a real layout problem requires more:

```python
INPUT_MD = "<BOOK_STEM>_master.md"
OUTPUT_PDF = ""

TITLE = "中文书名"
SHORT_TITLE = ""
AUTHORS = ["Author Name"]
LANG = "zh-CN"
EDITION_NOTE = "中文翻译稿"

TOC_TITLE = "目录"
TOC_DEPTH = 1
NOTES_TITLE = "注释"
MAINMATTER_START = ""
ASSETS_DIR = "assets"
```

`OUTPUT_PDF = ""` means use the Markdown stem plus `.pdf`.

`SHORT_TITLE = ""` means use `TITLE` in the running head.

`MAINMATTER_START = ""` is normally correct. The Lua filter automatically inserts `\mainmatter` at the first numbered chapter such as `第一章 ...`. Set an exact H1 only for an unusual book whose main matter cannot be auto-detected.

CLI overrides are available, for example:

```text
python PDF_SKILL/build_pdf.py --input <BOOK_STEM>_master.md --title "书名" --author "Author"
```

The top-of-file USER SETTINGS remain the preferred GPT-facing interface.

## 3. Source Markdown assumptions

Do not modify content merely to satisfy the PDF template.

In particular, do not:

- retranslate or polish正文;
- change quotations, dates, statistics, tables, or examples;
- renumber stable Markdown footnote IDs;
- change glossary decisions;
- move notes again unless the master is actually malformed;
- alter image paths except to repair a real broken path.

The PDF build understands the assembled source structure. It omits a source-side `# 目录` / `# 原书目录` because the LaTeX template generates a real PDF table of contents. It also omits the already assembled source `# 注释` shell and rebuilds the final Notes chapter from Pandoc native footnotes.

Before Pandoc runs, `build_pdf.py` creates a temporary Markdown copy and inserts invisible annotation spans immediately before named正文 footnote references. This preserves the source footnote identity that Pandoc would otherwise discard. `endnotes.lua` uses that identity to create stable note destinations and exact return destinations without changing visible正文 or the master Markdown. If a heading itself carries a note marker, the generated LaTeX is normalized to use the plain heading as its short title, so the marker is not copied into the TOC or running marks and cannot create duplicate PDF destinations.

Visible endnote numbering restarts within each H1 source unit. A heading such as `# 第三章 劳动过程` is grouped under `## 第三章`; appendix notes are grouped under `## 附录`. If one source footnote is cited more than once within the same H1 unit, it is emitted once in the Notes chapter and receives multiple numbered return links.

## 4. Default PDF design

The included template is intentionally generic and already tuned for Chinese long-form academic books:

- B5 paper;
- two-sided book layout;
- right-hand chapter openings;
- generated title page;
- generated table of contents;
- Chinese正文 with 2em first-line indent;
- book-style chapter/section hierarchy with deliberately moderate white space around headings, so chapter and section openings remain clear without consuming an excessive fraction of the page;
- centered running heads and centered page numbers on both odd and even pages; the even-page short title and odd-page chapter title may differ, but both occupy the centered header position;
- multi-page Markdown tables via Pandoc/LaTeX;
- images constrained to the text block without cropping;
- compact front-matter and正文 lists: redundant Markdown hard breaks at the end of list items are removed in the temporary generated LaTeX, preventing illustration/table directories from acquiring an extra blank baseline after every entry;
- book-end Notes grouped by top-level source unit;
- bidirectional note navigation: each正文 note marker links to its endnote and every endnote has an exact backlink to the正文 citation;
- repeated references to one source note receive multiple compact return links (`↩1`, `↩2`, etc.) rather than duplicate endnote entries.

There is normally no reason to redesign these settings for each book.

Only modify `preamble.tex`, `template.tex`, or `endnotes.lua` after observing a specific reproducible defect that cannot be solved by the USER SETTINGS.

## 5. Tables and images

Markdown tables should remain Markdown tables. Pandoc converts them into LaTeX tables/longtables.

Do not convert a readable Markdown table into an image just to make PDF generation easier.

Images should use relative source paths such as:

```markdown
![图 3.1](assets/fig_03_01.png)
```

`build_pdf.py` includes the project directory and `assets/` in Pandoc's resource path.

If a source asset is missing, report it rather than fabricating an image.

## 6. Build dependencies

The standard build requires:

```text
Python 3
Pandoc
XeLaTeX
xdvipdfmx
```

Typical TeX installations provide XeLaTeX and xdvipdfmx. The template uses `ctexbook` and TeX Live's Fandol fonts to avoid dependence on a particular Windows system font.

No PowerShell script and no hand-edited YAML are required. `build_pdf.py` generates temporary metadata automatically from its USER SETTINGS.

## 7. Build pipeline

`build_pdf.py` runs:

```text
<BOOK_STEM>_master.md
        ↓
temporary invisible footnote-reference annotation
        ↓
Pandoc + endnotes.lua + generated metadata + template.tex
        ↓
book.tex
        ↓
XeLaTeX pass 1
XeLaTeX pass 2
XeLaTeX pass 3
        ↓
book.xdv
        ↓
xdvipdfmx
        ↓
Book.pdf
```

Three XeLaTeX passes are retained so the generated table of contents, page references, and book structure settle reliably.

Temporary build files are kept under `PDF_SKILL/build/` and are recreated on each run.

## 8. QA

After building, verify at minimum:

- the final PDF exists and is non-empty;
- title and author are correct;
- title page is present;
- generated TOC is present and not duplicated by the source-side printed TOC;
-前置部分 and main numbered chapters have sensible pagination;
- chapter starts and page numbers look normal;
- on representative odd and even正文 pages, both the running head and page number are horizontally centered rather than alternating between outer margins;
- tables do not obviously overflow;
- front-matter directories such as `插图目录` do not show artificial blank-line spacing between entries and do not consume avoidable pages;
- chapter and section headings have clear but restrained vertical spacing, without the large empty bands produced by overly generous title spacing;
- images are present and not cropped;
- `注释` appears at the book end when the book has notes;
- note group headings correspond to source units such as `序言`, `第三章`, `附录`;
- each正文 note marker links to the matching endnote;
- each generated endnote has at least one backlink and that backlink returns to the exact正文 citation point, not merely to a chapter or page;
- if a source footnote is cited multiple times, every citation gets its own return target and the endnote shows the corresponding multiple return links;
- no duplicate PDF destination IDs are produced.

When link inspection is available, test representative full round trips: `正文注释号 → 书末注释 → ↩ → 原正文位置`, including at least one note near the beginning, middle, and end of the book. If repeated-note references exist, test every return link on at least one repeated note.

If the environment supports rendering/visual inspection, inspect representative pages including the title page, TOC,正文, a dense table/image page, and Notes. The return-link symbol must remain unobtrusive and must not cause obvious line overflow or broken glyphs. If visual inspection is unavailable, perform structural QA and say so.

## 9. Failure handling

If Pandoc fails, inspect its message.

If XeLaTeX fails, `build_pdf.py` prints a useful excerpt from `PDF_SKILL/build/book.log`. Fix the narrowest relevant issue.

Common problems include:

- wrong `INPUT_MD`;
- missing `assets/...` image;
- malformed Markdown table;
- unsupported Unicode character in a table;
- missing TeX package;
- a book structure that genuinely differs from the Translation Skill convention.

Do not use a build error as a reason to rewrite正文.

## 10. Deliverable

The primary PDF deliverable is the final `.pdf` file.

When this PDF build is the final publishing stage of the translation project and the EPUB plus `zlibrary_metadata.md` have also been completed, additionally create `<BOOK_STEM>_final.zip` for convenient download. Include exactly the final `<BOOK_STEM>_master.md`, EPUB, PDF, `glossary.md`, `zlibrary_metadata.md`, and `assets/` when present. Exclude temporary build files, logs, intermediate Part files, and `book_plan.md` unless the user explicitly asks for them. Provide the ZIP link in the final response; individual file links may also be provided.

Do not deliver `book.tex`, `.aux`, `.toc`, `.xdv`, generated metadata, or logs unless the user asks for debugging materials.
