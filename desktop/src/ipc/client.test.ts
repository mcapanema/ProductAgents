import { describe, it, expect } from "vitest";
import { IpcClient } from "./client";
import type { IpcMessage } from "./types";

function harness() {
  const sent: string[] = [];
  let cb: (m: IpcMessage) => void = () => {};
  const client = new IpcClient(
    async (line: string) => {
      sent.push(line);
    },
    (fn) => {
      cb = fn;
    },
  );
  return { client, sent, emit: (m: IpcMessage) => cb(m) };
}

describe("IpcClient", () => {
  it("sends a request with an incrementing id and correlates the result", async () => {
    const { client, sent, emit } = harness();
    const p = client.decisionsList();
    expect(JSON.parse(sent[0])).toMatchObject({ id: 1, method: "decisions.list" });
    emit({ id: 1, result: [{ id: "d1" }] });
    expect(await p).toEqual([{ id: "d1" }]);
  });

  it("passes params through", async () => {
    const { client, sent } = harness();
    void client.decisionsShow("d9");
    expect(JSON.parse(sent[0])).toMatchObject({
      id: 1,
      method: "decisions.show",
      params: { decision_id: "d9" },
    });
  });

  it("rejects when the server returns an error message", async () => {
    const { client, emit } = harness();
    const p = client.sessionsShow("missing");
    emit({ id: 1, error: "no such session: missing" });
    await expect(p).rejects.toThrow("no such session: missing");
  });

  it("streams run events to the handler, then resolves on the terminal result", async () => {
    const { client, emit } = harness();
    const events: { type: string }[] = [];
    const p = client.run(
      { workflow: "evaluate_initiative", title: "X" },
      { onEvent: (e) => events.push(e) },
    );
    emit({ id: 1, event: { type: "SessionStarted", payload: {} } });
    emit({ id: 1, event: { type: "NodeProgress", payload: { node: "market" } } });
    emit({ id: 1, result: { status: "finished", session_id: "s1" } });
    expect(events.map((e) => e.type)).toEqual(["SessionStarted", "NodeProgress"]);
    expect(await p).toEqual({ status: "finished", session_id: "s1" });
  });

  it("does not deliver events for an unrelated id", async () => {
    const { client, emit } = harness();
    const events: unknown[] = [];
    void client.run({ workflow: "w", title: "X" }, { onEvent: (e) => events.push(e) });
    emit({ id: 999, event: { type: "Stray", payload: {} } });
    expect(events).toEqual([]);
  });

  it("requests connectors.list and correlates the result", async () => {
    const { client, sent, emit } = harness();
    const p = client.connectorsList();
    expect(JSON.parse(sent[0])).toMatchObject({ id: 1, method: "connectors.list" });
    emit({ id: 1, result: { connectors: [{ name: "github" }], problems: [] } });
    expect(await p).toEqual({ connectors: [{ name: "github" }], problems: [] });
  });

  it("passes the optional connector to connectors.health and connectors.sync", async () => {
    const { client, sent } = harness();
    void client.connectorsHealth("github");
    expect(JSON.parse(sent[0])).toMatchObject({
      method: "connectors.health",
      params: { connector: "github" },
    });
    void client.connectorsSync("github");
    expect(JSON.parse(sent[1])).toMatchObject({
      method: "connectors.sync",
      params: { connector: "github" },
    });
    void client.connectorsHealth();
    expect(JSON.parse(sent[2])).not.toHaveProperty("params");
  });

  it("requests prompts.list and correlates the result", async () => {
    const { client, sent, emit } = harness();
    const p = client.promptsList();
    expect(JSON.parse(sent[0])).toMatchObject({ id: 1, method: "prompts.list" });
    emit({ id: 1, result: [{ name: "judge", versions: [0], active: 0 }] });
    expect(await p).toEqual([{ name: "judge", versions: [0], active: 0 }]);
  });

  it("passes prompts.show params", async () => {
    const { client, sent } = harness();
    void client.promptsShow("strategist", 2);
    expect(JSON.parse(sent[0])).toMatchObject({
      id: 1,
      method: "prompts.show",
      params: { name: "strategist", version: 2 },
    });
  });

  it("passes prompts.diff params", async () => {
    const { client, sent } = harness();
    void client.promptsDiff("strategist", 0, 2);
    expect(JSON.parse(sent[0])).toMatchObject({
      id: 1,
      method: "prompts.diff",
      params: { name: "strategist", old: 0, new: 2 },
    });
  });

  it("requests config.get and correlates the result", async () => {
    const { client, sent, emit } = harness();
    const p = client.configGet();
    expect(JSON.parse(sent[0])).toMatchObject({ id: 1, method: "config.get" });
    emit({
      id: 1,
      result: {
        model: "anthropic:claude-sonnet-4-6",
        provider: "anthropic",
        key_var: "ANTHROPIC_API_KEY",
        key_present: true,
        problems: [],
        providers: [],
      },
    });
    expect((await p).provider).toBe("anthropic");
  });

  it("passes config.set params", async () => {
    const { client, sent } = harness();
    void client.configSet({ model: "openai:gpt-4o", api_key: "sk-x" });
    expect(JSON.parse(sent[0])).toMatchObject({
      id: 1,
      method: "config.set",
      params: { model: "openai:gpt-4o", api_key: "sk-x" },
    });
  });

  it("sends an approve message with the verdict", async () => {
    const { client, sent } = harness();
    void client.approve("reject", "too risky");
    expect(JSON.parse(sent[0])).toMatchObject({
      id: 1,
      method: "approve",
      params: { verdict: "reject", rationale: "too risky" },
    });
  });

  it("requests reflection.record and correlates the result", async () => {
    const { client, sent, emit } = harness();
    const p = client.reflectionRecord("dec-1", "shipped");
    expect(JSON.parse(sent[0])).toMatchObject({
      id: 1,
      method: "reflection.record",
      params: { decision_id: "dec-1", note: "shipped" },
    });
    emit({
      id: 1,
      result: { decision_id: "dec-1", actual_outcomes: [], prediction_accuracy: 0, lessons_learned: [], reflected_at: "t", failed: false },
    });
    expect(await p).toMatchObject({ decision_id: "dec-1" });
  });

  it("workspacesShow calls workspaces.show and resolves the workspace", async () => {
    const { client, sent, emit } = harness();
    const promise = client.workspacesShow();
    const request = JSON.parse(sent[0]);
    expect(request.method).toBe("workspaces.show");
    emit({
      id: request.id,
      result: {
        name: "default",
        active: true,
        root: "/w",
        db_url: "sqlite:///w/productagents.db",
        connectors_file: "/w/connectors.yaml",
        env_file: "/w/.env",
        log_file: "/w/productagents.log",
        prompts_dir: "/w/prompts",
      },
    });
    await expect(promise).resolves.toMatchObject({ name: "default", prompts_dir: "/w/prompts" });
  });

  it("preferencesGet/preferencesSet round-trip preferences.*", async () => {
    const h = harness();
    const p1 = h.client.preferencesGet();
    let req = JSON.parse(h.sent[0]);
    expect(req.method).toBe("preferences.get");
    h.emit({ id: req.id, result: { theme: "dark" } });
    await expect(p1).resolves.toEqual({ theme: "dark" });

    const p2 = h.client.preferencesSet("light");
    req = JSON.parse(h.sent[1]);
    expect(req).toMatchObject({ method: "preferences.set", params: { theme: "light" } });
    h.emit({ id: req.id, result: { theme: "light" } });
    await expect(p2).resolves.toEqual({ theme: "light" });
  });

  it("connectorsConfigSave sends connector, config and optional secrets", async () => {
    const h = harness();
    const p = h.client.connectorsConfigSave("github", { owner: "a" }, { GH_TOKEN: "t" });
    const req = JSON.parse(h.sent[0]);
    expect(req).toMatchObject({
      method: "connectors.config.save",
      params: { connector: "github", config: { owner: "a" }, secrets: { GH_TOKEN: "t" } },
    });
    h.emit({ id: req.id, result: { connector: "github", installed: true, config: { owner: "a" }, schema: null, problems: [] } });
    await expect(p).resolves.toMatchObject({ connector: "github" });
  });
});

