import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./app/App";
// Design tokens — the source of truth lives in design/tokens/, imported here
// so desktop renders the real system (not a copy). Layer order: primitives →
// semantic (non-color) + components → themes (color, [data-theme]).
import "../../design/tokens/primitives.css";
import "../../design/tokens/semantic.css";
import "../../design/tokens/components.css";
import "../../design/tokens/themes/dark.css";
import "../../design/tokens/themes/light.css";
import "../../design/styleguide/src/fonts.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
