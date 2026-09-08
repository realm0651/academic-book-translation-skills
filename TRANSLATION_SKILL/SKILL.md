---
name: social-science-book-translation
description: >
  Translate complete English-language social science, history, political science, philosophy,
  political economy, anthropology, labour studies, gender studies, and related academic books into
  structured Chinese Markdown. Use when the source is one full PDF with either a reliable native
  text layer or a usable OCR text layer, and the task requires whole-book structure analysis,
  note-system classification, glossary management, Part-by-Part faithful translation, OCR-aware
  correction when needed, footnote/completeness QA, and final Markdown assembly. Do not use for
  image-only PDFs without a usable text layer, whole-book OCR, EPUB production, or PDF
  typesetting.
---

# Social Science Book Translation

## Scope and core architecture

This skill handles the workflow from one original English **PDF with a usable text layer** through:

- a native text PDF with a reliable embedded text layer; or
- an image/scanned PDF with an OCR text layer that is sufficiently complete and recoverable for scholarly translation.

1. whole-book structural inspection;
2. classification of the book's note system;
3. creation of a persistent `book_plan.md` for this specific book;
4. logical Part planning **without physically splitting the source PDF**;
5. creation of a book-wide `glossary.md`;
6. Part-by-Part Chinese translation directly from the original PDF using the page/range information stored in `book_plan.md`;
7. normalization of notes into native Markdown / Pandoc footnotes;
8. rolling glossary updates;
9. Part-level structural and completeness QA;
10. persistent workflow-state updates in `book_plan.md`;
11. final whole-book Markdown assembly with a unified endnotes chapter.

Do not perform EPUB generation or PDF typesetting unless the user explicitly asks for those tasks or another skill handles them.

Supporting script shipped with this skill:

```text
scripts/check_footnotes.py
```

Use it for footnote QA instead of reimplementing the same structural checks ad hoc.

## Book-specific filename stem

At initialization, derive one stable `BOOK_STEM` for the book. By default it is the original PDF filename without the `.pdf` extension; apply only minimal filename-safe cleanup when necessary, record the chosen value in `book_plan.md`, and do not change it later. The literal word `book` is never a fixed output prefix: source `book.pdf` yields `book_part1_中译.md`, while another source uses that book's own `BOOK_STEM`. Use `BOOK_STEM` for book-specific translated Part files, appendix/Notes working files, and the final master. Keep the generic workspace names `book_plan.md`, `glossary.md`, and `assets/` unchanged.

The previous workflow that created `<BOOK_STEM>_part1.pdf`, `<BOOK_STEM>_part2.pdf`, `<BOOK_STEM>_notes.pdf`, and similar derivative PDFs is **not the default workflow anymore**. Logical Parts are translation units recorded in `book_plan.md`; they are not source files that must be generated in advance.

---

# 1. Translation principles

The requested output is a scholarly full-text translation, not a summary.

Always:

- translate the complete requested source text;
- preserve argument structure, qualifications, examples, quotations, numbers, dates, percentages, statistical values, and table contents;
- preserve semantic heading hierarchy;
- preserve distinctions among related theoretical concepts;
- follow the current project glossary;
- use established Chinese forms for names, institutions, laws, movements, and historical terms when they can be identified reliably;
- preserve uncertainty when the source itself is uncertain.

Never:

- summarize or silently omit passages;
- expand the author's argument;
- replace the author's conceptual vocabulary with a preferred theory;
- silently correct substantive claims in the source;
- invent unreadable or missing source text;
- introduce GPT commentary into the translated book text.

The source text is authoritative. General knowledge may assist interpretation but must not replace or silently alter the source.

---

# 2. Classify the PDF and confirm that it is suitable

Before substantial processing, determine how the PDF carries text. Use the following source-type classification:

### PDF-T — native text PDF

The pages contain a reliable native / embedded text layer. Text extraction is substantially faithful and reading order is stable.

Use the normal translation workflow.

### PDF-O — image/scanned PDF with a usable OCR text layer

The visible pages are images or scans, but the PDF also contains an OCR text layer. PDF-O is supported when:

- the OCR layer covers the substantive text with reasonable continuity;
- paragraph and reading order are mostly recoverable;
- errors are predominantly local recognition defects rather than wholesale omissions;
- headings, note calls, names, numbers, quotations, and other critical details can be verified from the visible page when necessary;
- representative passages can be reconstructed reliably through extraction plus contextual and visual checking.

For PDF-O, enable **extraction + semantic/OCR correction mode** for the entire translation workflow. Do not reject a book merely because the OCR layer contains ordinary recognition errors that can be recovered reliably.

### PDF-I — image-only or unusable text layer

Use PDF-I when there is no usable text layer, or when the existing layer is so incomplete, garbled, or badly ordered that continuous source text cannot be reconstructed reliably.

PDF-I is outside the current workflow. In that case:

- do not pretend extraction succeeded;
- do not silently launch whole-book OCR;
- stop initialization and tell the user that the current file is image-only or has an unusable text layer.

This skill deliberately does not define a whole-book OCR pipeline.

## 2.1 Representative inspection

Before classification, inspect representative locations such as:

- front matter;
- an early chapter;
- a middle chapter;
- a late chapter;
- Notes / back matter where relevant.

For PDF-O, compare extracted text with the visible page at several representative locations. The purpose is not to demand error-free OCR, but to determine whether the text is sufficiently recoverable for accurate full-book translation.

Record the resulting source type in `book_plan.md`.

## 2.2 Extraction + semantic/OCR correction mode for PDF-O

For PDF-O, the extracted text is a **provisional transcription**, not the final authority. OCR correction is therefore a reading rule that persists through whole-book inspection, glossary construction, every Part translation, and QA.

When a defect is apparent, reconstruct the intended printed text using, in order:

1. the visible page image;
2. immediate sentence and paragraph context;
3. repeated occurrences elsewhere in the same book;
4. the current glossary and already established proper names / concepts, when they are independently supported by the book.

Typical OCR defects that may be corrected include:

- erroneous line-break hyphenation and broken words;
- words incorrectly joined or split;
- character confusions such as `l/1`, `I/l`, `O/0`, `rn/m`, or similar scan-dependent substitutions;
- corrupted ligatures, encoding artifacts, stray symbols, or lost punctuation;
- obvious misrecognition of names, titles, institutions, technical terms, abbreviations, and bibliographic strings;
- locally incorrect reading order caused by page layout;
- superscripts or note-call markers that are recoverable from the visible page;
- numbers or table entries that are clearly misread by the OCR layer and can be verified visually.

