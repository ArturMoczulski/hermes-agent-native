import { useEffect, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router";
import { Button } from "@nous-research/ui/ui/components/button";
import { agentsEndpoint, agentWorkStatus, validWorkLimits, outputVersionLink, type Agent, type OutputReference, type OutputVersion, type WorkResult } from "@/lib/agent-native";
import { Input } from "@nous-research/ui/ui/components/input";
import { Label } from "@nous-research/ui/ui/components/label";
import { Markdown } from "@/components/Markdown";
import { fetchJSON } from "@/lib/api";
import { usePageHeader } from "@/contexts/usePageHeader";

type LoadedAgent = { key: string; agent?: Agent; error?: string };

export default function AgentDetailPage() {
  const { agentId } = useParams<{ agentId: string }>();
  const { setTitle } = usePageHeader();
  const [retryError, setRetryError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const [refreshError, setRefreshError] = useState(false);
  const [reload, setReload] = useState(0);
  const mutationVersion = useRef(0);
  const [loaded, setLoaded] = useState<LoadedAgent>({ key: "" });
  const key = `${agentId}:${reload}`;
  const current = loaded.key === key ? loaded : undefined;
  const agent = current?.agent;

  useEffect(() => {
    let active = true;
    const fetchAgent = () => {
      const version = mutationVersion.current;
      return fetchJSON<Agent>(`${agentsEndpoint}/${encodeURIComponent(agentId ?? "")}`)
      .then((result) => { if (active && version === mutationVersion.current) { setLoaded({ key, agent: result }); setRefreshError(false); } })
      .catch(() => {
        if (active && version === mutationVersion.current) {
          setRefreshError(true);
          setLoaded((previous) => previous.key === key && previous.agent ? previous : { key, error: "Could not load this agent. Check the link, your connection and sign-in, then retry." });
        }
      });
    };
    let timer: number | undefined;
    const poll = async () => {
      await fetchAgent();
      if (active) timer = window.setTimeout(() => { void poll(); }, 1500);
    };
    void poll();
    return () => { active = false; window.clearTimeout(timer); };
  }, [agentId, key]);

  useEffect(() => {
    setTitle(agent?.name ?? "Agent");
    return () => setTitle(null);
  }, [agent?.name, setTitle]);

  const retrySetup = async () => {
    setRetrying(true);
    setRetryError(null);
    try {
      await fetchJSON<Agent>(`${agentsEndpoint}/${encodeURIComponent(agentId ?? "")}/setup/retry`, { method: "POST" });
      setReload((value) => value + 1);
    } catch {
      setRetryError("Could not request setup retry. Check your connection; setup may already be running.");
    } finally { setRetrying(false); }
  };
  const setup = agent?.setup;
  const setupTitles = { queued: "Setup queued", preparing: "Preparing agent", blocked: "Plane setup required", failed: "Setup needs attention", unresolved: "Setup outcome needs checking", ready: "Workspace and planning ready", superseded: "Setup superseded" };
  const startup = agent?.startup;
  const staleRequest = startup && startup.soul_revision !== agent?.soul_revision;

  return (
    <div className="mx-auto w-full max-w-4xl space-y-6 p-6">
      <Link to="/agents" className="text-sm underline underline-offset-4">All agents</Link>
      {!current && <p role="status">Loading agent…</p>}
      {current?.error && <div role="alert" className="space-y-3"><p>{current.error}</p><Button onClick={() => setReload((value) => value + 1)}>Retry</Button></div>}
      {agent && <>
        {refreshError && <p role="alert">Live updates are disconnected. Showing the last confirmed state; reconnect to see current progress.</p>}
        <header className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h1 className="text-2xl font-semibold">{agent.name}</h1>
            <span aria-label="Execution status" className="rounded-full border px-3 py-1 text-sm">{agentWorkStatus(agent)}</span>
          </div>
          <p className="break-all text-xs text-muted-foreground">Root agent · {agent.id}</p>
          <Link className="inline-block rounded-md border px-4 py-2 text-sm underline-offset-4 hover:underline" to={`/agents/${encodeURIComponent(agent.id)}/chat`}>Chat with agent</Link>
        </header>
        <WorkControls key={`work:${agent.id}`} agent={agent}
          onMutationStart={() => { mutationVersion.current += 1; }}
          onUpdate={(result) => {
            mutationVersion.current += 1;
            setLoaded((previous) => previous.key === key ? { key, agent: result } : previous);
          }} />
        <section aria-label="Agent purpose" className="space-y-3 rounded-xl border p-5">
          <h2 className="text-lg font-semibold">Purpose</h2>
          <p className="whitespace-pre-wrap break-words">{agent.purpose}</p>
          <p className="text-xs text-muted-foreground">Purpose revision {agent.soul_revision}</p>
        </section>
        <section aria-label="Startup request" className="space-y-3 rounded-xl border p-5">
          <h2 className="text-lg font-semibold">{startup ? "First review requested" : "No startup request recorded"}</h2>
          {startup ? <>
            <p>{agent.work
              ? "The initial work request is retained. Its current progress and limits are shown above."
              : "Your agent is saved and its first review has been requested. Set work limits above when you want it to begin work on its purpose."}</p>
            <dl className="grid gap-2 text-sm sm:grid-cols-[auto_1fr]">
              <dt className="text-muted-foreground">Requested</dt><dd><time dateTime={startup.requested_at}>{new Date(startup.requested_at).toLocaleString()}</time></dd>
              <dt className="text-muted-foreground">Cause</dt><dd>Agent creation</dd>
              <dt className="text-muted-foreground">Purpose revision</dt><dd>{startup.soul_revision}</dd>
              <dt className="text-muted-foreground">Request ID</dt><dd className="break-all">{startup.id}</dd>
            </dl>
            {staleRequest && <p role="status">The purpose changed after this request. It cannot authorize work on the current purpose.</p>}
          </> : <p>This agent was saved before startup requests were recorded. Opening this page does not start it.</p>}
        </section>
        {setup && <section aria-label="Agent setup" className="space-y-3 rounded-xl border p-5">
          <h2 className="text-lg font-semibold">{setupTitles[setup.status]}</h2>
          <p role="status">{setup.message}</p>
          <ul className="space-y-1 text-sm">
            <li>{setup.files_ready ? "Private files ready" : "Private files pending"}</li>
            <li>{setup.workspace_id ? "Plane workspace created" : "Plane workspace pending"}</li>
            <li>{setup.project_id ? "Private Plane project ready" : "Private Plane project pending"}</li>
            <li>{setup.discovery_item_id ? "First discovery task ready" : "First discovery task pending"}</li>
          </ul>
          {setup.project_id && setup.plane_origin && setup.workspace_slug && <a
            className="text-sm underline underline-offset-4"
            href={`${setup.plane_origin}/${encodeURIComponent(setup.workspace_slug)}/projects/${encodeURIComponent(setup.project_id)}/issues/`}
            target="_blank" rel="noreferrer">Open planning project</a>}
          {["blocked", "failed", "unresolved"].includes(setup.status) && <div><Button disabled={retrying} onClick={() => { void retrySetup(); }}>{retrying ? "Requesting retry…" : "Retry setup"}</Button></div>}
          {retryError && <p role="alert">{retryError}</p>}
          <p className="text-xs text-muted-foreground">Setup last updated <time dateTime={setup.updated_at}>{new Date(setup.updated_at).toLocaleString()}</time></p>
          <details><summary className="cursor-pointer text-sm">Setup history</summary><ol className="mt-3 space-y-2 text-sm">{setup.events.map((event) => <li key={event.sequence}><time className="text-muted-foreground" dateTime={event.created_at}>{new Date(event.created_at).toLocaleString()}</time> · {event.message}</li>)}</ol></details>
        </section>}
        <section aria-label="Agent activity" className="space-y-3 rounded-xl border p-5">
          <h2 className="text-lg font-semibold">Activity</h2>
          {agent.work?.events.length ? <ol className="space-y-3 text-sm">{agent.work.events.map((event) => <li key={event.id} className="space-y-1">
            <p className="whitespace-pre-wrap break-words">{event.summary}</p>
            <time className="text-xs text-muted-foreground" dateTime={event.created_at}>{new Date(event.created_at).toLocaleString()}</time>
          </li>)}</ol> : <p>No execution activity recorded yet.</p>}
          <p className="text-sm text-muted-foreground">Created <time dateTime={agent.created_at}>{new Date(agent.created_at).toLocaleString()}</time></p>
        </section>
        <WorkResults key={`results:${agent.id}`} agent={agent} />
        <SavedOutputs key={`outputs:${agent.id}`} agent={agent} />
      </>}
    </div>
  );
}

function WorkControls({ agent, onMutationStart, onUpdate }: {
  agent: Agent;
  onMutationStart: () => void;
  onUpdate: (agent: Agent) => void;
}) {
  const [seconds, setSeconds] = useState("");
  const [steps, setSteps] = useState("");
  const [action, setAction] = useState<"start" | "pause" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const busy = useRef(false);
  const limits = { timeout_seconds: Number(seconds), max_iterations: Number(steps) };
  const work = agent.work;
  const canPause = work && ["queued", "preparing", "running", "stopping"].includes(work.state);

  async function perform(nextAction: "start" | "pause") {
    if (busy.current || (nextAction === "start" && !validWorkLimits(limits))) return;
    busy.current = true;
    setAction(nextAction);
    setError(null);
    onMutationStart();
    try {
      const result = await fetchJSON<Agent>(`${agentsEndpoint}/${encodeURIComponent(agent.id)}/work${nextAction === "pause" ? "/pause" : ""}`, {
        method: "POST",
        ...(nextAction === "start" ? {
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...limits, expected_revision: agent.soul_revision }),
        } : {}),
      });
      onUpdate(result);
    } catch {
      setError(nextAction === "pause"
        ? "Could not confirm Pause. The last confirmed state is still shown; check the connection and retry."
        : "Could not confirm the work request. Check the current status before retrying with the same limits.");
    } finally {
      busy.current = false;
      setAction(null);
    }
  }

  return <section aria-label="Agent work" className="space-y-4 rounded-xl border p-5">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h2 className="text-lg font-semibold">{work ? "Current work" : "Start the first work run"}</h2>
      {canPause && <Button disabled={action !== null} onClick={() => { void perform("pause"); }}>{action === "pause" ? "Requesting pause…" : "Pause"}</Button>}
    </div>
    {work ? <>
      {work.summary && <p className="whitespace-pre-wrap break-words">{work.summary}</p>}
      {work.state === "queued" && agent.setup?.status !== "ready" && <p>The request is saved. Work will begin after the private workspace and Plane project are ready.</p>}
      {work.state === "stopping" && <p role="status">Stopping the current run. Pause will be confirmed after it stops.</p>}
      {work.state === "paused" && <p>The run is paused. It will not restart automatically.</p>}
      {work.state === "completed" && <p>This run has finished. Review its results and saved outputs below. Finishing a run does not mean its work has been accepted.</p>}
      {work.state === "unknown" && <p>The run outcome needs checking before any further work.</p>}
      {work.error && <p role="alert" className="whitespace-pre-wrap break-words">{work.error}</p>}
      <dl className="grid gap-2 text-sm sm:grid-cols-[auto_1fr]">
        <dt className="text-muted-foreground">Run limits</dt><dd>{work.limits.timeout_seconds} seconds · {work.limits.max_iterations} model steps</dd>
        <dt className="text-muted-foreground">Model calls</dt><dd>{work.model_calls}</dd>
        <dt className="text-muted-foreground">Session</dt><dd className="break-all">{work.session_id}</dd>
      </dl>
      <p className="text-xs text-muted-foreground">This is one bounded run. Automatic continuation and resume are not enabled yet.</p>
    </> : <form onSubmit={(event) => { event.preventDefault(); void perform("start"); }} className="space-y-4">
      <p className="text-sm text-muted-foreground">Set both limits to let this agent work on its purpose in its private workspace. Work waits for setup if needed.</p>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2"><Label htmlFor="agent-run-seconds">Maximum run time (seconds)</Label><Input id="agent-run-seconds" type="number" min={1} max={3600} step={1} required disabled={action !== null} value={seconds} onChange={(event) => setSeconds(event.target.value)} /></div>
        <div className="space-y-2"><Label htmlFor="agent-run-steps">Maximum model steps</Label><Input id="agent-run-steps" type="number" min={1} max={100} step={1} required disabled={action !== null} value={steps} onChange={(event) => setSteps(event.target.value)} /></div>
      </div>
      <Button type="submit" disabled={action !== null || !validWorkLimits(limits)}>{action === "start" ? "Requesting work…" : "Start work"}</Button>
    </form>}
    {error && <p role="alert">{error}</p>}
  </section>;
}

