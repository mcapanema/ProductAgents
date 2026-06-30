// Category: AI COMPONENTS — the differentiating layer (Phase 4: 4A–4C).
// Components anchored to the ProductAgents event vocabulary and streaming reasoning model.
import { Phase4Agents } from "./phase4/Phase4Agents";
import { Phase4Execution } from "./phase4/Phase4Execution";
import { Phase4LLM } from "./phase4/Phase4LLM";

export function AIComponents() {
  return (
    <>
      <div className="sg-intro">
        <h2>AI components</h2>
        <p>
          The differentiating layer — components anchored to the ProductAgents
          event vocabulary and streaming reasoning model. Phase 4: agent status,
          execution timeline, LLM inspection.
        </p>
      </div>
      <Phase4Agents />
      <Phase4Execution />
      <Phase4LLM />
    </>
  );
}
