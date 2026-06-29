// Phase 3C — Forms. The full component gallery: every control, every size,
// every state. Built only from the token layer (see phase3c-forms.css), so it
// flips across [data-theme] + [data-density] with zero markup change. Icons are
// inline Phosphor-style SVG; validation states always pair a hue with an icon
// AND a message (WCAG 1.4.1).
import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { Section, Specimen } from "../sg";

/* ── Inline icon kit (viewBox 24, stroke currentColor, Phosphor-ish) ── */
function Icon({ children, size = "var(--icon-sm)", label }: { children: ReactNode; size?: string; label?: string }) {
  return (
    <svg
      className="fm-ico"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      {children}
    </svg>
  );
}
const IcoSearch = () => <Icon><circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></Icon>;
const IcoX = (p: { size?: string }) => <Icon size={p.size}><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></Icon>;
const IcoEye = () => <Icon><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7Z" /><circle cx="12" cy="12" r="3" /></Icon>;
const IcoEyeOff = () => <Icon><path d="M10.6 6.2A9.7 9.7 0 0 1 12 6c6.4 0 10 6 10 6a17 17 0 0 1-2.4 3" /><path d="M6.3 6.4A17 17 0 0 0 2 12s3.6 7 10 7a9.7 9.7 0 0 0 3.2-.5" /><line x1="3" y1="3" x2="21" y2="21" /></Icon>;
const IcoCaretUp = (p: { size?: string }) => <Icon size={p.size}><polyline points="6 14 12 8 18 14" /></Icon>;
const IcoCaretDown = (p: { size?: string }) => <Icon size={p.size}><polyline points="6 10 12 16 18 10" /></Icon>;
const IcoCaretLeft = () => <Icon><polyline points="14 6 8 12 14 18" /></Icon>;
const IcoCaretRight = () => <Icon><polyline points="10 6 16 12 10 18" /></Icon>;
const IcoCheck = (p: { size?: string }) => <Icon size={p.size}><polyline points="20 6 9 17 4 12" /></Icon>;
const IcoMinus = (p: { size?: string }) => <Icon size={p.size}><line x1="5" y1="12" x2="19" y2="12" /></Icon>;
const IcoCalendar = () => <Icon><rect x="3" y="4" width="18" height="17" rx="2" /><line x1="3" y1="9" x2="21" y2="9" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="16" y1="2" x2="16" y2="6" /></Icon>;
const IcoClock = () => <Icon><circle cx="12" cy="12" r="9" /><polyline points="12 7 12 12 15.5 14" /></Icon>;
const IcoUpload = (p: { size?: string }) => <Icon size={p.size}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 9 12 4 17 9" /><line x1="12" y1="4" x2="12" y2="16" /></Icon>;
const IcoFile = () => <Icon><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z" /><polyline points="14 3 14 8 19 8" /></Icon>;
const IcoErrorCircle = (p: { size?: string }) => <Icon size={p.size}><circle cx="12" cy="12" r="9" /><line x1="12" y1="7.5" x2="12" y2="13" /><line x1="12" y1="16.4" x2="12" y2="16.6" /></Icon>;
const IcoCheckCircle = (p: { size?: string }) => <Icon size={p.size}><circle cx="12" cy="12" r="9" /><polyline points="8 12 11 15 16 9" /></Icon>;
const IcoWarnTriangle = (p: { size?: string }) => <Icon size={p.size}><path d="M12 3.5 2.3 20.5h19.4L12 3.5Z" /><line x1="12" y1="10" x2="12" y2="14" /><line x1="12" y1="16.8" x2="12" y2="17" /></Icon>;
const IcoSparkle = () => <Icon><path d="M12 3v18M3 12h18" /></Icon>;