The purpose is **source reconstruction, not editorial correction**. Therefore:

- do not change an author's factual claim, argument, wording, data, or idiosyncratic spelling merely because it seems wrong;
- do not use general knowledge to overwrite legible source text;
- do not invent text that cannot be recovered;
- when extraction, context, and the visible page do not support a confident reading, flag the specific passage for verification rather than guessing.

The corrected reading—not the raw OCR string—is the source used for Chinese translation and glossary decisions.

Do not create a separate cleaned-English edition unless the user requests one. Do not re-OCR the complete book by default. Local OCR may be used only as a last resort for isolated passages when ordinary extraction plus direct visual inspection is insufficient and a suitable OCR tool is available.

---

# 3. Inspect the whole book before translating

Do not begin Part translation immediately.

First inspect enough of the complete PDF to determine:

- source filename and total physical PDF pages;
- front matter boundaries;
- table of contents;
- Foreword / Preface / Editor's Preface / Acknowledgements;
- Introduction;
- chapter boundaries and internal section structure;
- conclusion;
- appendices, especially methodology, data-source, research-design, or supplementary explanatory appendices;
- Notes / Endnotes location and organization;
- References;
- Bibliography;
- Name Index;
- Subject Index;
- any other back matter.

Distinguish **physical PDF page numbers** from printed book page numbers. Logical Part ranges in `book_plan.md` must use physical PDF pages or another precise locator that can be reliably reopened in the original PDF.

---

# 4. Classify the note structure

Every book must first be classified as **Case A** or **Case B**. This classification affects later footnote processing, but it does **not** require separate Notes PDFs.

## Case A — centralized Notes after the main text

Use Case A when the main body is followed by a distinct Notes / Endnotes section, commonly near References, Bibliography, Name Index, or Subject Index.

Typical structure:

```text
Main text
→ Notes
→ References / Bibliography
→ Index
```

In Case A:

1. identify the entire Notes physical-page range;
2. record that range in `book_plan.md`;
3. exclude that range from ordinary body Part ranges;
4. translate the body note calls first using stable semantic IDs;
5. translate the centralized Notes later from the same original PDF and map each definition to the already assigned ID.

Do not create `<BOOK_STEM>_notes.pdf` by default.

References and Bibliography are not translated by default. Indexes are not translated by default, though they may be inspected for glossary construction.

## Case B — notes embedded in or attached to chapters

Use Case B when notes occur inside the body structure, including:

- page-bottom footnotes;
- notes embedded directly in chapter pages;
- chapter-end notes placed immediately after each chapter;
- note sections distributed throughout the book.

In Case B:

- keep the notes inside the same logical Part as the chapter or section they belong to;
- translate those notes in the same translation pass;
- after the translatable body ends, later References / Bibliography / Index material is not translated by default.

Never apply Case A logic to a Case B book or vice versa.

---

# 5. `book_plan.md` is the canonical book-specific plan and workflow state

After whole-book inspection and before systematic translation, create:

```text
book_plan.md
```

`book_plan.md` is a persistent operational file for this book. It replaces the need to create derivative Part PDFs merely to remember boundaries.

At the start of every later translation step, read:

1. `TRANSLATION_SKILL/SKILL.md` for general rules;
2. this book's current `book_plan.md` for book-specific structure and state;
3. the newest `glossary.md` for fixed translations;
4. the original full PDF for the actual source text.

Do not rely only on chat memory when `book_plan.md` is available.

## 5.1 Required content of `book_plan.md`

A useful plan should contain at least:

```markdown
# Book Plan

## 1. Source

- Source PDF: `BookName.pdf`
- BOOK_STEM: `BookName`
- PDF type: PDF-T / PDF-O
- Text handling: direct extraction / extraction + semantic/OCR correction
- Total physical PDF pages: xxx
- Notes type: Case A / Case B

## 2. Translation scope

Translate:
- ...

Do not translate by default:
- References
- Bibliography
- Name Index
- Subject Index
- publisher advertisements / blank pages / other non-substantive matter

## 3. Book structure

| Unit | Contents | Physical PDF pages | Translation treatment |
|---|---|---:|---|
| Front matter | ... | 1–12 | Part 1 |
| Introduction | ... | 13–40 | Part 2 |
| Chapter 1 | ... | 41–78 | Part 3 |
| Notes | ... | 301–336 | Case A centralized Notes |
| References | ... | 337–360 | inspect only / not translated |

## 4. Logical Parts

| Part | Contents | Source range in original PDF | Output Markdown | Footnote prefix | Status | Glossary used |
|---|---|---|---|---|---|---|
| Part 1 | Front matter + Preface | pp. 1–18 | `<BOOK_STEM>_part1_中译.md` | `pr` where applicable | pending | v1.0 |
| Part 2 | Introduction | pp. 19–47 | `<BOOK_STEM>_part2_中译.md` | `intro` | pending | v1.0 |
| Part 3 | Chapter 1 | pp. 48–91 | `<BOOK_STEM>_part3_中译.md` | `ch01` | pending | v1.0 |

## 5. Centralized Notes plan

- Applicable only for Case A.
- Notes source range: pp. xxx–yyy
- Expected grouping: Preface / Introduction / Chapter 1 / ...
- Output: `<BOOK_STEM>_notes_中译.md`
- Status: pending

## 6. Appendices

- Source range(s): ...
- Output: `<BOOK_STEM>_appen.md`
- Footnote prefix: `ap`
- Status: pending

## 7. Stable conventions for this book

- Top-level heading mapping: ...
- Footnote ID scheme: ...
- Anonymous case names: ...
- Special table / figure treatment: ...
- Any book-specific translation constraints: ...

## 8. Current state

- Initialization: done
- Latest glossary: v1.0
- Completed: none
- Next action: translate Part 1

## 9. Unresolved items

- ...
```

Do not fill sections with empty boilerplate if the book has no such material.

## 5.2 `book_plan.md` maintenance

After every completed stage, update the same file rather than creating `book_plan_v2.md`, `book_plan_v3.md`, etc.

At minimum update:

- the completed Part's status;
- its actual output filename;
- the glossary version used / produced;
- any new book-specific convention discovered;
- unresolved source problems, if any;
- `Current state` and `Next action`.

Use concise statuses such as:

```text
pending
in progress
done
blocked
```

Do not turn `book_plan.md` into a verbose diary or simulated Git log. It is an operational state file.

---

# 6. Logical Part planning rules

A Part is now a **logical translation unit inside the original PDF**, not a separate PDF file.

