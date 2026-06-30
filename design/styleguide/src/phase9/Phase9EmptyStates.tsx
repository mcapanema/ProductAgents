import type { ReactNode } from "react";
import type { Density } from "../sg";
import { Section, Specimen } from "../sg";
import "./phase9-empty-states.css";

type IconName = "folder" | "users" | "layers" | "play" | "search" | "rocket" | "check" | "circle";

const ICON_PATHS: Record<IconName, ReactNode> = {
  folder: <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z" />,
  users: (
    <>
      <circle cx={9} cy={8} r={3} />
      <path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6" />
      <path d="M16 5.5c1.4.4 2.5 1.7 2.5 3.2 0 1.5-1.1 2.8-2.5 3.2" />
      <path d="M16.5 14c2.5.4 4.5 2.6 4.5 5.4" />
    </>
  ),
  layers: (
    <>
      <path d="M12 3 21 8 12 13 3 8z" />
      <path d="M3 13l9 5 9-5" />
      <path d="M3 17l9 5 9-5" />
    </>
  ),
  play: <path d="M7 4.5l12 7.5-12 7.5V4.5z" />,
  search: (
    <>
      <circle cx={10} cy={10} r={6} />
      <line x1={15} y1={15} x2={20} y2={20} />
    </>
  ),
  rocket: (
    <>
      <path d="M14.5 3.5c2.5 1 4 2.5 5 5-1 3-3 5.5-6 7l-3-3c1.5-3 2-5.5 4-9z" />
      <path d="M9 14c-2 1-3 3-3 6 3 0 5-1 6-3" />
      <circle cx={15} cy={9} r={1.5} />
    </>
  ),
  check: <path d="M5 13l4 4 10-10" />,
  circle: <circle cx={12} cy={12} r={9} />,
};

function Icon({ name, size = "md" }: { name: IconName; size?: "sm" | "md" | "lg" }) {
  return (
    <svg
      className={size === "md" ? "p9-ico" : `p9-ico p9-ico--${size}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {ICON_PATHS[name]}
    </svg>
  );
}

function EmptyCollectionState(props: {
  icon: IconName;
  title: string;
  text: string;
  primary: string;
  secondary?: string;
}) {
  return (
    <div className="p9-state" data-kind="empty" role="status">
      <span className="p9-state__icon">
        <Icon name={props.icon} size="lg" />
      </span>
      <p className="p9-state__title">{props.title}</p>
      <p className="p9-state__text">{props.text}</p>
      <div className="p9-state__actions">
        {props.secondary && (
          <button type="button" className="p9-btn p9-btn--secondary">
            {props.secondary}
          </button>
        )}
        <button type="button" className="p9-btn p9-btn--primary">
          {props.primary}
        </button>
      </div>
    </div>
  );
}

type ChecklistStep = { label: string; done: boolean };

function FirstRunState({ steps }: { steps: ChecklistStep[] }) {
  return (
    <div className="p9-state" data-kind="first-run">
      <span className="p9-state__icon">
        <Icon name="rocket" size="lg" />
      </span>
      <p className="p9-state__title">Welcome to ProductAgents</p>
      <p className="p9-state__text">
        Connect a workspace, add an evidence source, then run your first evaluation — three steps to your first decision.
      </p>
      <ol className="p9-checklist">
        {steps.map((step) => (
          <li key={step.label} className="p9-checklist__item" data-done={step.done}>
            <Icon name={step.done ? "check" : "circle"} size="sm" />
            <span>{step.label}</span>
          </li>
        ))}
      </ol>
      <div className="p9-state__actions">
        <button type="button" className="p9-btn p9-btn--primary">
          Connect a workspace
        </button>
      </div>
    </div>
  );
}

function Spinner({ label }: { label: string }) {
  return (
    <svg className="p9-spinner" viewBox="0 0 24 24" role="status" aria-label={label}>
      <circle className="p9-spinner__track" cx={12} cy={12} r={10} />
      <circle className="p9-spinner__arc" cx={12} cy={12} r={10} pathLength={100} />
    </svg>
  );
}

function LoadingState({ label }: { label: string }) {
  return (
    <div className="p9-state" data-kind="loading" role="status" aria-live="polite">
      <Spinner label={label} />
      <p className="p9-state__title">{label}</p>
      <div className="p9-skeleton">
        <div className="p9-skeleton__row" />
        <div className="p9-skeleton__row" />
        <div className="p9-skeleton__row" />
      </div>
    </div>
  );
}

export function Phase9EmptyStates({ density }: { density: Density }) {
  void density;
  return (
    <>
      <Section
        id="p9-first-run"
        title="First-run experience"
        desc="The very first thing a new workspace sees — a welcome, a three-step checklist, and a single primary action."
      >
        <Specimen label="default">
          <FirstRunState
            steps={[
              { label: "Connect a workspace", done: true },
              { label: "Add an evidence source", done: false },
              { label: "Run your first evaluation", done: false },
            ]}
          />
        </Specimen>
      </Section>

      <Section
        id="p9-empty-collections"
        title="Empty collections"
        desc="One parameterized card for every list that can be empty — workspaces, agents, projects, executions, and search results."
      >
      <Specimen label="Empty workspace">
        <EmptyCollectionState
          icon="folder"
          title="No workspace yet"
          text="Create a workspace to hold its own database, connectors, and prompt overrides."
          primary="Create workspace"
        />
      </Specimen>
      <Specimen label="Empty agents">
        <EmptyCollectionState
          icon="users"
          title="No agents configured"
          text="Agents run as soon as evidence is collected — there's nothing to show until a decision run starts."
          primary="Add an agent"
        />
      </Specimen>
      <Specimen label="Empty projects">
        <EmptyCollectionState
          icon="layers"
          title="No projects yet"
          text="Projects group initiatives and their decision history. Add one to start tracking runs."
          primary="New project"
        />
      </Specimen>
      <Specimen label="Empty executions">
        <EmptyCollectionState
          icon="play"
          title="No executions yet"
          text="Completed runs appear here like a git log of decisions."
          primary="Run an evaluation"
          secondary="Import scenario"
        />
      </Specimen>
      <Specimen label="No search results">
        <EmptyCollectionState
          icon="search"
          title="No results"
          text="Nothing matches the current filters. Try a broader query or clear the filters."
          primary="Clear filters"
        />
      </Specimen>
      </Section>

      <Section
        id="p9-loading"
        title="Initial loading"
        desc="Shown while a workspace's first data load is in flight — a spinner plus skeleton rows, never a blank screen."
      >
        <Specimen label="default">
          <LoadingState label="Loading workspace…" />
        </Specimen>
      </Section>
    </>
  );
}
