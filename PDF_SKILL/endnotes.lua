-- Generic Pandoc/LaTeX endnotes filter for an already assembled book_master.md.
-- Expected source structure follows TRANSLATION_SKILL:
--   # 目录 / # 原书目录 (optional; omitted because the PDF template makes a TOC)
--   peer-level H1 book units such as # 序言, # 第一章 ..., # 附录
--   # 注释 with H2 grouping headings at the end
--
-- build_pdf.py temporarily annotates each named Markdown footnote reference with
-- an empty Span carrying a stable note key and an occurrence number. Pandoc still
-- resolves the native Note content, while this filter uses the annotation to:
--   * preserve note identity across repeated references;
--   * generate one book-end note entry per source note within an H1 group;
--   * generate a unique anchor at every正文 reference;
--   * generate one or more backlinks from the endnote to the exact正文 reference(s).
--
-- The source book_master.md itself is never modified.

local stringify = pandoc.utils.stringify

local groups = {}
local group_order = {}
local current_group = nil
local source_notes_skip = false
local skipping_source_toc = false
local mainmatter_started = false
local backmatter_started = false
local fallback_note_serial = 0

local mainmatter_start = ''
local notes_title = '注释'
local ungrouped_title = '其他'

local function meta_string(meta, key, default)
  local v = meta[key]
  if v == nil then return default or '' end
  local s = stringify(v)
  if s == '' then return default or '' end
  return s
end

local function is_source_toc(title)
  return title == '目录' or title == '原书目录'
end

local function canonical_group(h1text)
  local ch = h1text:match('^(第[一二三四五六七八九十百零〇0-9]+章)')
  if ch then return ch end
  if h1text:match('^附录') then return '附录' end
  return h1text
end

local function add_group(name)
  if not groups[name] then
    groups[name] = {name = name, notes = {}, by_key = {}}
    table.insert(group_order, name)
  end
  return groups[name]
end

local function latex_id(s)
  return s:gsub('[^%w%-:]', '-')
end

local function has_class(span, wanted)
  for _, c in ipairs(span.classes or {}) do
    if c == wanted then return true end
  end
  return false
end

local function register_note(note_key, note_blocks)
  local group_name = current_group or ungrouped_title
  local group = add_group(group_name)

  local entry = group.by_key[note_key]
  if not entry then
    local n = #group.notes + 1
    local gid = #group_order
    entry = {
      blocks = note_blocks,
      number = n,
      anchor = latex_id(string.format('endnote-g%d-n%d', gid, n)),
      refs = {},
    }
    group.by_key[note_key] = entry
    table.insert(group.notes, entry)
  end

  local refno = #entry.refs + 1
  local gid = #group_order
  local ref = latex_id(string.format('noteref-g%d-n%d-r%d', gid, entry.number, refno))
  table.insert(entry.refs, ref)

  local marker = string.format(
    '\\booknoteref{%s}{%s}{%d}',
    ref, entry.anchor, entry.number
  )
  return pandoc.RawInline('latex', marker)
end

local function fallback_note(note)
  fallback_note_serial = fallback_note_serial + 1
  local key = string.format('__fallback_%d', fallback_note_serial)
  return register_note(key, note.content)
end

-- Replace the temporary annotation Span + native Note pair with our own marker.
-- If a Note is encountered without an annotation (e.g. an inline note), preserve
-- functionality by treating it as a unique note with its own exact return link.
local function rewrite_inlines(inlines)
  local out = pandoc.List()
  local i = 1

  while i <= #inlines do
    local el = inlines[i]
    local nxt = inlines[i + 1]

    if el.t == 'Span' and has_class(el, 'pdf-noteref') and nxt and nxt.t == 'Note' then
      local key = el.attributes['data-note-key'] or ''
      if key == '' then
        fallback_note_serial = fallback_note_serial + 1
        key = string.format('__annotated_fallback_%d', fallback_note_serial)
      end
      out:insert(register_note(key, nxt.content))
      i = i + 2
    elseif el.t == 'Note' then
      out:insert(fallback_note(el))
      i = i + 1
    else
      out:insert(el)
      i = i + 1
    end
  end

  return out
