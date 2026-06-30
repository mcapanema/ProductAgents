// Phase 3F — Overlays gallery.
// Every overlay is rendered INSIDE a contained `.ov-stage` (position:relative,
// overflow:hidden) so the scrim covers only the preview box, never the page —
// the product portals these same surfaces to <body> with position:fixed. Each
// component ships both an interactive instance (trigger + Esc/focus management)
// and a static always-open preview so reviewers see the surface without acting.
import { useEffect, useId, useRef, useState } from "react";
import { Section } from "../sg";

/* ── Inline Phosphor-style icons (SVG only; sized via CSS class) ─────────── */
const ICONS = {
  close: "M18 6 6 18 M6 6l12 12",
  warning: "M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z M12 9v4 M12 17h.01",
  trash: "M3 6h18 M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2 M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6 M10 11v6 M14 11v6",
  search: "M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16Z M21 21l-4.3-4.3",
  caretRight: "m9 6 6 6-6 6",
  info: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z M12 16v-4 M12 8h.01",
  gear: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z M19.4 13a7.8 7.8 0 0 0 0-2l2-1.6-2-3.4-2.4 1a7.8 7.8 0 0 0-1.7-1L15 3H9l-.3 2.5a7.8 7.8 0 0 0-1.7 1l-2.4-1-2 3.4 2 1.6a7.8 7.8 0 0 0 0 2l-2 1.6 2 3.4 2.4-1c.5.4 1.1.7 1.7 1L9 21h6l.3-2.5c.6-.3 1.2-.6 1.7-1l2.4 1 2-3.4Z",
  copy: "M9 9h10v10a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2V9Z M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1",
  external: "M14 4h6v6 M20 4l-9 9 M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5",
  rename: "M12 20h9 M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5Z",
  bolt: "M13 2 4 14h7l-1 8 9-12h-7l1-8Z",
  doc: "M14 3v5h5 M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8l-5-5Z",
  flow: "M5 3a2 2 0 1 0 0 4 2 2 0 0 0 0-4Z M19 17a2 2 0 1 0 0 4 2 2 0 0 0 0-4Z M5 7v6a4 4 0 0 0 4 4h8",
} as const;

function I({ name, cls }: { name: keyof typeof ICONS; cls?: string }) {
  return (
    <svg
      className={cls ? `ov-ico ${cls}` : "ov-ico"}
      viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"
    >
      <path d={ICONS[name]} />
    </svg>
  );
}

/* ── useOverlay: Esc-to-close + initial focus + Tab focus-trap + focus restore.
 * onClose is read through a ref so the effect runs once per open, not per render.
 * Used by every scrim-backed surface (modal / drawer / command / confirm). ── */
function useOverlay(open: boolean, onClose: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    if (!open) return;
    const panel = ref.current;
    const prev = document.activeElement as HTMLElement | null;
    const focusables = () =>
      panel
        ? Array.from(
            panel.querySelectorAll<HTMLElement>(
              'button:not([disabled]), [href], input, textarea, select, [tabindex]:not([tabindex="-1"])',
            ),
          )
        : [];
    // preventScroll: a focused element inside a clipped stage would otherwise
    // scroll the stage to "reveal" it, dragging edge sheets off their edge.
    (focusables()[0] ?? panel)?.focus({ preventScroll: true });
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        closeRef.current();
      } else if (e.key === "Tab" && panel) {
        const f = focusables();
        if (f.length === 0) {
          e.preventDefault();
          return;
        }
        const i = f.indexOf(document.activeElement as HTMLElement);
        if (e.shiftKey && i <= 0) {
          e.preventDefault();
          f[f.length - 1].focus();
        } else if (!e.shiftKey && i === f.length - 1) {
          e.preventDefault();
          f[0].focus();
        }
      }
    }
    document.addEventListener("keydown", onKey, true);
    return () => {
      document.removeEventListener("keydown", onKey, true);
      prev?.focus?.();
    };
  }, [open]);
  return ref;
}

