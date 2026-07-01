// Phase 10B — Direct-manipulation & editing patterns gallery.
// Inline editing, keyboard-first interactions, drag-and-drop, selection, bulk
// actions, and undo/redo. Every demo is a real, working example (state +
// keyboard handling), not a static mock. Drag-and-drop and selection each ship
// a non-mouse path: explicit move-up/move-down buttons alongside the drag
// handle, and Tab+Space-operable checkboxes alongside shift/ctrl-click.
import { useEffect, useId, useRef, useState } from "react";
import type { Density } from "../sg";
import { Section, Specimen } from "../sg";
import "./phase10b-editing-patterns.css";

/* ── Inline Phosphor-style icons (SVG only; sized via CSS class) ─────────── */
type IconName = "pencil" | "check" | "x" | "grip" | "chevron-up" | "chevron-down" | "archive" | "trash";

const ICONS: Record<IconName, string> = {
  pencil: "M12 20h9 M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z",
  check: "M5 13l4 4L19 7",
  x: "M18 6 6 18 M6 6l12 12",
  grip: "M9 6h.01 M9 12h.01 M9 18h.01 M15 6h.01 M15 12h.01 M15 18h.01",
  "chevron-up": "m18 15-6-6-6 6",
  "chevron-down": "m6 9 6 6 6-6",
  archive: "M3 7h18 M5 7l1.2-3.6A2 2 0 0 1 8.1 2h7.8a2 2 0 0 1 1.9 1.4L19 7 M5 7v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7 M9.5 12h5",
  trash: "M3 6h18 M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2 M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6 M10 11v6 M14 11v6",
};

function Icon({ name, cls }: { name: IconName; cls?: string }) {
  return (
    <svg
      className={cls ? `p10b-ico ${cls}` : "p10b-ico"}
      viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"
    >
      <path d={ICONS[name]} />
    </svg>
  );
}

/* ── Keys: renders a keyboard shortcut as a row of `<kbd>` chips. Mirrors
 * Phase 3B's `Keys`/`.nv-keys`/`.nv-kbd`, kept local per the per-phase
 * self-containment convention every prior phase module follows. */
function Keys({ keys }: { keys: string[] }) {
  return (
    <span className="p10b-keys">
      {keys.map((k, i) => (
        <kbd key={`${k}-${i}`} className="p10b-kbd">{k}</kbd>
      ))}
    </span>
  );
}

/* ── useRowSelection: shared checkbox-selection state for the Selection and
 * Bulk actions demos below — click toggles a row, Shift+click extends a
 * contiguous range from the last-toggled row. Every row remains individually
 * toggleable with Tab+Space alone, so range-select is a shortcut, never the
 * only path. */
function useRowSelection(count: number) {
  const [selected, setSelected] = useState<Set<number>>(() => new Set());
  const lastClicked = useRef<number | null>(null);

  function toggleRow(i: number, shiftKey: boolean) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (shiftKey && lastClicked.current !== null) {
        const lo = Math.min(lastClicked.current, i);
        const hi = Math.max(lastClicked.current, i);
        for (let j = lo; j <= hi; j++) next.add(j);
      } else if (next.has(i)) {
        next.delete(i);
      } else {
        next.add(i);
      }
      return next;
    });
    lastClicked.current = i;
  }

  function toggleAll() {
    setSelected((prev) => (prev.size === count ? new Set() : new Set(Array.from({ length: count }, (_, i) => i))));
  }

  function clear() {
    setSelected(new Set());
    lastClicked.current = null;
  }

  return { selected, toggleRow, toggleAll, clear };
}

function SelectAllCheckbox({ count, selectedCount, onToggle }: { count: number; selectedCount: number; onToggle: () => void }) {
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (ref.current) ref.current.indeterminate = selectedCount > 0 && selectedCount < count;
  }, [selectedCount, count]);
  return (
    <input
      ref={ref}
      type="checkbox"
      checked={count > 0 && selectedCount === count}
      onChange={onToggle}
      aria-label="Select all rows"
    />
  );
}

/* ════════════════════════════════════════════════ 1. INLINE EDITING ══════ */

