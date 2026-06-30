// Phase 6 — Project components. ProductAgents-specific surfaces: switching
// workspaces, summarizing a project/repository, showing git state, and
// browsing a project's files. Built from the Phase-2 token layer only (no new
// colours); status hues reuse --success/--danger/--info/--signal (amber =
// generic state, never a literal "warning" token) and --text-tertiary for
// neutral/untracked. Keyboard-first; reduced-motion has nothing to guard here
// (no animation in this phase).
import { useState } from "react";
import type { CSSProperties, KeyboardEvent } from "react";
import type { Density } from "../sg";
import { Section, Specimen } from "../sg";
import "./phase6-project.css";

const vars = (o: Record<string, string>): CSSProperties => o as CSSProperties;

// Enter / Space activation for non-button interactive rows (keyboard-first).
const activate = (fn: () => void) => (e: KeyboardEvent) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    fn();
  }
};

/* ── Icons ──────────────────────────────────────────────────────────────────── */

type IconName =
  | "folder"
  | "file"
  | "file-code"
  | "file-image"
  | "git-branch"
  | "check-circle"
  | "alert-triangle"
  | "x-circle"
  | "chevron-right"
  | "chevron-down"
  | "search"
  | "clock";

const PATHS: Record<IconName, React.ReactNode> = {
  folder: <path d="M3 7a2 2 0 012-2h4l1.5 2H19a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" />,
  file: <><path d="M7 3h7l4 4v13a1 1 0 01-1 1H7a1 1 0 01-1-1V4a1 1 0 011-1z" /><path d="M14 3v4h4" /></>,
  "file-code": <><path d="M7 3h7l4 4v13a1 1 0 01-1 1H7a1 1 0 01-1-1V4a1 1 0 011-1z" /><path d="M14 3v4h4" /><path d="M9.5 13l-1.5 1.5 1.5 1.5M13.5 13l1.5 1.5-1.5 1.5" /></>,
  "file-image": <><path d="M7 3h7l4 4v13a1 1 0 01-1 1H7a1 1 0 01-1-1V4a1 1 0 011-1z" /><path d="M14 3v4h4" /><circle cx="10" cy="13.5" r="1" fill="currentColor" stroke="none" /><path d="M8 17l2.3-2.3 1.7 1.7 2-2L17 17" /></>,
  "git-branch": <><circle cx="6" cy="6" r="2.2" /><circle cx="6" cy="18" r="2.2" /><circle cx="18" cy="7.5" r="2.2" /><path d="M6 8.2V15.8" /><path d="M18 9.7v1.3a4 4 0 01-4 4H9" /></>,
  "check-circle": <><circle cx="12" cy="12" r="8" /><path d="M8.5 12.5l2.3 2.3L16 9.5" /></>,
  "alert-triangle": <><path d="M12 4l9 16H3z" /><path d="M12 10v4" /><path d="M12 17h.01" /></>,
  "x-circle": <><circle cx="12" cy="12" r="8" /><path d="M9 9l6 6M15 9l-6 6" /></>,
  "chevron-right": <path d="M9 6l6 6-6 6" />,
  "chevron-down": <path d="M6 9l6 6 6-6" />,
  search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="M20 20l-4.5-4.5" /></>,
  clock: <><circle cx="12" cy="12" r="8" /><path d="M12 7.5v5l3.2 1.8" /></>,
};