function WorkResults({ agent }: { agent: Agent }) {
  const results = agent.work?.results ?? [];
  const labels: Record<WorkResult["outcome"], string> = {
    submitted: "Submitted for review", discovery: "Discovery", waiting: "Waiting", blocked: "Blocked",
  };
  return <section aria-label="Work results" className="space-y-4 rounded-xl border p-5">
    <h2 className="text-lg font-semibold">Results</h2>
    {!results.length && <p>No results recorded yet.</p>}
    {results.map((result) => <article key={result.id} className="space-y-3 rounded-lg border p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold">{labels[result.outcome]}</h3>
        <time className="text-xs text-muted-foreground" dateTime={result.created_at}>{new Date(result.created_at).toLocaleString()}</time>
      </div>
      <p className="whitespace-pre-wrap break-words">{result.summary}</p>
      <section aria-label="Agent evaluation" className="space-y-2 text-sm">
        <h4 className="font-semibold">Agent evaluation</h4>
        <pre className="whitespace-pre-wrap break-words font-sans">{result.evaluation.report}</pre>
        <p className="text-muted-foreground">This is the agent’s assessment. Acceptance has not been evaluated.</p>
      </section>
      {result.outputs.length ? <ul className="space-y-1 text-sm">{result.outputs.map((output) => {
        const metadata = agent.work?.outputs.find((item) => item.output_id === output.output_id && item.version === output.version);
        return <li key={`${output.output_id}:${output.version}`}><Link className="underline underline-offset-4" to={outputVersionLink(agent.id, output)}>
          {metadata?.title ?? "Saved output"} · Version {output.version}
        </Link></li>;
      })}</ul> : <p className="text-sm text-muted-foreground">No saved outputs for this result.</p>}
      <PlanningItemLink agent={agent} itemId={result.item_id} />
    </article>)}
  </section>;
}

