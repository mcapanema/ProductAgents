import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./fonts.css";
// Design tokens — the source of truth lives in design/tokens/, imported here so
// the styleguide renders the real system (not a copy).
import "../../tokens/primitives.css";
import "../../tokens/themes/dark.css";
import "../../tokens/themes/light.css";
import "./harness.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
