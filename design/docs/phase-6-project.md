# Phase 6 — Project components

ProductAgents-specific surfaces: switching workspaces, summarizing a project
or connected repository, surfacing git state, and browsing a project's files.
Grounded in real platform shapes (`WorkspaceService.list()`/`resolve()` for
the workspace name/path, the GitHub connector's `owner/repo` for repository
identity) where a model exists today; git/file-tree state is forward-looking,
matching the surface a desktop file explorer needs. Built only from the
existing token layer (no new colors). Live gallery: `styleguide` → Project.

Icons are inline SVG (`viewBox 0 0 24 24`, `stroke currentColor`,
`stroke-width 1.75`, round caps), defined locally in `Phase6Project.tsx`.
Status hues reuse `--success`/`--danger`/`--info`/`--signal` (amber is a
generic *state* token, never a literal `--warning` — see the "SIGNALS" block
in `themes/dark.css`) and `--text-tertiary` for neutral/untracked.

---

## Workspace Selector

- **Purpose** — switch the active workspace; lists every workspace from
  `WorkspaceService.list()` with the active one marked.
- **When to use / not** — global chrome (top bar) for switching the working
  context. Not a project picker for a single run — that's scoped elsewhere.
- **Anatomy** — `p6-ws-trigger` button (folder icon + name + chevron) opening
  a `p6-ws-list` of `p6-ws-item` buttons, each with name, path, and an
  active-state dot.
- **States** — toggled open/closed by the trigger button (the gallery shows
  the open state, which demonstrates the trigger and the list together);
  `aria-current="true"` on the active item paints its dot `--success`.
- **Keyboard** — trigger is a real `button` with `aria-haspopup="listbox"` /
  `aria-expanded`; each item is a real `button` in normal tab order.
- **Tokens** — `--surface-raised`, `--card-bg-raised`, `--card-border`,
  `--card-radius`, `--card-shadow-hover`, `--text-tertiary`, `--success`,
  `--focus-ring-width/-offset`, `--border-focus`.

## Project Card

- **Purpose** — workspace summary: name, path, initiative/feature counts,
  last connector sync.
- **When to use / not** — a projects/workspaces overview grid. Not a single
  initiative's detail — see Phase 5A's `TaskCard` for that.
- **Anatomy** — `p6-card` → head (folder icon + name), path, a stat pair
  (initiatives/features), foot (sync time).
- **Tokens** — `--card-bg/-border/-radius/-pad/-shadow`, `--text-heading-4`,
  `--text-code`, `--text-caption`, `--ls-wide`.

## Repository Card

- **Purpose** — connected GitHub repository summary: default branch,
  visibility, connector health, last sync.
- **When to use / not** — the Connectors/repository overview. Distinct from
  `RepositoryCardData`'s sibling `ProjectCard`, which summarizes the local
  workspace, not the remote repo.
- **Anatomy** — `p6-card` → head (name), a row of `BranchBadge` +
  `p6-visibility` chip, foot (health + sync time).
- **States** — visibility `public`/`private`; health `healthy`/`degraded`/`error`.
- **Accessibility** — health is never color-only: every state pairs an icon
  (`check-circle`/`alert-triangle`/`x-circle`) with its text label.
- **Tokens** — `--text-success`, `--text-warning`, `--text-error`,
  `--border-subtle`, `--radius-pill`.

## Git Status

- **Purpose** — working-tree summary: clean / changed (with a count) /
  conflicted, plus ahead/behind counts vs. the remote.
- **When to use / not** — a file explorer or project header showing local
  git state. Not a CLI command's exit status — see Phase 5B's `ExitStatus`.
- **Anatomy** — `p6-git-status` → state label (icon + text, count inline for
  `dirty`) + optional ahead/behind counts in monospace.
- **States** — `clean` (success), `dirty` (signal/amber), `conflict` (danger).
- **Accessibility** — state color is paired with an icon and a text label,
  never color alone.
- **Tokens** — `--text-success`, `--text-warning`, `--text-error`,
  `--text-code`.

