-- Generic explicit book-structure + endnote filter.
--
-- build_pdf.py infers the H1 structure from the authoritative master.md and
-- passes one type per H1 through metadata (`book-h1-types`). This filter never
-- guesses book structure on its own and never silently drops an unknown H1.
-- The source-side printed TOC and the assembled source Notes shell are skipped;
-- a generated TOC and bidirectional book-end notes are emitted instead.

local stringify = pandoc.utils.stringify

local groups = {}
local group_order = {}
local current_group = nil
local skipping_source_toc = false
local skipping_source_notes = false
local notes_emitted = false
local toc_emitted = false
local mainmatter_started = false
local h1_serial = 0
local fallback_serial = 0
local awaiting_chapter_author = false

local h1_types = {}
local mainmatter_index = 0
local notes_title = '注释'

local function meta_string(meta, key, default)
  local v = meta[key]
  if v == nil then return default or '' end
  local s = stringify(v)
  if s == '' then return default or '' end
  return s
end

local function meta_list(meta, key)
  local result = {}
  local v = meta[key]
  if v == nil then return result end
  if type(v) == 'table' then
    for _, item in ipairs(v) do table.insert(result, stringify(item)) end
  else
    table.insert(result, stringify(v))
  end
  return result
end

local function has_class(el, wanted)
  for _, c in ipairs(el.classes or {}) do
    if c == wanted then return true end
  end
  return false
end

local function add_class(el, wanted)
  if not has_class(el, wanted) then el.classes:insert(wanted) end
end

local function latex_inlines(inlines)
  local d = pandoc.Pandoc({pandoc.Plain(inlines)})
  local s = pandoc.write(d, 'latex')
  return (s:gsub('%s+$', ''))
end

local function latex_text(text)
  return latex_inlines({pandoc.Str(text)})
end

local function canonical_group(title)
  local chapter = title:match('^(第[一二三四五六七八九十百零〇0-9]+章)')
  if chapter then return chapter end
  if title:match('^附录') or title:match('^[Aa]ppendix') then return title end
  return title
end

