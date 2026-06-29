// Shared styleguide kit — primitives reused by App.tsx and every phase3/* module.
// Keep this tiny: it is review-surface chrome, not part of the design system.
import type React from "react";

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
