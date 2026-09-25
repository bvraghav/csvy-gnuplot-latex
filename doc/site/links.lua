-- links.lua: pandoc filter for the doc/ static site.
--
-- Paths are relative to doc/, where make runs pandoc.  For each relative link:
--   X.md[#a]         -> X.html[#a]         (README.md -> index.html)
--   anything else    -> the file on GitHub (blob/ for files, tree/ for folders):
--                       ../README.md, examples/, examples/NAME.csvy, ...
-- Images are left alone: img/ is copied into the site.
-- The page title (<title>) comes from the first level-1 heading.
--
-- Metadata (set by the Makefile): repo_url, branch.

local repo_url, branch

local function split(path)
  local parts = {}
  for part in path:gmatch("[^/]+") do parts[#parts + 1] = part end
  return parts
end

-- Resolve `target` (relative to the page) to a path relative to doc/.
-- Returns nil if the path leaves doc/, along with the repo-relative path.
local function resolve(page, target)
  local parts = split(pandoc.path.directory(page))
  if parts[1] == "." then table.remove(parts, 1) end
  local up = 0
  for _, part in ipairs(split(target)) do
    if part == ".." then
      if #parts > 0 then table.remove(parts) else up = up + 1 end
    elseif part ~= "." then
      parts[#parts + 1] = part
    end
  end
  local path = table.concat(parts, "/")
  if up > 0 then
    -- doc/ is one level below the repo root
    return nil, (up == 1) and path or nil
  end
  return path, "doc/" .. path
end

local function github(repo_path, is_dir)
  return string.format("%s/%s/%s/%s", repo_url, is_dir and "tree" or "blob", branch,
                       repo_path)
end

local function relink(page, el)
  local target = el.target
  if target:match("^%a[%w+.-]*:") or target:match("^#") or target == "" then
    return nil -- absolute URL, mailto:, or same-page anchor
  end
  local path, frag = target:match("^([^#]*)(#?.*)$")
  local is_dir = path:sub(-1) == "/"
  local local_path, repo_path = resolve(page, path)

  if local_path and path:match("%.md$") then
    local html = path:gsub("%.md$", ".html")
    if pandoc.path.filename(path) == "README.md" then
      html = html:gsub("README%.html$", "index.html")
    end
    el.target = html .. frag
  elseif repo_path then
    el.target = github(repo_path:gsub("/$", ""), is_dir) .. frag
  else
    io.stderr:write(string.format("links.lua: %s: link %q leaves the repository\n",
                                  page, target))
  end
  return el
end

function Pandoc(doc)
  repo_url = pandoc.utils.stringify(doc.meta.repo_url or "")
  branch = pandoc.utils.stringify(doc.meta.branch or "master")
  local page = PANDOC_STATE.input_files[1]

  doc = doc:walk({ Link = function(el) return relink(page, el) end })

  if not doc.meta.pagetitle then
    for _, block in ipairs(doc.blocks) do
      if block.t == "Header" and block.level == 1 then
        doc.meta.pagetitle = pandoc.utils.stringify(block.content)
        break
      end
    end
  end
  return doc
end