/* Roving arrow-key focus for role="menu" lists. */
function onMenuKey(e: React.KeyboardEvent<HTMLDivElement>) {
  const items = Array.from(
    e.currentTarget.querySelectorAll<HTMLElement>('[role="menuitem"]:not([aria-disabled="true"])'),
  );
  if (items.length === 0) return;
  const i = items.indexOf(document.activeElement as HTMLElement);
  if (e.key === "ArrowDown") {
    e.preventDefault();
    items[(i + 1) % items.length].focus();
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    items[(i - 1 + items.length) % items.length].focus();
  } else if (e.key === "Home") {
    e.preventDefault();
    items[0].focus();
  } else if (e.key === "End") {
    e.preventDefault();
    items[items.length - 1].focus();
  }
}

/* ── Reusable surface bodies (shared by interactive + static previews) ───── */

function ModalSurface({ size, onClose }: { size: "sm" | "md" | "lg"; onClose?: () => void }) {
  return (
    <>
      <div className="ov-head">
        <div className="ov-titles">
          <h4 id={`ov-modal-${size}-title`}>Re-run analysis</h4>
          <p>Replays the pipeline against the current evidence snapshot.</p>
        </div>
        {onClose && (
          <button className="ov-close" type="button" aria-label="Close dialog" onClick={onClose}>
            <I name="close" cls="ov-ico--sm" />
          </button>
        )}
      </div>
      <div className="ov-body">
        <p>
          Five analysts will re-evaluate the initiative with the latest connector
          sync. The previous decision stays in the log; this creates a new run.
        </p>
        {size !== "sm" && (
          <p>Estimated cost is shown live in the Run view as tokens stream in.</p>
        )}
      </div>
      <div className="ov-foot">
        <button className="demo-btn demo-btn--ghost" type="button" onClick={onClose}>
          Cancel
        </button>
        <button className="demo-btn demo-btn--primary" type="button" onClick={onClose}>
          Re-run
        </button>
      </div>
    </>
  );
}

function DrawerBody({ onClose }: { onClose?: () => void }) {
  return (
    <>
      <div className="ov-head">
        <div className="ov-titles">
          <h4>Decision · D-4192</h4>
          <p>Expand checkout for returning buyers</p>
        </div>
        {onClose && (
          <button className="ov-close" type="button" aria-label="Close inspector" onClick={onClose}>
            <I name="close" cls="ov-ico--sm" />
          </button>
        )}
      </div>
      <div className="ov-body">
        <dl className="ov-kv">
          <div className="ov-kv-row"><dt>Verdict</dt><dd>Approved</dd></div>
          <div className="ov-kv-row"><dt>Confidence</dt><dd>0.78</dd></div>
          <div className="ov-kv-row"><dt>Risk</dt><dd>Medium</dd></div>
          <div className="ov-kv-row"><dt>Approver</dt><dd>You · 2d ago</dd></div>
          <div className="ov-kv-row"><dt>Run</dt><dd>R-2231</dd></div>
        </dl>
      </div>
      <div className="ov-foot">
        <button className="demo-btn demo-btn--secondary" type="button" onClick={onClose}>
          Close
        </button>
      </div>
    </>
  );
}

function MenuItems({ onClose }: { onClose?: () => void }) {
  return (
    <div className="ov-menu" role="menu" aria-label="Decision actions" onKeyDown={onMenuKey}>
      <button className="ov-menu-item" role="menuitem" type="button" onClick={onClose}>
        <I name="external" cls="ov-ico--sm" /> Open in Explorer
        <span className="ov-spacer" />
        <span className="ov-menu-shortcut">↵</span>
      </button>
      <button className="ov-menu-item" role="menuitem" type="button" onClick={onClose}>
        <I name="copy" cls="ov-ico--sm" /> Copy decision ID
        <span className="ov-spacer" />
        <span className="ov-menu-shortcut">⌘C</span>
      </button>
      <button className="ov-menu-item" role="menuitem" type="button" onClick={onClose}>
        <I name="rename" cls="ov-ico--sm" /> Rename
      </button>
      <hr className="ov-menu-sep" />
      {/* submenu hint via trailing caret */}
      <button className="ov-menu-item" role="menuitem" type="button" aria-haspopup="menu" onClick={onClose}>
        <I name="flow" cls="ov-ico--sm" /> Move to workflow
        <span className="ov-spacer" />
        <I name="caretRight" cls="ov-ico--sm" />
      </button>
      <button className="ov-menu-item" role="menuitem" type="button" aria-disabled="true" tabIndex={-1}>
        <I name="doc" cls="ov-ico--sm" /> Export (no outcome yet)
      </button>
      <hr className="ov-menu-sep" />
      <button className="ov-menu-item ov-menu-item--danger" role="menuitem" type="button" onClick={onClose}>
        <I name="trash" cls="ov-ico--sm" /> Delete decision
        <span className="ov-spacer" />
        <span className="ov-menu-shortcut">⌫</span>
      </button>
    </div>
  );
}

