-- Generic EPUB filter for an already assembled book_master.md.
-- Expected source structure:
--   # 目录 / # 原书目录       (optional source-side printed TOC; omitted from EPUB)
--   # 序言 / # 第一章 ...    (top-level book units)
--   # 附录                    (optional)
--   # 注释                    (assembled source endnotes section)
--     ## 序言 / ## 第三章 ... (source grouping headings)
--
-- Pandoc attaches native Markdown footnote definitions to their body references,
-- so this filter rebuilds a real book-end 注释 chapter from those Note nodes.
-- Visible note numbering restarts within each top-level book unit.

local stringify = pandoc.utils.stringify

local notes_by_group = {}
local group_order = {}
local group_seen = {}
local current_group = nil
local in_existing_notes_section = false
local skipping_source_toc = false

local notes_title = '注释'
local ungrouped_title = '其他'

local function meta_string(meta, key, default)
  local v = meta[key]
  if v == nil then return default end
  local s = stringify(v)
  if s == '' then return default end
  return s
end

local function is_source_toc(title)
  return title == '目录' or title == '原书目录'
end

-- Match the grouping convention produced by TRANSLATION_SKILL.
-- Numbered chapter headings may contain a chapter title after the chapter number;
-- endnote group headings use only “第X章”. Appendices are grouped as “附录”.
local function canonical_group(h1text)
  local ch = h1text:match('^(第[一二三四五六七八九十百零〇0-9]+章)')
  if ch then return ch end

  if h1text:match('^附录') then return '附录' end

  -- Common peer-level front/back matter titles are already suitable as note-group names.
  return h1text
end

local function ensure_group(g)
  if not group_seen[g] then
    group_seen[g] = true
    group_order[#group_order + 1] = g
    notes_by_group[g] = {}
  end
end

local function rewrite_note(note)
  local g = current_group or ungrouped_title
  ensure_group(g)

  local idx = #notes_by_group[g] + 1
  local gid = tostring(#group_order)
  local safe = gid .. '-' .. tostring(idx)
  local ref_id = 'endnote-ref-' .. safe
  local note_id = 'endnote-' .. safe

  notes_by_group[g][idx] = {
    blocks = note.content,
    ref_id = ref_id,
    note_id = note_id,
  }

  local attr = pandoc.Attr(ref_id, {'footnote-ref'}, {['role'] = 'doc-noteref'})
  return pandoc.Link(
    {pandoc.Superscript({pandoc.Str(tostring(idx))})},
    '#' .. note_id,
    '',
    attr
  )
end

local function add_backlink_and_anchor(item)
  local blocks = item.blocks
  if #blocks == 0 then
    blocks = {pandoc.Para({})}
  end

  local anchor = pandoc.Span({}, pandoc.Attr(item.note_id, {'endnote-anchor'}))
  local first = blocks[1]
  if first.t == 'Para' or first.t == 'Plain' then
    table.insert(first.content, 1, anchor)
  else
    table.insert(blocks, 1, pandoc.Plain({anchor}))
  end

  local backlink = pandoc.Link(
    {pandoc.Str('↩')},
    '#' .. item.ref_id,
    '',
    pandoc.Attr('', {'footnote-back'}, {['role'] = 'doc-backlink'})
  )

  local last = blocks[#blocks]
  if last.t == 'Para' or last.t == 'Plain' then
    table.insert(last.content, pandoc.Space())
    table.insert(last.content, backlink)
  else
    table.insert(blocks, pandoc.Para({backlink}))
  end

  return blocks
end

function Pandoc(doc)
  notes_title = meta_string(doc.meta, 'notes-title', '注释')
  ungrouped_title = meta_string(doc.meta, 'ungrouped-notes-title', '其他')

  local out = pandoc.List()

  for _, block in ipairs(doc.blocks) do
    if block.t == 'Header' and block.level == 1 then
      local txt = stringify(block.content)

      if is_source_toc(txt) then
        skipping_source_toc = true
        goto continue
      elseif txt == notes_title then
        skipping_source_toc = false
        in_existing_notes_section = true
        goto continue
      else
        if skipping_source_toc then
          skipping_source_toc = false
        end
        if not in_existing_notes_section then
          current_group = canonical_group(txt)
        end
      end
    end

    -- Omit the source-side manual TOC and the already assembled source Notes chapter.
    -- Native footnote content has already been attached to the body Note nodes by Pandoc.
    if not skipping_source_toc and not in_existing_notes_section then
      out:insert(pandoc.walk_block(block, {Note = rewrite_note}))
    end

    ::continue::
  end

  -- Rebuild one real book-end Notes chapter.
  if #group_order > 0 then
    out:insert(pandoc.Header(1, {pandoc.Str(notes_title)}, pandoc.Attr('notes')))

    for _, g in ipairs(group_order) do
      out:insert(pandoc.Header(2, {pandoc.Str(g)}))
      local items = pandoc.List()
      for _, item in ipairs(notes_by_group[g]) do
        items:insert(add_backlink_and_anchor(item))
      end
      local ol = pandoc.OrderedList(items)
      out:insert(pandoc.Div({ol}, pandoc.Attr('', {'footnotes-end-of-document'})))
    end
  end

  doc.blocks = out
  return doc
end
