import type { ReactNode } from "react";
import type { Density } from "../sg";
import { Section, Specimen } from "../sg";
import "./phase9-empty-states.css";

type IconName = "folder" | "users" | "layers" | "play" | "search";

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

export function Phase9EmptyStates({ density }: { density: Density }) {
  void density;
  return (
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
  );
}