function InlineEditField({ label, initial, variant }: { label: string; initial: string; variant?: "title" }) {
  const [value, setValue] = useState(initial);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(initial);
  const [saved, setSaved] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const savedTimer = useRef<number | undefined>(undefined);

  function startEdit() {
    setDraft(value);
    setEditing(true);
    setSaved(false);
  }
  function commit() {
    setEditing(false);
    setValue((v) => {
      const next = draft.trim() || v;
      return next;
    });
    setSaved(true);
    window.clearTimeout(savedTimer.current);
    savedTimer.current = window.setTimeout(() => setSaved(false), 2000);
  }
  function cancel() {
    setEditing(false);
  }
  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);
  useEffect(() => () => window.clearTimeout(savedTimer.current), []);

  if (editing) {
    return (
      <span className="p10b-inline-edit">
        <input
          ref={inputRef}
          className="p10b-inline-input"
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") commit();
            else if (e.key === "Escape") cancel();
          }}
          onBlur={commit}
          aria-label={label}
        />
        <span className="p10b-inline-actions">
          {/* mousedown preventDefault keeps focus on the input so onBlur doesn't
           * fire (and commit) before the click handler below runs. */}
          <button type="button" className="p10b-icon-btn" title="Save (Enter)" onMouseDown={(e) => e.preventDefault()} onClick={commit}>
            <Icon name="check" cls="p10b-ico--sm" />
          </button>
          <button type="button" className="p10b-icon-btn" title="Cancel (Esc)" onMouseDown={(e) => e.preventDefault()} onClick={cancel}>
            <Icon name="x" cls="p10b-ico--sm" />
          </button>
        </span>
      </span>
    );
  }

  return (
    <span className="p10b-inline-display">
      <button
        type="button"
        className={variant === "title" ? "p10b-inline-trigger p10b-inline-trigger--title" : "p10b-inline-trigger"}
        onClick={startEdit}
      >
        <span>{value}</span>
        <Icon name="pencil" cls="p10b-ico--sm p10b-inline-pencil" />
      </button>
      {saved && (
        <span className="p10b-inline-ack" role="status">
          <Icon name="check" cls="p10b-ico--sm" /> Saved
        </span>
      )}
    </span>
  );
}

function InlineTitleDemo() {
  return (
    <div className="p10b-stage">
      <span className="p10b-status">Click the title, or Tab to it and press Enter, to rename in place.</span>
      <InlineEditField label="Initiative name" initial="Q3 pricing experiment" variant="title" />
    </div>
  );
}

const ROADMAP = [
  { feature: "Inline editing", owner: "Priya" },
  { feature: "Bulk actions", owner: "Sam" },
  { feature: "Undo toast", owner: "Unassigned" },
];