## 6.1 Front matter and Preface

Everything through the end of the **Preface** should normally form Part 1.

This may include title pages, copyright, dedication, contents, lists of figures/tables, Foreword, Acknowledgements, and Preface.

```text
Front matter + Preface → Part 1
```

If there is no explicit Preface, use the last front-matter section before Introduction or Chapter 1 as the end of Part 1.

If an Introduction follows the Preface, it normally becomes the next Part rather than being automatically merged into Part 1.

## 6.2 Chapters

After front matter, the default unit is **one chapter per Part**.

For example:

```text
Part 1 = front matter + Preface
Part 2 = Introduction
Part 3 = Chapter 1
Part 4 = Chapter 2
Part 5 = Chapter 3
```

Preserve chapter boundaries whenever practical.

## 6.3 Acceptable Part size

A Part of approximately **20–80 physical PDF pages** is acceptable.

Do not force all Parts toward identical length. Semantic boundaries are more important than numerical symmetry.

## 6.4 Parts shorter than 20 pages

If a prospective Part is under approximately 20 pages, it may be merged with an adjacent Part.

When both previous and next Parts are possible merge targets:

1. compare their page counts;
2. prefer merging with the adjacent Part that is itself shorter;
3. keep the resulting Part reasonably manageable;
4. preserve conceptual and chapter coherence where possible.

A merged Part may contain more than one chapter. Keep the original chapter headings intact.

## 6.5 Chapters longer than 80 pages

If a single chapter exceeds roughly 80 pages:

1. inspect its internal section structure;
2. divide it into two or more logical Parts at the highest meaningful internal heading boundary;
3. prefer a natural conceptual break;
4. aim for resulting Parts within roughly 20–80 pages;
5. never divide a paragraph, table, figure block, or note block arbitrarily.

Sequential Part numbers are still used even if two Parts belong to the same chapter. Footnote IDs remain chapter-based where the chapter is known.

## 6.6 Analytical appendices

Appendices that contain substantive material such as methodology, data sources, research design, robustness discussion, supplementary analysis, or other explanatory material are part of the translatable book content.

By default:

- record their source range(s) in `book_plan.md`;
- translate them after the ordinary numbered Parts unless their original position requires another order;
- output substantive appendices as `<BOOK_STEM>_appen.md` when treated as one appendix translation unit;
- retain each appendix's own top-level `#` heading in Markdown.

Publisher advertisements, blank pages, purely administrative matter, and other non-substantive back matter are not treated as analytical appendices unless the user asks.

Appendix footnotes use one stable appendix sequence:

```text
[^ap-001]
[^ap-002]
[^ap-003]
```

## 6.7 Case A centralized Notes

Centralized Notes are a separate **logical translation stage**, not a separate source PDF.

Record the Notes source range and status in `book_plan.md`. Translate the Notes only after the body note calls have been assigned stable IDs, unless a different order is necessary for reliable mapping.

---

# 7. Do not physically split the source PDF by default

The standard workflow keeps the complete original PDF as the sole source document.

Therefore:

- do not create `<BOOK_STEM>_part1.pdf`, `<BOOK_STEM>_part2.pdf`, etc. merely for workflow management;
- do not create `<BOOK_STEM>_notes.pdf` or `<BOOK_STEM>_appen.pdf` merely to isolate ranges;
- do not maintain `split_pdf.py` as a required component of this skill;
- do not ask the user to download and re-upload derivative Part PDFs between translation rounds.

For each Part, reopen the original PDF and read only the range specified in `book_plan.md`.

If the current environment temporarily cannot reopen the original PDF, ask for **that original PDF only** (or the minimum missing source), not for a full set of derivative Part files.

If the user explicitly requests physical PDF splitting for another purpose, treat that as a separate optional task rather than the default translation workflow.

---

# 8. Markdown top-level structure

The following major book divisions are treated as peers in translated Markdown and therefore use a single `#` heading when they appear:

```markdown
# 目录
# 序言
# 编者前言
# 读者的话
# 导论
# 第一章 ……
# 第二章 ……
# 附录 ……
```

A logical Part may contain more than one such `#` heading. Do not nest a major book division merely because it shares a translation Part with another division.

Lower-level sections inside a chapter or appendix use `##`, `###`, and so on according to the source's semantic hierarchy.

---

# 9. Build `glossary.md` before systematic Part translation

After whole-book inspection and `book_plan.md` creation, inspect the book globally and create the initial book-wide glossary.

The glossary must reflect the **whole book**, not merely Part 1.

For PDF-O, glossary headwords and proper names must be based on the corrected reading of the printed source, not on obvious OCR misspellings or encoding artifacts.

Useful evidence includes:

- table of contents;
- Preface;
- Introduction;
- chapter titles;
- representative passages across the book;
- passages where the author defines concepts;
- recurring technical vocabulary;
- Subject Index, when useful;
- Name Index, when useful;
- recurring people, institutions, organizations, policies, events, and case names.

Do not turn the Subject Index into a line-by-line bilingual index. The goal is a stable translation system.

Prioritize:

- core theoretical concepts;
- high-frequency concepts;
- terms with multiple plausible Chinese translations;
- near-synonyms the author distinguishes;
- book-specific usages;
- important people, institutions, organizations, laws, policies, events, and place names;
- anonymous case names that must remain stable across Parts.

Recommended file:

```text
glossary.md
```

For this workflow, the glossary is not only a bilingual term list. It also carries the controlled **first-appearance rendering state** needed to keep proper names and key academic terms consistent across Parts. Use a Markdown table with these columns unless the book has a documented reason to simplify it:

```markdown
| Source | Translation | Type | First-use | Subsequent-use | Status | Notes |
|---|---|---|---|---|---:|---|
| labour process | 劳动过程 | term | 中文（English） | 中文 | 0 | 核心理论术语 |
| Guy Standing | 盖伊·斯坦丁 | person | 中文（English） | 中文 | 0 | 正文人物名；引文不套用 |
| International Labour Organization | 国际劳工组织 | institution | 中文（English, ILO） | 中文 / ILO，按正文需要 | 0 | |
| Fiverr | Fiverr | platform | English | English | — | 无需强行音译 |
| Amazon Mechanical Turk | Amazon Mechanical Turk | platform | English（AMT） | AMT / English，按正文需要 | 0 | |
| London | 伦敦 | place | 中文 | 中文 | — | 通行中文地名 |
```

Column meanings:

- `Source`: the corrected original-language form used as the lookup key; for PDF-O, never use an obvious OCR misspelling as the headword.
- `Translation`: the fixed Chinese rendering when Chinese is used. This field is lexical authority and must not be changed merely because `Status` changes.
- `Type`: use a stable category such as `term`, `person`, `place`, `institution`, `company`, `platform`, `law`, `policy`, `event`, `title`, or `other`.
- `First-use`: the form to print at the first eligible substantive occurrence, for example `中文（English）`, `中文（English, ABBR）`, `English（ABBR）`, `中文`, or `English`.
- `Subsequent-use`: the form to use after the first eligible occurrence has been established.
- `Status`: `0` means the required first-use form has not yet been consumed in translated reading text; `1` means it has; `—` means no first-use state is needed because the entry is always rendered the same way.
- `Notes`: brief justification, disambiguation, official-name information, contested translation choices, or a reminder that citation/reference strings are exempt.

If translation may proceed out of book order, an optional `First location` column may be added for status-sensitive entries. It should record the earliest eligible substantive location in original book order, not merely the first location encountered during workflow execution.

Systematic Part translation begins only after `glossary.md` v1.0 exists.

---

# 10. Glossary rules

When fixing a translation:

- distinguish concepts the author distinguishes;
- do not collapse theoretically different terms into one Chinese expression;
- use established disciplinary translations where appropriate;
- explain contested choices briefly;
- distinguish ordinary and technical senses where necessary;
- preserve the author's conceptual vocabulary even if another wording sounds stylistically smoother.

The glossary has priority over ad hoc translation choices in individual Parts.

## 10.1 Entity and term categories

Apply first-appearance rules by category rather than treating every foreign string the same way.

### Key academic terms

Use `中文（English）` at the first eligible occurrence when the item is a central theoretical concept, disciplinary term, author-defined analytical category, term with competing Chinese translations, or another recurring concept whose English form materially helps scholarly identification. Use only the fixed Chinese form thereafter.

Do **not** add English parentheticals to ordinary vocabulary merely because it appears in the glossary. Entries such as common words for worker, company, employment, production, and similar non-technical language normally use Chinese only.

### People

For a person named in narrative or expository prose, prefer an established Chinese name where one exists. Otherwise use a reliable conventional transliteration when Chinese rendering is appropriate. At the first eligible narrative occurrence, normally render:

```text
中文名（Original Name）
```

Thereafter use the fixed Chinese name, following the source's level of reference where practical. Do not force the English form to reappear merely because the person appears in a new Part.

This rule applies to the person as a **narrative entity**, not to bibliographic identity strings. Author names inside author-year citations, note citations, References, Bibliography, bibliographic lists, and similar apparatus remain in the source bibliographic form unless the source itself gives otherwise.

### Places

Common, standardized Chinese place names normally use Chinese only, for example `伦敦`, `纽约`, `英国`, `德国`. Do not mechanically produce forms such as `伦敦（London）`.

For obscure, potentially ambiguous, or book-specific locations where the original form is useful for identification, `中文（Original）` may be used at the first eligible occurrence and Chinese alone thereafter.

### Institutions, organizations, laws, policies, and events

When a stable Chinese form exists and the original name or abbreviation is useful, normally use:

```text
中文名（Original Name, ABBR）
```

on first eligible occurrence, then the fixed Chinese name or established abbreviation according to `Subsequent-use`. Avoid inventing abbreviations not used or clearly licensed by the source.

### Companies, brands, and platforms

Do not mechanically transliterate every company or platform name.

- If there is a stable, context-appropriate official or established Chinese name, it may be used according to the glossary, normally with the original name at first eligible occurrence.
- If there is no stable Chinese name, or the brand is conventionally used in its original form in Chinese scholarship, keep the original form throughout; use `Status = —` unless a first-use abbreviation or explanatory form is needed.
- If the platform has a standard abbreviation useful to the book, first use may be `Original Name（ABBR）`, followed by the abbreviation or original form as specified in `Subsequent-use`.
- Never invent a Chinese brand name merely to satisfy bilingual formatting.

## 10.2 What counts as a first occurrence

`Status` is consumed only by the first **eligible substantive occurrence in the translated reading text, in original book order**. A mere string appearance does not automatically count.

The following do **not** consume first-use status:

- author-year citation strings such as `(Duggan et al., 2020)` or `(Howcroft & Bergvall-Kareborn, 2019)`;
- References or Bibliography entries;
- Name Index or Subject Index entries;
- pure bibliographic strings inside notes;
- table-of-contents listings, running heads, publisher advertisements, copyright metadata, or credits that merely list a name;
- image-source / permissions credits that do not form part of substantive exposition.

A substantive explanatory sentence in the main text, translated appendix, caption, or note may consume first-use status when the entity or concept is genuinely introduced there.

If a surname appears earlier only inside a citation, that does not prevent the later first narrative mention from being rendered as `中文名（Original Name）`.

If Parts are translated out of order, do not let workflow order redefine first occurrence. Use original book order and, when necessary, the optional `First location` field or a targeted search of the original PDF.

## 10.3 Status transitions

For entries with `Status = 0`:

1. verify that the current location is the first eligible substantive occurrence in original book order;
2. render exactly according to `First-use`;
3. change `Status` to `1` in the current glossary after the translated occurrence has actually been written;
4. use `Subsequent-use` thereafter across all later Parts.

For entries with `Status = 1`, do not repeat the first-use English parenthetical unless the source itself requires the English form for a new analytical reason or the glossary explicitly marks a custom exception.

For entries with `Status = —`, render the entry the same way every time according to the glossary.

`Status` controls presentation only. It must never determine or alter the lexical translation stored in `Translation`.

The initial glossary remains open to genuinely new recurring terminology discovered later.

Prefer adding new terms over repeatedly rewriting established translations.

If an existing fixed translation must change, record:

```text
旧译法：
新译法：
修改原因：
受影响的 Part：
```

Do not silently rewrite earlier completed Parts unless the user requests consistency repair.

---

# 11. Part translation workflow

For each logical Part:

1. read the current `book_plan.md`;
2. read the newest `glossary.md`;
3. identify the Part's source range in the **original complete PDF**;
4. reopen and read that range from the original PDF;
5. if the source is PDF-O, treat extracted text as provisional and continuously apply the extraction + semantic/OCR correction rules in Section 2.2 before and during translation; visually verify ambiguous names, quotations, numbers, note calls, headings, broken words, and suspicious characters;
6. identify the chapter(s), heading hierarchy, tables, figures, and source note calls in that range;
7. translate the complete Part from the reliable reconstructed reading;
8. preserve headings and paragraph order;
9. normalize notes to native Markdown / Pandoc syntax;
10. place Case B footnote definitions at the **end of the Part Markdown file**;
11. convert suitable tables to Markdown;
12. preserve figures, captions, and textual references;
13. perform completeness and footnote QA, plus OCR-specific QA for PDF-O;
14. update `glossary.md` when genuinely new stable terminology appears **and** persist any first-use `Status` transitions created by this Part;
15. save the translated Markdown under the output filename already specified in `book_plan.md`;
16. update `book_plan.md` status, glossary version, and next action.