function Icon({ name, size = "sm" }: { name: IconName; size?: "xs" | "sm" | "md" }) {
  return (
    <svg
      className={`p6-ico p6-ico--${size}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {PATHS[name]}
    </svg>
  );
}

/* ── 1. Workspace Selector ─────────────────────────────────────────────────── */

interface WorkspaceData { name: string; path: string; active: boolean }

const WORKSPACES: WorkspaceData[] = [
  { name: "default", path: "~/.productagents/workspaces/default", active: true },
  { name: "acme-corp", path: "~/.productagents/workspaces/acme-corp", active: false },
  { name: "staging", path: "~/.productagents/workspaces/staging", active: false },
];

function WorkspaceSelector({ startOpen = false }: { startOpen?: boolean }) {
  const [open, setOpen] = useState(startOpen);
  const [current, setCurrent] = useState(WORKSPACES[0].name);
  return (
    <div className="p6-ws-selector">
      <button
        type="button"
        className="p6-ws-trigger"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <Icon name="folder" size="sm" />
        <span className="p6-ws-trigger__name">{current}</span>
        <span className="p6-ws-trigger__chevron"><Icon name={open ? "chevron-down" : "chevron-right"} size="xs" /></span>
      </button>
      {open && (
        <ul className="p6-ws-list" role="listbox" aria-label="Workspaces">
          {WORKSPACES.map((w) => (
            <li key={w.name} role="option" aria-selected={w.name === current}>
              <button
                type="button"
                className="p6-ws-item"
                aria-current={w.name === current}
                onClick={() => { setCurrent(w.name); setOpen(false); }}
              >
                <Icon name="folder" size="sm" />
                <span className="p6-ws-item__meta">
                  <span>{w.name}</span>
                  <span className="p6-ws-item__path">{w.path}</span>
                </span>
                <span className="p6-ws-item__dot" aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/* ── 2. Project Card ───────────────────────────────────────────────────────── */

interface ProjectCardData {
  name: string;
  path: string;
  initiatives: number;
  features: number;
  lastSync: string;
}

const PROJECTS: ProjectCardData[] = [
  { name: "default", path: "~/.productagents/workspaces/default", initiatives: 6, features: 23, lastSync: "2m ago" },
  { name: "acme-corp", path: "~/.productagents/workspaces/acme-corp", initiatives: 2, features: 9, lastSync: "1h ago" },
];

function ProjectCard({ data }: { data: ProjectCardData }) {
  return (
    <article className="p6-card">
      <div className="p6-card__head">
        <Icon name="folder" size="md" />
        <h4 className="p6-card__title">{data.name}</h4>
      </div>
      <span className="p6-card__path">{data.path}</span>
      <div className="p6-card__stats">
        <div className="p6-card__stat">
          <span className="p6-card__stat-value">{data.initiatives}</span>
          <span className="p6-card__stat-label">Initiatives</span>
        </div>
        <div className="p6-card__stat">
          <span className="p6-card__stat-value">{data.features}</span>
          <span className="p6-card__stat-label">Features</span>
        </div>
      </div>
      <div className="p6-card__foot">
        <span className="p6-card__sync">Synced {data.lastSync}</span>
      </div>
    </article>
  );
}

/* ── 3. Repository Card ────────────────────────────────────────────────────── */

type Health = "healthy" | "degraded" | "error";

interface RepositoryCardData {
  fullName: string;
  defaultBranch: string;
  visibility: "public" | "private";
  health: Health;
  lastSynced: string;
}

const HEALTH_CFG: Record<Health, { label: string; icon: IconName }> = {
  healthy: { label: "Healthy", icon: "check-circle" },
  degraded: { label: "Degraded", icon: "alert-triangle" },
  error: { label: "Error", icon: "x-circle" },
};

const REPOSITORIES: RepositoryCardData[] = [
  { fullName: "acme/productagents", defaultBranch: "main", visibility: "private", health: "healthy", lastSynced: "3m ago" },
  { fullName: "acme/connectors-sdk", defaultBranch: "main", visibility: "public", health: "degraded", lastSynced: "40m ago" },
];

function RepositoryCard({ data }: { data: RepositoryCardData }) {
  const h = HEALTH_CFG[data.health];
  return (
    <article className="p6-card">
      <div className="p6-card__head">
        <Icon name="folder" size="md" />
        <h4 className="p6-card__title">{data.fullName}</h4>
      </div>
      <div className="p6-row">
        <BranchBadge name={data.defaultBranch} isDefault />
        <span className="p6-visibility">{data.visibility}</span>
      </div>
      <div className="p6-card__foot">
        <span className="p6-health" data-state={data.health}>
          <Icon name={h.icon} size="xs" />
          {h.label}
        </span>
        <span className="p6-card__sync">Synced {data.lastSynced}</span>
      </div>
    </article>
  );
}

/* ── 4. Git Status ─────────────────────────────────────────────────────────── */

type GitState = "clean" | "dirty" | "conflict";

const GIT_STATE_CFG: Record<GitState, { label: string; icon: IconName }> = {
  clean: { label: "Clean", icon: "check-circle" },
  dirty: { label: "Changes", icon: "alert-triangle" },
  conflict: { label: "Conflicts", icon: "x-circle" },
};

function GitStatus({ state, changed = 0, ahead = 0, behind = 0 }: {
  state: GitState; changed?: number; ahead?: number; behind?: number;
}) {
  const cfg = GIT_STATE_CFG[state];
  return (
    <div className="p6-git-status" data-state={state}>
      <span className="p6-git-status__label">
        <Icon name={cfg.icon} size="xs" />
        {cfg.label}{state === "dirty" && changed > 0 ? ` (${changed})` : ""}
      </span>
      {(ahead > 0 || behind > 0) && (
        <span className="p6-git-status__counts">
          {ahead > 0 && <span className="p6-git-status__ahead">↑{ahead}</span>}
          {behind > 0 && <span className="p6-git-status__behind">↓{behind}</span>}
        </span>
      )}
    </div>
  );
}

/* ── 5. Branch Badge ───────────────────────────────────────────────────────── */

function BranchBadge({ name, isDefault = false, isCurrent = false }: {
  name: string; isDefault?: boolean; isCurrent?: boolean;
}) {
  return (
    <span className="p6-branch-badge" data-current={isCurrent}>
      <Icon name="git-branch" size="xs" />
      {name}
      {isDefault && <span className="p6-branch-badge__default">default</span>}
    </span>
  );
}

/* ── 6. Directory Tree ─────────────────────────────────────────────────────── */

type FileStatus = "modified" | "added" | "untracked";
type FileKind = "folder" | "code" | "image" | "other";
interface FileNode {
  id: string;
  name: string;
  kind: FileKind;
  status?: FileStatus;
  children?: FileNode[];
}

const FILE_TREE: FileNode[] = [
  {
    id: "src", name: "src", kind: "folder", children: [
      {
        id: "phase6", name: "phase6", kind: "folder", children: [
          { id: "p6tsx", name: "Phase6Project.tsx", kind: "code", status: "modified" },
          { id: "p6css", name: "phase6-project.css", kind: "code", status: "added" },
        ],
      },
      { id: "app", name: "App.tsx", kind: "code", status: "modified" },
    ],
  },
  {
    id: "docs", name: "docs", kind: "folder", children: [
      { id: "doc6", name: "phase-6-project.md", kind: "code", status: "untracked" },
    ],
  },
  { id: "logo", name: "logo.png", kind: "image" },
];

const FILE_ICON: Record<FileKind, IconName> = { folder: "folder", code: "file-code", image: "file-image", other: "file" };

function TreeNode({ node, level, expanded, toggle, selected, select }: {
  node: FileNode; level: number; expanded: Set<string>; toggle: (id: string) => void;
  selected: string; select: (id: string) => void;
}) {
  const hasChildren = !!node.children?.length;
  const isOpen = expanded.has(node.id);
  const style = vars({ "--p6-tree-level": String(level) });
  const activateRow = () => { if (hasChildren) toggle(node.id); else select(node.id); };
  return (
    <li role="treeitem" aria-expanded={hasChildren ? isOpen : undefined} aria-level={level + 1} aria-selected={selected === node.id}>
      <div
        className="p6-tree-row"
        tabIndex={0}
        style={style}
        aria-selected={selected === node.id}
        onClick={activateRow}
        onKeyDown={activate(activateRow)}
      >
        <span className="p6-tree-twist">
          {hasChildren ? <Icon name={isOpen ? "chevron-down" : "chevron-right"} size="xs" /> : null}
        </span>
        <Icon name={FILE_ICON[node.kind]} size="sm" />
        <span className="p6-tree-label">{node.name}</span>
        {node.status && <span className="p6-tree-status" data-status={node.status} aria-label={node.status} />}
      </div>
      {hasChildren && isOpen && (
        <ul role="group" className="p6-tree-group">
          {node.children!.map((c) => (
            <TreeNode key={c.id} node={c} level={level + 1} expanded={expanded} toggle={toggle} selected={selected} select={select} />
          ))}
        </ul>
      )}
    </li>
  );
}

function DirectoryTree({ selected, onSelect }: { selected: string; onSelect: (id: string) => void }) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set(["src", "phase6"]));
  const toggle = (id: string) => setExpanded((s) => {
    const next = new Set(s);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  });
  return (
    <ul className="p6-tree" role="tree" aria-label="Project files">
      {FILE_TREE.map((n) => (
        <TreeNode key={n.id} node={n} level={0} expanded={expanded} toggle={toggle} selected={selected} select={onSelect} />
      ))}
    </ul>
  );
}

/* ── 7 & 8. File Preview + File Explorer ───────────────────────────────────── */

interface FilePreviewData { id: string; name: string; path: string; kind: FileKind; sizeLabel: string; modified: string; snippet?: string[] }

const FILE_PREVIEWS: Record<string, FilePreviewData> = {
  p6tsx: {
    id: "p6tsx", name: "Phase6Project.tsx", path: "src/phase6/Phase6Project.tsx", kind: "code",
    sizeLabel: "11.4 KB", modified: "2m ago",
    snippet: ["export function Phase6Project({ density }: Props) {", "  return (", "    <Section id=\"p6-workspace-selector\" …>", "      <WorkspaceSelector />", "    </Section>", "  );", "}"],
  },
  logo: { id: "logo", name: "logo.png", path: "logo.png", kind: "image", sizeLabel: "84 KB", modified: "3d ago" },
};

function FilePreview({ data }: { data: FilePreviewData | null }) {
  if (!data) {
    return <div className="p6-preview__empty">Select a file to preview it</div>;
  }
  return (
    <div className="p6-preview">
      <div className="p6-preview__head">
        <Icon name={FILE_ICON[data.kind]} size="sm" />
        <span className="p6-preview__name">{data.name}</span>
      </div>
      <span className="p6-preview__meta">{data.path} · {data.sizeLabel} · modified {data.modified}</span>
      {data.kind === "image" ? (
        <div className="p6-preview__image-tile"><Icon name="file-image" size="md" /></div>
      ) : (
        <div className="p6-preview__body">
          {(data.snippet ?? []).map((line, i) => (
            <div className="p6-preview__line" key={i}><span className="p6-preview__line-no">{i + 1}</span>{line}</div>
          ))}
        </div>
      )}
    </div>
  );
}

function FileExplorer() {
  const [selected, setSelected] = useState("p6tsx");
  return (
    <div className="p6-explorer">
      <div className="p6-explorer__tree">
        <div className="p6-explorer__crumbs">
          <Icon name="folder" size="xs" />
          <span>default workspace</span>
        </div>
        <DirectoryTree selected={selected} onSelect={setSelected} />
      </div>
      <FilePreview data={FILE_PREVIEWS[selected] ?? null} />
    </div>
  );
}

/* ── 9. Recent Projects ────────────────────────────────────────────────────── */

interface RecentProjectData { name: string; path: string; opened: string }

const RECENT: RecentProjectData[] = [
  { name: "default", path: "~/.productagents/workspaces/default", opened: "Just now" },
  { name: "acme-corp", path: "~/.productagents/workspaces/acme-corp", opened: "Yesterday" },
  { name: "staging", path: "~/.productagents/workspaces/staging", opened: "3 days ago" },
];

function RecentProjects() {
  return (
    <ul className="p6-recent">
      {RECENT.map((r) => (
        <li key={r.name}>
          <button type="button" className="p6-recent-row">
            <Icon name="folder" size="sm" />
            <span className="p6-recent-row__meta">
              <span className="p6-recent-row__name">{r.name}</span>
              <span className="p6-recent-row__path">{r.path}</span>
            </span>
            <span className="p6-recent-row__time">
              <Icon name="clock" size="xs" /> {r.opened}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}

/* ── Gallery ────────────────────────────────────────────────────────────────── */

export function Phase6Project({ density }: { density: Density }) {
  return (
    <div data-density={density}>
      <div className="sg-intro">
        <h2>Project components</h2>
        <p>
          ProductAgents-specific surfaces: switching workspaces, summarizing a
          project or connected repository, surfacing git state, and browsing a
          project's files. Reuses the existing status/semantic tokens — no new
          colours.
        </p>
      </div>

      <Section id="p6-workspace-selector" title="Workspace Selector" desc="Switch the active workspace (WorkspaceService.list()/resolve()); active workspace marked with a dot.">
        <Specimen label="closed"><WorkspaceSelector /></Specimen>
        <Specimen label="open"><WorkspaceSelector startOpen /></Specimen>
      </Section>

      <Section id="p6-project-card" title="Project Card" desc="Workspace summary: name, path, initiative/feature counts, last connector sync.">
        <Specimen label="grid">
          <div className="p6-grid">
            {PROJECTS.map((p) => <ProjectCard key={p.name} data={p} />)}
          </div>
        </Specimen>
      </Section>

      <Section id="p6-repository-card" title="Repository Card" desc="Connected GitHub repository: default branch, visibility, connector health.">
        <Specimen label="grid">
          <div className="p6-grid">
            {REPOSITORIES.map((r) => <RepositoryCard key={r.fullName} data={r} />)}
          </div>
        </Specimen>
      </Section>

      <Section id="p6-git-status" title="Git Status" desc="Working-tree summary: clean / changed / conflicted, plus ahead/behind counts.">
        <Specimen label="clean"><GitStatus state="clean" /></Specimen>
        <Specimen label="dirty"><GitStatus state="dirty" changed={4} ahead={2} /></Specimen>
        <Specimen label="conflict"><GitStatus state="conflict" changed={1} behind={3} /></Specimen>
      </Section>

      <Section id="p6-branch-badge" title="Branch Badge" desc="Branch name pill; current branch is accent-tinted, default branch is labeled.">
        <Specimen label="variants">
          <div className="p6-row">
            <BranchBadge name="main" isDefault />
            <BranchBadge name="feature/phase-6-project" isCurrent />
            <BranchBadge name="release/2.4" />
          </div>
        </Specimen>
      </Section>

      <Section id="p6-directory-tree" title="Directory Tree" desc="Recursive file/folder list with git-status decoration dots (modified/added/untracked).">
        <Specimen label="default">
          <DirectoryTree selected="p6tsx" onSelect={() => {}} />
        </Specimen>
      </Section>

      <Section id="p6-file-explorer" title="File Explorer" desc="Directory tree paired with a file preview pane — select a file on the left to preview it on the right.">
        <Specimen label="default">
          <FileExplorer />
        </Specimen>
      </Section>

      <Section id="p6-file-preview" title="File Preview" desc="Selected-file detail: name, path, size, modified time, and a code snippet or image tile.">
        <Specimen label="code"><FilePreview data={FILE_PREVIEWS.p6tsx} /></Specimen>
        <Specimen label="image"><FilePreview data={FILE_PREVIEWS.logo} /></Specimen>
        <Specimen label="empty"><FilePreview data={null} /></Specimen>
      </Section>

      <Section id="p6-recent-projects" title="Recent Projects" desc="Recently opened workspaces, most recent first — each row is keyboard-operable.">
        <Specimen label="default">
          <RecentProjects />
        </Specimen>
      </Section>
    </div>
  );
}
