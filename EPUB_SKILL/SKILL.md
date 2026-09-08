---
name: academic-book-epub
description: >
  Build and verify a polished EPUB3 from a completed Chinese academic-book master Markdown file
  produced by the translation workflow. Use when translation and final Markdown assembly are
  finished and the user wants an EPUB, with optional assets. Perform structural preflight, adjust
  only necessary book-specific build settings, reuse the bundled CSS and Lua resources, run the
  build, verify the EPUB, and deliver it without retranslating or substantially editing the book.
---

# Academic Book EPUB

## Scope

Use this skill after the translation/assembly stage is complete. The expected input is an already integrated Markdown master file, normally with:

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

Images, maps, photographs, and image-based complex tables normally live under `assets/` and are referenced with relative Markdown paths.

This skill is for **EPUB production only**. Do not retranslate, rewrite, polish, renumber notes, or reorganize the source book unless an actual structural error prevents a valid build.

Supporting files shipped with this skill:

```text
build_epub.py
epub_generic.css
epub_endnotes.lua
```

## 1. Normal workflow

When the user provides an assembled Markdown book and asks for EPUB:

1. locate the final master Markdown and `assets/` if present;
2. verify that the source is already assembled rather than a collection of untranslated Parts;
3. make only the small book-specific changes in the `USER SETTINGS` block at the top of `build_epub.py`;
4. run `build_epub.py` from the book project directory;
5. inspect the build result structurally;
6. deliver the generated `.epub`.

In normal cases, no other source modification is required.

## 2. Parameters GPT normally changes

Edit only these values unless the book genuinely requires something unusual:

```python
INPUT_MD = "book_master.md"
OUTPUT_EPUB = ""
TITLE = "中文书名"
AUTHORS = ["Author Name"]
LANG = "zh-CN"

TOC_TITLE = "目录"
TOC_DEPTH = 3
SPLIT_LEVEL = 1
NOTES_TITLE = "注释"
ASSETS_DIR = "assets"
COVER_IMAGE = ""
```

`OUTPUT_EPUB = ""` means the script uses the Markdown filename stem and adds `.epub`.

Because the Translation Skill treats Contents, Preface, main chapters, appendices, and Notes as peer-level H1 units, `SPLIT_LEVEL = 1` is normally correct. Do not change it merely for stylistic preference.

A CLI override is also available, for example:

```text
python EPUB_SKILL/build_epub.py --input Book_master.md --title "书名" --author "Author"
```

The top-of-file settings remain the preferred interface for GPT because they are easy to inspect and modify reproducibly.

## 3. Source Markdown assumptions

The master Markdown is authoritative.

Do not:

- change正文 wording;
- change quotations, statistics, years, percentages, or tables;
- renumber stable footnote IDs;
- alter glossary decisions;
- change image paths without a real broken-path problem;
- rebuild chapter hierarchy solely to fit EPUB styling.

If the Markdown has a source-side `# 目录` or `# 原书目录`, the Lua filter omits it from EPUB content because Pandoc generates the EPUB navigation TOC automatically.

If the Markdown has the final assembled `# 注释` section, the filter omits that source structural shell and rebuilds one real book-end EPUB Notes chapter from Pandoc native footnotes. Visible note numbering restarts within each source H1 book unit. Numbered chapters are grouped under headings such as `第三章`; appendices are grouped as `附录`.

## 4. Tables and images

Markdown tables are passed directly to Pandoc. Do not convert them back to images merely for EPUB.

Images should already use relative paths such as:

```markdown
![图 3.1](assets/fig_03_01.png)
```

`build_epub.py` includes the project directory and `assets/` in Pandoc's resource path.

If an image is genuinely missing, report the missing file. Do not fabricate or redraw it.

## 5. Build dependencies

The standard build requires:

```text
Python 3
Pandoc
```

Check `pandoc --version` if the build fails because the command is unavailable.

No separate YAML editing is normally needed. `build_epub.py` generates temporary metadata automatically from its USER SETTINGS.

## 6. What the build script does

The script performs:

```text
book_master.md
+ generated metadata
+ epub_generic.css
+ epub_endnotes.lua
        ↓
      Pandoc EPUB3
        ↓
      Book.epub
```

It also performs a basic ZIP/EPUB structural sanity check after generation.

The CSS is intentionally generic. Do not make a book-specific CSS copy unless an observed rendering problem requires it.

The Lua filter is likewise intended to match the master Markdown structure produced by the Translation Skill. Modify it only when the actual book structure differs materially from that convention.

## 7. QA

After a successful build, verify at minimum:

- EPUB file exists and is non-empty;
- EPUB package/navigation/content files exist;
- title and author metadata are correct;
- generated navigation TOC is present;
- source printed TOC is not duplicated unnecessarily;
- chapter splitting follows H1 boundaries;
- images are present;
- tables remain readable;
- `注释` appears at the end when the book has notes;
-正文 note links and note backlinks work when the reading environment permits inspection.

If only structural QA is available, state that rather than claiming a full visual-reader QA.

## 8. Error policy

If Pandoc fails, inspect the actual error and fix the narrowest relevant issue.

Do not respond to a build failure by rewriting book content.

Typical fixes are limited to:

- correcting `INPUT_MD`;
- correcting an `assets/...` path;
- correcting `TITLE` / `AUTHORS`;
- supplying a missing cover;
- adjusting `TOC_DEPTH` only when needed;
- making a minimal Lua/CSS adjustment for a genuinely different book structure.

## 9. Deliverable

The primary deliverable is the final `.epub` file.

Do not deliver temporary metadata or `.epub_build/` files unless the user asks for debugging materials.
