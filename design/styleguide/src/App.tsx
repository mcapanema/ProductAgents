import { useEffect, useLayoutEffect, useState } from "react";
import { Section } from "./sg";
import { Phase3Layout } from "./phase3/Phase3Layout";
import { Phase3Navigation } from "./phase3/Phase3Navigation";
import { Phase3Forms } from "./phase3/Phase3Forms";
import { Phase3DataDisplay } from "./phase3/Phase3DataDisplay";
import { Phase3Feedback } from "./phase3/Phase3Feedback";
import { Phase3Overlays } from "./phase3/Phase3Overlays";

type Theme = "dark" | "light";
type Density = "comfortable" | "compact";

/** Two-option segmented toggle that writes a data-* attribute on <html>. */
function Toggle<T extends string>(props: {
  label: string;
  value: T;
  options: readonly { value: T; label: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <div className="sg-toggle" role="group" aria-label={props.label}>
      <span className="sg-label">{props.label}</span>
      {props.options.map((o) => (
        <button
          key={o.value}
          type="button"
          aria-pressed={props.value === o.value}
          onClick={() => props.onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

/** Reads a resolved CSS custom property off <html> (re-reads when `dep` changes).
 *  Uses a PASSIVE effect on purpose: it must run AFTER the layout effect that
 *  writes `data-theme` on <html> (App, below), or it would read the prior
 *  theme's values. Effect order is: all layout effects (child→parent), then all
 *  passive effects — so the parent's layout-effect attribute write lands first. */
function useResolvedVars(names: string[], dep: unknown): Record<string, string> {
  const [vals, setVals] = useState<Record<string, string>>({});
  useEffect(() => {
    const cs = getComputedStyle(document.documentElement);
    const next: Record<string, string> = {};
    for (const n of names) next[n] = cs.getPropertyValue(n).trim();
    setVals(next);
    // names is a stable literal per call site; dep drives re-read on theme change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dep]);
  return vals;
}

const NEUTRAL_STEPS = [50, 100, 200, 300, 400, 450, 500, 600, 700, 800, 850, 900, 950];
const SIGNAL_STEPS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950];
const RAMPS: { name: string; label: string; steps: number[] }[] = [
  { name: "slate", label: "cool graphite — dark grounds + cross-theme ink/border", steps: NEUTRAL_STEPS },
  { name: "sand", label: "warm neutral — light grounds", steps: NEUTRAL_STEPS },
  { name: "indigo", label: "primary — interactive accent (buttons / links / focus)", steps: SIGNAL_STEPS },
  { name: "amber", label: "signal — live / running / attention", steps: SIGNAL_STEPS },
  { name: "teal", label: "resolved — measured / settled / done", steps: SIGNAL_STEPS },
  { name: "red", label: "danger", steps: SIGNAL_STEPS },
  { name: "green", label: "success", steps: SIGNAL_STEPS },
  { name: "blue", label: "info", steps: SIGNAL_STEPS },
];

function Ramp({ name, label, steps, theme }: { name: string; label: string; steps: number[]; theme: Theme }) {
  const vars = useResolvedVars(steps.map((s) => `--c-${name}-${s}`), theme);
  return (
    <div className="sg-ramp">
      <div className="sg-ramp-head">
        <b>{name}</b>
        <span>{label}</span>
      </div>
      <div className="sg-ramp-steps">
        {steps.map((s) => (
          <div
            key={s}
            className="sg-step"
            style={{ background: `var(--c-${name}-${s})`, color: s <= 400 ? "#14171c" : "#f1f6fd" }}
            title={`--c-${name}-${s}: ${vars[`--c-${name}-${s}`] ?? ""}`}
          >
            <code>{s}</code>
          </div>
        ))}
      </div>
    </div>
  );
}

// Theme role tokens (resolved per theme). Glyph + label carry meaning, not color alone.
const ROLES = [
  ["--bg", "canvas"], ["--panel", "panel"], ["--elevated", "elevated"], ["--well", "well"],
  ["--field", "field"], ["--hairline", "hairline"], ["--structural", "structural"], ["--focus", "focus"],
  ["--ink", "ink"], ["--muted", "muted"], ["--primary", "primary"], ["--signal", "signal ●"], ["--resolved", "resolved ✓"],
  ["--danger", "danger ✕"], ["--success", "success ✓"], ["--info", "info ◆"],
] as const;

function Roles({ theme }: { theme: Theme }) {
  const vars = useResolvedVars(ROLES.map((r) => r[0]), theme);
  return (
    <div className="sg-swatches">
      {ROLES.map(([v, name]) => (
        <div className="sg-swatch" key={v}>
          <div className="chip" style={{ background: `var(${v})` }} />
          <b>{name}</b>
          <code>{vars[v]}</code>
        </div>
      ))}
    </div>
  );
}

const TYPE_SIZES = [
  ["5xl", "Display"], ["4xl", "—"], ["3xl", "—"], ["2xl", "—"], ["xl", "Heading"],
  ["lg", "—"], ["md", "—"], ["base", "Body"], ["sm", "Caption"], ["xs", "Label"],
] as const;
const SPACE_STEPS = [2, 4, 6, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96];
const RADII = ["none", "xs", "sm", "md", "lg", "xl", "2xl", "full"];
const SHADOWS = ["xs", "sm", "md", "lg", "xl"];
const ICON_SIZES = [["xs", 14], ["sm", 16], ["md", 20], ["lg", 24], ["xl", 32]] as const;
const MOTION = [
  ["fast", "--dur-fast", "--ease-standard"],
  ["normal", "--dur-normal", "--ease-decelerate"],
  ["slow", "--dur-slow", "--ease-emphasis"],
] as const;

// ─────────────────────────────────────────────── Phase 2 · token reference ───

const BG_ROLES = [
  ["--bg-primary", "Canvas"], ["--bg-secondary", "Secondary"], ["--bg-tertiary", "Tertiary"],
  ["--bg-elevated", "Elevated"], ["--bg-inverse", "Inverse"],
] as const;
const SURFACE_ROLES = [
  ["--surface-default", "Default"], ["--surface-raised", "Raised"], ["--surface-floating", "Floating"],
  ["--surface-sunken", "Sunken"], ["--surface-hover", "Hover"], ["--surface-pressed", "Pressed"],
  ["--surface-selected", "Selected"],
] as const;
const BORDER_ROLES = [
  ["--border-subtle", "Subtle"], ["--border-default", "Default"], ["--border-strong", "Strong"], ["--border-focus", "Focus"],
] as const;
const TEXT_ROLES2 = [
  ["--text-primary", "primary"], ["--text-secondary", "secondary"], ["--text-tertiary", "tertiary"],
  ["--text-disabled", "disabled"], ["--text-link", "link"],
] as const;
const TYPE_STYLES = [
  ["display", "Display"], ["heading-1", "Heading 1"], ["heading-2", "Heading 2"], ["heading-3", "Heading 3"],
  ["heading-4", "Heading 4"], ["title", "Title"], ["body-l", "Body L"], ["body-m", "Body M"], ["body-s", "Body S"],
  ["caption", "Caption"], ["label", "Label"], ["button", "Button"], ["code", "Code"], ["terminal", "Terminal"],
] as const;
const ELEVATIONS = [
  ["raised", "card resting on canvas"], ["floating", "popover / menu"],
  ["overlay", "drawer / sheet"], ["modal", "dialog above scrim"],
] as const;
const FEEDBACK = [
  { k: "success", ico: "✓", title: "Decision recorded", body: "The verdict was written to the DecisionStore." },
  { k: "warning", ico: "⚠", title: "Run degraded", body: "Two analysts fell back to scenario evidence." },
  { k: "error", ico: "✕", title: "Run aborted", body: "The provider returned a rate-limit error." },
  { k: "info", ico: "◆", title: "Sync scheduled", body: "Connectors refresh every 30 minutes." },
] as const;
const AI_STATUS = [
  { tok: "--ai-waiting", glyph: "◌", label: "Waiting", live: false },
  { tok: "--ai-running", glyph: "◐", label: "Running", live: true },
  { tok: "--ai-done", glyph: "✓", label: "Done", live: false },
  { tok: "--ai-degraded", glyph: "⚠", label: "Degraded", live: false },
  { tok: "--ai-failed", glyph: "✕", label: "Failed", live: false },
  { tok: "--ai-awaiting-human", glyph: "◆", label: "Awaiting you", live: false },
  { tok: "--ai-cancelled", glyph: "⊘", label: "Cancelled", live: false },
] as const;
const LOG_LEVELS = [
  ["trace", "resolved evidence source ref #4821"],
  ["debug", "strategist prompt rendered · 1,204 tok"],
  ["info", "customer_research complete · 0.78 conf"],
  ["warn", "market analyst degraded to scenario text"],
  ["error", "tool call failed — GitHub 422"],
  ["critical", "run aborted — provider auth rejected"],
] as const;
const GAUGES = [
  { label: "Skeptic-adjusted", val: 0.34, tok: "--ai-confidence-low" },
  { label: "Strategist", val: 0.68, tok: "--ai-confidence-medium" },
  { label: "Judge-validated", val: 0.91, tok: "--ai-confidence-high" },
] as const;
const ANALYSTS = [
  { tok: "--ai-analyst-customer", shape: "●", name: "Customer research" },
  { tok: "--ai-analyst-analytics", shape: "▲", name: "Product analytics" },
  { tok: "--ai-analyst-market", shape: "◆", name: "Market" },
  { tok: "--ai-analyst-business", shape: "■", name: "Business" },
  { tok: "--ai-analyst-technical", shape: "★", name: "Technical" },
] as const;

/** Resolved-value swatch grid for a set of semantic color roles. */
function SwatchGroup({ items, theme }: { items: readonly (readonly [string, string])[]; theme: Theme }) {
  const vars = useResolvedVars(items.map((i) => i[0]), theme);
  return (
    <div className="sg-roles2">
      {items.map(([tok, label]) => (
        <div className="sg-role" key={tok}>
          <div className="chip" style={{ background: `var(${tok})` }} />
          <b>{label}</b>
          <code title={tok}>{vars[tok]}</code>
        </div>
      ))}
    </div>
  );
}

/** One simple SVG icon reused at each size token — proves icon sizing + a
 *  consistent stroke. The product uses Phosphor (regular); this is illustrative. */
function GlyphIcon({ sizeVar }: { sizeVar: string }) {
  return (
    <svg style={{ width: `var(${sizeVar})`, height: `var(${sizeVar})` }} viewBox="0 0 24 24"
      fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <path d="M8 12.5l2.6 2.6L16 9.4" />
    </svg>
  );
}

export function App() {
  const [theme, setTheme] = useState<Theme>("light"); // light is the default theme (owner decision)
  const [density, setDensity] = useState<Density>("comfortable");

  // Layout effects so the attribute write happens BEFORE useResolvedVars' passive
  // read (which displays the resolved hexes) — otherwise the values lag a theme.
  useLayoutEffect(() => { document.documentElement.setAttribute("data-theme", theme); }, [theme]);
  useLayoutEffect(() => { document.documentElement.setAttribute("data-density", density); }, [density]);

  return (
    <div className="sg-shell">
      <header className="sg-bar">
        <h1>ProductAgents</h1>
        <span className="sg-sub">Phase 1–3 · Foundations + Tokens + Components</span>
        <span className="sg-spacer" />
        <Toggle
          label="Theme"
          value={theme}
          onChange={setTheme}
          options={[{ value: "light", label: "Light" }, { value: "dark", label: "Dark" }]}
        />
        <Toggle
          label="Density"
          value={density}
          onChange={setDensity}
          options={[{ value: "comfortable", label: "Comfortable" }, { value: "compact", label: "Compact" }]}
        />
      </header>

      <main className="sg-main">
        <div className="sg-intro">
          <h2>Foundation primitives</h2>
          <p>
            The raw, theme-agnostic values everything derives from — verified, on-grid, and
            consumed only through semantic roles. Color ramps are OKLCH-derived with hexes pinned
            and gated by <code>contrast.py</code>; every signal pairs with a glyph or label so
            color is never the only channel.
          </p>
        </div>

        <Section id="color" title="Color ramps" desc="Two neutral ramps, the indigo primary, and five signal ramps. Step 500 is the saturated anchor. Hover a step for its token + hex.">
          <div className="sg-card">
            {RAMPS.map((r) => <Ramp key={r.name} {...r} theme={theme} />)}
          </div>
        </Section>

        <Section id="roles" title="Theme roles (scaffold)" desc="How primitives map to surface / text / border / signal roles in the active theme. Phase 2 expands this into the full semantic set.">
          <div className="sg-card"><Roles theme={theme} /></div>
        </Section>

        <Section id="type" title="Type scale" desc="IBM Plex Sans (UI/body) and IBM Plex Mono (data/traces). 1.20 minor-third scale, 16px base.">
          <div className="sg-card sg-type">
            {TYPE_SIZES.map(([sz, role]) => (
              <div className="sg-type-row" key={sz}>
                <span className="meta">{role !== "—" ? `${role} · ` : ""}{sz}</span>
                <span className="sample" style={{ fontSize: `var(--fs-${sz})`, fontWeight: "var(--fw-semibold)", letterSpacing: "var(--ls-tight)" }}>
                  Reasoning, made legible.
                </span>
              </div>
            ))}
            <div className="sg-type-row">
              <span className="meta">weights</span>
              <div className="sg-weights">
                <span style={{ fontWeight: 400 }}>Regular 400</span>
                <span style={{ fontWeight: 500 }}>Medium 500</span>
                <span style={{ fontWeight: 600 }}>Semibold 600</span>
                <span style={{ fontWeight: 700 }}>Bold 700</span>
              </div>
            </div>
            <div className="sg-type-row">
              <span className="meta">mono · tabular</span>
              <div className="sg-mono-figures">confidence 0.78 · 1,204 tok · $0.0123 · 0123456789</div>
            </div>
          </div>
        </Section>

        <Section id="space" title="Spacing scale" desc="4px base grid. Density rescales role tokens in Phase 2 — these primitives stay fixed.">
          <div className="sg-card sg-scale">
            {SPACE_STEPS.map((s) => (
              <div className="sg-scale-row" key={s}>
                <span className="meta">space-{s}</span>
                <div className="sg-bar-fill" style={{ width: `var(--space-${s})` }} />
              </div>
            ))}
          </div>
        </Section>

        <Section id="radius" title="Radius" desc="Restrained corners — a precision instrument, not a soft consumer app.">
          <div className="sg-card sg-sizes">
            {RADII.map((r) => (
              <div className="sg-size-demo" key={r}>
                <div className="sg-radius-demo" style={{ borderRadius: `var(--radius-${r})` }} />
                <code>{r}</code>
              </div>
            ))}
          </div>
        </Section>

        <Section id="sizes" title="Icon & control sizes" desc="Fixed pixel sizes for icons, avatars, and control heights (≥44px touch target where touch applies).">
          <div className="sg-card sg-sizes">
            {ICON_SIZES.map(([name, px]) => (
              <div className="sg-size-demo" key={name}>
                <div className="sg-size-box" style={{ width: `var(--icon-${name})`, height: `var(--icon-${name})` }} />
                <code>icon-{name} · {px}</code>
              </div>
            ))}
          </div>
        </Section>

        <Section id="elevation" title="Elevation" desc="Shadows tuned for the dark canvas: deep, low-spread. Best judged in the dark theme.">
          <div className="sg-card sg-elevations">
            {SHADOWS.map((s) => (
              <div className="sg-elevation" key={s} style={{ boxShadow: `var(--shadow-${s})` }}>
                <code>shadow-{s}</code>
              </div>
            ))}
          </div>
        </Section>

        <Section id="motion" title="Motion" desc="Brisk and mechanical durations + easings. Reduced-motion parks the dot at rest.">
          <div className="sg-card sg-motion">
            {MOTION.map(([name, dur, ease]) => (
              <div className="sg-motion-row" key={name}>
                <span className="meta">{name} · {dur.replace("--dur-", "")}</span>
                <div className="sg-motion-track">
                  <div
                    className="sg-motion-dot"
                    style={{ animationDuration: `var(${dur})`, ["--_ease" as string]: `var(${ease})` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Section>

        {/* ═══════════════════════════════════ PHASE 2 · TOKEN REFERENCE ═══ */}
        <div className="sg-band">
          <h2>Token reference</h2>
          <span>Semantic → component → state → theme. Every demo is built from these tokens alone.</span>
        </div>

        <Section id="sem-color" title="2A · Semantic color" desc="Backgrounds (the grounds), surfaces (interactive material + states), the text ladder, and borders. Themes redefine only these — components never change across light/dark.">
          <div className="sg-card" style={{ display: "grid", gap: "var(--space-24)" }}>
            <div>
              <p className="sg-comp-label">Backgrounds</p>
              <SwatchGroup items={BG_ROLES} theme={theme} />
            </div>
            <div>
              <p className="sg-comp-label">Surfaces &amp; interaction states</p>
              <SwatchGroup items={SURFACE_ROLES} theme={theme} />
            </div>
            <div>
              <p className="sg-comp-label">Borders</p>
              <SwatchGroup items={BORDER_ROLES} theme={theme} />
            </div>
            <div>
              <p className="sg-comp-label">Text ladder (on this panel)</p>
              <div className="sg-textladder">
                {TEXT_ROLES2.map(([tok, label]) => (
                  <div className="row" key={tok}>
                    <span className="meta">{label}</span>
                    <span className="demo" style={{ color: `var(${tok})` }}>
                      Reasoning, made legible — evidence, disagreement, confidence.
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Section>

        <Section id="feedback" title="2A · Feedback" desc="success / warning / error / info, each a bg · surface · border · text · icon set. Every alert pairs its color with an icon and a label — color is never the only channel (WCAG 1.4.1).">
          <div className="sg-card sg-alerts">
            {FEEDBACK.map((f) => (
              <div className="demo-alert" key={f.k}
                style={{ background: `var(--fb-${f.k}-bg)`, borderColor: `var(--fb-${f.k}-border)` }}>
                <span className="ico" style={{ color: `var(--fb-${f.k}-icon)` }} aria-hidden="true">{f.ico}</span>
                <span>
                  <b style={{ color: `var(--fb-${f.k}-text)` }}>{f.title}</b>
                  <p>{f.body}</p>
                </span>
              </div>
            ))}
          </div>
        </Section>

        <Section id="type-styles" title="2B · Type styles" desc="Composed styles over the Phase-1 primitives. Code & Terminal are mono with tabular figures so measured values hold their columns.">
          <div className="sg-card sg-typestyles">
            {TYPE_STYLES.map(([k, label]) => {
              const mono = k === "code" || k === "terminal";
              return (
                <div className="sg-ts-row" key={k}>
                  <span className="meta">{label}</span>
                  <span className="demo"
                    style={{ font: `var(--text-${k})`, letterSpacing: `var(--text-${k}-tracking)`, fontVariantNumeric: mono ? "tabular-nums" : undefined, textTransform: k === "label" ? "uppercase" : undefined }}>
                    {mono ? "confidence=0.78  tokens=1,204  cost=$0.0123" : "Reasoning, made legible."}
                  </span>
                </div>
              );
            })}
          </div>
        </Section>

        <Section id="dimensional" title="2C · Dimensional" desc="Radius, border-width, and elevation promoted to intent-named roles. Elevation is best judged in dark; light re-tints the shadows softer.">
          <div className="sg-card sg-dim">
            {ELEVATIONS.map(([name, role]) => (
              <div className="sg-dim-cell" key={name} style={{ boxShadow: `var(--elevation-${name})` }}>
                <code>elevation-{name} · {role}</code>
              </div>
            ))}
          </div>
        </Section>

        <Section id="components" title="2E · Component + state tokens" desc="Buttons, fields, and chips built ONLY from --btn-* / --field-* / --chip-* tokens. Hover, focus (Tab to a control), pressed, and disabled all come from the state matrix. Toggle theme — the markup doesn't change.">
          <div className="sg-card sg-comp">
            <div className="sg-comp-row">
              <span className="sg-comp-label">Button — variants</span>
              <button className="demo-btn demo-btn--primary" type="button">Run evaluation</button>
              <button className="demo-btn demo-btn--secondary" type="button">Open session</button>
              <button className="demo-btn demo-btn--ghost" type="button">Cancel</button>
              <button className="demo-btn demo-btn--danger" type="button">Delete workspace</button>
              <button className="demo-btn demo-btn--primary" type="button" disabled>Disabled</button>
            </div>
            <div className="sg-comp-row">
              <span className="sg-comp-label">Field — default · invalid</span>
              <input className="demo-field" placeholder="Initiative name…" defaultValue="" />
              <input className="demo-field" aria-invalid="true" defaultValue="—" />
            </div>
            <div className="sg-comp-row">
              <span className="sg-comp-label">Chip</span>
              <span className="demo-chip">v3 · sonnet-4-6</span>
              <span className="demo-chip">2 connectors</span>
            </div>
          </div>
        </Section>

        <Section id="ai-status" title="2F · AI status" desc="Grounded in the real node states (waiting → running → done / degraded / failed / awaiting-human). amber = live (its reserved job), teal = settled, indigo = your turn, red = failed. Every status carries a glyph + label.">
          <div className="sg-card sg-ai-status">
            {AI_STATUS.map((s) => (
              <span className="demo-status" key={s.tok}>
                <span className="sg-status-dot" data-live={s.live} style={{ background: `var(${s.tok})`, color: `var(${s.tok})` }} />
                <span className="glyph" style={{ color: `var(${s.tok})` }} aria-hidden="true">{s.glyph}</span>
                <span className="lbl">{s.label}</span>
              </span>
            ))}
          </div>
        </Section>

        <Section id="confidence" title="2F · Confidence gauge" desc="The signature motif — confidence as a measured quantity. A calibrated low→high scale; the numeric reading is always shown, so color is reinforcement, not the message.">
          <div className="sg-card sg-gauges">
            {GAUGES.map((g) => (
              <div className="sg-gauge-row" key={g.label}>
                <div className="sg-gauge-head">
                  <span className="lbl">{g.label}</span>
                  <span className="val" style={{ color: `var(${g.tok})` }}>{g.val.toFixed(2)}</span>
                </div>
                <div className="sg-gauge">
                  <div className="fill" style={{ width: `${g.val * 100}%`, background: `var(${g.tok})` }} />
                </div>
              </div>
            ))}
          </div>
        </Section>

        <Section id="logs" title="2F · Log levels" desc="trace → critical in the log well. Body levels clear AA; trace/debug are de-emphasized (still ≥3:1). The level label carries meaning alongside color.">
          <div className="sg-card">
            <div className="sg-log">
              {LOG_LEVELS.map(([lvl, msg]) => (
                <div className="line" key={lvl}>
                  <span className="lvl" style={{ color: `var(--ai-log-${lvl})` }}>{lvl}</span>
                  <span className="msg">{msg}</span>
                </div>
              ))}
            </div>
          </div>
        </Section>

        <Section id="debate" title="2F · Debate & analysts" desc="The advocate/skeptic dialectic is a first-class element. The five analyst perspectives stay visually distinct — by color AND a unique shape AND a label AND position, because the hues are not all separable under color-blindness.">
          <div className="sg-card" style={{ display: "grid", gap: "var(--space-20)" }}>
            <div className="sg-debate">
              <div className="demo-debate" style={{ ["--side" as string]: "var(--ai-advocate)" }}>
                <h4><span className="tag" aria-hidden="true">＋</span> Opportunity advocate</h4>
                <p>Synced feedback shows 38% of churned accounts cite this exact gap.</p>
              </div>
              <div className="demo-debate" style={{ ["--side" as string]: "var(--ai-skeptic)" }}>
                <h4><span className="tag" aria-hidden="true">？</span> Opportunity skeptic</h4>
                <p>The sample skews enterprise; the SMB segment shows no such signal.</p>
              </div>
            </div>
            <div className="sg-analysts">
              {ANALYSTS.map((a) => (
                <span className="demo-analyst" key={a.tok}>
                  <span className="mark" style={{ color: `var(${a.tok})` }} aria-hidden="true">{a.shape}</span>
                  <span className="name">{a.name}</span>
                </span>
              ))}
            </div>
          </div>
        </Section>

        <Section id="iconography" title="2D · Iconography" desc="Locked set: Phosphor (MIT), one weight (regular), filled reserved for the single active item. Sizes use the --icon-* tokens. SVG only — never emoji. (Icon below is illustrative; the product imports Phosphor.)">
          <div className="sg-card sg-icons">
            {([["icon-xs", "xs"], ["icon-sm", "sm"], ["icon-md", "md"], ["icon-lg", "lg"], ["icon-xl", "xl"]] as const).map(([v, n]) => (
              <div className="sg-icon-demo" key={n}>
                <GlyphIcon sizeVar={`--${v}`} />
                <code>{n}</code>
              </div>
            ))}
          </div>
        </Section>

        <Section id="a11y" title="2D · 2G — Focus, density & accessibility" desc="Keyboard-first: Tab to the control to see the ring (offset is load-bearing). Density rescales spacing roles only — toggle it above. Reduced-motion collapses every transition system-wide.">
          <div className="sg-card" style={{ display: "grid", gap: "var(--space-16)" }}>
            <div className="sg-focus-demo">
              <button className="demo-btn demo-btn--secondary" type="button">Tab to me — focus ring</button>
              <input className="demo-field" placeholder="…and to me" />
            </div>
            <p className="sg-density-note">
              Density is <b>{density}</b>. It drives <code>--pad-*</code>, <code>--gap-*</code> and{" "}
              <code>--row-height</code> — never type size — so 60–90-minute sessions trade breathing room for
              rows-on-screen without reflowing the type system. Min interactive target where touch applies:{" "}
              <code>--a11y-target-touch-min</code> (44px).
            </p>
          </div>
        </Section>

        {/* ═══════════════════════════════════ PHASE 3 · CORE COMPONENTS ═══ */}
        <div className="sg-band">
          <h2>Core components</h2>
          <span>The working component vocabulary — built only from the token layer, adapting across theme + density with zero markup change.</span>
        </div>
        <Phase3Layout />
        <Phase3Navigation />
        <Phase3Forms />
        <Phase3DataDisplay />
        <Phase3Feedback />
        <Phase3Overlays />
      </main>
    </div>
  );
}