Default translated filenames:

```text
<BOOK_STEM>_part1_中译.md
<BOOK_STEM>_part2_中译.md
<BOOK_STEM>_part3_中译.md
...
```

The user may override this naming convention.

Do not paste the entire translation into chat when a file deliverable was requested. Create the file and provide it.

---

# 12. Heading structure

Preserve the source book's semantic hierarchy.

Example:

```markdown
# Chapter title
## Section title
### Subsection title
```

Do not create headings merely because source text is bold.
Do not flatten chapter / section hierarchy.
Do not insert artificial headings such as `Translation`, `Translated Text`, or `Part Translation` unless they belong to the source.

---

# 13. Native Markdown footnotes and fixed ID convention

All translated Markdown must use native Markdown / Pandoc footnotes:

```markdown
正文。[^ch01-001]

[^ch01-001]: 注释正文。
```

Never use HTML anchor-style notes.
Never use bare IDs such as `[^1]`, `[^2]` when the stable semantic ID is known.
Every ID must be unique across the whole book.

Use these standard IDs:

### Preface

```text
[^pr-001]
[^pr-002]
```

If the Preface contains notes, use `pr`.

### Introduction

```text
[^intro-001]
[^intro-002]
```

### Numbered chapters

```text
[^ch01-001]
[^ch01-002]
[^ch02-001]
```

Use at least two digits for chapter numbers and three digits for note numbers.

### Conclusion

```text
[^conclusion-001]
```

### Appendices

```text
[^ap-001]
[^ap-002]
```

Do not reset chapter-based IDs merely because one chapter is divided across two logical Parts. If Chapter 4 spans Part 5 and Part 6, its notes continue as `ch04-...`.

If two short chapters are merged into one logical Part, each chapter retains its own prefix.

Once a stable ID is assigned, do not rename it without changing both its正文 reference and its definition.

---

# 14. Case A note workflow — centralized Notes

In Case A,正文 note calls and note definitions are physically separated in the original book.

While translating body Parts:

1. identify every note call;
2. identify the section/chapter to which it belongs;
3. assign the stable semantic ID;
4. preserve the original note order.

Examples:

```text
Preface note 1      → [^pr-001]
Introduction note 3 → [^intro-003]
Chapter 3 note 7    → [^ch03-007]
Appendix note 2     → [^ap-002]
```

When the `book_plan.md` state reaches the centralized Notes stage:

1. reopen the original PDF at the Notes range recorded in `book_plan.md`;
2. preserve the source's chapter / section grouping;
3. match each source note to the already assigned正文 ID;
4. translate the complete note;
5. use **exactly the same ID** as the body reference;
6. never guess when the correspondence is uncertain.

The translated Notes file may be named:

```text
<BOOK_STEM>_notes_中译.md
```

It should contain native definitions such as:

```markdown
[^ch03-007]: 注释全文……
```

If extraction order or formatting makes a mapping uncertain, flag the specific note for verification rather than attaching the wrong definition.

---

# 15. Case B note workflow — notes embedded in the body

In Case B, notes are translated together with their logical Part.

Convert source note calls to stable IDs in正文, for example:

```markdown
正文。[^ch03-007]
```

Translate the corresponding note in full.

Regardless of whether the source note appeared at the bottom of a page, immediately after a paragraph, or at the end of a chapter, the translated Part Markdown must collect all footnote definitions at the end of that Part file.

Required working-file structure:

```markdown
# 第三章 ……

正文……[^ch03-001]

更多正文……[^ch03-002]

## 小节

正文……[^ch03-003]

[^ch03-001]: 第一条注释全文……

[^ch03-002]: 第二条注释全文……

[^ch03-003]: 第三条注释全文……
```

After the first `[^id]:` definition begins, do not place ordinary正文, headings, tables, or figures after the definitions. The definitions form the final section of the Part file.

If one Part contains two short chapters, collect **all** of that Part's note definitions at the end while preserving chapter-specific IDs.

Do not create a separate `<BOOK_STEM>_notes_中译.md` for Case B.

---

# 16. Footnote QA script

Use `scripts/check_footnotes.py` after producing or modifying translated Part Markdown.

Examples:

```bash
python scripts/check_footnotes.py <BOOK_STEM>_part1_中译.md
```

Case A whole-project check:

```bash
python scripts/check_footnotes.py \
  <BOOK_STEM>_part1_中译.md \
  <BOOK_STEM>_part2_中译.md \
  <BOOK_STEM>_notes_中译.md
```

Directory check:

```bash
python scripts/check_footnotes.py GPT_translation/
```

Final assembled master check:

```bash
python scripts/check_footnotes.py --strict-ids <BOOK_STEM>_master.md
```

The checker reports:

- duplicate footnote definitions;
- references with no definition;
- definitions with no reference;
- non-standard footnote IDs;
- ordinary content appearing after footnote definitions have begun;
- numbering gaps within the same prefix.

By default, non-standard IDs and numbering gaps are warnings. Use `--strict-ids` when strict validation is required.

---

# 17. Tables

Translate tables whenever reasonably possible and reconstruct them as Markdown tables.

Preserve:

- table number;
- title;
- row labels;
- column labels;
- values;
- units;
- table notes.

Do not simplify numerical tables, silently round values, or modify statistics.

If a table is structurally too complex for reliable Markdown conversion, preserve it as an image or retain its position using available file tools rather than inventing a simplified table. Translate the table title, caption, headings, and explanatory notes whenever they can be recovered reliably.

---

# 18. Figures, maps, photographs, and visual material

Do not recreate figures from textual guesses.

Preserve figure numbers, titles, captions, and正文 references.

Extract source figures, maps, photographs, and other non-table visual material into an `assets/` directory whenever the available environment supports reliable extraction. Use project-relative paths:

```markdown
![图 3.2](assets/fig_03_02.png)
```

The Markdown should reference the asset from its correct position in the translated text.

Never place sandbox paths, local absolute paths, or inaccessible internal paths into final Markdown.

If visual extraction is unavailable, do not fabricate the missing visual content.