end

local function add_anchor_to_item(blocks, anchor)
  local marker = pandoc.RawInline('latex', string.format('\\hypertarget{%s}{}', anchor))
  for _, b in ipairs(blocks) do
    if b.t == 'Para' or b.t == 'Plain' then
      table.insert(b.content, 1, marker)
      return blocks
    end
  end
  table.insert(blocks, 1, pandoc.Para({marker}))
  return blocks
end

local function add_backlinks_to_item(blocks, refs)
  if #refs == 0 then return blocks end

  local inlines = pandoc.List()
  if #refs == 1 then
    inlines:insert(pandoc.RawInline('latex', string.format('\\booknotebacklink{%s}', refs[1])))
  else
    for i, ref in ipairs(refs) do
      inlines:insert(pandoc.RawInline('latex', string.format('\\booknotebacklinkmulti{%s}{%d}', ref, i)))
    end
  end

  for i = #blocks, 1, -1 do
    local b = blocks[i]
    if b.t == 'Para' or b.t == 'Plain' then
      for _, inline in ipairs(inlines) do
        table.insert(b.content, inline)
      end
      return blocks
    end
  end

  table.insert(blocks, pandoc.Para(inlines))
  return blocks
end

local function build_endnotes()
  local out = {}
  if #group_order == 0 then return out end

  if not backmatter_started then
    table.insert(out, pandoc.RawBlock('latex', '\\backmatter'))
    backmatter_started = true
  end

  table.insert(out, pandoc.Header(1, notes_title, pandoc.Attr('notes', {}, {})))

  for _, name in ipairs(group_order) do
    local group = groups[name]
    table.insert(out, pandoc.Header(2, name))
    local items = {}

    for _, entry in ipairs(group.notes) do
      local item_blocks = {}
      for _, b in ipairs(entry.blocks) do table.insert(item_blocks, b) end
      add_anchor_to_item(item_blocks, entry.anchor)
      add_backlinks_to_item(item_blocks, entry.refs)
      table.insert(items, item_blocks)
    end

    table.insert(out, pandoc.RawBlock('latex', '\\begin{bookendnotelist}'))
    table.insert(out, pandoc.OrderedList(items))
    table.insert(out, pandoc.RawBlock('latex', '\\end{bookendnotelist}'))
  end

  return out
end

local function looks_like_numbered_chapter(title)
  if title:match('^第[一二三四五六七八九十百零〇0-9]+章') then return true end
  if title:match('^[Cc]hapter%s+%d+') then return true end
  return false
end

function Pandoc(doc)
  mainmatter_start = meta_string(doc.meta, 'mainmatter-start', '')
  notes_title = meta_string(doc.meta, 'notes-title', '注释')
  ungrouped_title = meta_string(doc.meta, 'ungrouped-notes-title', '其他')

  local out = {}

  for _, block in ipairs(doc.blocks) do
    if block.t == 'Header' and block.level == 1 then
      local title = stringify(block.content)

      if is_source_toc(title) then
        skipping_source_toc = true
        goto continue
      elseif title == notes_title then
        skipping_source_toc = false
        source_notes_skip = true
        goto continue
      else
        if skipping_source_toc then
          skipping_source_toc = false
        end
        if source_notes_skip then
          source_notes_skip = false
        end

        current_group = canonical_group(title)

        if not mainmatter_started then
          local should_start_main = false
          if mainmatter_start ~= '' then
            should_start_main = (title == mainmatter_start)
          else
            should_start_main = looks_like_numbered_chapter(title)
          end
          if should_start_main then
            table.insert(out, pandoc.RawBlock('latex', '\\mainmatter'))
            mainmatter_started = true
          end
        end
      end
    end

    if not skipping_source_toc and not source_notes_skip then
      local walked = pandoc.walk_block(block, {Inlines = rewrite_inlines})
      table.insert(out, walked)
    end

    ::continue::
  end

  local e = build_endnotes()
  for _, b in ipairs(e) do table.insert(out, b) end

  doc.blocks = out
  return doc
end
