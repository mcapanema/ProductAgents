import type {
  ConnectorHealth,
  ConnectorList,
  ConnectorSync,
  DecisionDetail,
  DecisionSummary,
  IpcMessage,
  PromptDiff,
  PromptSummary,
  PromptVersion,
  RunHandlers,
  RunParams,
  RunResult,
  SessionDetail,
  SessionSummary,
  WorkflowSummary,
} from "./types";

type Pending = {
  resolve: (value: unknown) => void;
  reject: (error: Error) => void;
};

/**
 * Transport-agnostic client for the NDJSON IPC protocol. `send` writes one
 * request line; `subscribe` registers a callback for each decoded response
 * message. Responses correlate to requests by `id`; `run` fans `event` messages
 * to a per-call handler before its terminal `result`/`error`.
 *
 * ponytail: single counter + two maps, no concurrency primitives — the sidecar
 * services one request at a time. Revisit only if the backend goes concurrent.
 */
export class IpcClient {
  private nextId = 1;
  private readonly pending = new Map<number, Pending>();
  private readonly runs = new Map<number, RunHandlers>();

  constructor(
    private readonly send: (line: string) => Promise<void>,
    subscribe: (cb: (msg: IpcMessage) => void) => void,
  ) {
    subscribe((msg) => this.dispatch(msg));
  }

  private dispatch(msg: IpcMessage): void {
    if (typeof msg.id !== "number") return; // {id: null} parse error → no waiter
    const id = msg.id;
    if (msg.event) {
      this.runs.get(id)?.onEvent(msg.event);
      return;
    }
    const waiter = this.pending.get(id);
    if (!waiter) return;
    this.pending.delete(id);
    this.runs.delete(id);
    if (msg.error !== undefined) waiter.reject(new Error(msg.error));
    else waiter.resolve(msg.result);
  }

  private call(
    method: string,
    params?: Record<string, unknown>,
    handlers?: RunHandlers,
  ): Promise<unknown> {
    const id = this.nextId++;
    return new Promise<unknown>((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      if (handlers) this.runs.set(id, handlers);
      const line = JSON.stringify(
        params === undefined ? { id, method } : { id, method, params },
      );
      this.send(line).catch((err) => {
        this.pending.delete(id);
        this.runs.delete(id);
        reject(err instanceof Error ? err : new Error(String(err)));
      });
    });
  }

  workflowsList(): Promise<WorkflowSummary[]> {
    return this.call("workflows.list") as Promise<WorkflowSummary[]>;
  }

  sessionsList(): Promise<SessionSummary[]> {
    return this.call("sessions.list") as Promise<SessionSummary[]>;
  }

  sessionsShow(sessionId: string): Promise<SessionDetail> {
    return this.call("sessions.show", { session_id: sessionId }) as Promise<SessionDetail>;
  }

  decisionsList(): Promise<DecisionSummary[]> {
    return this.call("decisions.list") as Promise<DecisionSummary[]>;
  }

  decisionsShow(decisionId: string): Promise<DecisionDetail> {
    return this.call("decisions.show", { decision_id: decisionId }) as Promise<DecisionDetail>;
  }

  connectorsList(): Promise<ConnectorList> {
    return this.call("connectors.list") as Promise<ConnectorList>;
  }

  connectorsHealth(): Promise<ConnectorHealth> {
    return this.call("connectors.health") as Promise<ConnectorHealth>;
  }

  connectorsSync(): Promise<ConnectorSync> {
    return this.call("connectors.sync") as Promise<ConnectorSync>;
  }

  promptsList(): Promise<PromptSummary[]> {
    return this.call("prompts.list") as Promise<PromptSummary[]>;
  }

  promptsShow(name: string, version: number): Promise<PromptVersion> {
    return this.call("prompts.show", { name, version }) as Promise<PromptVersion>;
  }

  promptsDiff(name: string, old: number, next: number): Promise<PromptDiff> {
    return this.call("prompts.diff", { name, old, new: next }) as Promise<PromptDiff>;
  }

  run(params: RunParams, handlers: RunHandlers): Promise<RunResult> {
    return this.call("run", params as unknown as Record<string, unknown>, handlers) as Promise<RunResult>;
  }
}
