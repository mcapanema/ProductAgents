import "./phase9-empty-states.css";
import { Specimen } from "../sg";

/* Inline Icons — 24px, same convention Phase 4 established. */
function Layers24({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polygon points="12 2 2 7 2 17 12 22 22 17 22 7 12 2" />
      <polyline points="2 12 12 16.5 22 12" />
      <polyline points="2 7 12 11.5 22 7" />
    </svg>
  );
}

function Archive24({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="2" y="3" width="20" height="5" rx="1" />
      <path d="M4 8v11c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8" />
      <path d="M10 12h4" />
    </svg>
  );
}

function Clock24({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 6v6l4 2" />
    </svg>
  );
}

function AlertCircle24({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

function HelpCircle24({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 16v.01" />
      <path d="M12 13a2 2 0 0 0-2-2 2 2 0 0 0 2-2c0-1.11.89-2 2-2s2 .89 2 2" />
    </svg>
  );
}

const ICONS: { [key: string]: React.ComponentType<{ className?: string }> } = {
  layers: Layers24,
  archive: Archive24,
  clock: Clock24,
  alert: AlertCircle24,
  help: HelpCircle24,
};

interface EmptyCollectionStateProps {
  icon: keyof typeof ICONS;
  title: string;
  text: string;
  primary?: string;
  secondary?: string;
}

function EmptyCollectionState({
  icon,
  title,
  text,
  primary,
  secondary,
}: EmptyCollectionStateProps) {
  const Icon = ICONS[icon];
  if (!Icon) return null;

  return (
    <div className="p9-state">
      <div className="p9-state__icon">
        <Icon className="p9-ico--lg" />
      </div>
      <h3 className="p9-state__title">{title}</h3>
      <p className="p9-state__text">{text}</p>
      {(primary || secondary) && (
        <div className="p9-state__actions">
          {primary && <button className="p9-btn p9-btn--primary">{primary}</button>}
          {secondary && <button className="p9-btn p9-btn--secondary">{secondary}</button>}
        </div>
      )}
    </div>
  );
}

export function Phase9EmptyStates() {
  return (
    <div className="sg-frame">
      <h2 className="sg-heading">Empty States</h2>
      <p className="sg-explainer">
        Empty Collection State: surface when a list is empty. Choose an icon, title, descriptive
        text, and up to two CTAs. See <a href="#specs">Specimen specs</a> for all icon options.
      </p>

      <h3 className="sg-subheading" id="specs">
        Specimens
      </h3>

      <Specimen label="Empty projects">
        <EmptyCollectionState
          icon="layers"
          title="No projects yet"
          text="Projects group initiatives and their decision history. Add one to start tracking runs."
          primary="New project"
        />
      </Specimen>

      <Specimen label="Archived decisions">
        <EmptyCollectionState
          icon="archive"
          title="Nothing archived"
          text="Archive past decisions to clean up your list. Visit the main Decisions tab to archive."
          primary="Go to Decisions"
        />
      </Specimen>

      <Specimen label="Live runs (no current decisions)">
        <EmptyCollectionState
          icon="clock"
          title="No active decisions"
          text="Waiting for new initiatives to evaluate. Past decision runs are shown in the Sessions tab."
          secondary="View Sessions"
        />
      </Specimen>

      <Specimen label="Error — something's broken">
        <EmptyCollectionState
          icon="alert"
          title="Evaluation failed"
          text="An error occurred during the decision run. Check your internet connection and try again, or contact support if this persists."
          primary="Retry"
          secondary="Contact support"
        />
      </Specimen>

      <Specimen label="Help state (no onboarding context)">
        <EmptyCollectionState
          icon="help"
          title="Learn about decisions"
          text="ProductAgents evaluates product initiatives against evidence and past lessons to surface risks and opportunities before decisions are made."
          secondary="Read the guide"
        />
      </Specimen>
    </div>
  );
}