---

# 19. Original page numbers

Do not add internal source-location markers such as:

```text
source_pdf_page: 37
```

to the translated正文.

However, page numbers that are genuinely part of the original book must remain where appropriate, including printed Contents page references and explicit page cross-references inside the author's text.

Physical PDF ranges are recorded in `book_plan.md` for workflow control only; they are not inserted into the translated正文.

---

# 20. Rolling glossary updates

During every Part translation, watch for newly appearing people, theoretical terms, institutions, organizations, policies, events, place names, companies, platforms, and other expressions whose translation or first-use rendering should remain stable in later Parts.

When a genuinely important new name or recurring term appears:

1. add it to the glossary using the structured fields in Sections 9–10;
2. preserve existing organization;
3. determine `Type`, `First-use`, `Subsequent-use`, and `Status`;
4. if the first eligible occurrence has just been translated in the current Part, save the new entry with `Status = 1`; otherwise save it with `Status = 0` when a first-use transition is still pending;
5. increment the glossary version if versioning is used and the lexical inventory, fixed translation, classification, or rendering rule changed;
6. state which Part introduced the additions;
7. update `book_plan.md` with the newest glossary version.

A pure `Status` transition from `0` to `1` is operational state, not a lexical glossary revision. Persist it in the same `glossary.md`, but do not increment the glossary version **solely** for that transition. This prevents meaningless version inflation while preserving first-use state across Parts.

If a Part has neither lexical glossary changes nor status transitions, leave the glossary file untouched.

All subsequent Parts use the newest glossary file, including its current statuses.

---

# 21. First appearance of concepts and names

First-appearance rendering is mandatory when the glossary marks it, not an ad hoc stylistic choice.

For each status-sensitive entry:

- `Status = 0` + first eligible substantive occurrence → use `First-use`, then set status to `1`;
- `Status = 1` → use `Subsequent-use`;
- `Status = —` → use the same prescribed form throughout.

Key academic terms normally use first-occurrence `中文（English）` only when the English form materially helps scholarly identification. Narrative person names normally use `中文名（Original Name）` at first eligible occurrence. Common place names and untranslatable / conventionally original-form brands normally do not receive unnecessary bilingual parentheses.

Do not apply these rules to author-year citations or bibliographic identity strings. Citation and reference formatting is governed by Section 22 and remains source-faithful.

The glossary controls cross-Part consistency and first-use state.

---

# 22. References, Bibliography, citations, and Index

By default:

- do not translate References;
- do not translate Bibliography;
- do not translate Name Index;
- do not translate Subject Index.

Indexes may be inspected for glossary construction.

Author names and other bibliographic identity strings inside in-text citations remain in the source bibliographic form. For example, preserve forms such as:

```text
(Howcroft & Bergvall-Kareborn, 2019)
(Duggan et al., 2020)
```

rather than replacing those names with Chinese transliterations from the narrative-person glossary. This applies equally to citation clusters, parenthetical references, source lists, and ordinary bibliographic strings inside translated notes.

References contained inside ordinary Notes remain part of those Notes and must be preserved when the Notes are translated. Translating the surrounding explanatory note does not imply translating the cited authors' names or bibliographic titles unless the source itself treats them as ordinary narrative text and the project explicitly requires it.

Citation/reference occurrences do not change a glossary entry's first-use `Status`.

Any exception to these defaults should be recorded in `book_plan.md` under Translation scope.

---

# 23. QA after every translated Part

Before marking a Part `done` in `book_plan.md`, verify:

## Completeness

- the Part begins and ends at the intended range from `book_plan.md`;
- no正文 section or paragraph is intentionally omitted;
- no section is summarized;
- quotations are preserved;
- tables and captions are present;
- notes are present or correctly mapped to centralized Notes.

## Structure

- major book divisions are top-level `#` headings when present;
- chapter headings are preserved;
- section headings are preserved;
- hierarchy is coherent;
- no artificial GPT headings appear.

## Terminology

- glossary terms use fixed translations;
- related concepts remain distinct;
- proper names remain consistent;
- status-sensitive entries use `First-use` exactly once at the earliest eligible substantive occurrence in original book order;
- later occurrences use `Subsequent-use` without unnecessary repeated English parentheticals;
- ordinary vocabulary has not been over-marked with English merely because it appears in the glossary;
- common place names and original-form brands follow their category-specific rendering rules;
- author-year citations and bibliographic identity strings remain source-faithful and have not been replaced by Chinese narrative-name forms.

## Numbers

- dates match source;
- percentages match source;
- statistics match source;
- table values match source.

## Footnotes

- Preface notes use `[^pr-001]` form;
- Introduction notes use `[^intro-001]` form;
- chapter notes use `[^ch01-001]` form;
- appendix notes use `[^ap-001]` form;
- IDs are unique across the book;
- Case A正文 calls are ready to match centralized Notes definitions;
- Case B definitions are collected at the end of the Part file;
- no HTML anchor footnotes remain;
- `scripts/check_footnotes.py` reports no structural errors for the delivered files.

## Markdown

- tables parse correctly;
- image paths are relative where images exist;
- no temporary or sandbox path appears;
- no conversation commentary appears in the translated text.

## OCR-specific QA for PDF-O

- obvious OCR garbage has not been carried into the Chinese translation or glossary;
- suspicious line-break hyphenation and split / joined words have been resolved from context or the visible page;
- proper names, titles, institutions, technical terms, quotations, numbers, dates, percentages, table values, and note-call markers have been visually checked whenever the OCR reading is doubtful;
- a plausible semantic guess has not been substituted for source text that remains unreadable;
- no authorial wording, factual claim, argument, or data has been “corrected” merely because it appears mistaken;
- any unresolved source-reading problem is recorded specifically rather than silently guessed.

Only after QA succeeds should `book_plan.md` move the Part to `done` and point to the next action.

---

# 24. Persistent state and the meaning of “continue”

Within the same book translation conversation/workspace, if the user says only:

```text
继续
```

interpret it as:

> Execute the next incomplete stage recorded in `book_plan.md`.

Before acting:

1. read `book_plan.md`;
2. read the newest `glossary.md`;
3. confirm the original PDF is still accessible;
4. find the first required stage whose status is not `done`;
5. execute that stage without asking the user to restate page ranges, filename conventions, footnote rules, or glossary rules already recorded.

Typical progression:

```text
Initialization
→ Part 1
→ Part 2
→ Part 3
→ ...
→ substantive appendices, if any
→ centralized Notes, Case A only
→ translation complete / ready for final assembly
```

