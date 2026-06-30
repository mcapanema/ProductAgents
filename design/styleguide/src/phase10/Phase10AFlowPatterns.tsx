// Phase 10A — Flow & risk patterns gallery.
// Five patterns for consequential, destructive, long-running, sequential and
// progressively-disclosed interactions. Confirmation/destructive dialogs are
// rendered INSIDE a contained `.p10a-stage` (position:relative, overflow:clip)
// so the scrim covers only the preview box, never the page — same convention
// Phase 3F established for overlays. Each demo is a real, working example
// (state + keyboard handling), not a static mock.
import { useEffect, useId, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import type { Density } from "../sg";
import { Section, Specimen } from "../sg";
import "./phase10a-flow-patterns.css";

/* ── Inline Phosphor-style icons (SVG only; sized via CSS class) ─────────── */
type IconName =
  | "warning" | "trash" | "check" | "info" | "lock"
  | "chevron-down" | "chevron-left" | "chevron-right" | "git-branch" | "ticket";

const ICONS: Record<IconName, string> = {
  warning: "M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z M12 9v4 M12 17h.01",
  trash: "M3 6h18 M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2 M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6 M10 11v6 M14 11v6",
  check: "M5 13l4 4L19 7",
  info: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z M12 16v-4 M12 8h.01",
  lock: "M6 10V7a6 6 0 1 1 12 0v3 M5 10h14v10H5z",
  "chevron-down": "m6 9 6 6 6-6",
  "chevron-left": "m15 18-6-6 6-6",
  "chevron-right": "m9 18 6-6-6-6",
  "git-branch": "M6 3v12 M6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z M6 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z M18 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z M18 9v2a4 4 0 0 1-4 4H6",
  ticket: "M3 9a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v2a2 2 0 0 0 0 4v2a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-2a2 2 0 0 0 0-4V9z M9 7v10",
};

function Icon({ name, cls }: { name: IconName; cls?: string }) {
  return (
    <svg
      className={cls ? `p10a-ico ${cls}` : "p10a-ico"}
      viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"
    >
      <path d={ICONS[name]} />
    </svg>
  );
}

/* ── useOverlay: Esc-to-close + initial focus + Tab focus-trap + focus restore.
 * Mirrors Phase 3F's hook of the same name; kept local per the per-phase
 * self-containment convention every prior phase module follows. */
function useOverlay(active: boolean, onClose: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!active) return;
    const panel = ref.current;
    const restore = document.activeElement as HTMLElement | null;
    const focusables = () =>
      panel
        ? Array.from(panel.querySelectorAll<HTMLElement>('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'))
        : [];
    focusables()[0]?.focus();

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onCloseRef.current();
        return;
      }
      if (e.key !== "Tab") return;
      const items = focusables();
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      restore?.focus();
    };
  }, [active]);

  return ref;
}

/* ════════════════════════════════════════════ 1. CONFIRMATION FLOWS ═══════ */

function DecisionTree() {
  return (
    <ol className="p10a-tree">
      <li className="p10a-tree__row">
        <span className="p10a-tree__badge p10a-tree__badge--skip" aria-hidden="true">1</span>
        <div className="p10a-tree__copy">
          <span className="p10a-tree__cause">Trivial &amp; reversible — e.g. toggling a column, collapsing a panel</span>
          <span className="p10a-tree__effect">Skip confirmation entirely. The action just happens.</span>
        </div>
      </li>
      <li className="p10a-tree__row">
        <span className="p10a-tree__badge p10a-tree__badge--undo" aria-hidden="true">2</span>
        <div className="p10a-tree__copy">
          <span className="p10a-tree__cause">Consequential but reversible — e.g. archiving a project, removing a row</span>
          <span className="p10a-tree__effect">No dialog. Act immediately, then offer an inline undo (see Undo/redo).</span>
        </div>
      </li>
      <li className="p10a-tree__row">
        <span className="p10a-tree__badge p10a-tree__badge--block" aria-hidden="true">3</span>
        <div className="p10a-tree__copy">
          <span className="p10a-tree__cause">Irreversible or high blast radius — e.g. deleting a workspace, submitting a governance decision</span>
          <span className="p10a-tree__effect">Block with a confirmation dialog before acting.</span>
        </div>
      </li>
    </ol>
  );
}

