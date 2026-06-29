import type {
  ConfigSetParams,
  ConfigStatus,
  ConnectorHealth,
  ConnectorList,
  ConnectorSync,
  DecisionDetail,
  DecisionSummary,
  IpcMessage,
  OutcomeRecord,
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

  // ponytail: Promise<unknown> internally; R asserted at return — dispatch map must stay unknown-typed
  private call<R = unknown>(
    method: string,
    params?: Record<string, unknown>,
    handlers?: RunHandlers,
  ): Promise<R> {
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
    }) as unknown as Promise<R>;
  }

  workflowsList(): Promise<WorkflowSummary[]> {
    return this.call<WorkflowSummary[]>("workflows.list");
  }

  sessionsList(): Promise<SessionSummary[]> {
    return this.call<SessionSummary[]>("sessions.list");
  }

  sessionsShow(sessionId: string): Promise<SessionDetail> {
    return this.call<SessionDetail>("sessions.show", { session_id: sessionId });
  }

  decisionsList(): Promise<DecisionSummary[]> {
    return this.call<DecisionSummary[]>("decisions.list");
  }

  decisionsShow(decisionId: string): Promise<DecisionDetail> {
    return this.call<DecisionDetail>("decisions.show", { decision_id: decisionId });
  }

  connectorsList(): Promise<ConnectorList> {
    return this.call<ConnectorList>("connectors.list");
  }

  connectorsHealth(): Promise<ConnectorHealth> {
    return this.call<ConnectorHealth>("connectors.health");
  }

  connectorsSync(): Promise<ConnectorSync> {
    return this.call<ConnectorSync>("connectors.sync");
  }

  promptsList(): Promise<PromptSummary[]> {
    return this.call<PromptSummary[]>("prompts.list");
  }

  promptsShow(name: string, version: number): Promise<PromptVersion> {
    return this.call<PromptVersion>("prompts.show", { name, version });
  }

  promptsDiff(name: string, old: number, next: number): Promise<PromptDiff> {
    return this.call<PromptDiff>("prompts.diff", { name, old, new: next });
  }

  configGet(): Promise<ConfigStatus> {
    return this.call<ConfigStatus>("config.get");
  }

  configSet(params: ConfigSetParams): Promise<ConfigStatus> {
    return this.call<ConfigStatus>("config.set", { ...params });
  }

  reflectionRecord(decisionId: string, note: string): Promise<OutcomeRecord> {
    return this.call<OutcomeRecord>("reflection.record", {
      decision_id: decisionId,
      note,
    });
  }

  approve(verdict: string, rationale = ""): Promise<{ ok: boolean }> {
    return this.call<{ ok: boolean }>("approve", { verdict, rationale });
  }

  run(params: RunParams, handlers: RunHandlers): Promise<RunResult> {
    return this.call<RunResult>("run", { ...params }, handlers);
  }
}
