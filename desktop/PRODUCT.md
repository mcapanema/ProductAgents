# Product

## Register

product

## Users

Senior product leaders, principal PMs, and product orgs making high-stakes decisions
under uncertainty. Technically sophisticated — they install a local desktop app and
configure model providers and live connectors (GitHub/Jira). Power users: keyboard-driven,
density-tolerant, running long 60–90-minute analytical sessions. They re-read decisions
months later to defend them — traceability is the product, not a feature.

## Product Purpose

A local-first operating environment for product decision-making — "an IDE for
decision-making," not an AI chat app. A multi-agent pipeline turns evidence into governed,
defensible decisions (five analysts → advocate/skeptic debate → strategist → judge → risk →
governance/approval → DecisionStore), and an organizational-memory loop feeds outcomes back
into future decisions. The interface exists to make *reasoning* legible — evidence,
disagreement, confidence under uncertainty, traceability — never conversation. Success = a
decision a leader can defend months later from what's on screen.

## Brand Personality

Calm, rigorous, evidence-grounded, trustworthy, defensible. The aesthetic is "Instrument" —
a precision, telemetry-grade panel in the lineage of LangSmith, Datadog, and GitHub Actions,
but warmer and hand-built, not a generic ops dashboard. The signature idea: a decision is a
set of *measured quantities*, and confidence is a shown, calibrated reading on every verdict.
It visualizes reasoning, not chat.

## Anti-references

- **Not ChatGPT / an AI chat app.** No conversation thread as the primary surface.
- **Not generic SaaS** — beat the cornflower-blue-accent-on-near-black reflex (the old
  placeholder was exactly this).
- **Not the "AI dev tool" cliché** — dark + one neon/acid-green accent.
- **Not a heavy, ceremonial "deposition/record" register** — too solemn for a
  Linear/LangSmith-class tool.
- Banned patterns: gradient text, glassmorphism-as-default, tracked-uppercase eyebrows on
  every section, side-stripe-only accents, nested cards, emoji as icons.
- North-star references (the *right* feel): VS Code, Linear, LangSmith, GitHub Actions, Datadog.

## Design Principles

1. **Visualize reasoning, not chat.** The centerpiece is a streaming reasoning timeline, not a
   message log.
2. **Traceability is the product.** Every claim traceable on screen; raw data always one expand away.
3. **Keep specialists distinct.** The five analyst perspectives stay visually separable
   (shape + label + position + color, CVD-honest); don't collapse them early.
4. **Structured disagreement is first-class.** The advocate/skeptic dialectic is a primary
   visual element, not a footnote.
5. **Learning is visible.** Outcomes and lessons surface next to the original prediction they test.
6. **Confidence as a measured quantity.** One calibration-gauge motif recurs on every verdict —
   color reinforces a shown numeric reading, never replaces it.

## Accessibility & Inclusion

WCAG 2.1 AA minimum — body ≥ 4.5:1, large/UI/structural ≥ 3:1 — computed by `design/contrast.py`,
never asserted by hand, and verified under protanopia/deuteranopia simulation in both themes.
Color is never the only channel (WCAG 1.4.1): every signal also carries a glyph, label, and
position. Keyboard-first — every surface, especially the reasoning timeline, is fully
keyboard-operable. Dark is primary (dim rooms, long sessions) but never pure #000 (halation); a
light theme is fully designed (bright offices, board-deck screenshots). Density must survive
60–90-minute sessions (comfortable + compact). Reduced-motion is a global switch, not per-component.