After each stage, update `book_plan.md` and give only a concise status message in chat.

Example:

```text
Part 3 已完成
输出：<BOOK_STEM>_part3_中译.md
Glossary：v1.2 → v1.3
下一步：Part 4
```

Do not create long progress reports unless requested.

---

# 25. File continuity and re-upload policy

The workflow assumes one persistent cloud/workspace context whenever available.

During initialization and Part translation:

- continue using the original full PDF already present in the workspace;
- continue using the same `book_plan.md`;
- continue using the newest `glossary.md`;
- continue using previously generated translated Markdown and `assets/` when accessible;
- do not require the user to upload a new source file for every Part;
- do not ask for derivative Part PDFs that the workflow no longer creates.

If a needed file is truly unavailable, identify the **specific missing file**. Prefer asking for the original PDF, current `book_plan.md`, newest `glossary.md`, or the exact missing translated file rather than asking the user to “upload everything again.”

---

# 26. Translation completion and handoff to final assembly

When all logical body Parts, substantive appendices, and required Case A centralized Notes have status `done`:

1. update `book_plan.md` to:

```text
Translation stage: complete
Next action: whole-book Markdown assembly
```

2. do **not** assume that every historical Markdown artifact is necessarily still exposed to the assembly environment;
3. if all final translated Markdown files and assets are still reliably accessible, assembly may proceed from them;
4. otherwise ask the user once, at the assembly boundary, to attach only the final artifacts needed for merging:

```text
- all final Part Markdown files;
- <BOOK_STEM>_appen.md, if applicable;
- <BOOK_STEM>_notes_中译.md, Case A only;
- assets/ or assets ZIP, if any.
```

Do not ask for the original PDF again unless a source verification issue requires it.

This is the normal point at which a one-time manual upload may be needed; it should not be required during ordinary Part-by-Part translation.

---

# 27. Whole-book Markdown assembly

After all requested Parts have been translated, glossary updates are complete, and all final translated working files are available, assemble them into one whole-book Markdown master.

The assembly stage is a **structural relocation task**, not a translation or editing pass.

Default output filename:

```text
<BOOK_STEM>_master.md
```

## 27.1 Inputs

Typical inputs are:

```text
<BOOK_STEM>_part1_中译.md
<BOOK_STEM>_part2_中译.md
<BOOK_STEM>_part3_中译.md
...
<BOOK_STEM>_appen.md                 # when substantive appendices exist
<BOOK_STEM>_notes_中译.md            # Case A only
assets/
glossary.md
book_plan.md
```

`book_plan.md` supplies authoritative original order and unit mapping. `assets/` remains a separate resource directory.

## 27.2 Pre-assembly validation

Before merging, run footnote QA across the complete set of translated working files.

For Case A, check all body Part files, `<BOOK_STEM>_appen.md` when present, and `<BOOK_STEM>_notes_中译.md` together.

For Case B, check all translated Part files and `<BOOK_STEM>_appen.md` together.

If there are duplicate IDs, missing definitions, orphaned mappings that indicate a likely source mismatch, or other structural errors, report them and do not silently repair or renumber them during assembly.

## 27.3 Body merge order

Merge the translated body in the original book order recorded in `book_plan.md`. Preserve all top-level units as peer `#` headings.

Do not create `Part 1`, `Part 2`, or other workflow-management headings in the master file.

## 27.4 Remove working footnote-definition blocks from Parts

For Case B, remove Part-end definition blocks from their working locations and relocate them to the unified endnotes chapter.

For Case A, use definitions from `<BOOK_STEM>_notes_中译.md` as the source of the final endnotes chapter.

In both cases:

- keep every正文 footnote call exactly where it is;
- keep every footnote ID exactly unchanged;
- keep every footnote definition text exactly unchanged;
- do not renumber notes;
- do not rewrite references inside notes;
- do not normalize wording, punctuation, names, bibliography entries, or quotation style merely because definitions are being relocated.

## 27.5 Create one top-level `# 注释` chapter

After all translated正文 chapters and substantive appendices, create exactly one final top-level chapter:

```markdown
# 注释
```

## 27.6 Group notes under second-level origin headings

Inside `# 注释`, group definitions by the top-level book unit from which their references originate.

Example:

```markdown
# 注释

## 序言

[^pr-001]: ……

## 导论

[^intro-001]: ……

## 第三章

[^ch03-001]: ……

## 附录

[^ap-001]: ……
```

Only create a group when that unit actually has notes.

For numbered chapters, the minimal chapter label such as `## 第三章` is normally sufficient.

## 27.7 Preserve note order

Within each group, preserve the note order already established during translation. Across groups, follow the original book order.

Do not sort notes alphabetically, by filename, or by raw footnote ID when that would alter the book's original sequence.

## 27.8 Minimal-change rule

Whole-book assembly should normally change only:

1. the physical location of `[^id]:` definition blocks;
2. the addition of `# 注释`;
3. the addition or normalization of required `##` note-group headings;
4. minimal blank lines needed for valid Markdown concatenation.

It should **not** change:

- 正文 wording;
- translations;
- paragraph content;
- quotations;
- numbers or dates;
- glossary choices or first-use renderings already established during sequential translation;
- heading wording in the 正文;
- table contents;
- image paths;
- footnote IDs;
- footnote definition text.

If a substantive correction is needed, treat it as a separate correction task rather than hiding it inside assembly.

## 27.9 Post-assembly QA

After creating `<BOOK_STEM>_master.md`, verify:

- all expected top-level book units are present in order;
- no workflow `Part` headings were introduced;
- every正文 `[^id]` reference still exists unchanged;
- every definition appears exactly once;
- no definition remains at the end of an individual正文 Part section;
- `# 注释` appears exactly once and after the translated正文 / appendices;
- each note definition is under the correct `##` origin heading;
- note order within each group is unchanged;
- first-use bilingual renderings remain exactly where translation established them; assembly has not added or removed English parentheticals;
- assets paths remain valid and relative;
- no正文, table, figure, or appendix content was lost during concatenation.

Run:

```bash
python scripts/check_footnotes.py --strict-ids <BOOK_STEM>_master.md
```

as a final structural check.

---

# 28. Delivery behavior

When the user provides a complete book PDF and asks to start:

1. inspect representative pages and classify the source as PDF-T, PDF-O, or PDF-I;
2. if PDF-I, stop and explain that the current workflow does not handle image-only / unusable-text-layer PDFs;
3. if PDF-T or PDF-O, inspect the complete PDF; for PDF-O, keep extraction + semantic/OCR correction mode active throughout later stages;
4. classify Case A / Case B;
5. create `book_plan.md` with the PDF type, text-handling mode, logical Part plan, source ranges, translation scope, conventions, and initial workflow state;
6. create initial whole-book `glossary.md`, using corrected source readings for PDF-O;
7. verify those files exist;
8. do not physically split the PDF by default;
9. do not automatically translate Part 1 unless the user also asked to begin translation immediately.

A concise initialization status is enough:

```text
当前状态：初始化完成
已完成：全书结构分析 / book_plan.md / glossary v1.0
下一步：翻译 Part 1
```

When the user asks to translate or says `继续`:

1. read `book_plan.md`;
2. read the newest glossary;
3. open the original PDF at the planned range;
4. complete the next logical Part;
5. run QA;
6. update glossary if needed;
7. update `book_plan.md`;
8. deliver the translated Markdown and any changed glossary/plan files.

When the user asks to integrate all completed translations:

1. use `book_plan.md` as the authoritative unit order;
2. gather the final translated Markdown files and assets;
3. run project-wide footnote QA before changing structure;
4. concatenate正文 units in original book order;
5. relocate all footnote definitions into one final `# 注释` chapter;
6. preserve every footnote ID and definition body unchanged;
7. preserve existing `assets/...` paths;
8. create `<BOOK_STEM>_master.md` unless the user specifies another filename;
9. run final footnote and structural QA;
10. deliver the assembled master and keep source Part files unchanged.

Never claim a PDF, Markdown file, glossary, plan, or other artifact exists unless it was actually created successfully.

---

# 29. Workflow summary

## Case A

```text
original book.pdf
→ classify PDF-T / PDF-O / PDF-I
→ PDF-I: stop (unsupported image-only / unusable text layer)
→ PDF-T: direct extraction
→ PDF-O: extraction + semantic/OCR correction throughout
→ inspect complete book
→ identify centralized Notes range
→ create book_plan.md
   ├─ logical Part ranges
   ├─ Notes range
   ├─ appendix ranges
   ├─ footnote scheme
   └─ workflow state
→ create glossary.md v1.0
→ translate each logical body Part directly from original book.pdf
   └─ stable pr / intro / chXX / ap note calls
→ translate substantive appendices directly from original book.pdf
→ translate centralized Notes directly from original book.pdf
   └─ definitions use exactly the same IDs
→ scripts/check_footnotes.py
→ rolling glossary + book_plan updates
→ translation complete
→ gather final translated MD / assets at assembly boundary if needed
→ assemble body + appendix + Notes
→ move all [^id]: definitions to final # 注释
   └─ group under ## 序言 / ## 导论 / ## 第一章 / ... / ## 附录
→ <BOOK_STEM>_master.md
→ final footnote + structure QA
```

## Case B

```text
original book.pdf
→ classify PDF-T / PDF-O / PDF-I
→ PDF-I: stop (unsupported image-only / unusable text layer)
→ PDF-T: direct extraction
→ PDF-O: extraction + semantic/OCR correction throughout
→ inspect complete book
→ identify embedded / chapter-end notes
→ create book_plan.md
   ├─ logical Part ranges
   ├─ appendix ranges
   ├─ footnote scheme
   └─ workflow state
→ create glossary.md v1.0
→ translate each logical Part directly from original book.pdf
   └─ notes translated in same pass
→ collect every [^id]: definition at each Part Markdown end
→ translate substantive appendices directly from original book.pdf
→ scripts/check_footnotes.py
→ rolling glossary + book_plan updates
→ translation complete
→ gather final translated MD / assets at assembly boundary if needed
→ assemble translated Parts + appendix
→ move all Part-end [^id]: definitions to final # 注释
   └─ group under ## 序言 / ## 导论 / ## 第一章 / ... / ## 附录
→ <BOOK_STEM>_master.md
→ final footnote + structure QA
```

The key invariant is:

```text
one original PDF as source
+ PDF-T direct extraction OR PDF-O extraction + semantic/OCR correction
+ one persistent book_plan.md as book-specific roadmap/state
+ one current glossary.md as translation authority
+ logical Parts as processing units
+ no routine source-PDF splitting
= minimal manual re-upload during the translation stage
```

The resulting `<BOOK_STEM>_master.md` should be structurally stable enough to hand off to a separate EPUB / PDF publishing workflow.

---

## PDF-O extension boundary

PDF-O support changes only the source-reading layer. Unless the user explicitly asks otherwise, it does **not** change:

- Case A / Case B note classification or note normalization;
- logical Part planning or source-range conventions;
- heading hierarchy, table handling, figure handling, or Markdown layout;
- glossary versioning policy;
- whole-book Markdown assembly;
- downstream EPUB / PDF publishing;
- Z-Library metadata fields or timing.

Those stages follow the existing rules exactly; PDF-O merely requires that the English source be reconstructed reliably from extraction plus semantic/visual correction before those rules are applied.

# 30. Z-Library upload metadata

After the translation and final publishing workflow is complete, prepare a compact metadata sheet for the user's usual Z-Library upload step. This is a bibliographic handoff only; do not alter the translation, `<BOOK_STEM>_master.md`, EPUB, PDF, glossary, or assets.

Create:

```text
zlibrary_metadata.md
```

It should contain only the information needed for the upload:

```markdown
# Z-Library 上传信息

- 中文书名：
- English Title:
- 作者（Author）：
- ISBN：
- 出版年份：

## 简介

一段简短、客观的中文内容介绍。
```

Rules:

1. Preserve the complete original title and subtitle in `English Title`; the Chinese title should match the finalized translation title.
2. For the author field, use the original-language name and, when a stable Chinese form exists, include the Chinese form as well.
3. Prefer the ISBN of the exact source edition represented by the original PDF. Prefer ISBN-13 when both ISBN-10 and ISBN-13 are available. If the source edition cannot be identified confidently, mark the ISBN as `待核对` rather than guessing.
4. Use the original publication year of that source edition unless the user explicitly asks for another edition's year.
5. The introduction should be brief, neutral, and bibliographic in tone. Summarize the book's subject, central problem, and broad analytical approach without promotional language or invented claims.
6. Prefer metadata from the title page and copyright page of the source PDF. If those are missing or contradictory and web verification is available, verify against reliable bibliographic records before filling the field.
7. Do not add extra upload fields such as tags, categories, language, publisher, or file format unless the user asks for them.

A concise completion status is enough:

```text
Z-Library 上传信息已整理
输出：zlibrary_metadata.md
```