function InlineTableDemo() {
  return (
    <div className="p10b-stage" style={{ alignItems: "stretch" }}>
      <span className="p10b-status">Click an Owner cell to reassign without leaving the table.</span>
      <table className="p10b-table">
        <thead>
          <tr><th>Feature</th><th>Owner</th></tr>
        </thead>
        <tbody>
          {ROADMAP.map((r) => (
            <tr key={r.feature} className="p10b-table__row">
              <td>{r.feature}</td>
              <td><InlineEditField label={`Owner for ${r.feature}`} initial={r.owner} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ═══════════════════════════════════════ 2. KEYBOARD-FIRST INTERACTIONS ══ */

function KeyboardConventionsDemo() {
  return (
    <dl className="p10b-conventions">
      <div className="p10b-conventions__row">
        <dt>Focus order</dt>
        <dd>Follows reading order — top→bottom, left→right — and DOM order; never reordered visually with CSS alone (e.g. <code>order</code> or grid placement) without also reordering the markup.</dd>
      </div>
      <div className="p10b-conventions__row">
        <dt><Keys keys={["⌘", "K"]} /> Command palette</dt>
        <dd>The system's primary keyboard entry point — opens the global command palette from anywhere. Already built: see Navigation's <code>.nv-palette</code> (the embedded omnibox) and Overlays' <code>.ov-command</code> (the modal launched by this shortcut). Referenced here, not rebuilt.</dd>
      </div>
      <div className="p10b-conventions__row">
        <dt>Arrow keys</dt>
        <dd>Inside a composite widget (menu, listbox, toolbar) arrow keys move a single roving tab stop — Tab itself only enters or exits the widget once, never steps through its items one at a time. Demoed below.</dd>
      </div>
      <div className="p10b-conventions__row">
        <dt>Focus rings</dt>
        <dd>Every interactive element in this design system shows a visible <code>:focus-visible</code> ring on keyboard focus (never on mouse click) — Tab through any control on this page to see it; none rely on color alone.</dd>
      </div>
    </dl>
  );
}

const MENU_ITEMS = ["New decision", "New connector", "Open settings", "Sign out"];

function ArrowMenuDemo() {
  const [active, setActive] = useState(0);
  const [ran, setRan] = useState<string | null>(null);
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([]);

  // Moves both the roving tab stop and DOM focus together. Elements with
  // tabIndex={-1} are still focusable via .focus() even though Tab skips
  // them, so this works without waiting for the tabIndex prop to re-render.
  // (Deliberately not a useEffect on `active` — that would also fire on
  // mount and steal focus into the menu before the user touches it.)
  function moveTo(i: number) {
    setActive(i);
    itemRefs.current[i]?.focus();
  }
  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") { e.preventDefault(); moveTo((active + 1) % MENU_ITEMS.length); }
    else if (e.key === "ArrowUp") { e.preventDefault(); moveTo((active - 1 + MENU_ITEMS.length) % MENU_ITEMS.length); }
    else if (e.key === "Home") { e.preventDefault(); moveTo(0); }
    else if (e.key === "End") { e.preventDefault(); moveTo(MENU_ITEMS.length - 1); }
  }

  return (
    <div className="p10b-stage">
      <ul className="p10b-menu" role="menu" aria-label="Quick actions" onKeyDown={onKeyDown}>
        {MENU_ITEMS.map((label, i) => (
          <li key={label} role="none">
            <button
              ref={(el) => { itemRefs.current[i] = el; }}
              type="button"
              role="menuitem"
              className="p10b-menu__item"
              tabIndex={i === active ? 0 : -1}
              onFocus={() => setActive(i)}
              onClick={() => setRan(label)}
            >
              {label}
            </button>
          </li>
        ))}
      </ul>
      <p className="p10b-status" role="status">
        {ran ? `Ran: ${ran}` : (<><Keys keys={["↑", "↓"]} /> move · <Keys keys={["Home", "End"]} /> jump · <Keys keys={["↵"]} /> activate</>)}
      </p>
    </div>
  );
}

/* ════════════════════════════════════════════════════ 3. DRAG-AND-DROP ═══ */

function ReorderListDemo() {
  const [items, setItems] = useState(["Decision throughput", "Connector health", "Open risks", "Recent feedback"]);
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [announce, setAnnounce] = useState("");

  function move(index: number, delta: number) {
    const target = index + delta;
    if (target < 0 || target >= items.length) return;
    setItems((prev) => {
      const next = [...prev];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
    setAnnounce(`Moved “${items[index]}” to position ${target + 1} of ${items.length}.`);
  }

  function onDrop(targetIndex: number) {
    if (dragIndex === null || dragIndex === targetIndex) { setDragIndex(null); return; }
    const movedLabel = items[dragIndex];
    setItems((prev) => {
      const next = [...prev];
      const [moved] = next.splice(dragIndex, 1);
      next.splice(targetIndex, 0, moved);
      return next;
    });
    setAnnounce(`Moved “${movedLabel}” to position ${targetIndex + 1} of ${items.length}.`);
    setDragIndex(null);
  }

  return (
    <div className="p10b-stage" style={{ alignItems: "stretch" }}>
      <span className="p10b-status">Drag the handle, or use the move buttons — both reorder the same list.</span>
      <ul className="p10b-reorder">
        {items.map((item, i) => (
          <li
            key={item}
            className={dragIndex === i ? "p10b-reorder__item is-dragging" : "p10b-reorder__item"}
            draggable
            onDragStart={() => setDragIndex(i)}
            onDragOver={(e) => e.preventDefault()}
            onDrop={() => onDrop(i)}
            onDragEnd={() => setDragIndex(null)}
            aria-grabbed={dragIndex === i}
          >
            <span className="p10b-reorder__handle" aria-hidden="true"><Icon name="grip" cls="p10b-ico--sm" /></span>
            <span className="p10b-reorder__label">{item}</span>
            <span className="p10b-reorder__controls">
              <button type="button" className="p10b-icon-btn" disabled={i === 0} onClick={() => move(i, -1)} aria-label={`Move ${item} up`}>
                <Icon name="chevron-up" cls="p10b-ico--sm" />
              </button>
              <button type="button" className="p10b-icon-btn" disabled={i === items.length - 1} onClick={() => move(i, 1)} aria-label={`Move ${item} down`}>
                <Icon name="chevron-down" cls="p10b-ico--sm" />
              </button>
            </span>
          </li>
        ))}
      </ul>
      <p className="p10b-sr-only" role="status" aria-live="polite">{announce}</p>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════ 4. SELECTION ════ */

const DECISIONS = [
  { id: 1, name: "Q3 pricing experiment", status: "Approved" },
  { id: 2, name: "Sunset legacy connector", status: "In review" },
  { id: 3, name: "Raise judge threshold", status: "Approved" },
  { id: 4, name: "Add Linear connector", status: "Draft" },
];

function SelectionListDemo() {
  const { selected, toggleRow, toggleAll, clear } = useRowSelection(DECISIONS.length);
  return (
    <div className="p10b-stage" style={{ alignItems: "stretch" }}>
      <div className="p10b-row" style={{ justifyContent: "space-between" }}>
        <span className="p10b-status" role="status">
          {selected.size > 0 ? `${selected.size} of ${DECISIONS.length} selected` : "Click a checkbox; Shift+click extends a range from the last one you clicked."}
        </span>
        {selected.size > 0 && <button type="button" className="p10b-btn p10b-btn--ghost" onClick={clear}>Clear selection</button>}
      </div>
      <table className="p10b-table">
        <thead>
          <tr>
            <th className="p10b-table__check"><SelectAllCheckbox count={DECISIONS.length} selectedCount={selected.size} onToggle={toggleAll} /></th>
            <th>Initiative</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {DECISIONS.map((d, i) => (
            <tr key={d.id} aria-selected={selected.has(i)} className={selected.has(i) ? "p10b-table__row is-selected" : "p10b-table__row"}>
              <td className="p10b-table__check">
                <input
                  type="checkbox"
                  checked={selected.has(i)}
                  onClick={(e) => { e.preventDefault(); toggleRow(i, e.shiftKey); }}
                  onChange={() => {}}
                  aria-label={`Select ${d.name}`}
                />
              </td>
              <td>{d.name}</td>
              <td>{d.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ═══════════════════════════════════════════════════ 5. BULK ACTIONS ═════ */

const FEEDBACK = [
  { id: 1, subject: "Export button is hard to find", tag: "UX" },
  { id: 2, subject: "API rate limit too low", tag: "API" },
  { id: 3, subject: "Connector sync fails silently", tag: "Bug" },
  { id: 4, subject: "Add dark mode", tag: "Feature" },
  { id: 5, subject: "Slow dashboard load", tag: "Performance" },
];

function BulkActionsDemo() {
  const { selected, toggleRow, toggleAll, clear } = useRowSelection(FEEDBACK.length);
  const [status, setStatus] = useState<string | null>(null);

  // ponytail: the demo doesn't actually remove/archive rows — the toolbar
  // mechanics (count, actions, clear) are the point, not a real feedback
  // backend. Real archive/delete should pair with the Undo/redo toast below.
  function applyBulk(action: string) {
    setStatus(`${action} ${selected.size} item${selected.size === 1 ? "" : "s"}.`);
    clear();
  }

  return (
    <div className="p10b-stage" style={{ alignItems: "stretch" }}>
      {selected.size > 0 ? (
        <div className="p10b-bulk-bar" role="toolbar" aria-label="Bulk actions">
          <span className="p10b-bulk-bar__count">{selected.size} selected</span>
          <span className="p10b-row">
            <button type="button" className="p10b-btn p10b-btn--secondary" onClick={() => applyBulk("Archived")}>
              <Icon name="archive" cls="p10b-ico--sm" /> Archive
            </button>
            <button type="button" className="p10b-btn p10b-btn--danger" onClick={() => applyBulk("Deleted")}>
              <Icon name="trash" cls="p10b-ico--sm" /> Delete
            </button>
          </span>
          <button type="button" className="p10b-btn p10b-btn--ghost p10b-bulk-bar__clear" onClick={clear}>Clear</button>
        </div>
      ) : (
        <span className="p10b-status" role="status">{status ?? "Select one or more feedback items to act on them in bulk."}</span>
      )}
      <table className="p10b-table">
        <thead>
          <tr>
            <th className="p10b-table__check"><SelectAllCheckbox count={FEEDBACK.length} selectedCount={selected.size} onToggle={toggleAll} /></th>
            <th>Feedback</th>
            <th>Tag</th>
          </tr>
        </thead>
        <tbody>
          {FEEDBACK.map((f, i) => (
            <tr key={f.id} aria-selected={selected.has(i)} className={selected.has(i) ? "p10b-table__row is-selected" : "p10b-table__row"}>
              <td className="p10b-table__check">
                <input
                  type="checkbox"
                  checked={selected.has(i)}
                  onClick={(e) => { e.preventDefault(); toggleRow(i, e.shiftKey); }}
                  onChange={() => {}}
                  aria-label={`Select ${f.subject}`}
                />
              </td>
              <td>{f.subject}</td>
              <td>{f.tag}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════ 6. UNDO/REDO ════ */

const CONNECTORS = ["GitHub", "Jira", "Linear"];

function UndoToastDemo() {
  const [items, setItems] = useState(CONNECTORS);
  const [pending, setPending] = useState<{ name: string; index: number } | null>(null);
  const timer = useRef<number | undefined>(undefined);
  const titleId = useId();

  function remove(name: string) {
    const index = items.indexOf(name);
    setItems((prev) => prev.filter((n) => n !== name));
    setPending({ name, index });
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setPending(null), 6000);
  }

  function undo() {
    setPending((current) => {
      if (!current) return current;
      setItems((prev) => {
        const next = [...prev];
        next.splice(current.index, 0, current.name);
        return next;
      });
      window.clearTimeout(timer.current);
      return null;
    });
  }

  useEffect(() => {
    if (!pending) return;
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "z") {
        e.preventDefault();
        undo();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
    // undo only reads/writes via the functional setPending updater above, so
    // it doesn't need to be in deps for this to stay correct.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pending]);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  return (
    <div className="p10b-stage" style={{ alignItems: "stretch" }}>
      <span className="p10b-status">
        Removing a connector is reversible — no confirmation dialog (cross-ref Phase 10A's Confirmation
        flows: tier 2, consequential-but-reversible gets an inline undo, not a blocking gate).
      </span>
      <ul className="p10b-connector-list">
        {items.length === 0 && <li className="p10b-status">No connectors configured.</li>}
        {items.map((name) => (
          <li key={name} className="p10b-connector-row">
            <span>{name}</span>
            <button type="button" className="p10b-icon-btn" onClick={() => remove(name)} aria-label={`Remove ${name}`}>
              <Icon name="x" cls="p10b-ico--sm" />
            </button>
          </li>
        ))}
      </ul>
      {pending && (
        <div className="p10b-toast" role="status" aria-live="polite" aria-labelledby={titleId}>
          <span className="p10b-toast__icon"><Icon name="check" cls="p10b-ico--sm" /></span>
          <span className="p10b-toast__text" id={titleId}>Removed &ldquo;{pending.name}&rdquo;.</span>
          <button type="button" className="p10b-toast__action" onClick={undo}>
            Undo <Keys keys={["⌘", "Z"]} />
          </button>
          <span className="p10b-toast__timer" key={pending.name} />
        </div>
      )}
    </div>
  );
}

/* ── Gallery ─────────────────────────────────────────────────────────────── */
export function Phase10BEditingPatterns({ density }: { density: Density }) {
  void density;
  return (
    <>
      <Section
        id="p10b-inline-editing"
        title="Inline editing"
        desc="Edit a value where it lives — a title or a table cell — instead of navigating to a separate form."
      >
        <Specimen label="inline title"><InlineTitleDemo /></Specimen>
        <Specimen label="table cell"><InlineTableDemo /></Specimen>
      </Section>

      <Section
        id="p10b-keyboard-first"
        title="Keyboard-first interactions"
        desc="The system's keyboard conventions in one place — focus order, the command palette, composite-widget arrow keys, and focus rings."
      >
        <Specimen label="conventions"><KeyboardConventionsDemo /></Specimen>
        <Specimen label="arrow-key menu"><ArrowMenuDemo /></Specimen>
      </Section>

      <Section
        id="p10b-drag-drop"
        title="Drag-and-drop"
        desc="Reorder a list by dragging — but dragging is never the only way; explicit move buttons do the same thing."
      >
        <Specimen label="reorder widgets"><ReorderListDemo /></Specimen>
      </Section>

      <Section
        id="p10b-selection"
        title="Selection"
        desc="Single and multi-select via a checkbox column — click toggles, Shift+click extends a range, every row stays keyboard-toggleable."
      >
        <Specimen label="decisions list"><SelectionListDemo /></Specimen>
      </Section>

      <Section
        id="p10b-bulk-actions"
        title="Bulk actions"
        desc="Once 1+ rows are selected, a toolbar appears with actions that apply to the whole selection, a count, and a way to clear it."
      >
        <Specimen label="feedback inbox"><BulkActionsDemo /></Specimen>
      </Section>

      <Section
        id="p10b-undo-redo"
        title="Undo/redo"
        desc="The inline 'Undone — Undo' toast: act immediately on a reversible destructive-ish action, then offer a way back."
      >
        <Specimen label="remove connector"><UndoToastDemo /></Specimen>
      </Section>
    </>
  );
}
