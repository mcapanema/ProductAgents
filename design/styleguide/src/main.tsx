import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./fonts.css";
// Design tokens — the source of truth lives in design/tokens/, imported here so
// the styleguide renders the real system (not a copy). Layer order:
// primitives → semantic (non-color) + components → themes (color, [data-theme]).
import "../../tokens/primitives.css";
import "../../tokens/semantic.css";
import "../../tokens/components.css";
import "../../tokens/themes/dark.css";
import "../../tokens/themes/light.css";
import "./harness.css";
// Phase 3 — core components. Each sub-phase ships a self-contained CSS module
// (prefixed classes + any new component tokens) consumed by its Phase3*.tsx.
import "./phase3/phase3a-layout.css";
import "./phase3/phase3b-navigation.css";
import "./phase3/phase3c-forms.css";
import "./phase3/phase3d-datadisplay.css";
import "./phase3/phase3e-feedback.css";
import "./phase3/phase3f-overlays.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