const CMD_GROUPS: { group: string; items: { icon: keyof typeof ICONS; label: string; hint: string }[] }[] = [
  {
    group: "Navigate",
    items: [
      { icon: "flow", label: "Go to Run", hint: "G R" },
      { icon: "doc", label: "Open Decisions", hint: "G D" },
    ],
  },
  {
    group: "Actions",
    items: [
      { icon: "bolt", label: "Evaluate initiative…", hint: "⌘N" },
      { icon: "gear", label: "Open Settings", hint: "⌘," },
    ],
  },
];

function CommandSurface({ onClose, inputRef }: { onClose?: () => void; inputRef?: React.Ref<HTMLInputElement> }) {
  const total = CMD_GROUPS.reduce((n, g) => n + g.items.length, 0);
  const [active, setActive] = useState(0);
  const uid = useId(); // unique per instance — the interactive dialog + the static preview both render this
  // Focus stays in the input (combobox); ↑/↓ move the active option via
  // aria-activedescendant, Enter activates it.
  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => (a + 1) % total); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => (a - 1 + total) % total); }
    else if (e.key === "Enter") { e.preventDefault(); onClose?.(); }
  }
  let idx = -1; // running flat index across groups
  return (
    <>
      <div className="ov-cmd-search">
        <I name="search" cls="ov-ico--sm" />
        <input
          ref={inputRef}
          type="text"
          role="combobox"
          aria-expanded="true"
          aria-controls={`${uid}-listbox`}
          aria-autocomplete="list"
          aria-activedescendant={`${uid}-opt-${active}`}
          placeholder="Type a command or search…"
          aria-label="Command"
          onKeyDown={onKeyDown}
        />
        <kbd>Esc</kbd>
      </div>
      <div className="ov-cmd-list" id={`${uid}-listbox`} role="listbox" aria-label="Commands">
        {CMD_GROUPS.map((g) => (
          <div key={g.group}>
            <div className="ov-cmd-group">{g.group}</div>
            {g.items.map((it) => {
              idx += 1;
              const i = idx;
              return (
                <button
                  key={it.label}
                  id={`${uid}-opt-${i}`}
                  className="ov-cmd-item"
                  role="option"
                  aria-selected={i === active}
                  type="button"
                  onMouseMove={() => setActive(i)}
                  onClick={onClose}
                >
                  <I name={it.icon} cls="ov-ico--sm" />
                  {it.label}
                  <span className="ov-spacer" />
                  <span className="ov-menu-shortcut">{it.hint}</span>
                </button>
              );
            })}
          </div>
        ))}
      </div>
    </>
  );
}

