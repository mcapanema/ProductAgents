import { useEffect, useState } from "react";
import { Button, Input } from "antd";
import { useIpc } from "../app/IpcProvider";
import type { PromptDiff, PromptSummary, PromptVersion } from "../ipc/types";
import { defaultDiffPair, versionLabel } from "./promptView";
import { EmptyState } from "../ui/EmptyState";
import { EmptyStateIcon } from "../ui/emptyStateIcons";

export function PromptsPanel() {
  const ipc = useIpc();
  const [list, setList] = useState<PromptSummary[]>([]);
  const [selected, setSelected] = useState<PromptSummary | null>(null);
  const [version, setVersion] = useState<PromptVersion | null>(null);
  const [diff, setDiff] = useState<PromptDiff | null>(null);
  const [draft, setDraft] = useState("");

  useEffect(() => {
    if (ipc) ipc.promptsList().then(setList).catch(() => setList([]));
  }, [ipc]);

  async function open(summary: PromptSummary) {
    if (!ipc) return;
    setSelected(summary);
    setDiff(null);
    try {
      const v = await ipc.promptsShow(summary.name, summary.active);
      setVersion(v);
      setDraft(v.text);
    } catch {
      setVersion(null);
    }
  }

  async function showVersion(name: string, v0: number) {
    if (!ipc) return;
    setDiff(null);
    try {
      const v = await ipc.promptsShow(name, v0);
      setVersion(v);
      setDraft(v.text);
    } catch {
      setVersion(null);
    }
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

  async function refreshAfterWrite(updated: PromptSummary) {
    setList((prev) => prev.map((p) => (p.name === updated.name ? updated : p)));
    setSelected(updated);
    setDiff(null);
    try {
      const v = await ipc!.promptsShow(updated.name, updated.active);
      setVersion(v);
      setDraft(v.text);
    } catch {
      setVersion(null);
    }
  }

  async function save() {
    if (!ipc || !selected) return;
    try {
      await refreshAfterWrite(await ipc.promptsSave(selected.name, draft));
    } catch { /* degrade: leave editor as-is */ }
  }

  async function rollback(name: string, v: number) {
    if (!ipc) return;
    try {
      await refreshAfterWrite(await ipc.promptsRollback(name, v));
    } catch { /* degrade */ }
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
            <div
              className={`list-item${selected?.name === p.name ? " is-selected" : ""}`}
              key={p.name}
              onClick={() => open(p)}
            >
              <div>{p.name}</div>
              <div className="muted">{versionLabel(p.active, p.active)}</div>
            </div>
          ))}
        </div>
        {selected && (
          <div className="master-detail__detail">
            <h2 style={{ marginTop: 0 }}>{selected.name}</h2>
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
                    <Button onClick={() => rollback(selected.name, v)}>↺</Button>
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
                    onChange={(e) => setDraft(e.target.value)}
                    style={{ width: "100%", minHeight: 240, ...pre }}
                  />
                  <div className="row" style={{ gap: 8, marginTop: 8 }}>
                    <Button onClick={save} disabled={!ipc}>Save as new version</Button>
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
