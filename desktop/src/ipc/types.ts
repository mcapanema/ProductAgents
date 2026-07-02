export interface IpcEvent {
  type: string;
  payload: Record<string, unknown>;
}

/** One response line from the sidecar; each echoes the request `id`. */
export interface IpcMessage {
  id: number | null;
  result?: unknown;
  error?: string;
  event?: IpcEvent;
}

export interface RunParams {
  workflow: string;
  title: string;
  evidence?: string;
  approval?: boolean;
}

export interface RunHandlers {
  onEvent: (event: IpcEvent) => void;
}

export interface RunResult {
  status: "finished" | "failed" | "cancelled";
  session_id: string;
}

export interface WorkflowSummary {
  name: string;
  title: string;
  description: string;
}

export interface SessionSummary {
  id: string;
  workflow: string;
  status: string;
  created_at: string;
}

export interface SessionDetail {
  session: SessionSummary;
  events: IpcEvent[];
}

export interface DecisionSummary {
  id: string;
  title: string;
  recommendation: string;
  confidence: number;
  created_at: string;
}

export interface DecisionDetail {
  record: {
    decision_id: string;
    session_id?: string | null;
    initiative: { title: string; description: string };
    recommendation: {
      recommendation: string;
      confidence: number;
      rationale: string;
      expected_outcomes: string[];
    };
    evidence_sources?: { field: string; source: string; location: string }[];
    debate?: { round: number; side: string; argument: string }[];
    risks?: { reviewer: string; role: string; level: string; rationale: string }[];
    governance?: { verdict: string; rationale: string; decided_by: string } | null;
    timestamp: string;
    [key: string]: unknown;
  };
  outcomes: {
    decision_id: string;
    actual_outcomes: string[];
    prediction_accuracy: number;
    lessons_learned: string[];
    reflected_at: string;
  }[];
}

export interface OutcomeRecord {
  decision_id: string;
  actual_outcomes: string[];
  prediction_accuracy: number;
  lessons_learned: string[];
  reflected_at: string;
  failed: boolean;
}

export interface ConnectorSummary {
  name: string;
}

export interface ConnectorList {
  connectors: ConnectorSummary[];
  problems: string[];
  last_synced?: Record<string, string>;
}

export interface ConnectorHealthStatus {
  ok: boolean;
  detail: string;
}

export interface ConnectorHealth {
  statuses: Record<string, ConnectorHealthStatus>;
  problems: string[];
}

export interface ConnectorSyncResult {
  connector: string;
  written: number;
  ok: boolean;
  error: string | null;
}

export interface ConnectorSync {
  results: ConnectorSyncResult[];
  problems: string[];
}

export interface PromptSummary {
  name: string;
  versions: number[];
  active: number;
}

export interface PromptVersion {
  name: string;
  version: number;
  text: string;
}

export interface PromptDiff {
  name: string;
  old: number;
  new: number;
  diff: string;
}

export interface ProviderInfo {
  id: string;
  label: string;
  key_var: string;
  default_model: string;
}

export interface ConfigSettings {
  debate_rounds: number;
  judge_threshold: number;
  judge_max_retries: number;
  max_retries: number;
  log_level: string;
  github_repo: string;
  github_token_present: boolean;
}

export interface ConfigStatus {
  model: string;
  provider: string;
  key_var: string;
  key_present: boolean;
  problems: string[];
  settings: ConfigSettings;
  providers: ProviderInfo[];
}

export interface ConfigSetSettings {
  debate_rounds?: number;
  judge_threshold?: number;
  judge_max_retries?: number;
  max_retries?: number;
  log_level?: string;
  github_repo?: string;
  github_token?: string;
}

export interface ConfigSetParams {
  model: string;
  provider?: string;
  api_key?: string;
  settings?: ConfigSetSettings;
}

export interface WorkspaceInfo {
  name: string;
  active: boolean;
  root: string;
  db_url: string;
  connectors_file: string;
  env_file: string;
  log_file: string;
  prompts_dir: string;
}

export interface Lesson {
  decision_id: string;
  title: string;
  text: string;
  validated: boolean;
  prediction_accuracy: number | null;
}