function ConfirmSurface({
  variant,
  onClose,
}: {
  variant: "info" | "danger";
  onClose?: () => void;
}) {
  const danger = variant === "danger";
  return (
    <>
      <div className="ov-head">
        <span className={`ov-medallion ov-medallion--${variant}`} aria-hidden="true">
          <I name={danger ? "warning" : "info"} />
        </span>
        <div className="ov-titles">
          <h4>{danger ? "Delete workspace?" : "Discard draft run?"}</h4>
          <p>
            {danger
              ? "“Q3 Pricing” and everything inside it."
              : "Your unsaved evaluation parameters will be lost."}
          </p>
          {danger && (
            <div className="ov-consequence" role="note">
              <I name="warning" cls="ov-ico--sm" />
              <span>
                This permanently removes 142 decisions, 9 connectors and all
                synced evidence. This cannot be undone.
              </span>
            </div>
          )}
        </div>
      </div>
      <div className="ov-foot">
        <button className="demo-btn demo-btn--ghost" type="button" onClick={onClose}>
          Cancel
        </button>
        <button
          className={`demo-btn ${danger ? "demo-btn--danger" : "demo-btn--primary"} ov-trigger`}
          type="button"
          onClick={onClose}
        >
          {danger && <I name="trash" cls="ov-ico--sm" />}
          {danger ? "Delete workspace" : "Discard"}
        </button>
      </div>
    </>
  );
}

/* ── Interactive demos (each contained to its own stage) ─────────────────── */

function ModalDemo() {
  const [size, setSize] = useState<null | "sm" | "md" | "lg">(null);
  const ref = useOverlay(size !== null, () => setSize(null));
  return (
    <div className="ov-stage">
      <span className="ov-stage-note">scrim contained to this box</span>
      <div className="ov-row">
        {(["sm", "md", "lg"] as const).map((s) => (
          <button key={s} className="demo-btn demo-btn--secondary" type="button" onClick={() => setSize(s)}>
            Open {s}
          </button>
        ))}
      </div>
      {size !== null && (
        <>
          <div className="ov-scrim" onClick={() => setSize(null)} />
          <div
            ref={ref}
            className={`ov-modal ov-modal--${size}`}
            role="dialog"
            aria-modal="true"
            aria-labelledby={`ov-modal-${size}-title`}
            tabIndex={-1}
          >
            <ModalSurface size={size} onClose={() => setSize(null)} />
          </div>
        </>
      )}
    </div>
  );
}

function DrawerDemo() {
  const [edge, setEdge] = useState<null | "right" | "left">(null);
  const ref = useOverlay(edge !== null, () => setEdge(null));
  return (
    <div className="ov-stage">
      <span className="ov-stage-note">edge sheet · contained</span>
      <div className="ov-row">
        <button className="demo-btn demo-btn--secondary" type="button" onClick={() => setEdge("right")}>
          Open right
        </button>
        <button className="demo-btn demo-btn--secondary" type="button" onClick={() => setEdge("left")}>
          Open left
        </button>
      </div>
      {edge !== null && (
        <>
          <div className="ov-scrim" onClick={() => setEdge(null)} />
          <div
            ref={ref}
            className={`ov-drawer ov-drawer--${edge}`}
            role="dialog"
            aria-modal="true"
            aria-label="Decision inspector"
            tabIndex={-1}
          >
            <DrawerBody onClose={() => setEdge(null)} />
          </div>
        </>
      )}
    </div>
  );
}