## Branch Badge

- **Purpose** — compact pill naming a git branch.
- **When to use / not** — alongside a repository or git-status surface. Not a
  generic tag — see Phase 3D's `Tag`/`Chip`.
- **Anatomy** — `p6-branch-badge` (git-branch icon + name), optional
  `default` qualifier.
- **States** — default (`data-current="false"`, neutral) vs. current
  (`data-current="true"`, accent-tinted border + text).
- **Tokens** — `--surface-raised`, `--border-subtle`, `--accent`,
  `--accent-text`, `--radius-pill`.

## Directory Tree

- **Purpose** — recursive file/folder list with git-status decoration dots.
- **When to use / not** — browsing a project's files (paired with File
  Preview in File Explorer). Not a generic data hierarchy — see Phase 3D's
  `Tree` for that; this one is file-system-specific (file-type icons +
  git-status dots).
- **Anatomy** — `p6-tree` (`role="tree"`) → `p6-tree-row` per node, indented
  by `--p6-tree-level` × `--space-20`, with a twist chevron, a file/folder
  icon, the name, and an optional status dot.
- **States** — expanded/collapsed per folder; selected row gets
  `aria-selected` + an accent-subtle background; status dot is
  `modified` (signal) / `added` (success) / `untracked` (tertiary).
- **Keyboard** — every row is a focusable, `Enter`/`Space`-activatable `div`
  (matches Phase 3D's `dd-tree` convention); folders toggle, files select.
- **Tokens** — `--space-20`, `--icon-sm`, `--text-tertiary`,
  `--accent-subtle`, `--signal`, `--success`, `--radius-full`.

## File Explorer

- **Purpose** — composite panel: `DirectoryTree` on the left, `FilePreview`
  on the right, wired together by selection state.
- **When to use / not** — a project's file-browsing surface. Pair with Phase
  3D's `Diff Viewer` for a file's change history; this component does not
  duplicate diffing.
- **Anatomy** — `p6-explorer` two-column grid: `p6-explorer__crumbs` +
  `DirectoryTree` on the left, `FilePreview` on the right.
- **Tokens** — `--surface-sunken`, `--border-subtle`, `--card-radius`,
  `--space-16`.

## File Preview

- **Purpose** — selected-file detail: name, path, size, modified time, and
  either a code snippet, an image placeholder tile, or an
  unsupported-type notice.
- **When to use / not** — the right pane of File Explorer, or standalone when
  a single file needs inspecting. Not a full code editor.
- **Anatomy** — `p6-preview` → head (icon + name), meta line (path · size ·
  modified), then one of: `p6-preview__body` (line-numbered monospace
  snippet, for code/docs files), `p6-preview__placeholder` (icon tile, for
  images and unsupported binary files, with an optional caption).
- **States** — `code` (any text-like kind — TSX, YAML, Markdown, etc. all
  share the same snippet rendering) / `image` / `other` (binary, e.g.
  `productagents.db` — "No preview available") / no selection
  (`p6-preview__empty`, an icon + "No file selected" + a hint sentence,
  distinct from the `other` state: nothing is selected at all, vs. a file is
  selected but can't be rendered).
- **Tokens** — `--text-code`, `--surface-sunken`, `--card-bg-raised`,
  `--text-disabled` (line numbers), `--text-secondary` (empty-state title),
  `--space-24` (empty-state padding).

## Recent Projects

- **Purpose** — recently opened workspaces, most recent first.
- **When to use / not** — a landing/empty-state surface for re-entering a
  workspace. Not the full `Workspace Selector` list (no active-state dot;
  ordered by recency, not name).
- **Anatomy** — `p6-recent` list of `p6-recent-row` buttons: folder icon,
  name + path, relative "opened" time with a clock icon.
- **Keyboard** — each row is a real `button`, focusable with a visible ring.
- **Tokens** — `--text-tertiary`, `--text-code`, `--surface-hover`,
  `--radius-control`.
