import { useEffect, useMemo, useState } from "react";
import { Button, Drawer, Input, Tag, Tooltip, Alert, Typography } from "antd";
import { useIpc } from "../app/IpcProvider";
import type { PromptSummary, WorkflowNode } from "../ipc/types";
import { nodeLabel } from "./workflowView";
import { KIND_META, nodeKind } from "./workflowNodeKinds";
import { versionLabel } from "./promptView";
import { extractVariables, KNOWN_VARIABLES, lineDiff, isDirty } from "./promptEditorView";

interface Props {
  node: WorkflowNode | null;
  onClose: () => void;
  onDirtyChange?: (dirty: boolean) => void;
}

type SaveState = "idle" | "saved" | "error";

const MONO = { fontFamily: "var(--font-mono), ui-monospace, monospace", fontSize: 13 } as const;

/**
 * One editor per prompt the clicked graph node renders. Saving appends a new
 * version through the existing prompt registry (same surface as PromptsPanel;
 * diff/rollback stay over there).
 */
export function NodePromptDrawer({ node, onClose, onDirtyChange }: Props) {
  const ipc = useIpc();
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [originals, setOriginals] = useState<Record<string, string>>({});
  const [summaries, setSummaries] = useState<Record<string, PromptSummary>>({});
  const [saveState, setSaveState] = useState<Record<string, SaveState>>({});
  const [showDiff, setShowDiff] = useState<Record<string, boolean>>({});

  const dirty = useMemo(
    () => Object.keys(drafts).some((k) => isDirty(drafts[k] ?? "", originals[k] ?? "")),
    [drafts, originals],
  );
  useEffect(() => { onDirtyChange?.(dirty); }, [dirty, onDirtyChange]);

  useEffect(() => {
    if (!ipc || !node) return;
    setDrafts({}); setOriginals({}); setSaveState({}); setShowDiff({});
    (async () => {
      try {
        const all = await ipc.promptsList();
        const sums: Record<string, PromptSummary> = {};
        const loaded: Record<string, string> = {};
        for (const name of node.prompts) {
          const s = all.find((p) => p.name === name);
          if (s) sums[name] = s;
          const active = s?.active ?? 0;
          loaded[name] = (await ipc.promptsShow(name, active)).text;
        }
        setSummaries(sums);
        setDrafts(loaded);
        setOriginals(loaded);
      } catch {
        setDrafts({}); setOriginals({});
      }
    })();
  }, [ipc, node]);

  async function save(name: string) {
    if (!ipc) return;
    try {
      const updated = await ipc.promptsSave(name, drafts[name] ?? "");
      setSummaries((s) => ({ ...s, [name]: updated }));
      setOriginals((o) => ({ ...o, [name]: drafts[name] ?? "" }));
      setSaveState((s) => ({ ...s, [name]: "saved" }));
    } catch {
      setSaveState((s) => ({ ...s, [name]: "error" }));
    }
  }

  const meta = node ? KIND_META[nodeKind(node.id)] : null;

  return (
    <Drawer
      title={
        node && meta ? (
          <div>
            <Typography.Text type="secondary" style={{ textTransform: "uppercase", fontSize: 11, letterSpacing: "0.06em" }}>
              {meta.role}
            </Typography.Text>
            <div style={{ font: "var(--text-heading-4)" }}>{nodeLabel(node.id)}</div>
            <Typography.Text type="secondary" style={{ fontWeight: 400 }}>{meta.description}</Typography.Text>
          </div>
        ) : ""
      }
      open={node !== null}
      onClose={onClose}
      width="var(--width-dialog-lg)"
      destroyOnClose
    >
      {node?.prompts.map((name) => {
        const summary = summaries[name];
        const draft = drafts[name] ?? "";
        const vars = extractVariables(draft);
        const nodeDirty = isDirty(draft, originals[name] ?? "");
        const diff = lineDiff(originals[name] ?? "", draft);
        return (
          <section key={name} style={{ marginBottom: 32 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
              <code style={{ font: "var(--text-code)" }}>{name}</code>
              {summary && <Tag>{versionLabel(summary.active, summary.active)}</Tag>}
            </div>

            {vars.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4, margin: "8px 0" }}>
                {vars.map((v) => (
                  <Tooltip key={v} title={KNOWN_VARIABLES.includes(v) ? "Substituted at runtime" : "Unknown variable — will not be substituted"}>
                    <Tag color={KNOWN_VARIABLES.includes(v) ? "blue" : "warning"} style={MONO}>${v}</Tag>
                  </Tooltip>
                ))}
              </div>
            )}

            {showDiff[name] ? (
              <pre style={{ ...MONO, margin: 0, padding: 12, background: "var(--surface-sunken)", borderRadius: "var(--radius-field)", maxHeight: 260, overflow: "auto" }}>
                {diff.map((l, idx) => (
                  <div key={idx} style={{
                    background: l.type === "add" ? "color-mix(in oklch, var(--ai-done) 18%, transparent)"
                      : l.type === "del" ? "color-mix(in oklch, var(--ai-failed) 18%, transparent)" : "transparent",
                    color: "var(--text-primary)", whiteSpace: "pre-wrap",
                  }}>
                    {l.type === "add" ? "+ " : l.type === "del" ? "- " : "  "}{l.text || " "}
                  </div>
                ))}
              </pre>
            ) : (
              <Input.TextArea
                value={draft}
                onChange={(e) => {
                  setDrafts((d) => ({ ...d, [name]: e.target.value }));
                  setSaveState((s) => ({ ...s, [name]: "idle" }));
                }}
                autoSize={{ minRows: 8, maxRows: 20 }}
                style={{ ...MONO, whiteSpace: "pre" }}
                spellCheck={false}
              />
            )}

            <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8 }}>
              <Button type="primary" onClick={() => save(name)} disabled={!ipc || !nodeDirty}>
                Save as new version
              </Button>
              <Button type="text" disabled={!nodeDirty} onClick={() => setShowDiff((s) => ({ ...s, [name]: !s[name] }))}>
                {showDiff[name] ? "Edit" : "View diff"}
              </Button>
              {saveState[name] === "saved" && (
                <Alert type="success" showIcon message="Saved a new version." style={{ padding: "2px 8px" }} />
              )}
              {saveState[name] === "error" && (
                <Alert type="error" showIcon message="Couldn't save — try again." style={{ padding: "2px 8px" }} />
              )}
            </div>
          </section>
        );
      })}
    </Drawer>
  );
}
