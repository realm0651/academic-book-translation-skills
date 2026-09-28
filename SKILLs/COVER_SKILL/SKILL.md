---
name: academic-book-cover
description: >
  Create and verify a restrained bilingual cover for a translated academic book after master Markdown
  assembly and before EPUB/PDF compilation. Default to a reference-reimagining workflow: use the
  original cover only as a visual/style reference, generate a new text-free background with similar
  broad palette, composition, motif, and scholarly tone, then add the exact Chinese title, English
  title, and author deterministically. Output cover.png, cover_epub.jpg, and cover_pdf.png; keep
  master.md unchanged; update book_plan and hand the cover assets to EPUB_SKILL/PDF_SKILL.
---

# Academic Book Cover

## Scope and place in the workflow

Use this skill **after** whole-book Markdown assembly is complete and **before** EPUB/PDF compilation. The final `<BOOK_STEM>_master.md` remains the only body manuscript; cover work must never alter it.

Default workflow position:

```text
... → <BOOK_STEM>_master.md → COVER_SKILL → EPUB_SKILL + PDF_SKILL → metadata → final ZIP
```

`book_plan.md` remains the workflow authority. When cover creation is completed, record the cover outputs and set `Next action` to EPUB/PDF publishing. Do not create a second cover-state file.

Bundled file:

```text
scripts/compose_cover.py
```

## 1. Default cover strategy: reference reimagining

The project default is **not** a direct copy of the original cover and **not** a completely unrelated AI design. Use the original cover as a visual/style reference and create a new, text-free cover background that preserves only broad visual qualities such as:

- overall palette;
- broad composition and balance;
- historical/academic mood;
- general motif or image category;
- density, texture, and degree of restraint.

Do not reproduce publisher logos, barcodes, ISBN blocks, series marks, exact typography, or other source-cover text. Do not deliberately reproduce a distinctive copyrighted illustration or photograph pixel-for-pixel. If the source cover is mostly typography, infer its palette and compositional restraint and create a simple new background rather than imitating the exact lettering.

Use the available image-generation tool for this first phase. The generated background must contain **no readable words, letters, pseudo-text, logos, or watermarks** and should deliberately leave a quiet area for later deterministic typography.

Fallbacks:

1. If the original cover is unusually simple and the user explicitly asks to preserve it closely, a direct rebuild may be used.
2. If the original cover is missing/unusable, create a restrained new scholarly background based on the book's subject and period.
3. If image generation is unavailable, report that limitation and use the narrowest non-generative fallback rather than silently copying the source cover.

## 2. Inputs

Required whenever available:

- final `<BOOK_STEM>_master.md`;
- original source PDF or a clear image of its front cover;
- `book_plan.md` for current workflow state;
- latest `glossary.md` when it contains a stable Chinese author name.

If the original PDF/cover is unavailable in a resumed session, ask only for that missing source (or a cover image), not for all historical Part files.

## 3. Text that belongs on the cover

The default cover contains only:

1. **Chinese main title**;
2. **English main title**;
3. **original author name**;
4. a stable Chinese author name may be added when one already exists in the project or is clearly established.

Do **not** add a subtitle, translator line, publisher, edition statement, ISBN, series name, blurb, slogan, or promotional copy unless the user explicitly requests it.

The cover title is a display title, not bibliographic metadata. If the bibliographic title contains a subtitle separated by a colon or equivalent delimiter, omit the subtitle on the cover while leaving the authoritative master/metadata title unchanged.

Never invent a Chinese author name solely for the cover. If no stable Chinese name is available, use the original name only.

## 4. Two-phase production method

### Phase A — create the text-free background

1. Render or inspect the original front cover.
2. Identify only broad visual features worth carrying over: palette, motif, composition, period feel, amount of negative space.
3. Generate a **new** text-free background in a vertical B5-compatible aspect ratio.
4. In the image-generation request, explicitly require:
   - no text, letters, logos, signatures, ISBNs, barcodes, or watermarks;
   - restrained academic-book tone;
   - one clean negative-space zone for title/author typography;
   - no gratuitous decorative elements unrelated to the source cover or subject.
5. Save the chosen background as a temporary `cover_base.png` or equivalent. It is a build intermediate and does not belong in the final ZIP.

Recommended image-generation framing:

> Reimagine this academic-book cover as a new text-free background. Preserve only the broad palette, compositional balance, visual motif category, historical mood, and restrained scholarly character. Do not copy any lettering, logo, barcode, publisher mark, or exact artwork. Leave a quiet uncluttered area in the upper third for later typography. No words, letters, pseudo-text, watermark, or signature anywhere.

Adjust the requested negative-space position when the source composition makes `center` or `bottom` more appropriate.

### Phase B — deterministic typography and exports

Do **not** ask the image model to typeset the final Chinese/English titles. Use `scripts/compose_cover.py` so the exact text comes from the project state and cannot be hallucinated by image generation.

Typical command:

```text
python COVER_SKILL/scripts/compose_cover.py \
  --base cover_base.png \
  --zh-title "中文主标题" \
  --en-title "English Main Title" \
  --author-original "Author Name" \
  --author-zh "作者中文名" \
  --position top \
  --out-dir .
```

`--author-zh` is optional. For multiple authors, pass a preformatted author string to `--author-original` and/or `--author-zh` rather than inventing a new layout system.

The script creates:

```text
cover.png       # canonical high-quality cover asset; include this in final ZIP
cover_epub.jpg  # EPUB input
cover_pdf.png   # PDF input
```

Default raster size is 1760 × 2500 px, matching the B5 PDF aspect ratio closely enough that EPUB/PDF share the same visual design without stretching.

## 5. Typography defaults

The project does not aim to simulate a commercial publisher's full cover system. Prioritize legibility and restraint.

Default hierarchy:

- Chinese title: largest;
- English title: clearly secondary but readable;
- author: smaller and separated from the titles;
- no subtitle.

Use a CJK-capable serif font and a compatible Latin serif font when available. Do not package or redistribute font files. The composition script searches installed fonts; if it cannot find a CJK-capable font, pass an installed font path explicitly instead of substituting broken glyphs.

The script may add a subtle light/dark translucent text field and shadow for legibility. It must not obscure the central visual subject or turn the design into a heavy opaque title card.

## 6. Canonical filenames and authority

The standard cover assets are always:

```text
cover.png
cover_epub.jpg
cover_pdf.png
```

These names are independent of `BOOK_STEM` and contain no spaces or `%20`.

Authority:

- `cover.png` is the canonical visible cover asset distributed in the final ZIP;
- `cover_epub.jpg` is the EPUB-specific derivative;
- `cover_pdf.png` is the PDF-specific derivative;
- `cover_base.png` is temporary and should not be packaged.

Do not create alternate long-lived files such as `cover_final_v2.png`, `cover_fixed.png`, or `epub_cover_new.jpg`. If a cover is revised, replace the standard files after QA.

## 7. Cover QA

Before marking the cover stage done, verify:

- Chinese title exactly matches the chosen main Chinese title and contains no subtitle;
- English title exactly matches the original main English title and contains no subtitle;
- author spelling is correct;
- a Chinese author name, if shown, is already established and not newly invented;
- no residual AI pseudo-text, logo, barcode, publisher mark, or watermark appears in the generated background;
- no title/author text is clipped or too close to the trim edge;
- Chinese and Latin glyphs render correctly;
- text remains legible at thumbnail size;
- the design remains restrained and recognizably related in mood to the source cover without being a direct copy;
- `cover.png`, `cover_epub.jpg`, and `cover_pdf.png` all exist and have the expected dimensions/aspect ratio;
- `master.md` hash/content is unchanged by cover work.

Visual inspection is mandatory. If the generated background contains pseudo-text or an awkward focal composition, regenerate the background rather than trying to hide the defect with typography.

## 8. State update and handoff

After QA succeeds:

- mark the cover stage `done` in the existing `book_plan.md`;
- record the three standard cover outputs;
- record only brief book-specific decisions when needed (for example `cover mode: reference-reimagining`, `text position: top`);
- set `Next action: EPUB/PDF publishing`.

The next publishing turn reads `EPUB_SKILL` and `PDF_SKILL`. EPUB must consume `cover_epub.jpg`; PDF must consume `cover_pdf.png`; the final ZIP must also include canonical `cover.png` at archive top level.

If the user asks only to revise the cover, regenerate/replace the standard cover assets and do not modify the master or retranslate anything.
