import { useCallback, useEffect, useRef, useState } from "react";
import { AutoComplete, Breadcrumb, Button, Input, Modal, Select } from "antd";
import type { InputRef } from "antd";
import { useIpc } from "./IpcProvider";
import type { View } from "./Sidebar";
import type { SearchEntry } from "./topBarView";
import type { WorkspaceInfo } from "../ipc/types";
import {
  CREATE_OPTION,
  activeWorkspaceName,
  filterEntries,
  searchEntries,
  validWorkspaceName,
  workspaceOptions,
} from "./topBarView";
import "./TopBar.css";

const VIEW_LABELS: Record<View, string> = {
  run: "Run",
  workflows: "Workflows",
  sessions: "Sessions",
  decisions: "Decisions",
  memory: "Memory",
  connectors: "Connectors",
  prompts: "Prompts",
  settings: "Settings",
  reflection: "Reflection",
};

export function TopBar({
  view,
  onNavigate,
  running,
}: {
  view: View;
  onNavigate: (view: View) => void;
  running: boolean;
}) {
  const ipc = useIpc();
  const [workspaces, setWorkspaces] = useState<WorkspaceInfo[]>([]);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);
  const [switching, setSwitching] = useState(false);
  const [entries, setEntries] = useState<SearchEntry[] | null>(null);
  const [query, setQuery] = useState("");
  const searchRef = useRef<InputRef>(null);

  useEffect(() => {
    if (!ipc) return;
    ipc
      .workspacesList()
      .then(setWorkspaces)
      .catch(() => setWorkspaces([]));
  }, [ipc]);

  // ⌘K / Ctrl+K focuses the global search (styleguide: search carries a ⌘K kbd).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // Fetch the searchable corpora lazily, once, on first focus — never during a
  // run (the IPC protocol is single-in-flight while a run streams).
  const loadEntries = useCallback(() => {
    if (!ipc || entries !== null || running) return;
    Promise.all([
      ipc.decisionsList().catch(() => []),
      ipc.sessionsList().catch(() => []),
      ipc.workflowsList().catch(() => []),
    ]).then(([decisions, sessions, workflows]) =>
      setEntries(searchEntries(decisions, sessions, workflows)),
    );
  }, [ipc, entries, running]);

  // A finished run may have recorded a new decision/session — invalidate the
  // cached corpus when idle so the next focus reloads fresh data. (Fetching
  // itself still waits for focus, and never runs mid-run: single-in-flight IPC.)
  useEffect(() => {
    if (!running) setEntries(null);
  }, [running]);

  const active = activeWorkspaceName(workspaces);

  async function switchTo(name: string) {
    if (!ipc || name === active) return;
    setSwitching(true);
    try {
      await ipc.workspacesUse(name);
      // Backend already switched live (workspaces.use rebuilds its services);
      // reload just remounts the panels so every list refetches in the new scope.
      window.location.reload();
    } catch {
      setSwitching(false); // degrade: stay on the current workspace
    }
  }

  function onWorkspaceChange(value: string) {
    if (value === CREATE_OPTION) {
      setNewName("");
      setCreateError(null);
      setCreating(true);
      return;
    }
    void switchTo(value);
  }

  async function onCreate() {
    if (!ipc) return;
    const name = newName.trim();
    if (!validWorkspaceName(name)) {
      setCreateError(
        "invalid workspace name (letters/digits, then letters/digits/._-, max 64)",
      );
      return;
    }
    try {
      await ipc.workspacesCreate(name);
      await ipc.workspacesUse(name);
      // Backend already switched live (workspaces.use rebuilds its services);
      // reload just remounts the panels so every list refetches in the new scope.
      window.location.reload();
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : String(err));
    }
  }

  const results = filterEntries(entries ?? [], query);

  return (
    <header className="topbar">
      <Select
        className="topbar-ws"
        size="small"
        aria-label="Workspace"
        value={active}
        options={workspaceOptions(workspaces)}
        onChange={onWorkspaceChange}
        disabled={running || switching || !ipc}
        loading={switching}
      />
      {/* antd Breadcrumb renders its own <nav>; label it directly instead of
          wrapping in a second nav (nested landmarks confuse screen readers). */}
      <Breadcrumb
        aria-label="Breadcrumb"
        className="topbar-crumbs"
        items={[
          { title: active },
          {
            title: (
              <span aria-current="page">{VIEW_LABELS[view]}</span>
            ),
          },
        ]}
      />
      <div className="topbar-spacer" />
      <div role="search" className="topbar-search">
        <AutoComplete
          value={query}
          onChange={setQuery}
          onFocus={loadEntries}
          disabled={running || !ipc}
          options={results.map((e) => ({
            value: e.key,
            label: e.label,
          }))}
          onSelect={(key: string) => {
            const entry = results.find((e) => e.key === key);
            if (entry) onNavigate(entry.view);
            setQuery("");
          }}
          popupMatchSelectWidth
        >
          <Input
            ref={searchRef}
            size="small"
            aria-label="Global search"
            placeholder="Search decisions, sessions, workflows…"
            suffix={<kbd className="topbar-kbd">⌘K</kbd>}
            allowClear
          />
        </AutoComplete>
      </div>
      <Button
        type="primary"
        size="small"
        disabled={running}
        onClick={() => onNavigate("run")}
      >
        New decision
      </Button>
      <Modal
        title="New workspace"
        open={creating}
        onOk={onCreate}
        okText="Create"
        onCancel={() => setCreating(false)}
        destroyOnHidden
      >
        <Input
          placeholder="workspace name"
          value={newName}
          onChange={(e) => {
            setNewName(e.target.value);
            setCreateError(null);
          }}
          onPressEnter={onCreate}
          autoFocus
        />
        <p className="topbar-modal-hint">
          A workspace is an isolated home for one product organization: its own
          decisions, sessions, memory, connectors, prompts and settings.
        </p>
        {createError && <p className="topbar-modal-error">{createError}</p>}
      </Modal>
    </header>
  );
}
