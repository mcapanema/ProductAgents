import { useEffect, useState } from "react";
import { Alert, Button, Input } from "antd";
import { useIpc } from "../app/IpcProvider";
import type { PromptDiff, PromptSummary, PromptVersion } from "../ipc/types";
import { defaultDiffPair, versionLabel } from "./promptView";
import { isDirty } from "./promptEditorView";
import { EmptyState } from "../ui/EmptyState";
import { EmptyStateIcon } from "../ui/emptyStateIcons";

type SaveState = "idle" | "saved" | "error";

export function PromptsPanel() {
  const ipc = useIpc();
  const [list, setList] = useState<PromptSummary[]>([]);
  const [selected, setSelected] = useState<PromptSummary | null>(null);
  const [version, setVersion] = useState<PromptVersion | null>(null);
  const [diff, setDiff] = useState<PromptDiff | null>(null);
  const [draft, setDraft] = useState("");
  const [original, setOriginal] = useState("");
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [pending, setPending] = useState<PromptSummary | null>(null);

  const dirty = isDirty(draft, original);

  useEffect(() => {
    if (ipc) ipc.promptsList().then(setList).catch(() => setList([]));
  }, [ipc]);

  function load(name: string, v: number, summary: PromptSummary) {
    setSelected(summary);
    setDiff(null);
    setSaveState("idle");
    if (!ipc) return;
    ipc
      .promptsShow(name, v)
      .then((ver) => {
        setVersion(ver);
        setDraft(ver.text);
        setOriginal(ver.text);
      })
      .catch(() => setVersion(null));
  }

  // Guard a list-selection change: never silently discard an unsaved draft.
  function requestOpen(summary: PromptSummary) {
    if (dirty && selected && summary.name !== selected.name) {
      setPending(summary);
      return;
    }
    load(summary.name, summary.active, summary);
  }

  function discardAndOpen() {
    if (!pending) return;
    const next = pending;
    setPending(null);
    load(next.name, next.active, next);
  }

  function showVersion(name: string, v0: number) {
    if (!selected) return;
    load(name, v0, selected);
  }

  async function showDiff(summary: PromptSummary) {
    if (!ipc) return;
    const pair = defaultDiffPair(summary);
    if (!pair) return;
    try {
      setDiff(await ipc.promptsDiff(summary.name, pair[0], pair[1]));
    } catch {
      setDiff(null);
    }
  }

  function applyWrite(updated: PromptSummary, text: string) {
    setList((prev) => prev.map((p) => (p.name === updated.name ? updated : p)));
    setSelected(updated);
    setDiff(null);
    setDraft(text);
    setOriginal(text);
    setSaveState("saved");
  }

  async function save() {
    if (!ipc || !selected) return;
    try {
      applyWrite(await ipc.promptsSave(selected.name, draft), draft);
    } catch {
      setSaveState("error");
    }
  }

  async function rollback(name: string, v: number) {
    if (!ipc) return;
    try {
      const updated = await ipc.promptsRollback(name, v);
      const text = (await ipc.promptsShow(updated.name, updated.active)).text;
      applyWrite(updated, text);
    } catch {
      setSaveState("error");
    }
  }

  const pre = { overflow: "auto", whiteSpace: "pre-wrap" } as const;

  return (
    <div>
      <h1>Prompts</h1>
      <p className="page-desc">Versioned prompt templates for each pipeline node. Edit to create a new version; roll back anytime.</p>
      {list.length === 0 && (
        <EmptyState
          title="No prompts found"
          description="Prompt templates ship with the app and appear here once the registry loads."
          icon={<EmptyStateIcon name="prompts" />}
        />
      )}
      <div className="master-detail">
        <div className="master-detail__list" style={{ flexBasis: 280 }}>
          {list.map((p) => (
            <button
              type="button"
              className={`list-item${selected?.name === p.name ? " is-selected" : ""}`}
              key={p.name}
              onClick={() => requestOpen(p)}
            >
              <div>{p.name}</div>
              <div className="muted">{versionLabel(p.active, p.active)}</div>
            </button>
          ))}
        </div>
        {selected && (
          <div className="master-detail__detail">
            <h2 style={{ marginTop: 0 }}>{selected.name}</h2>
            {pending && (
              <Alert
                type="warning"
                showIcon
                style={{ marginBottom: 12 }}
                message="Unsaved changes"
                description={`Switch to "${pending.name}" and discard your edits to ${selected.name}?`}
                action={
                  <span style={{ display: "inline-flex", gap: 8 }}>
                    <Button size="small" danger onClick={discardAndOpen}>Discard</Button>
                    <Button size="small" onClick={() => setPending(null)}>Keep editing</Button>
                  </span>
                }
              />
            )}
            <div className="row" style={{ gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
              {selected.versions.map((v) => (
                <span key={v} style={{ display: "inline-flex", gap: 4 }}>
                  <Button
                    type={v === selected.active ? "primary" : "default"}
                    onClick={() => showVersion(selected.name, v)}
                  >
                    {versionLabel(v, selected.active)}
                  </Button>
                  {v !== selected.active && (
                    <Button
                      aria-label={`Roll back to ${versionLabel(v, selected.active)}`}
                      onClick={() => rollback(selected.name, v)}
                    >
                      ↺
                    </Button>
                  )}
                </span>
              ))}
              {defaultDiffPair(selected) && (
                <Button onClick={() => showDiff(selected)}>Diff vs default</Button>
              )}
            </div>
            {diff ? (
              <pre style={pre}>{diff.diff}</pre>
            ) : (
              version && (
                <div>
                  <Input.TextArea
                    value={draft}
                    onChange={(e) => { setDraft(e.target.value); setSaveState("idle"); }}
                    style={{ width: "100%", minHeight: 240, ...pre }}
                  />
                  <div className="row" style={{ gap: 8, marginTop: 8, alignItems: "center" }}>
                    <Button onClick={save} disabled={!ipc || !dirty}>Save as new version</Button>
                    {saveState === "saved" && (
                      <Alert type="success" showIcon message="Saved a new version." style={{ padding: "2px 8px" }} />
                    )}
                    {saveState === "error" && (
                      <Alert type="error" showIcon message="Couldn't save — try again." style={{ padding: "2px 8px" }} />
                    )}
                  </div>
                </div>
              )
            )}
          </div>
        )}
      </div>
    </div>
  );
}