function PopoverDemo() {
  const [open, setOpen] = useState(false);
  return (
    <div className="ov-stage">
      <span className="ov-stage-note">anchored · arrow · Esc</span>
      <div style={{ position: "relative" }}>
        <button
          className="demo-btn demo-btn--secondary"
          type="button"
          aria-haspopup="dialog"
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
          onKeyDown={(e) => e.key === "Escape" && setOpen(false)}
        >
          Filters
        </button>
        {open && (
          <>
            <div className="ov-catch" onClick={() => setOpen(false)} />
            <div
              className="ov-popover"
              role="dialog"
              aria-label="Filters"
              style={{ top: "calc(100% + var(--ov-offset))", left: 0, zIndex: "var(--z-popover)" }}
            >
              <span className="ov-arrow ov-arrow--top" aria-hidden="true" />
              <h5>Quick filters</h5>
              <p>Scope the decision log to approved runs from the last 30 days.</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function MenuDemo() {
  const [open, setOpen] = useState(false);
  return (
    <div className="ov-stage">
      <span className="ov-stage-note">menu · arrow keys · ⌫ destructive</span>
      <div style={{ position: "relative" }}>
        <button
          className="demo-btn demo-btn--secondary"
          type="button"
          aria-haspopup="menu"
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
          onKeyDown={(e) => e.key === "Escape" && setOpen(false)}
        >
          Actions
        </button>
        {open && (
          <>
            <div className="ov-catch" onClick={() => setOpen(false)} />
            <div style={{ position: "absolute", top: "calc(100% + var(--ov-offset))", left: 0 }}>
              <MenuItems onClose={() => setOpen(false)} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function CommandDemo() {
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const ref = useOverlay(open, () => setOpen(false));
  // ⌘K / Ctrl+K toggles the palette — the defining global shortcut. preventDefault
  // stops the browser's own ⌘K. Esc closes (via useOverlay).
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  // Command palette opens focused on its input, not the first button.
  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);
  return (
    <div className="ov-stage">
      <span className="ov-stage-note">⌘K shell · input-focused</span>
      <button className="demo-btn demo-btn--secondary ov-trigger" type="button" onClick={() => setOpen(true)}>
        <I name="search" cls="ov-ico--sm" /> Open command dialog
      </button>
      {open && (
        <>
          <div className="ov-scrim" onClick={() => setOpen(false)} />
          <div ref={ref} className="ov-command" role="dialog" aria-modal="true" aria-label="Command palette" tabIndex={-1}>
            <CommandSurface onClose={() => setOpen(false)} inputRef={inputRef} />
          </div>
        </>
      )}
    </div>
  );
}

function ConfirmDemo() {
  const [variant, setVariant] = useState<null | "info" | "danger">(null);
  const ref = useOverlay(variant !== null, () => setVariant(null));
  return (
    <div className="ov-stage">
      <span className="ov-stage-note">confirm · destructive variant</span>
      <div className="ov-row">
        <button className="demo-btn demo-btn--secondary" type="button" onClick={() => setVariant("info")}>
          Discard…
        </button>
        <button className="demo-btn demo-btn--danger ov-trigger" type="button" onClick={() => setVariant("danger")}>
          <I name="trash" cls="ov-ico--sm" /> Delete workspace…
        </button>
      </div>
      {variant !== null && (
        <>
          <div className="ov-scrim" onClick={() => setVariant(null)} />
          <div
            ref={ref}
            className="ov-modal ov-modal--sm"
            role="alertdialog"
            aria-modal="true"
            aria-label={variant === "danger" ? "Delete workspace" : "Discard draft run"}
            tabIndex={-1}
          >
            <ConfirmSurface variant={variant} onClose={() => setVariant(null)} />
          </div>
        </>
      )}
    </div>
  );
}

/* ── Gallery ─────────────────────────────────────────────────────────────── */
export function Phase3Overlays() {
  return (
    <>
      <div className="sg-subband">
        <h3>3F · Overlays</h3>
        <span>
          Modals, drawers, popovers, menus, tooltips and command/confirm dialogs —
          stacking from --z-* tokens, scrims contained, Esc + focus-trap everywhere.
        </span>
      </div>

      <Section
        id="ov-modal"
        title="Modal & dialog"
        desc="Three widths (sm/md/lg). Header + body + footer actions over a contained, dimmed scrim. Esc closes, focus is trapped, focus returns to the trigger on close."
      >
        <div className="sg-card">
          <ModalDemo />
          <p className="sg-note" style={{ marginTop: "var(--space-16)" }}>
            Static previews (always open, no scrim):
          </p>
          <div className="ov-static" style={{ marginTop: "var(--space-12)" }}>
            {(["sm", "md", "lg"] as const).map((s) => (
              <div
                key={s}
                className={`ov-modal ov-modal--${s}`}
                role="group"
                aria-label={`Modal ${s} preview`}
                style={{ position: "static" }}
              >
                <ModalSurface size={s} />
              </div>
            ))}
          </div>
        </div>
      </Section>

      <Section
        id="ov-drawer"
        title="Drawer (edge sheet)"
        desc="A right/left inspector that slides from the viewport edge. Same dialog semantics as a modal; used for details that keep the underlying list in view."
      >
        <div className="sg-card">
          <DrawerDemo />
        </div>
      </Section>

      <Section
        id="ov-popover-menu"
        title="Popover & menu"
        desc="Anchored, non-modal surfaces. Popover = free content with an optional arrow; menu = role=menu with arrow-key navigation, separators, shortcuts, a submenu hint and a destructive item."
      >
        <div className="sg-card">
          <div className="ov-static" style={{ marginBottom: "var(--space-16)" }}>
            <PopoverDemo />
            <MenuDemo />
          </div>
          <p className="sg-note">Static menu preview (always open):</p>
          <div style={{ position: "relative", minHeight: "var(--ov-stage-h)", marginTop: "var(--space-12)" }}>
            <div style={{ position: "absolute", top: 0, left: 0 }}>
              <MenuItems />
            </div>
          </div>
        </div>
      </Section>

      <Section
        id="ov-tooltip-hovercard"
        title="Tooltip & hover card"
        desc="Reveal-on-hover surfaces that also open on keyboard focus, after an intent dwell. Tooltip = a terse label (role=tooltip); hover card = a richer preview."
      >
        <div className="sg-card">
          <div className="ov-row" style={{ gap: "var(--space-32)" }}>
            <span className="ov-tip-target">
              <button
                className="demo-btn demo-btn--secondary"
                type="button"
                aria-describedby="ov-tip-1"
              >
                Confidence 0.78
              </button>
              <span className="ov-tooltip" role="tooltip" id="ov-tip-1">
                Calibrated across 142 past decisions
              </span>
            </span>

            <span className="ov-hc-target">
              <button className="demo-btn demo-btn--ghost" type="button" aria-describedby="ov-hc-1">
                @strategist
              </button>
              <div className="ov-hovercard" role="dialog" aria-label="Agent preview" id="ov-hc-1">
                <div className="ov-hc-head">
                  <span className="ov-hc-avatar" aria-hidden="true">S</span>
                  <div>
                    <b>Strategist</b>
                    <span>Synthesis · prompt v7</span>
                  </div>
                </div>
                <p>Weighs the five analyst reports plus recalled lessons into a single recommendation.</p>
                <div className="ov-hc-stats">
                  <div className="ov-hc-stat"><b>0.81</b><span>avg confidence</span></div>
                  <div className="ov-hc-stat"><b>1 retry</b><span>judge loop</span></div>
                </div>
              </div>
            </span>
          </div>
          <p className="sg-note" style={{ marginTop: "var(--space-12)" }}>
            Hover or Tab to either trigger. Both open after a dwell and never trap focus.
          </p>
        </div>
      </Section>

      <Section
        id="ov-command"
        title="Command dialog (⌘K)"
        desc="A centered command surface over a scrim. Opens focused on the search input; grouped commands with shortcuts; Esc closes. The dialog shell of the Command Palette."
      >
        <div className="sg-card">
          <CommandDemo />
          <p className="sg-note" style={{ marginTop: "var(--space-16)" }}>Static preview:</p>
          <div style={{ position: "relative", marginTop: "var(--space-12)" }}>
            <div
              className="ov-command"
              role="group"
              aria-label="Command palette preview"
              style={{ position: "static", width: "100%" }}
            >
              <CommandSurface />
            </div>
          </div>
        </div>
      </Section>

      <Section
        id="ov-confirm"
        title="Confirmation dialog"
        desc="role=alertdialog. The destructive variant pairs danger color with a warning glyph, an explicit consequence block and a 'Delete workspace' confirm label — color is never the only channel (1.4.1)."
      >
        <div className="sg-card">
          <ConfirmDemo />
          <p className="sg-note" style={{ marginTop: "var(--space-16)" }}>Static previews:</p>
          <div className="ov-static" style={{ marginTop: "var(--space-12)" }}>
            {(["info", "danger"] as const).map((v) => (
              <div
                key={v}
                className="ov-modal ov-modal--sm"
                role="group"
                aria-label={`${v} confirm preview`}
                style={{ position: "static" }}
              >
                <ConfirmSurface variant={v} />
              </div>
            ))}
          </div>
        </div>
      </Section>
    </>
  );
}