local function normalized_structural_title(title)
  -- Normalize only the rendered separator after Chinese 第X章/第X部分.
  local prefix = title:match('^(第[一二三四五六七八九十百零〇0-9]+章)')
  if not prefix then
    prefix = title:match('^(第[一二三四五六七八九十百零〇0-9]+部分)')
  end
  if not prefix then return title end
  local rest = title:sub(#prefix + 1)
  if rest:sub(1, 3) == '　' then rest = rest:sub(4) end
  rest = rest:gsub('^%s+', '')
  if rest == '' then return prefix end
  return prefix .. '　' .. rest
end

local function is_chapter_author_para(block)
  if block.t ~= 'Para' and block.t ~= 'Plain' then return false end
  local text = stringify(block.content)
  if #text == 0 or #text > 90 then return false end
  if text:find('。') or text:find('：') or text:find(':') or text:find('；') then return false end
  -- Conservative: author lines usually contain a name separator/middle dot,
  -- several Latin letters, or a short list separated by ideographic commas.
  if text:find('·') or text:find('、') or text:match('[A-Za-z][A-Za-z]') then return true end
  return false
end

local function add_group(name)
  if not groups[name] then
    groups[name] = {name = name, notes = {}, by_key = {}}
    table.insert(group_order, name)
  end
  return groups[name]
end

local function register_note(note_key, note_blocks)
  local group_name = current_group or '其他'
  local group = add_group(group_name)
  local entry = group.by_key[note_key]
  if not entry then
    local group_index = #group_order
    local note_number = #group.notes + 1
    entry = {
      blocks = note_blocks,
      number = note_number,
      anchor = string.format('book-note-g%02d-n%03d', group_index, note_number),
      refs = {},
    }
    group.by_key[note_key] = entry
    table.insert(group.notes, entry)
  end
  local ref_number = #entry.refs + 1
  local ref_anchor = string.format('%s-r%02d', entry.anchor, ref_number)
  table.insert(entry.refs, ref_anchor)
  return pandoc.RawInline(
    'latex',
    string.format('\\booknoteref{%s}{%s}{%d}', ref_anchor, entry.anchor, entry.number)
  )
end

local function rewrite_inlines(inlines)
  local out = pandoc.List()
  local i = 1
  while i <= #inlines do
    local el = inlines[i]
    local nxt = inlines[i + 1]
    if el.t == 'Span' and has_class(el, 'pdf-noteref') and nxt and nxt.t == 'Note' then
      local key = el.attributes['data-note-key'] or ''
      if key == '' then
        fallback_serial = fallback_serial + 1
        key = string.format('__annotated_fallback_%d', fallback_serial)
      end
      out:insert(register_note(key, nxt.content))
      i = i + 2
    elseif el.t == 'Note' then
      fallback_serial = fallback_serial + 1
      out:insert(register_note(string.format('__fallback_%d', fallback_serial), el.content))
      i = i + 1
    else
      out:insert(el)
      i = i + 1
    end
  end
  return out
end

local function prepend_note_anchor(blocks, anchor)
  local marker = pandoc.RawInline('latex', string.format('\\booknoteanchor{%s}', anchor))
  for _, block in ipairs(blocks) do
    if block.t == 'Para' or block.t == 'Plain' then
      table.insert(block.content, 1, marker)
      return
    end
  end
  table.insert(blocks, 1, pandoc.Para({marker}))
end

local function append_backlinks(blocks, refs)
  local links = pandoc.List()
  if #refs == 1 then
    links:insert(pandoc.RawInline('latex', string.format('\\booknotebacklink{%s}', refs[1])))
  else
    for i, ref in ipairs(refs) do
      links:insert(pandoc.RawInline(
        'latex', string.format('\\booknotebacklinkmulti{%s}{%d}', ref, i)
      ))
    end
  end
  for i = #blocks, 1, -1 do
    local block = blocks[i]
    if block.t == 'Para' or block.t == 'Plain' then
      for _, link in ipairs(links) do table.insert(block.content, link) end
      return
    end
  end
  table.insert(blocks, pandoc.Para(links))
end

local function build_endnotes()
  local out = {}
  if notes_emitted or #group_order == 0 then return out end
  notes_emitted = true
  if mainmatter_started then table.insert(out, pandoc.RawBlock('latex', '\\backmatter')) end
  table.insert(out, pandoc.RawBlock(
    'latex', string.format('\\booknoteschapter{%s}{book-notes}', latex_text(notes_title))
  ))
  for _, name in ipairs(group_order) do
    local group = groups[name]
    table.insert(out, pandoc.RawBlock(
      'latex', string.format('\\booknotegroup{%s}', latex_text(name))
    ))
    local items = {}
    for _, entry in ipairs(group.notes) do
      local item_blocks = {}
      for _, block in ipairs(entry.blocks) do table.insert(item_blocks, block) end
      prepend_note_anchor(item_blocks, entry.anchor)
      append_backlinks(item_blocks, entry.refs)
      table.insert(items, item_blocks)
    end
    table.insert(out, pandoc.RawBlock('latex', '\\begin{bookendnotelist}'))
    table.insert(out, pandoc.OrderedList(items))
    table.insert(out, pandoc.RawBlock('latex', '\\end{bookendnotelist}'))
  end
  return out
end

local function maybe_emit_toc(out)
  if not toc_emitted then
    table.insert(out, pandoc.RawBlock('latex', '\\booktableofcontents'))
    toc_emitted = true
  end
end

local function emit_structural(header, kind, out)
  local title = stringify(header.content)
  local display_title = normalized_structural_title(title)
  local latex_title = latex_text(display_title)
  local anchor = string.format('book-h1-%03d', h1_serial)

  if kind == 'source-title' then
    awaiting_chapter_author = false
    return
  elseif kind == 'source-toc' then
    awaiting_chapter_author = false
    maybe_emit_toc(out)
    skipping_source_toc = true
    return
  elseif kind == 'notes' then
    awaiting_chapter_author = false
    skipping_source_notes = true
    local notes = build_endnotes()
    for _, item in ipairs(notes) do table.insert(out, item) end
    return
  end

  if h1_serial == mainmatter_index and not mainmatter_started then
    maybe_emit_toc(out)
    table.insert(out, pandoc.RawBlock('latex', '\\mainmatter'))
    mainmatter_started = true
  end

  if kind == 'front' then
    current_group = canonical_group(title)
    table.insert(out, pandoc.RawBlock(
      'latex', string.format('\\bookfrontchapter{%s}{%s}', latex_title, anchor)
    ))
  elseif kind == 'front-unlisted' then
    current_group = canonical_group(title)
    table.insert(out, pandoc.RawBlock(
      'latex', string.format('\\bookchapterunlisted{%s}{%s}', latex_title, anchor)
    ))
  elseif kind == 'part' then
    current_group = nil
    table.insert(out, pandoc.RawBlock(
      'latex', string.format('\\bookpart{%s}{%s}', latex_title, anchor)
    ))
  elseif kind == 'part-unlisted' then
    current_group = nil
    table.insert(out, pandoc.RawBlock(
      'latex', string.format('\\bookpartunlisted{%s}{%s}', latex_title, anchor)
    ))
  elseif kind == 'chapter-sub' then
    current_group = canonical_group(title)
    awaiting_chapter_author = true
    table.insert(out, pandoc.RawBlock(
      'latex', string.format('\\bookchaptersub{%s}{%s}', latex_title, anchor)
    ))
  elseif kind == 'chapter-sub-unlisted' then
    current_group = canonical_group(title)
    awaiting_chapter_author = true
    table.insert(out, pandoc.RawBlock(
      'latex', string.format('\\bookchapterunlisted{%s}{%s}', latex_title, anchor)
    ))
  else
    current_group = canonical_group(title)
    awaiting_chapter_author = true
    if kind == 'chapter-top-unlisted' then
      table.insert(out, pandoc.RawBlock(
        'latex', string.format('\\bookchapterunlisted{%s}{%s}', latex_title, anchor)
      ))
    else
      table.insert(out, pandoc.RawBlock(
        'latex', string.format('\\bookchaptertop{%s}{%s}', latex_title, anchor)
      ))
    end
  end
end

function Pandoc(doc)
  h1_types = meta_list(doc.meta, 'book-h1-types')
  mainmatter_index = tonumber(meta_string(doc.meta, 'book-mainmatter-index', '0')) or 0
  notes_title = meta_string(doc.meta, 'notes-title', '注释')
  local out = {}

  for _, block in ipairs(doc.blocks) do
    if block.t == 'Header' and block.level == 1 then
      h1_serial = h1_serial + 1
      local kind = h1_types[h1_serial] or 'chapter-top'

      if skipping_source_toc and kind ~= 'source-toc' then skipping_source_toc = false end
      if skipping_source_notes and kind ~= 'notes' then skipping_source_notes = false end

      if not skipping_source_notes then emit_structural(block, kind, out) end
    elseif not skipping_source_toc and not skipping_source_notes then
      if awaiting_chapter_author and is_chapter_author_para(block) then
        local author_inlines = rewrite_inlines(block.content)
        local author_text = latex_inlines(author_inlines)
        table.insert(out, pandoc.RawBlock('latex', string.format('\\bookchapterauthor{%s}', author_text)))
        awaiting_chapter_author = false
      else
        awaiting_chapter_author = false
        if block.t == 'Header' and block.level >= 2 then
          add_class(block, 'unnumbered')
          add_class(block, 'unlisted')
        end
        local walked = pandoc.walk_block(block, {Inlines = rewrite_inlines})
        table.insert(out, walked)
      end
    end
  end

  maybe_emit_toc(out)
  if not notes_emitted then
    local notes = build_endnotes()
    for _, item in ipairs(notes) do table.insert(out, item) end
  end
  doc.blocks = out
  return doc
end
