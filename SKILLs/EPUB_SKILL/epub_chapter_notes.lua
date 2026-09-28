-- EPUB filter for an already assembled academic-book master Markdown file.
--
-- Responsibilities are deliberately narrow:
--   1. remove source-side printed TOC and assembled Notes shells;
--   2. keep Pandoc Note nodes untouched so EPUB3-native, same-XHTML footnotes are emitted;
--   3. optionally mark front-matter headings before the first numbered body unit as
--      "unlisted", so reader navigation starts at the real book body rather than title,
--      dedication, acknowledgements, contributor lists, table lists, etc.;
--   4. mark configured exact title/subtitle headings as unlisted.
--
-- It must NOT rewrite正文, quotations, tables, bibliography content, or Note nodes.

local stringify = pandoc.utils.stringify

local notes_title = '注释'
local source_toc_titles = {
  ['目录'] = true,
  ['原书目录'] = true,
  ['Contents'] = true,
}
local toc_omit_headings = {}
local toc_start_at_first_numbered_unit = true

local function meta_string(meta, key, default)
  local v = meta[key]
  if v == nil then return default end
  local s = stringify(v)
  if s == '' then return default end
  return s
end

local function meta_bool(meta, key, default)
  local v = meta[key]
  if v == nil then return default end
  local s = stringify(v):lower()
  if s == 'true' or s == 'yes' or s == '1' then return true end
  if s == 'false' or s == 'no' or s == '0' then return false end
  return default
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

local function is_numbered_body_heading(txt)
  -- Chinese numbered structural units. Intentionally broad enough for 第一部分 / 第一章 / 第一编.
  if txt:match('^第.-章') then return true end
  if txt:match('^第.-部分') then return true end
  if txt:match('^第.-部') then return true end
  if txt:match('^第.-编') then return true end
  if txt:match('^第.-卷') then return true end

  -- Common English equivalents; string.lower is sufficient for ASCII here.
  local lower = txt:lower()
  if lower:match('^chapter%s+[%divxlcdm]+') then return true end
  if lower:match('^part%s+[%divxlcdm]+') then return true end
  if lower:match('^book%s+[%divxlcdm]+') then return true end
  return false
end

local function document_has_numbered_body_start(blocks)
  for _, block in ipairs(blocks) do
    if block.t == 'Header' then
      local txt = stringify(block.content)
      if is_numbered_body_heading(txt) then return true end
    end
  end
  return false
end

function Pandoc(doc)
  notes_title = meta_string(doc.meta, 'notes-title', '注释')
  toc_omit_headings = meta_string_set(doc.meta, 'toc-omit-headings')
  toc_start_at_first_numbered_unit = meta_bool(
    doc.meta,
    'toc-start-at-first-numbered-unit',
    true
  )

  local has_body_start = toc_start_at_first_numbered_unit
    and document_has_numbered_body_start(doc.blocks)
  local before_body_start = has_body_start

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
          -- Markdown footnote definitions have already become Note inlines at their
          --正文 references. The final source-side Notes shell must not become an EPUB chapter.
          skipping_source_toc = false
          in_source_notes = true
          goto continue
        else
          skipping_source_toc = false
        end
      end

      if not skipping_source_toc and not in_source_notes then
        if block.level > 1 and txt == notes_title then
          -- Redundant source heading; native chapter-end footnotes provide the actual notes.
          goto continue
        end

        if before_body_start then
          if is_numbered_body_heading(txt) then
            before_body_start = false
          else
            -- Keep front matter in the reading flow but exclude it from nav.xhtml/toc.ncx.
            add_class(block.attr, 'unlisted')
          end
        end

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
