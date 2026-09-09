# Academic Book Translation Skills

中文 | English

A modular set of ChatGPT skills for translating long-form English academic books into structured Chinese Markdown and publishing the completed translation as EPUB3 and PDF.

Read USAGE.md to acknowledge how to 

一套面向英文长篇学术著作翻译与数字出版的 ChatGPT Skills，覆盖从原始英文 PDF、全书结构分析、术语管理和逐部分翻译，到最终 Markdown 母稿、EPUB3 与 PDF 出版的完整工作流。

For usage instructions, see `USAGE.md`

---

## 中文介绍

### 项目简介

本项目是一套用于长篇英文学术著作中译的模块化 ChatGPT Skills.

整个流程被拆分为三个相互独立但能够衔接的 Skill：

- `TRANSLATION_SKILL`：负责英文 PDF 的结构分析、注释系统识别、术语表建立、分 Part 完整翻译、脚注规范化、完整性检查以及最终 Markdown 母稿合并。
- `EPUB_SKILL`：从已经完成的中文 Markdown 母稿生成并检查 EPUB3。
- `PDF_SKILL`：从同一份 Markdown 母稿生成适合中文学术著作阅读的 B5 PDF，并处理书末注释及双向注释链接。

### Translation Skill

`TRANSLATION_SKILL` 面向具有可靠原生文字层或可用 OCR 文字层的英文 PDF。

其工作流包括：

- 全书结构检查；
- PDF 文本层质量分类；
- Notes / Endnotes 结构识别；
- 创建并维护 `book_plan.md`；
- 创建并滚动更新全书 `glossary.md`；
- 在不物理拆分原始 PDF 的情况下规划逻辑 Part；
- 按 Part 忠实完整翻译正文；
- 保留原文论证结构、限定条件、引文、数字、统计资料和表格；
- 使用稳定的语义化 Markdown / Pandoc 脚注 ID；
- 对 OCR 缺陷进行基于原页面和上下文的谨慎校正；
- 进行脚注、结构和完整性 QA；
- 最终合并形成统一的中文 Markdown 母稿和书末注释。

本 Skill 不以摘要或改写为目标，也不要求把英文著作重新解释为某一种理论框架。原始文本始终是翻译的最高依据。

纯图片且没有可用文字层的 PDF 当前不属于默认工作流。

### EPUB Skill

`EPUB_SKILL` 用于在翻译和 Markdown 合并已经完成以后生成 EPUB3。

它以最终 Markdown 母稿为权威输入，复用通用 CSS 和 Lua filter，处理：

- EPUB 导航目录；
- H1 章节拆分；
- 中文正文排版；
- 图片与 Markdown 表格；
- 全书书末注释；
- 正文注释与注释章节之间的链接；
- EPUB 基本结构检查。

出版阶段不会重新翻译或无必要修改正文。

### PDF Skill

`PDF_SKILL` 使用 Pandoc、XeLaTeX 和 xdvipdfmx 将同一份 Markdown 母稿生成中文 B5 学术书 PDF。

默认版式包括：

- B5 双面书籍布局；
- 中文正文首行缩进；
- 书名页和自动目录；
- 章节分页；
- 页眉与页码；
- Markdown 表格；
- 图片尺寸约束；
- 全书书末注释；
- 正文注释标记到书末注释的链接；
- 从书末注释精确返回正文引用位置的反向链接。

三个 Skill 共同遵循一个基本原则：

> Translation content should have a single authoritative Markdown source.

翻译正文只维护一份最终 Markdown 母稿；EPUB 与 PDF 的差异尽量由 CSS、Lua、Pandoc 和 LaTeX 层解决，而不是维护不同版本的译文。

---

## English

### Overview

This repository provides a modular set of ChatGPT skills for translating long-form English academic books into Chinese and publishing the completed translation as EPUB3 and PDF.

Rather than treating a book as a collection of independent pages for machine translation, the workflow treats the entire book as a structured scholarly document with persistent terminology, notes, chapter hierarchy, tables, images, and cross-part consistency.

The repository contains three coordinated skills:

- `TRANSLATION_SKILL` handles source-PDF inspection, note-system classification, glossary management, Part-by-Part full translation, footnote normalization, completeness QA, and final Markdown assembly.
- `EPUB_SKILL` builds and verifies an EPUB3 from the completed Chinese Markdown master.
- `PDF_SKILL` produces a B5 Chinese academic-book PDF from the same master Markdown, including book-end notes and bidirectional note navigation.

### Translation Skill

`TRANSLATION_SKILL` is intended for English PDFs with either a reliable native text layer or a sufficiently usable OCR text layer.

Its workflow includes:

- whole-book structural inspection;
- PDF text-layer classification;
- Notes / Endnotes classification;
- persistent `book_plan.md` workflow state;
- book-wide `glossary.md` management;
- logical Part planning without physically splitting the original PDF;
- faithful full-text translation;
- preservation of arguments, qualifications, quotations, numbers, statistics, and tables;
- stable semantic Markdown / Pandoc footnote identifiers;
- cautious OCR-aware source reconstruction when required;
- footnote, structural, and completeness QA;
- final assembly into a unified Chinese Markdown master with book-end notes.

The skill is intended for scholarly full-text translation rather than summarization or free rewriting. The source text remains authoritative.

Image-only PDFs without a usable text layer are currently outside the default translation workflow.

### EPUB Skill

`EPUB_SKILL` builds an EPUB3 after translation and Markdown assembly are complete.

It reuses bundled CSS and Lua resources to provide:

- generated EPUB navigation;
- chapter splitting;
- Chinese long-form typography;
- image and Markdown-table support;
- book-end notes;
- note links and backlinks;
- basic EPUB structural verification.

The publishing stage does not retranslate or substantially rewrite the completed book.

### PDF Skill

`PDF_SKILL` converts the same Markdown master into a B5 Chinese academic-book PDF using Pandoc, XeLaTeX, and xdvipdfmx.

The default publishing workflow supports:

- two-sided B5 book layout;
- Chinese paragraph indentation;
- title page and generated table of contents;
- chapter pagination and running heads;
- Markdown tables and images;
- book-end notes;
- bidirectional navigation between in-text note markers and endnotes.

The overall design follows a single-source publishing principle:

> One authoritative Markdown translation, multiple publication formats.

Book content is maintained in the Markdown master, while EPUB- and PDF-specific presentation is handled by the publishing layer.