/* ── Demo option data ── */
const FRAMEWORKS = ["Retention play", "Activation funnel", "Pricing test", "Enterprise SSO", "Churn save flow", "Mobile parity"];
const ANALYSTS = ["Customer research", "Product analytics", "Market", "Business", "Technical"];
const MONTH_DAYS = (() => {
  // Static June-style month: starts Wed (3 leading), 30 days, 1 trailing → 5 rows.
  const cells: { day: number; outside: boolean }[] = [];
  for (let i = 29; i >= 27; i--) cells.push({ day: i, outside: true });
  for (let d = 1; d <= 30; d++) cells.push({ day: d, outside: false });
  cells.push({ day: 1, outside: true }, { day: 2, outside: true });
  return cells;
})();

export function Phase3Forms() {
  // Live controls.
  const [text, setText] = useState("Retention initiative Q3");
  const [search, setSearch] = useState("churn");
  const [reveal, setReveal] = useState(false);
  const [count, setCount] = useState(3);
  const [select, setSelect] = useState("Activation funnel");
  const [comboOpen, setComboOpen] = useState(false);
  const [comboQuery, setComboQuery] = useState("");
  const [comboValue, setComboValue] = useState("");
  const [multiOpen, setMultiOpen] = useState(false);
  const [multi, setMulti] = useState<string[]>(["Customer research", "Market"]);
  const [agree, setAgree] = useState(true);
  const [partial, setPartial] = useState(true);
  const [radio, setRadio] = useState("balanced");
  const [live, setLive] = useState(true);
  const [confidence, setConfidence] = useState(72);
  const [calDay, setCalDay] = useState(18);
  const [dragging, setDragging] = useState(false);

  // Indeterminate is a DOM property, not an attribute — set it via ref.
  const partialRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (partialRef.current) partialRef.current.indeterminate = partial;
  }, [partial]);

  const comboMatches = FRAMEWORKS.filter((f) => f.toLowerCase().includes(comboQuery.toLowerCase()));
  const sliderStyle = { ["--fm-slider-pct"]: `${confidence}%` } as CSSProperties;

  return (
    <>
      <div className="sg-subband">
        <h3>3C · Forms</h3>
        <span>The input vocabulary — buttons, fields, choices, and pickers. Every variant, size, and state, token-only, keyboard-first, both themes + densities.</span>
      </div>

      {/* ───────────────────────────────────────────────── BUTTONS ─── */}
      <Section id="fm-buttons" title="Button" desc="Primary / secondary / ghost / danger across sm·md·lg, plus icon, toggle, link, and loading. One accent CTA per view; danger is the only other filled variant.">
        <div className="sg-card fm-stack">
          <Specimen label="variants · md">
            <button className="fm-btn fm-btn--primary" type="button">Run analysis</button>
            <button className="fm-btn fm-btn--secondary" type="button">Save draft</button>
            <button className="fm-btn fm-btn--ghost" type="button">Cancel</button>
            <button className="fm-btn fm-btn--danger" type="button">Discard run</button>
          </Specimen>
          <Specimen label="sizes (secondary)">
            <button className="fm-btn fm-btn--secondary fm-btn--sm" type="button">Small</button>
            <button className="fm-btn fm-btn--secondary" type="button">Medium</button>
            <button className="fm-btn fm-btn--secondary fm-btn--lg" type="button">Large</button>
          </Specimen>
          <Specimen label="with icon">
            <button className="fm-btn fm-btn--primary" type="button"><IcoSparkle /> New run</button>
            <button className="fm-btn fm-btn--secondary" type="button"><IcoUpload /> Import</button>
          </Specimen>
          <Specimen label="icon button">
            <button className="fm-btn fm-btn--secondary fm-btn--icon fm-btn--sm" type="button" aria-label="Search"><IcoSearch /></button>
            <button className="fm-btn fm-btn--secondary fm-btn--icon" type="button" aria-label="Add filter"><IcoSparkle /></button>
            <button className="fm-btn fm-btn--ghost fm-btn--icon" type="button" aria-label="Calendar"><IcoCalendar /></button>
          </Specimen>
          <Specimen label="toggle button">
            <button className="fm-btn fm-btn--secondary" type="button" aria-pressed={live} onClick={() => setLive((v) => !v)}>
              <IcoClock /> Live updates {live ? "on" : "off"}
            </button>
            <span className="fm-inline-note">aria-pressed latches the state</span>
          </Specimen>
          <Specimen label="link button">
            <button className="fm-btn fm-btn--link" type="button">View full evidence</button>
          </Specimen>
          <Specimen label="loading">
            <button className="fm-btn fm-btn--primary" type="button" data-loading="true" aria-busy="true"><span className="fm-spinner" aria-hidden="true" /> Running…</button>
            <button className="fm-btn fm-btn--secondary" type="button" data-loading="true" aria-busy="true"><span className="fm-spinner" aria-hidden="true" /> Syncing</button>
          </Specimen>
          <Specimen label="hover (note)">
            <span className="fm-inline-note">Hover any button: background steps to its -hover token; :active uses -pressed.</span>
          </Specimen>
          <Specimen label="focus">
            <button className="fm-btn fm-btn--secondary" type="button">Tab to me — focus ring</button>
          </Specimen>
          <Specimen label="disabled">
            <button className="fm-btn fm-btn--primary" type="button" disabled>Run analysis</button>
            <button className="fm-btn fm-btn--secondary" type="button" disabled>Save draft</button>
            <button className="fm-btn fm-btn--danger" type="button" disabled>Discard</button>
          </Specimen>
        </div>
      </Section>

      {/* ───────────────────────────────────────────────── TEXT INPUTS ─── */}
      <Section id="fm-text" title="Text · Search · Password · Number · Textarea" desc="The field family. All share the --field-* token set; affix fields wrap leading/trailing icons around a borderless input so the shell owns focus.">
        <div className="sg-card fm-cols">
          <div className="fm-field">
            <label className="fm-label" htmlFor="fm-t-default">Initiative name</label>
            <input id="fm-t-default" className="fm-input" value={text} onChange={(e) => setText(e.target.value)} placeholder="Name this run…" />
            <span className="fm-help" id="fm-t-default-help">Shown in the decision log.</span>
          </div>

          <div className="fm-field">
            <label className="fm-label" htmlFor="fm-t-empty">Placeholder (default)</label>
            <input id="fm-t-empty" className="fm-input" placeholder="e.g. Expand SSO to SMB" />
            <span className="fm-help">Default · hover lifts the border · focus shows the ring.</span>
          </div>

          <div className="fm-field">
            <label className="fm-label" htmlFor="fm-search">Search</label>
            <div className="fm-affix">
              <span className="fm-affix-icon"><IcoSearch /></span>
              <input id="fm-search" className="fm-bare" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Filter decisions…" />
              {search && (
                <button className="fm-iconbtn" type="button" aria-label="Clear search" onClick={() => setSearch("")}><IcoX /></button>
              )}
            </div>
          </div>

          <div className="fm-field">
            <label className="fm-label" htmlFor="fm-pw">Password</label>
            <div className="fm-affix">
              <input id="fm-pw" className="fm-bare" type={reveal ? "text" : "password"} defaultValue="anthropic-key" />
              <button className="fm-iconbtn" type="button" aria-label={reveal ? "Hide" : "Reveal"} aria-pressed={reveal} onClick={() => setReveal((v) => !v)}>
                {reveal ? <IcoEyeOff /> : <IcoEye />}
              </button>
            </div>
          </div>

          <div className="fm-field">
            <label className="fm-label" htmlFor="fm-num">Debate rounds</label>
            <div className="fm-affix fm-affix--stepper">
              <input id="fm-num" className="fm-bare" type="number" inputMode="numeric" value={count} onChange={(e) => setCount(Number(e.target.value) || 0)} />
              <span className="fm-stepper-btns">
                <button className="fm-step-btn" type="button" aria-label="Increment" onClick={() => setCount((c) => c + 1)}><IcoCaretUp size="var(--icon-xs)" /></button>
                <button className="fm-step-btn" type="button" aria-label="Decrement" onClick={() => setCount((c) => Math.max(0, c - 1))}><IcoCaretDown size="var(--icon-xs)" /></button>
              </span>
            </div>
          </div>

          <div className="fm-field">
            <label className="fm-label" htmlFor="fm-disabled">Disabled</label>
            <input id="fm-disabled" className="fm-input" value="anthropic:claude-sonnet-4-6" disabled readOnly />
            <span className="fm-help">Dimmed + not-allowed cursor.</span>
          </div>

          <div className="fm-field" style={{ gridColumn: "1 / -1" }}>
            <label className="fm-label" htmlFor="fm-area">Notes</label>
            <textarea id="fm-area" className="fm-input fm-textarea" placeholder="Free-text rationale… (drag the corner to resize)" defaultValue={"Enterprise churn cites this gap in 38% of exit interviews.\nSMB segment shows no equivalent signal — sample skew?"} />
          </div>
        </div>
      </Section>

      {/* ───────────────────────────────────────────────── SELECT FAMILY ─── */}
      <Section id="fm-select" title="Select · Combobox · Multi-select" desc="Native select styled to the field; a typeahead combobox; and a token-chip multi-select. Options are real buttons so the list is keyboard-operable.">
        <div className="sg-card fm-cols">
          <div className="fm-field">
            <label className="fm-label" htmlFor="fm-sel">Workflow (native select)</label>
            <div className="fm-select-wrap">
              <select id="fm-sel" className="fm-select" value={select} onChange={(e) => setSelect(e.target.value)}>
                {FRAMEWORKS.map((f) => <option key={f} value={f}>{f}</option>)}
              </select>
              <span className="fm-select-caret"><IcoCaretDown /></span>
            </div>
          </div>

          <div className="fm-field">
            <label className="fm-label" htmlFor="fm-combo">Combobox (typeahead)</label>
            <div className="fm-combo">
              <div className="fm-affix" role="combobox" aria-expanded={comboOpen} aria-controls="fm-combo-list" aria-haspopup="listbox">
                <input
                  id="fm-combo"
                  className="fm-bare"
                  value={comboQuery || comboValue}
                  placeholder="Type to filter…"
                  onChange={(e) => { setComboQuery(e.target.value); setComboOpen(true); }}
                  onFocus={() => setComboOpen(true)}
                  onBlur={() => window.setTimeout(() => setComboOpen(false), 120)}
                />
                <button className="fm-iconbtn" type="button" aria-label="Toggle list" onClick={() => setComboOpen((v) => !v)}><IcoCaretDown /></button>
              </div>
              {comboOpen && (
                <div className="fm-listbox" id="fm-combo-list" role="listbox">
                  {comboMatches.length === 0 && <div className="fm-option-empty">No matches</div>}
                  {comboMatches.map((f) => (
                    <button
                      key={f}
                      className="fm-option"
                      type="button"
                      role="option"
                      aria-selected={comboValue === f}
                      onMouseDown={(e) => e.preventDefault()}
                      onClick={() => { setComboValue(f); setComboQuery(""); setComboOpen(false); }}
                    >
                      {f}
                      {comboValue === f && <span className="fm-option-check"><IcoCheck /></span>}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <span className="fm-help">Selected: {comboValue || "—"}</span>
          </div>

          <div className="fm-field">
            <span className="fm-label" id="fm-multi-label">Analyst perspectives (multi)</span>
            <div className="fm-combo">
              <div className="fm-affix fm-affix--multi" aria-labelledby="fm-multi-label">
                {multi.map((m) => (
                  <span className="fm-chip" key={m}>
                    {m}
                    <button className="fm-chip-x" type="button" aria-label={`Remove ${m}`} onClick={() => setMulti((arr) => arr.filter((x) => x !== m))}><IcoX size="var(--icon-xs)" /></button>
                  </span>
                ))}
                <input className="fm-bare" placeholder={multi.length ? "" : "Add perspectives…"} onFocus={() => setMultiOpen(true)} onBlur={() => window.setTimeout(() => setMultiOpen(false), 120)} />
              </div>
              {multiOpen && (
                <div className="fm-listbox" role="listbox" aria-multiselectable="true">
                  {ANALYSTS.map((a) => {
                    const on = multi.includes(a);
                    return (
                      <button
                        key={a}
                        className="fm-option"
                        type="button"
                        role="option"
                        aria-selected={on}
                        onMouseDown={(e) => e.preventDefault()}
                        onClick={() => setMulti((arr) => (on ? arr.filter((x) => x !== a) : [...arr, a]))}
                      >
                        <span className="fm-checkfield" aria-hidden="true">
                          <input className="fm-checkbox" type="checkbox" checked={on} readOnly tabIndex={-1} />
                          <span className="fm-checkmark fm-checkmark--check"><IcoCheck size="var(--icon-xs)" /></span>
                        </span>
                        {a}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      </Section>

      {/* ───────────────────────────────────────────────── CHOICES ─── */}
      <Section id="fm-choices" title="Checkbox · Radio · Toggle switch" desc="Binary + exclusive choices. Checkbox supports an indeterminate (mixed) state. The switch is for instant on/off settings, not form submission.">
        <div className="sg-card fm-cols">
          <div className="fm-stack">
            <span className="fm-label">Checkbox</span>
            <label className="fm-choice">
              <span className="fm-checkfield">
                <input className="fm-checkbox" type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} />
                <span className="fm-checkmark fm-checkmark--check"><IcoCheck size="var(--icon-xs)" /></span>
              </span>
              Require human approval
            </label>
            <label className="fm-choice">
              <span className="fm-checkfield">
                <input ref={partialRef} className="fm-checkbox" type="checkbox" onChange={(e) => setPartial(e.target.checked)} />
                <span className="fm-checkmark fm-checkmark--check"><IcoCheck size="var(--icon-xs)" /></span>
                <span className="fm-checkmark fm-checkmark--minus"><IcoMinus size="var(--icon-xs)" /></span>
              </span>
              All analysts (indeterminate = mixed)
            </label>
            <label className="fm-choice" data-disabled="true">
              <span className="fm-checkfield">
                <input className="fm-checkbox" type="checkbox" checked readOnly disabled />
                <span className="fm-checkmark fm-checkmark--check"><IcoCheck size="var(--icon-xs)" /></span>
              </span>
              Locked (disabled, checked)
            </label>
          </div>

          <div className="fm-stack">
            <span className="fm-label" id="fm-radio-label">Risk posture (radio)</span>
            <div className="fm-radio-group" role="radiogroup" aria-labelledby="fm-radio-label">
              {[["conservative", "Conservative"], ["balanced", "Balanced"], ["aggressive", "Aggressive"]].map(([v, l]) => (
                <label className="fm-choice" key={v}>
                  <input className="fm-radio" type="radio" name="fm-risk" value={v} checked={radio === v} onChange={() => setRadio(v)} />
                  {l}
                </label>
              ))}
              <label className="fm-choice" data-disabled="true">
                <input className="fm-radio" type="radio" name="fm-risk" disabled />
                Custom (disabled)
              </label>
            </div>
          </div>

          <div className="fm-stack">
            <span className="fm-label">Toggle switch</span>
            <label className="fm-choice">
              <input className="fm-switch" type="checkbox" checked={live} onChange={(e) => setLive(e.target.checked)} role="switch" aria-checked={live} />
              Stream events live
            </label>
            <label className="fm-choice">
              <input className="fm-switch" type="checkbox" defaultChecked={false} role="switch" />
              Auto-approve low-risk
            </label>
            <label className="fm-choice" data-disabled="true">
              <input className="fm-switch" type="checkbox" checked readOnly disabled role="switch" aria-checked="true" />
              Telemetry (disabled)
            </label>
          </div>
        </div>
      </Section>

      {/* ───────────────────────────────────────────────── SLIDER ─── */}
      <Section id="fm-slider" title="Slider" desc="Single-value range with a measured numeric readout (mono, tabular). Native input — arrow keys, Home/End, and Page Up/Down all work; the fill tracks the value.">
        <div className="sg-card fm-stack" style={{ maxWidth: "var(--width-dialog-md)" }}>
          <div className="fm-field">
            <label className="fm-label" htmlFor="fm-conf">Judge pass threshold</label>
            <div className="fm-slider-row">
              <input
                id="fm-conf"
                className="fm-slider"
                type="range"
                min={0}
                max={100}
                value={confidence}
                style={sliderStyle}
                onChange={(e) => setConfidence(Number(e.target.value))}
                aria-describedby="fm-conf-val"
              />
              <span className="fm-slider-val" id="fm-conf-val">{confidence}%</span>
            </div>
            <span className="fm-help">Recommendations below this score loop back to the strategist.</span>
          </div>
          <div className="fm-field">
            <label className="fm-label" htmlFor="fm-conf-dis" data-disabled="true">Disabled</label>
            <div className="fm-slider-row">
              <input id="fm-conf-dis" className="fm-slider" type="range" min={0} max={100} defaultValue={40} style={{ ["--fm-slider-pct"]: "40%" } as CSSProperties} disabled />
              <span className="fm-slider-val">40%</span>
            </div>
          </div>
        </div>
      </Section>

      {/* ───────────────────────────────────────────────── DATE / TIME ─── */}
      <Section id="fm-date" title="Date / Time picker" desc="A styled trigger plus a static calendar + time popover (no date library — the product wires a real one; this proves the surface). Days are buttons: arrow-key navigable.">
        <div className="sg-card fm-cols">
          <div className="fm-field">
            <span className="fm-label">Trigger</span>
            <button className="fm-datetrigger" type="button" aria-haspopup="dialog">
              <span className="fm-affix-icon"><IcoCalendar /></span>
              Jun {calDay}, 2026
              <span className="fm-date-caret"><IcoCaretDown /></span>
            </button>
            <span className="fm-help">Opens the calendar below.</span>
          </div>

          <div className="fm-calendar" role="dialog" aria-label="Choose a date">
            <div className="fm-cal-head">
              <button className="fm-iconbtn" type="button" aria-label="Previous month"><IcoCaretLeft /></button>
              <span className="fm-cal-title">June 2026</span>
              <button className="fm-iconbtn" type="button" aria-label="Next month"><IcoCaretRight /></button>
            </div>
            <div className="fm-cal-grid" role="grid">
              {["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"].map((d) => <span className="fm-cal-dow" key={d}>{d}</span>)}
              {MONTH_DAYS.map((c, i) => (
                <button
                  key={i}
                  className="fm-cal-day"
                  type="button"
                  data-outside={c.outside}
                  data-today={!c.outside && c.day === 24}
                  aria-selected={!c.outside && c.day === calDay}
                  onClick={() => !c.outside && setCalDay(c.day)}
                  tabIndex={c.outside ? -1 : 0}
                >
                  {c.day}
                </button>
              ))}
            </div>
            <div className="fm-cal-foot">
              <span className="fm-affix-icon"><IcoClock /></span>
              <input className="fm-input" type="time" defaultValue="14:30" aria-label="Time" style={{ maxWidth: "var(--width-dialog-sm)" }} />
            </div>
          </div>
        </div>
      </Section>

      {/* ───────────────────────────────────────────────── FILE UPLOAD ─── */}
      <Section id="fm-file" title="File upload" desc="A keyboard-reachable dropzone (a label wrapping a visually-hidden input) plus a file list with size + remove. Drag-over flips the dropzone to its active token set.">
        <div className="sg-card fm-stack" style={{ maxWidth: "var(--width-dialog-md)" }}>
          <label
            className="fm-dropzone"
            data-dragging={dragging}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => { e.preventDefault(); setDragging(false); }}
          >
            <span className="fm-dz-icon"><IcoUpload size="var(--fm-dropzone-icon)" /></span>
            <span className="fm-dz-title"><b>Click to upload</b> or drag evidence files here</span>
            <span className="fm-dz-hint">CSV, JSON, or Markdown · up to 25 MB</span>
            <input className="fm-dz-input" type="file" multiple aria-label="Upload evidence files" />
          </label>
          <div className="fm-filelist">
            {[["customer-interviews.csv", "412 KB"], ["q3-funnel.json", "88 KB"]].map(([name, size]) => (
              <div className="fm-file" key={name}>
                <span className="fm-file-icon"><IcoFile /></span>
                <span className="fm-file-name">{name}</span>
                <span className="fm-file-size">{size}</span>
                <button className="fm-iconbtn" type="button" aria-label={`Remove ${name}`}><IcoX /></button>
              </div>
            ))}
          </div>
        </div>
      </Section>

      {/* ───────────────────────────────────────────────── FORM FIELD + VALIDATION ─── */}
      <Section id="fm-field" title="Form field · Label · Help · Validation" desc="The wrapper that binds a label to its control with help + error text via aria-describedby. Validation is never color-only: each state pairs a hue with an icon AND a message.">
        <div className="sg-card fm-cols">
          <div className="fm-field">
            <label className="fm-label" htmlFor="fm-v-default" data-required>Initiative title</label>
            <input id="fm-v-default" className="fm-input" defaultValue="Expand SSO to SMB tier" aria-describedby="fm-v-default-help" />
            <span className="fm-help" id="fm-v-default-help">Required · this is the run’s headline.</span>
          </div>

          <div className="fm-field">
            <label className="fm-label" htmlFor="fm-v-invalid">Model id</label>
            <input id="fm-v-invalid" className="fm-input" defaultValue="gemma-2b" aria-invalid="true" aria-describedby="fm-v-invalid-msg" />
            <span className="fm-msg fm-msg--error" id="fm-v-invalid-msg">
              <IcoErrorCircle /> Model lacks tool-calling — structured output will fail.
            </span>
          </div>

          <div className="fm-field">
            <label className="fm-label" htmlFor="fm-v-success">Model id</label>
            <input id="fm-v-success" className="fm-input" defaultValue="anthropic:claude-sonnet-4-6" data-valid="true" aria-describedby="fm-v-success-msg" />
            <span className="fm-msg fm-msg--success" id="fm-v-success-msg">
              <IcoCheckCircle /> Tool-calling supported — ready to run.
            </span>
          </div>

          <div className="fm-field">
            <label className="fm-label" htmlFor="fm-v-warning">API key</label>
            <input id="fm-v-warning" className="fm-input" type="password" defaultValue="sk-ant-…" aria-describedby="fm-v-warning-msg" />
            <span className="fm-msg fm-msg--warning" id="fm-v-warning-msg">
              <IcoWarnTriangle /> Free-tier key — runs may hit rate limits.
            </span>
          </div>

          <div className="fm-field" style={{ gridColumn: "1 / -1" }}>
            <span className="fm-label">Standalone validation messages</span>
            <span className="fm-msg fm-msg--error"><IcoErrorCircle /> Error — color + icon + text, never color alone (WCAG 1.4.1).</span>
            <span className="fm-msg fm-msg--success"><IcoCheckCircle /> Success — the check glyph reinforces the green.</span>
            <span className="fm-msg fm-msg--warning"><IcoWarnTriangle /> Warning — the triangle reinforces the amber.</span>
          </div>
        </div>
      </Section>
    </>
  );
}
