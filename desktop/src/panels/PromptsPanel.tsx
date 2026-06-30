import { useEffect, useState } from "react";
import { useIpc } from "../app/IpcProvider";
import type { PromptDiff, PromptSummary, PromptVersion } from "../ipc/types";
import { defaultDiffPair, versionLabel } from "./promptView";

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
      {list.length === 0 && <p className="muted">No prompts found.</p>}
      <div className="row" style={{ alignItems: "flex-start", gap: 24 }}>
        <div style={{ flex: "0 0 280px" }}>
          {list.map((p) => (
            <div className="list-item" key={p.name} onClick={() => open(p)}>
              <div>{p.name}</div>
              <div className="muted">{versionLabel(p.active, p.active)}</div>
            </div>
          ))}
        </div>
        {selected && (
          <div style={{ flex: 1 }}>
            <h2 style={{ marginTop: 0 }}>{selected.name}</h2>
            <div
              className="row"
              style={{ gap: 8, flexWrap: "wrap", marginBottom: 12 }}
            >
              {selected.versions.map((v) => (
                <span key={v} style={{ display: "inline-flex", gap: 4 }}>
                  <button onClick={() => showVersion(selected.name, v)}>
                    {versionLabel(v, selected.active)}
                  </button>
                  {v !== selected.active && (
                    <button onClick={() => rollback(selected.name, v)}>↺</button>
                  )}
                </span>
              ))}
              {defaultDiffPair(selected) && (
                <button onClick={() => showDiff(selected)}>Diff vs default</button>
              )}
            </div>
            {diff ? (
              <pre style={pre}>{diff.diff}</pre>
            ) : (
              version && (
                <div>
                  <textarea
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    style={{ width: "100%", minHeight: 240, ...pre }}
                  />
                  <div className="row" style={{ gap: 8, marginTop: 8 }}>
                    <button onClick={save} disabled={!ipc}>Save as new version</button>
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