function ConfirmFlowDemo() {
  const [open, setOpen] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const ref = useOverlay(open, () => setOpen(false));
  const titleId = useId();

  return (
    <div className="p10a-stage">
      <span className="p10a-status">Tier 3 — irreversible, blocking confirmation.</span>
      <button type="button" className="p10a-btn p10a-btn--primary" onClick={() => { setOpen(true); setSubmitted(false); }}>
        Submit governance decision…
      </button>
      {submitted && <span className="p10a-status" data-tone="success" role="status">Decision submitted.</span>}
      {open && (
        <>
          <div className="p10a-scrim" onClick={() => setOpen(false)} />
          <div ref={ref} className="p10a-modal" role="alertdialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1}>
            <div className="p10a-head">
              <span className="p10a-medallion p10a-medallion--info" aria-hidden="true">
                <Icon name="info" />
              </span>
              <div className="p10a-titles">
                <h4 id={titleId}>Submit this decision?</h4>
                <p>Once submitted, the recommendation moves to governance review and can no longer be edited.</p>
              </div>
            </div>
            <div className="p10a-foot">
              <button type="button" className="p10a-btn p10a-btn--ghost" onClick={() => setOpen(false)}>Cancel</button>
              <button type="button" className="p10a-btn p10a-btn--primary" onClick={() => { setOpen(false); setSubmitted(true); }}>
                Submit decision
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

/* ════════════════════════════════════════════ 2. DESTRUCTIVE ACTIONS ══════ */

function DeleteProjectDemo() {
  const [open, setOpen] = useState(false);
  const [typed, setTyped] = useState("");
  const [deleted, setDeleted] = useState(false);
  const ref = useOverlay(open, () => setOpen(false));
  const titleId = useId();
  const resourceName = "atlas-pricing";
  const matched = typed.trim() === resourceName;

  return (
    <div className="p10a-stage">
      <span className="p10a-status">Most catastrophic — require typing the resource name.</span>
      <button
        type="button"
        className="p10a-btn p10a-btn--danger"
        onClick={() => { setOpen(true); setTyped(""); setDeleted(false); }}
      >
        <Icon name="trash" cls="p10a-ico--sm" /> Delete project…
      </button>
      {deleted && <span className="p10a-status" role="status">Project deleted.</span>}
      {open && (
        <>
          <div className="p10a-scrim" onClick={() => setOpen(false)} />
          <div ref={ref} className="p10a-modal" role="alertdialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1}>
            <div className="p10a-head">
              <span className="p10a-medallion p10a-medallion--danger" aria-hidden="true">
                <Icon name="warning" />
              </span>
              <div className="p10a-titles">
                <h4 id={titleId}>Delete &ldquo;{resourceName}&rdquo;?</h4>
                <p>This removes its connectors, evidence and decision history.</p>
                <div className="p10a-consequence" role="note">
                  <Icon name="warning" cls="p10a-ico--sm" />
                  <span>This permanently deletes 12 decisions and 3 connectors. This cannot be undone.</span>
                </div>
              </div>
            </div>
            <div className="p10a-body">
              <div className="p10a-field">
                <label className="p10a-label" htmlFor={`${titleId}-confirm`}>
                  Type <strong>{resourceName}</strong> to confirm
                </label>
                <input
                  id={`${titleId}-confirm`}
                  className="p10a-input"
                  type="text"
                  autoComplete="off"
                  value={typed}
                  onChange={(e) => setTyped(e.target.value)}
                  placeholder={resourceName}
                />
              </div>
            </div>
            <div className="p10a-foot">
              {/* Cancel is first in DOM order, so it — not the destructive
               * action — receives initial focus when the dialog opens. */}
              <button type="button" className="p10a-btn p10a-btn--ghost" onClick={() => setOpen(false)}>Cancel</button>
              <button
                type="button"
                className="p10a-btn p10a-btn--danger"
                disabled={!matched}
                onClick={() => { setOpen(false); setDeleted(true); }}
              >
                Delete project
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function RevokeKeyDemo() {
  const [open, setOpen] = useState(false);
  const [ack, setAck] = useState(false);
  const [revoked, setRevoked] = useState(false);
  const ref = useOverlay(open, () => setOpen(false));
  const titleId = useId();

  return (
    <div className="p10a-stage">
      <span className="p10a-status">Moderately catastrophic — require an explicit acknowledgement.</span>
      <button
        type="button"
        className="p10a-btn p10a-btn--danger"
        onClick={() => { setOpen(true); setAck(false); setRevoked(false); }}
      >
        <Icon name="lock" cls="p10a-ico--sm" /> Revoke API key…
      </button>
      {revoked && <span className="p10a-status" role="status">Key revoked.</span>}
      {open && (
        <>
          <div className="p10a-scrim" onClick={() => setOpen(false)} />
          <div ref={ref} className="p10a-modal" role="alertdialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1}>
            <div className="p10a-head">
              <span className="p10a-medallion p10a-medallion--danger" aria-hidden="true">
                <Icon name="warning" />
              </span>
              <div className="p10a-titles">
                <h4 id={titleId}>Revoke this API key?</h4>
                <p>Any integration using this key will stop working immediately.</p>
              </div>
            </div>
            <div className="p10a-body">
              <label className="p10a-check-row">
                <input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} />
                I understand this cannot be undone.
              </label>
            </div>
            <div className="p10a-foot">
              <button type="button" className="p10a-btn p10a-btn--ghost" onClick={() => setOpen(false)}>Cancel</button>
              <button
                type="button"
                className="p10a-btn p10a-btn--danger"
                disabled={!ack}
                onClick={() => { setOpen(false); setRevoked(true); }}
              >
                Revoke key
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

/* ════════════════════════════════════════ 3. LONG-RUNNING OPERATIONS ══════ */

function Spinner() {
  return (
    <svg className="p10a-spinner" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <circle className="p10a-spinner__track" cx={12} cy={12} r={10} />
      <circle className="p10a-spinner__arc" cx={12} cy={12} r={10} pathLength={100} />
    </svg>
  );
}

function DeterminateRunDemo() {
  const [pct, setPct] = useState<number | null>(null);
  const timer = useRef<number | undefined>(undefined);

  const start = () => {
    setPct(0);
    window.clearInterval(timer.current);
    timer.current = window.setInterval(() => {
      setPct((p) => {
        if (p === null) return p;
        const next = p + 10;
        if (next >= 100) {
          window.clearInterval(timer.current);
          return 100;
        }
        return next;
      });
    }, 250);
  };

  const cancel = () => {
    window.clearInterval(timer.current);
    setPct(null);
  };

  useEffect(() => () => window.clearInterval(timer.current), []);

  const running = pct !== null && pct < 100;
  const done = pct === 100;

  return (
    <div className="p10a-stage">
      <span className="p10a-status">Known total — e.g. syncing N issues from a GitHub connector.</span>
      <div className="p10a-row">
        <button type="button" className="p10a-btn p10a-btn--secondary" disabled={running} onClick={start}>
          {running && <Spinner />} {running ? "Syncing…" : "Sync connector"}
        </button>
        {running && <button type="button" className="p10a-btn p10a-btn--ghost" onClick={cancel}>Cancel</button>}
      </div>
      {pct !== null && (
        <div className="p10a-progress" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label="Connector sync progress">
          <div className="p10a-progress__bar"><div className="p10a-progress__fill" style={{ "--p10a-pct": `${pct}%` } as CSSProperties} /></div>
          <span className="p10a-progress__meta"><span>{done ? "Synced" : "Syncing issues…"}</span><span>{pct}%</span></span>
        </div>
      )}
    </div>
  );
}

function IndeterminateRunDemo() {
  const [running, setRunning] = useState(false);
  const [done, setDone] = useState(false);
  const timer = useRef<number | undefined>(undefined);

  const start = () => {
    setRunning(true);
    setDone(false);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      setRunning(false);
      setDone(true);
    }, 2500);
  };

  const cancel = () => {
    window.clearTimeout(timer.current);
    setRunning(false);
  };

  useEffect(() => () => window.clearTimeout(timer.current), []);

  return (
    <div className="p10a-stage">
      <span className="p10a-status">Unknown duration — e.g. a decision pipeline run (five analysts, debate, judge).</span>
      <div className="p10a-row">
        <button type="button" className="p10a-btn p10a-btn--primary" disabled={running} onClick={start}>
          {running && <Spinner />} {running ? "Running…" : "Run evaluation"}
        </button>
        {running && <button type="button" className="p10a-btn p10a-btn--ghost" onClick={cancel}>Cancel</button>}
      </div>
      {running && <p className="p10a-status" role="status" aria-live="polite">Evaluating evidence — this can take a few minutes.</p>}
      {done && <p className="p10a-status" data-tone="success" role="status">Evaluation complete.</p>}
    </div>
  );
}

/* ═════════════════════════════════════════════ 4. MULTI-STEP WORKFLOWS ════ */

type ConnectorType = "github" | "jira";
const STEP_LABELS = ["Connector type", "Configure", "Review"];

function ConnectorWizardDemo() {
  const [step, setStep] = useState(0);
  const [type, setType] = useState<ConnectorType | null>(null);
  const [repo, setRepo] = useState("");
  const [finished, setFinished] = useState(false);

  const canAdvance = step === 0 ? type !== null : step === 1 ? repo.trim().length > 0 : true;

  const reset = () => { setStep(0); setType(null); setRepo(""); setFinished(false); };

  return (
    <div className="p10a-stage" style={{ alignItems: "stretch" }}>
      <div className="p10a-stepper" aria-label="Add a connector — step progress">
        {STEP_LABELS.map((label, i) => (
          <span key={label} style={{ display: "flex", alignItems: "center", flex: i < STEP_LABELS.length - 1 ? "1 1 auto" : "0 0 auto" }}>
            <span className="p10a-step" data-state={i < step ? "done" : i === step ? "current" : "upcoming"}>
              <span className="p10a-step__dot">{i < step ? <Icon name="check" cls="p10a-ico--sm" /> : i + 1}</span>
              <span className="p10a-step__label">{label}</span>
            </span>
            {i < STEP_LABELS.length - 1 && <span className="p10a-step__line" />}
          </span>
        ))}
      </div>

      {finished ? (
        <div className="p10a-wizard-card">
          <p className="p10a-status" data-tone="success" role="status">Connector added.</p>
          <button type="button" className="p10a-btn p10a-btn--secondary" onClick={reset}>Add another</button>
        </div>
      ) : (
        <div className="p10a-wizard-card">
          {step === 0 && (
            <>
              <h4 className="p10a-wizard-title">Choose a connector type</h4>
              <div className="p10a-type-row">
                <button type="button" className="p10a-type-opt" aria-pressed={type === "github"} onClick={() => setType("github")}>
                  <Icon name="git-branch" cls="p10a-ico--sm" /> GitHub
                </button>
                <button type="button" className="p10a-type-opt" aria-pressed={type === "jira"} onClick={() => setType("jira")}>
                  <Icon name="ticket" cls="p10a-ico--sm" /> Jira
                </button>
              </div>
            </>
          )}
          {step === 1 && (
            <>
              <h4 className="p10a-wizard-title">Configure {type === "jira" ? "Jira" : "GitHub"}</h4>
              <div className="p10a-field">
                <label className="p10a-label" htmlFor="p10a-repo">{type === "jira" ? "Project key" : "Repository"}</label>
                <input
                  id="p10a-repo"
                  className="p10a-input"
                  type="text"
                  value={repo}
                  onChange={(e) => setRepo(e.target.value)}
                  placeholder={type === "jira" ? "PROD" : "org/repo"}
                />
                <span className="p10a-help">Required to continue.</span>
              </div>
            </>
          )}
          {step === 2 && (
            <>
              <h4 className="p10a-wizard-title">Review</h4>
              <dl className="p10a-summary">
                <div><dt>Type</dt><dd>{type === "jira" ? "Jira" : "GitHub"}</dd></div>
                <div><dt>{type === "jira" ? "Project key" : "Repository"}</dt><dd>{repo}</dd></div>
              </dl>
            </>
          )}
          <div className="p10a-wizard-foot">
            <button type="button" className="p10a-btn p10a-btn--ghost" disabled={step === 0} onClick={() => setStep((s) => s - 1)}>
              <Icon name="chevron-left" cls="p10a-ico--sm" /> Back
            </button>
            {step < STEP_LABELS.length - 1 ? (
              <button type="button" className="p10a-btn p10a-btn--primary" disabled={!canAdvance} onClick={() => setStep((s) => s + 1)}>
                Next <Icon name="chevron-right" cls="p10a-ico--sm" />
              </button>
            ) : (
              <button type="button" className="p10a-btn p10a-btn--primary" onClick={() => setFinished(true)}>
                <Icon name="check" cls="p10a-ico--sm" /> Add connector
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════ 5. PROGRESSIVE DISCLOSURE ════ */

function Disclosure({ label, children }: { label: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <div className="p10a-disclosure">
      <button type="button" className="p10a-disclosure__trigger" aria-expanded={open} aria-controls={id} onClick={() => setOpen((v) => !v)}>
        <Icon name="chevron-down" cls="p10a-ico--sm p10a-disclosure__chevron" />
        {label}
      </button>
      {open && <div id={id} className="p10a-disclosure__panel">{children}</div>}
    </div>
  );
}

function AdvancedSettingsDemo() {
  return (
    <div className="p10a-stage" style={{ alignItems: "stretch" }}>
      <div className="p10a-field">
        <label className="p10a-label" htmlFor="p10a-init-name">Initiative name</label>
        <input id="p10a-init-name" className="p10a-input" type="text" defaultValue="Q3 pricing experiment" />
      </div>
      <Disclosure label="Advanced settings">
        <div className="p10a-field">
          <label className="p10a-label" htmlFor="p10a-judge-threshold">Judge threshold</label>
          <input id="p10a-judge-threshold" className="p10a-input" type="text" defaultValue="0.7" />
        </div>
        <div className="p10a-field">
          <label className="p10a-label" htmlFor="p10a-debate-rounds">Debate rounds</label>
          <input id="p10a-debate-rounds" className="p10a-input" type="text" defaultValue="2" />
        </div>
      </Disclosure>
    </div>
  );
}

const FAQ_ITEMS = [
  { q: "Why didn't my run loop back to the strategist?", a: "The judge only retries up to PRODUCTAGENTS_JUDGE_MAX_RETRIES times (default 1); after that it proceeds to risk regardless." },
  { q: "Where do prompt overrides live?", a: "Per-workspace, under <workspace>/prompts/<name>/NNNN.txt — the highest number wins; version 0 is the bundled default." },
];

function FaqAccordionDemo() {
  return (
    <div className="p10a-accordion">
      {FAQ_ITEMS.map((item) => (
        <div key={item.q} className="p10a-accordion__item">
          <Disclosure label={item.q}>
            <p className="p10a-status">{item.a}</p>
          </Disclosure>
        </div>
      ))}
    </div>
  );
}

/* ── Gallery ─────────────────────────────────────────────────────────────── */
export function Phase10AFlowPatterns({ density }: { density: Density }) {
  void density;
  return (
    <>
      <Section
        id="p10a-confirmation"
        title="Confirmation flows"
        desc="Most actions don't need a dialog. Gate only the irreversible, high-blast-radius ones."
      >
        <Specimen label="decision tree"><DecisionTree /></Specimen>
        <Specimen label="blocking confirmation"><ConfirmFlowDemo /></Specimen>
      </Section>

      <Section
        id="p10a-destructive"
        title="Destructive actions"
        desc="Danger color, an explicit cost statement, and a deliberate second step before the data is gone."
      >
        <Specimen label="type to confirm"><DeleteProjectDemo /></Specimen>
        <Specimen label="acknowledge checkbox"><RevokeKeyDemo /></Specimen>
      </Section>

      <Section
        id="p10a-long-running"
        title="Long-running operations"
        desc="Determinate when a total is known, indeterminate otherwise — the trigger stays visible, disabled, with a spinner."
      >
        <Specimen label="determinate (known total)"><DeterminateRunDemo /></Specimen>
        <Specimen label="indeterminate (unknown duration)"><IndeterminateRunDemo /></Specimen>
      </Section>

      <Section
        id="p10a-multi-step"
        title="Multi-step workflows"
        desc="A stepper for naturally sequential input — per-step validation, and state preserved when navigating back."
      >
        <Specimen label="add a connector"><ConnectorWizardDemo /></Specimen>
      </Section>

      <Section
        id="p10a-disclosure"
        title="Progressive disclosure"
        desc="Hide detail most people don't need by default; keep it one click away with a visible expanded state."
      >
        <Specimen label="advanced settings"><AdvancedSettingsDemo /></Specimen>
        <Specimen label="FAQ accordion"><FaqAccordionDemo /></Specimen>
      </Section>
    </>
  );
}
