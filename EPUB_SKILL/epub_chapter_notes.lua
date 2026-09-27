-- EPUB filter for an already assembled book master Markdown file.
--
-- Expected current TRANSLATION_SKILL structure:
--   # 目录 / # 原书目录       (optional source-side printed TOC; omitted from EPUB)
--   # 序言 / # 第一章 ...    (top-level book units)
--   ...
--   # 注释                    (assembled source notes shell)
--     ## 序言 / ## 第一章 ...
--     [^id]: ...              (Pandoc has already attached these definitions to Note inlines)
--
-- IMPORTANT:
--   This filter does NOT rewrite Pandoc Note nodes into custom endnote links.
--   It removes only source-side structural shells that should not appear as EPUB content.
--   Pandoc's EPUB3 writer then emits native same-XHTML footnotes at the end of each
--   chapter/chunk, with epub:type="noteref" / epub:type="footnote" and backlinks.

local stringify = pandoc.utils.stringify

local notes_title = '注释'
local source_toc_titles = {
  ['目录'] = true,
  ['原书目录'] = true,
}
local toc_omit_headings = {}

local function meta_string(meta, key, default)
  local v = meta[key]
  if v == nil then return default end
  local s = stringify(v)
  if s == '' then return default end
  return s
end

local function meta_string_set(meta, key)
  local out = {}
  local v = meta[key]
  if v == nil then return out end

  local added = false
  if type(v) == 'table' then
    for _, item in ipairs(v) do
      local s = stringify(item)
      if s ~= '' then
        out[s] = true
        added = true
      end
    end
  end
  if not added then
    local s = stringify(v)
    if s ~= '' then out[s] = true end
  end
  return out
end

local function add_class(attr, class_name)
  for _, c in ipairs(attr.classes) do
    if c == class_name then return end
  end
  attr.classes:insert(class_name)
end

function Pandoc(doc)
  notes_title = meta_string(doc.meta, 'notes-title', '注释')
  toc_omit_headings = meta_string_set(doc.meta, 'toc-omit-headings')

  local out = pandoc.List()
  local skipping_source_toc = false
  local in_source_notes = false

  for _, block in ipairs(doc.blocks) do
    if block.t == 'Header' then
      local txt = stringify(block.content)

      if block.level == 1 then
        if source_toc_titles[txt] then
          skipping_source_toc = true
          in_source_notes = false
          goto continue
        elseif txt == notes_title then
          -- Translation master keeps all Markdown footnote definitions under this
          -- final source shell. Definitions have already become Note inlines at
          -- their body references, so the shell itself must not become an EPUB
          -- chapter. Everything after this H1 is source-side note organization.
          skipping_source_toc = false
          in_source_notes = true
          goto continue
        else
          skipping_source_toc = false
        end
      end

      if not skipping_source_toc and not in_source_notes then
        -- Empty chapter-level "注释" headings are redundant once native EPUB
        -- footnotes are emitted at the end of the chapter/chunk.
        if block.level > 1 and txt == notes_title then
          goto continue
        end

        -- Keep book-title / subtitle text in the reading flow when it belongs to
        -- the source front matter, but exclude configured exact matches from the
        -- generated navigation TOC.
        if toc_omit_headings[txt] then
          add_class(block.attr, 'unlisted')
        end
      end
    end

    if not skipping_source_toc and not in_source_notes then
      out:insert(block)
    end

    ::continue::
  end

  doc.blocks = out
  return doc
end