describe("workspace methods", () => {
  function harness() {
    const sent: string[] = [];
    let push: (msg: IpcMessage) => void = () => {};
    const client = new IpcClient(
      (line) => {
        sent.push(line);
        return Promise.resolve();
      },
      (cb) => {
        push = cb;
      },
    );
    return { client, sent, push: (msg: IpcMessage) => push(msg) };
  }

  it("workspacesList sends workspaces.list and resolves the result", async () => {
    const { client, sent, push } = harness();
    const promise = client.workspacesList();
    const req = JSON.parse(sent[0]);
    expect(req.method).toBe("workspaces.list");
    push({ id: req.id, result: [{ name: "default", active: true }] });
    await expect(promise).resolves.toEqual([{ name: "default", active: true }]);
  });

  it("workspacesCreate sends the name param", async () => {
    const { client, sent, push } = harness();
    const promise = client.workspacesCreate("acme");
    const req = JSON.parse(sent[0]);
    expect(req.method).toBe("workspaces.create");
    expect(req.params).toEqual({ name: "acme" });
    push({ id: req.id, result: { name: "acme", active: false } });
    await promise;
  });

  it("workspacesUse resolves the switched workspace", async () => {
    const { client, sent, push } = harness();
    const promise = client.workspacesUse("acme");
    const req = JSON.parse(sent[0]);
    expect(req.method).toBe("workspaces.use");
    push({ id: req.id, result: { name: "acme", active: true } });
    await expect(promise).resolves.toEqual({
      name: "acme",
      active: true,
    });
  });

  it("workspacesRename sends both names", async () => {
    const { client, sent, push } = harness();
    const promise = client.workspacesRename("default", "main");
    const req = JSON.parse(sent[0]);
    expect(req.method).toBe("workspaces.rename");
    expect(req.params).toEqual({ name: "default", new_name: "main" });
    push({ id: req.id, result: { name: "main", active: true, created_at: "t" } });
    await expect(promise).resolves.toEqual({ name: "main", active: true, created_at: "t" });
  });
});

