import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./app/App";
// Design system — one stable public entry point (src/ui/tokens.css) re-exports
// the token layers + fonts. Token values stay sourced from design/tokens/*.css.
import "./ui/tokens.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
