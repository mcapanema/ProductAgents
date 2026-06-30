// Shared styleguide kit — primitives reused by the category modules
// (Foundation / Tokens / Components) and the App shell.
// Keep this tiny: it is review-surface chrome, not part of the design system.
import { useEffect, useState } from "react";
import type React from "react";

export type Theme = "dark" | "light";
export type Density = "comfortable" | "compact";

/** A titled gallery block. `desc` is the one-line intent shown under the title. */
export function Section(props: { id: string; title: string; desc: string; children: React.ReactNode }) {
  return (
    <section className="sg-section" id={props.id}>
      <header>
        <h3>{props.title}</h3>
        <p className="sg-desc">{props.desc}</p>
      </header>
      {props.children}
    </section>
  );
}

/** A labelled row inside a card — `label` on the left, demo content on the right.
 *  Used across the Phase 3 galleries so every component variant is named. */
export function Specimen(props: { label: string; children: React.ReactNode }) {
  return (
    <div className="sg-specimen">
      <span className="sg-specimen-label">{props.label}</span>
      <div className="sg-specimen-body">{props.children}</div>
    </div>
  );
}

/** Reads resolved CSS custom properties off <html> (re-reads when `dep` changes).
 *  Uses a PASSIVE effect on purpose: it must run AFTER the layout effect that
 *  writes `data-theme` on <html> (App), or it would read the prior theme's
 *  values. Effect order is: all layout effects (child→parent), then all passive
 *  effects — so the parent's layout-effect attribute write lands first. */
export function useResolvedVars(names: string[], dep: unknown): Record<string, string> {
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
