import type { PaletteKind } from "../ipc/types";
import { KIND_META, nodeKind } from "./workflowNodeKinds";
import "./WorkflowPalette.css";

export function newInstanceId(kind: string, existing: Set<string>): string {
  if (!existing.has(kind)) return kind;
  let n = 2;
  while (existing.has(`${kind}#${n}`)) n += 1;
  return `${kind}#${n}`;
}

export function WorkflowPalette({
  palette,
  onAdd,
}: {
  palette: PaletteKind[];
  onAdd: (kind: string) => void;
}) {
  return (
    <div className="wf-palette" role="list">
      {palette.map((k) => {
        const meta = KIND_META[nodeKind(k.kind)];
        return (
          <button
            key={k.kind}
            type="button"
            className="wf-palette-item"
            onClick={() => onAdd(k.kind)}
            title={meta.description}
          >
            <span className="wf-palette-role">{k.role}</span>
            <span className="wf-palette-label">{k.label}</span>
            {k.singleton && <span className="wf-palette-badge">single</span>}
          </button>
        );
      })}
    </div>
  );
}
