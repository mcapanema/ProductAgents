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

  useEffect(() => {
    if (ipc) ipc.promptsList().then(setList).catch(() => setList([]));
  }, [ipc]);

  async function open(summary: PromptSummary) {
    if (!ipc) return;
    setSelected(summary);
    setDiff(null);
    try {
      setVersion(await ipc.promptsShow(summary.name, summary.active));
    } catch {
      setVersion(null);
    }
  }

  async function showVersion(name: string, v: number) {
    if (!ipc) return;
    setDiff(null);
    try {
      setVersion(await ipc.promptsShow(name, v));
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
                <button key={v} onClick={() => showVersion(selected.name, v)}>
                  {versionLabel(v, selected.active)}
                </button>
              ))}
              {defaultDiffPair(selected) && (
                <button onClick={() => showDiff(selected)}>Diff vs default</button>
              )}
            </div>
            {diff ? (
              <pre style={pre}>{diff.diff}</pre>
            ) : (
              version && <pre style={pre}>{version.text}</pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
