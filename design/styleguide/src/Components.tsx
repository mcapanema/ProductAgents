// Category: COMPONENTS — the working component vocabulary (Phase 3: 3A–3F).
// Each sub-phase is a self-contained module under ./phase3/.
import { Phase3Layout } from "./phase3/Phase3Layout";
import { Phase3Navigation } from "./phase3/Phase3Navigation";
import { Phase3Forms } from "./phase3/Phase3Forms";
import { Phase3DataDisplay } from "./phase3/Phase3DataDisplay";
import { Phase3Feedback } from "./phase3/Phase3Feedback";
import { Phase3Overlays } from "./phase3/Phase3Overlays";

export function Components() {
  return (
    <>
      <div className="sg-intro">
        <h2>Core components</h2>
        <p>
          The working component vocabulary — built only from the token layer, adapting across
          theme and density with zero markup change. Each group below is one sub-phase
          (layout · navigation · forms · data display · feedback · overlays).
        </p>
      </div>
      <Phase3Layout />
      <Phase3Navigation />
      <Phase3Forms />
      <Phase3DataDisplay />
      <Phase3Feedback />
      <Phase3Overlays />
    </>
  );
}
