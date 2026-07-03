import { useEffect, useState } from "react";
import { Button, Drawer, Input } from "antd";
import { useIpc } from "../app/IpcProvider";
import type { WorkflowNode } from "../ipc/types";
import { nodeLabel } from "./workflowView";

interface Props {
  node: WorkflowNode | null;
  onClose: () => void;
}

/**
 * One editor per prompt the clicked graph node renders. Saving appends a new
 * version through the existing prompt registry (same surface as PromptsPanel;
 * diff/rollback stay over there).
 */
export function NodePromptDrawer({ node, onClose }: Props) {
  const ipc = useIpc();
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState<string | null>(null);

  useEffect(() => {
    if (!ipc || !node) return;
    setDrafts({});
    setSaved(null);
    (async () => {
      try {
        const all = await ipc.promptsList();
        const loaded: Record<string, string> = {};
        for (const name of node.prompts) {
          const active = all.find((p) => p.name === name)?.active ?? 0;
          loaded[name] = (await ipc.promptsShow(name, active)).text;
        }
        setDrafts(loaded);
      } catch {
        setDrafts({});
      }
    })();
  }, [ipc, node]);

  async function save(name: string) {
    if (!ipc) return;
    try {
      await ipc.promptsSave(name, drafts[name] ?? "");
      setSaved(name);
    } catch {
      /* degrade: leave the editor as-is */
    }
  }

  return (
    <Drawer
      title={node ? `${nodeLabel(node.id)} prompts` : ""}
      open={node !== null}
      onClose={onClose}
      width={560}
    >
      {node?.prompts.map((name) => (
        <div key={name} style={{ marginBottom: 24 }}>
          <h3 style={{ marginTop: 0 }}>{name}</h3>
          <Input.TextArea
            value={drafts[name] ?? ""}
            onChange={(e) => {
              setDrafts((d) => ({ ...d, [name]: e.target.value }));
              setSaved(null);
            }}
            style={{ width: "100%", minHeight: 180, whiteSpace: "pre-wrap" }}
          />
          <div className="row" style={{ gap: 8, marginTop: 8 }}>
            <Button onClick={() => save(name)} disabled={!ipc}>
              Save as new version
            </Button>
            {saved === name && <span className="muted">Saved.</span>}
          </div>
        </div>
      ))}
    </Drawer>
  );
}
