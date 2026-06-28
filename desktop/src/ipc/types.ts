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
}

export interface RunHandlers {
  onEvent: (event: IpcEvent) => void;
}

export interface RunResult {
  status: "finished" | "failed";
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
    initiative: { title: string; description: string };
    recommendation: {
      recommendation: string;
      confidence: number;
      rationale: string;
      expected_outcomes: string[];
    };
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
