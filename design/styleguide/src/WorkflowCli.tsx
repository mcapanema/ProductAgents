// Category: WORKFLOW & CLI — planning and orchestration layer (Phase 5: 5A–5B).
// Components anchored to the roadmap/initiative-planning domain and the productagents CLI.
import type { Density } from "./sg";
import { Phase5Workflow } from "./phase5/Phase5Workflow";
import { Phase5CLI } from "./phase5/Phase5CLI";

export function WorkflowCli({ density }: { density: Density }) {
  return (
    <>
      <div className="sg-intro">
        <h2>Workflow & CLI</h2>
        <p>
          Planning and orchestration layer — roadmap/initiative-planning
          primitives (Phase 5A) and terminal/command-output primitives for the
          productagents CLI (Phase 5B).
        </p>
      </div>
      <Phase5Workflow density={density} />
      <Phase5CLI density={density} />
    </>
  );
}
