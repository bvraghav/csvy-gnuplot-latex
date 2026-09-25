-- links.lua: pandoc filter for the doc/ static site.
--
-- Every relative link is resolved to a path in the repository, then:
--   README.md         -> ABOUT.html       (the top-level README)
--   doc/README.md     -> index.html
--   doc/X.md[#a]      -> X.html[#a]
--   anything else     -> the file on GitHub (blob/ for files, tree/ for folders):
--                        LICENSE, doc/examples/, doc/examples/NAME.csvy, ...
-- The href is written relative to the page's own place in the site.
-- Images are left alone: their paths under doc/ are the same in the site.
-- The page title (<title>) comes from the first level-1 heading.
--
-- make runs pandoc in doc/, so input paths are relative to doc/
-- (e.g. tutorials/101.md, or ../README.md for ABOUT.html).
-- Metadata (set by the Makefile): repo_url, branch.

local repo_url, branch

local function split(path)
  local parts = {}
  for part in path:gmatch("[^/]+") do parts[#parts + 1] = part end
  return parts
end

-- Normalise a repository path; nil if it climbs out of the repository.
local function normalize(path)
  local parts = {}
  for _, part in ipairs(split(path)) do
    if part == ".." then
      if #parts == 0 then return nil end
      table.remove(parts)
    elseif part ~= "." then
      parts[#parts + 1] = part
    end
  end
  return table.concat(parts, "/")
end

local function dirname(path)
  return path:match("^(.*)/[^/]*$") or ""
end

-- The site page for a repository path, or nil if it is not a page.
local function site_path(repo)
  if repo == "README.md" then return "ABOUT.html" end
  if repo == "doc/README.md" then return "index.html" end
  local inside = repo:match("^doc/(.+)%.md$")
  if inside then return inside .. ".html" end
  return nil
end

-- `to` relative to the folder `from_dir` (both site paths, "" = site root).
local function relpath(to, from_dir)
  local a, b = split(from_dir), split(to)
  local i = 1
  while i <= #a and i < #b and a[i] == b[i] do i = i + 1 end
  local out = {}
  for _ = i, #a do out[#out + 1] = ".." end
  for j = i, #b do out[#out + 1] = b[j] end
  return table.concat(out, "/")
end

local function github(repo, is_dir)
  return string.format("%s/%s/%s/%s", repo_url, is_dir and "tree" or "blob", branch, repo)
end

local function relink(page_repo, page_site, el)
  local target = el.target
  if target:match("^%a[%w+.-]*:") or target:match("^#") or target == "" then
    return nil -- absolute URL, mailto:, or same-page anchor
  end
  local path, frag = target:match("^([^#]*)(#?.*)$")
  local is_dir = path:sub(-1) == "/"
  local base = dirname(page_repo)
  local repo = normalize((base ~= "" and base .. "/" or "") .. path)
  if not repo then
    io.stderr:write(string.format("links.lua: %s: link %q leaves the repository\n",
                                  page_repo, target))
    return nil
  end
  local site = site_path(repo)
  if site then
    el.target = relpath(site, dirname(page_site)) .. frag
  else
    el.target = github(repo, is_dir) .. frag
  end
  return el
end

function Pandoc(doc)
  repo_url = pandoc.utils.stringify(doc.meta.repo_url or "")
  branch = pandoc.utils.stringify(doc.meta.branch or "master")
  local page_repo = normalize("doc/" .. PANDOC_STATE.input_files[1])
  local page_site = page_repo and site_path(page_repo)
  if not page_site then
    error("links.lua: " .. PANDOC_STATE.input_files[1] .. " is not a site page")
  end

  doc = doc:walk({ Link = function(el) return relink(page_repo, page_site, el) end })

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
