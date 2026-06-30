// Category: TOKENS — the layered token reference (Phase 2: semantic → component
// → state → theme). Every demo is built from these tokens alone.
import { Section, useResolvedVars } from "./sg";
import type { Theme, Density } from "./sg";

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

export function Tokens({ theme, density }: { theme: Theme; density: Density }) {
  return (
    <>
      <div className="sg-intro">
        <h2>Token reference</h2>
        <p>
          Semantic → component → state → theme. Every demo below is built from these tokens
          alone — proof that components can be composed from the token layer and adapt across
          light/dark and density with zero markup change.
        </p>
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
    </>
  );
}