function PlanningItemLink({ agent, itemId }: { agent: Agent; itemId: string }) {
  const setup = agent.setup;
  if (!setup?.plane_origin || !setup.workspace_slug || !setup.project_id) return null;
  return <a className="inline-block text-sm underline underline-offset-4" target="_blank" rel="noreferrer"
    href={`${setup.plane_origin}/${encodeURIComponent(setup.workspace_slug)}/projects/${encodeURIComponent(setup.project_id)}/issues/${encodeURIComponent(itemId)}/`}>Open work item</a>;
}

function SavedOutputs({ agent }: { agent: Agent }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const outputs = agent.work?.outputs ?? [];
  const outputId = searchParams.get("output");
  const version = searchParams.get("version");
  const hasSelection = outputId !== null || version !== null;
  const uniqueSelection = searchParams.getAll("output").length === 1 && searchParams.getAll("version").length === 1;

  function select(output: OutputReference | null) {
    setSearchParams((previous) => {
      const next = new URLSearchParams(previous);
      next.delete("output");
      next.delete("version");
      if (output) { next.set("output", output.output_id); next.set("version", String(output.version)); }
      return next;
    });
  }

  return <section aria-label="Saved outputs" className="space-y-4 rounded-xl border p-5">
    <h2 className="text-lg font-semibold">Saved outputs</h2>
    {!outputs.length && <p>No output versions saved yet.</p>}
    <div className="space-y-4">{outputs.map((output) => <article key={`${output.output_id}:${output.version}`} className="space-y-2 rounded-lg border p-4">
      <h3 className="font-semibold">{output.title} · Version {output.version}</h3>
      <p className="text-xs text-muted-foreground">{output.format === "markdown" ? "Markdown" : "Plain text"} · <time dateTime={output.created_at}>{new Date(output.created_at).toLocaleString()}</time></p>
      <p className="break-all text-xs text-muted-foreground">{output.relative_path}</p>
      <PlanningItemLink agent={agent} itemId={output.item_id} />
      <div><Button onClick={() => select(output)}>Read output</Button></div>
    </article>)}</div>
    {hasSelection && <OutputReader key={`${outputId}:${version}:${uniqueSelection}`} agentId={agent.id}
      outputId={outputId} requestedVersion={version} uniqueSelection={uniqueSelection} onClose={() => select(null)} />}
  </section>;
}