describe("workflowsShow", () => {
  it("sends workflows.show with the name and resolves the detail", async () => {
    const sent: string[] = [];
    let deliver: (msg: IpcMessage) => void = () => {};
    const client = new IpcClient(
      async (line) => {
        sent.push(line);
      },
      (cb) => {
        deliver = cb;
      },
    );
    const promise = client.workflowsShow("evaluate_initiative");
    expect(JSON.parse(sent[0])).toEqual({
      id: 1,
      method: "workflows.show",
      params: { name: "evaluate_initiative" },
    });
    deliver({
      id: 1,
      result: {
        name: "evaluate_initiative",
        title: "Evaluate Initiative",
        description: "d",
        topology: null,
      },
    });
    await expect(promise).resolves.toMatchObject({
      name: "evaluate_initiative",
      topology: null,
    });
  });
});

describe("IpcClient disconnect", () => {
  it("rejects every in-flight request when the transport disconnects", async () => {
    const client = new IpcClient(
      async () => {},
      () => {},
    );
    const pending = client.workflowsList();
    client.disconnect();
    await expect(pending).rejects.toThrow("backend disconnected");
  });

  it("rejects new calls made after a disconnect", async () => {
    const client = new IpcClient(
      async () => {},
      () => {},
    );
    client.disconnect();
    await expect(client.workflowsList()).rejects.toThrow("backend disconnected");
  });

  it("uses the supplied reason string", async () => {
    const client = new IpcClient(
      async () => {},
      () => {},
    );
    const pending = client.decisionsList();
    client.disconnect("sidecar exited");
    await expect(pending).rejects.toThrow("sidecar exited");
  });
});
