import type {
  ConfigSetParams,
  ConfigStatus,
  ConnectorConfigEntry,
  ConnectorHealth,
  ConnectorList,
  ConnectorSync,
  DecisionDetail,
  DecisionSummary,
  IpcMessage,
  Lesson,
  OutcomeRecord,
  Preferences,
  PromptDiff,
  PromptSummary,
  PromptVersion,
  RunHandlers,
  RunParams,
  RunResult,
  SessionDetail,
  SessionSummary,
  WorkflowDetail,
  WorkflowSummary,
  WorkspaceInfo,
  WorkspaceUseResult,
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
  private closed = false;

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

  /**
   * The transport reported the backend went away: reject every in-flight
   * request so callers leave their pending/"running" states instead of hanging
   * forever. Idempotent; after this, new calls reject at once.
   */
  disconnect(reason = "backend disconnected"): void {
    this.closed = true;
    const err = new Error(reason);
    for (const waiter of this.pending.values()) waiter.reject(err);
    this.pending.clear();
    this.runs.clear();
  }

  // ponytail: Promise<unknown> internally; R asserted at return — dispatch map must stay unknown-typed
  private call<R = unknown>(
    method: string,
    params?: Record<string, unknown>,
    handlers?: RunHandlers,
  ): Promise<R> {
    const id = this.nextId++;
    return new Promise<unknown>((resolve, reject) => {
      if (this.closed) {
        reject(new Error("backend disconnected"));
        return;
      }
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

  workflowsShow(name: string): Promise<WorkflowDetail> {
    return this.call<WorkflowDetail>("workflows.show", { name });
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

  memoryLessons(): Promise<Lesson[]> {
    return this.call<Lesson[]>("memory.lessons");
  }

  decisionsShow(decisionId: string): Promise<DecisionDetail> {
    return this.call<DecisionDetail>("decisions.show", { decision_id: decisionId });
  }

  connectorsList(): Promise<ConnectorList> {
    return this.call<ConnectorList>("connectors.list");
  }

  connectorsHealth(connector?: string): Promise<ConnectorHealth> {
    return this.call<ConnectorHealth>(
      "connectors.health",
      connector === undefined ? undefined : { connector },
    );
  }

  connectorsSync(connector?: string): Promise<ConnectorSync> {
    return this.call<ConnectorSync>(
      "connectors.sync",
      connector === undefined ? undefined : { connector },
    );
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

  promptsSave(name: string, text: string): Promise<PromptSummary> {
    return this.call<PromptSummary>("prompts.save", { name, text });
  }

  promptsRollback(name: string, version: number): Promise<PromptSummary> {
    return this.call<PromptSummary>("prompts.rollback", { name, version });
  }

  configGet(): Promise<ConfigStatus> {
    return this.call<ConfigStatus>("config.get");
  }

  configSet(params: ConfigSetParams): Promise<ConfigStatus> {
    return this.call<ConfigStatus>("config.set", { ...params });
  }

  workspacesShow(name?: string): Promise<WorkspaceInfo> {
    return this.call<WorkspaceInfo>("workspaces.show", name ? { name } : {});
  }

  workspacesList(): Promise<WorkspaceInfo[]> {
    return this.call<WorkspaceInfo[]>("workspaces.list");
  }

  workspacesCreate(name: string): Promise<WorkspaceInfo> {
    return this.call<WorkspaceInfo>("workspaces.create", { name });
  }

  workspacesUse(name: string): Promise<WorkspaceUseResult> {
    return this.call<WorkspaceUseResult>("workspaces.use", { name });
  }

  workspacesRename(name: string, newName: string): Promise<WorkspaceInfo> {
    return this.call<WorkspaceInfo>("workspaces.rename", {
      name,
      new_name: newName,
    });
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

  runCancel(sessionId: string): Promise<{ ok: boolean }> {
    return this.call<{ ok: boolean }>("run.cancel", { session_id: sessionId });
  }

  preferencesGet(): Promise<Preferences> {
    return this.call<Preferences>("preferences.get");
  }

  preferencesSet(theme: string): Promise<Preferences> {
    return this.call<Preferences>("preferences.set", { theme });
  }

  connectorsConfigList(): Promise<ConnectorConfigEntry[]> {
    return this.call<ConnectorConfigEntry[]>("connectors.config.list");
  }

  connectorsConfigSave(
    connector: string,
    config: Record<string, unknown>,
    secrets?: Record<string, string>,
  ): Promise<ConnectorConfigEntry> {
    return this.call<ConnectorConfigEntry>("connectors.config.save", {
      connector,
      config,
      ...(secrets ? { secrets } : {}),
    });
  }
}