type LoadedOutput = { key: string; output?: OutputVersion; error?: boolean };

function OutputReader({ agentId, outputId, requestedVersion, uniqueSelection, onClose }: {
  agentId: string; outputId: string | null; requestedVersion: string | null; uniqueSelection: boolean; onClose: () => void;
}) {
  const [retry, setRetry] = useState(0);
  const [loaded, setLoaded] = useState<LoadedOutput | null>(null);
  const version = Number(requestedVersion);
  const validSelection = uniqueSelection && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(outputId ?? "")
    && /^[1-9][0-9]*$/.test(requestedVersion ?? "") && Number.isSafeInteger(version);
  const key = `${agentId}:${outputId}:${requestedVersion}:${retry}`;
  const current = loaded?.key === key ? loaded : null;

  useEffect(() => {
    if (!validSelection) return;
    let active = true;
    void fetchJSON<OutputVersion>(`${agentsEndpoint}/${encodeURIComponent(agentId)}/outputs/${encodeURIComponent(outputId ?? "")}/versions/${version}`)
      .then((result) => {
        if (result.agent_id !== agentId || result.output_id !== outputId || result.version !== version || typeof result.content !== "string"
            || !["markdown", "text"].includes(result.format)) throw new Error("Output version does not match");
        if (active) setLoaded({ key, output: result });
      })
      .catch(() => { if (active) setLoaded({ key, error: true }); });
    return () => { active = false; };
  }, [agentId, outputId, version, validSelection, key]);

  if (!validSelection || current?.error) return <div className="space-y-3 border-t pt-5">
    <p role="alert">Could not load or verify this output version. Check the link, connection and sign-in, then retry.</p>
    <div className="flex gap-2"><Button onClick={() => setRetry((value) => value + 1)}>Retry output</Button><Button onClick={onClose}>Close output</Button></div>
  </div>;
  if (!current?.output) return <p role="status">Loading output…</p>;
  const output = current.output;
  return <article aria-label="Output reader" className="space-y-4 border-t pt-5">
    <div className="flex items-start justify-between gap-3"><h3 className="text-xl font-semibold">{output.title} · Version {output.version}</h3><Button onClick={onClose}>Close output</Button></div>
    <a className="inline-block text-sm underline underline-offset-4" href={outputVersionLink(agentId, output)}>Link to this version</a>
    {output.format === "markdown" ? <Markdown content={output.content} /> : <pre className="whitespace-pre-wrap break-words text-sm">{output.content}</pre>}
    {output.evaluation != null && <section aria-label="Saved version evaluation" className="space-y-2 border-t pt-4">
      <h4 className="font-semibold">Agent evaluation</h4>
      <p className="text-xs text-muted-foreground">The agent’s assessment of this saved version. Acceptance has not been evaluated.</p>
      <pre className="whitespace-pre-wrap break-words text-sm">{typeof output.evaluation === "string" ? output.evaluation : typeof output.evaluation.report === "string" ? output.evaluation.report : JSON.stringify(output.evaluation, null, 2)}</pre>
    </section>}
  </article>;
}
