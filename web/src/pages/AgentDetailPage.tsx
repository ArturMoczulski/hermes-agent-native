import { AgentCadence } from '@/components/AgentCadence';
import { WorkQuestions } from '@/components/WorkQuestions';
import { WorkFeedback } from '@/components/WorkFeedback';
import { AgentProgressSettings } from "@/components/AgentProgressSettings";
import { AgentAutonomySettings } from "@/components/AgentAutonomySettings";
import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Link, useLocation, useParams, useSearchParams } from "react-router";
import { Button } from "@nous-research/ui/ui/components/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@nous-research/ui/ui/components/dialog";
import { agentsEndpoint, agentWorkStatus, validWorkLimits, validModelChoice, outputVersionLink, type Agent, type OutputReference, type OutputVersion, type WorkResult, modelChoiceLabel } from "@/lib/agent-native";
import { Input } from "@nous-research/ui/ui/components/input";
import { Label } from "@nous-research/ui/ui/components/label";
import { Markdown } from "@/components/Markdown";
import { fetchJSON } from "@/lib/api";
import PlanningWork from "./PlanningWork";
import { AgentModelControls } from "@/components/AgentModelControls";
import { usePageHeader } from "@/contexts/usePageHeader";
import { Settings, SquareKanban } from "lucide-react";

type LoadedAgent = { key: string; agent?: Agent; error?: string };

export default function AgentDetailPage() {
  const { agentId } = useParams<{ agentId: string }>();
  const [pageSearchParams] = useSearchParams();
  const fullView = pageSearchParams.get("view") === "full";
  const { setTitle } = usePageHeader();
  const [retryError, setRetryError] = useState<string | null>(null);
  const [removing, setRemoving] = useState(false);
  const [confirmRemove, setConfirmRemove] = useState(false);
  const [removeError, setRemoveError] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [refreshError, setRefreshError] = useState(false);
  const [reload, setReload] = useState(0);
  const [settingsOpen, setSettingsOpen] = useState(false);
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
  async function removeAgent() {
    setRemoving(true); setRemoveError(false); mutationVersion.current += 1;
    try {
      const result = await fetchJSON<Agent>(`${agentsEndpoint}/${encodeURIComponent(agentId ?? "")}`, { method: "DELETE" });
      mutationVersion.current += 1;
      setLoaded({ key, agent: result }); setConfirmRemove(false);
    } catch { setRemoveError(true); }
    finally { setRemoving(false); }
  }
  const setup = agent?.setup;
  const setupTitles = { queued: "Setup queued", preparing: "Preparing agent", blocked: "Plane setup required", failed: "Setup needs attention", unresolved: "Setup outcome needs checking", ready: "Workspace and planning ready", superseded: "Setup superseded" };
  const startup = agent?.startup;
  const staleRequest = startup && startup.soul_revision !== agent?.soul_revision;
  const planeUrl = agent?.setup?.project_id && agent.setup.plane_origin && agent.setup.workspace_slug
    ? `${agent.setup.plane_origin}/${encodeURIComponent(agent.setup.workspace_slug)}/projects/${encodeURIComponent(agent.setup.project_id)}/issues/`
    : null;

  return (
    <div className="mx-auto w-full max-w-4xl space-y-6 p-6">
      <Link to="/agents" className="text-sm underline underline-offset-4">All agents</Link>
      {!current && <p role="status">Loading agent…</p>}
      {current?.error && <div role="alert" className="space-y-3"><p>{current.error}</p><Button onClick={() => setReload((value) => value + 1)}>Retry</Button></div>}
      {agent && <>
        {refreshError && <p role="alert">Live updates are disconnected. Showing the last confirmed state; reconnect to see current progress.</p>}
        <header className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-semibold">{agent.name}</h1>
              {!agent.removed_at && <IconTooltip label="Agent settings">
                <Button size="icon" className="size-10 border border-border bg-background text-foreground shadow-sm hover:bg-muted" aria-label="Agent settings" onClick={() => setSettingsOpen(true)}><Settings className="size-5" strokeWidth={2.5} aria-hidden="true" /></Button>
              </IconTooltip>}
              {planeUrl && <IconTooltip label="Open project in Plane">
                <a className="inline-flex size-10 items-center justify-center rounded-md border border-border bg-background text-foreground shadow-sm hover:bg-muted" href={planeUrl} target="_blank" rel="noreferrer" aria-label="Open project in Plane"><SquareKanban className="size-5" strokeWidth={2.5} aria-hidden="true" /></a>
              </IconTooltip>}
            </div>
            <span aria-label="Execution status" className="rounded-full border px-3 py-1 text-sm">{agentWorkStatus(agent)}</span>
          </div>
          <p className="break-all text-xs text-muted-foreground">Root agent · {agent.id}</p>
          <div className="flex flex-wrap gap-2">
            {!agent.removed_at && <Link className="inline-block rounded-md border px-4 py-2 text-sm underline-offset-4 hover:underline" to={`/agents/${encodeURIComponent(agent.id)}/chat`}>Chat with agent</Link>}
            <Link className="inline-block rounded-md border px-4 py-2 text-sm underline-offset-4 hover:underline"
              to={fullView ? `/agents/${encodeURIComponent(agent.id)}` : `/agents/${encodeURIComponent(agent.id)}?view=full`}>
              {fullView ? "Compact view" : "Full view"}
            </Link>
          </div>
        </header>
        {!fullView ? <CompactAgentView agent={agent} /> : <>
        {agent.removed_at ? <p role="status">Agent removed. Autonomous work and conversations are disabled; history is retained. {agent.work?.state === 'stopping' && 'The existing work process is still stopping.'}</p> : <section aria-label="Remove agent" className="space-y-3 rounded-xl border p-5">
          <Button onClick={() => setConfirmRemove(true)}>Remove agent</Button>
          {confirmRemove && <div className="space-y-3">
            <p>Remove this agent and stop its work? This cannot be undone.</p>
            <p>History, saved outputs and Plane records are retained.</p>
            <Button disabled={removing} onClick={() => { void removeAgent(); }}>{removing ? "Removing…" : "Confirm removal"}</Button>
            <Button disabled={removing} onClick={() => setConfirmRemove(false)}>Cancel</Button>
          </div>}
          {removeError && <p role="alert">Could not confirm removal. Reload or retry; repeating removal is safe.</p>}
        </section>}
        {!agent.removed_at && <><AgentModelControls key={`model:${agent.id}`} agent={agent}
          onMutationStart={() => { mutationVersion.current += 1; }}
          onUpdate={(result) => {
            mutationVersion.current += 1;
            setLoaded((previous) => previous.key === key ? { key, agent: result } : previous);
          }} />
        <AgentProgressSettings key={`progress-settings:${agent.id}`} agentId={agent.id} />
        <AgentAutonomySettings key={`autonomy:${agent.id}`} agentId={agent.id} />
        <WorkControls key={`work:${agent.id}`} agent={agent}
          onMutationStart={() => { mutationVersion.current += 1; }}
          onUpdate={(result) => {
            mutationVersion.current += 1;
            setLoaded((previous) => previous.key === key ? { key, agent: result } : previous);
          }} />
        <AgentCadence key={`cadence:${agent.id}:${agent.soul_revision}`} agentId={agent.id} revision={agent.soul_revision} />
        <WorkQuestions key={`questions:${agent.id}:${agent.soul_revision}`} agentId={agent.id} revision={agent.soul_revision} setup={agent.setup} />
        <WorkFeedback key={`feedback:${agent.id}:${agent.soul_revision}`} agentId={agent.id} revision={agent.soul_revision} />
        </>}
        <PlanningWork key={`planning:${agent.id}:${agent.soul_revision}:${agent.setup?.activation_id}`} agent={agent} />
        {agent.work && <section aria-label="Plane progress" className="space-y-3 rounded-xl border p-5">
          <h2 className="text-lg font-semibold">Plane progress</h2>
          <p className="text-sm text-muted-foreground">Latest 20 progress updates. Confirmed means Plane acknowledged the comment. Unknown delivery is not retried automatically.</p>
          {agent.work.progress?.length ? <div className="overflow-x-auto"><table className="w-full text-left text-sm">
            <thead><tr><th className="p-2">Time</th><th className="p-2">Update</th><th className="p-2">Delivery</th></tr></thead>
            <tbody>{agent.work.progress.map((report) => <tr key={report.operation_id} className="border-t">
              <td className="p-2"><time dateTime={report.created_at}>{new Date(report.created_at).toLocaleString()}</time></td>
              <td className="p-2">{report.summary}{report.link_url && <a className="block underline underline-offset-4" href={report.link_url}>{report.link_label}</a>}</td>
              <td className="p-2">{{ pending: "Pending", confirmed: "Confirmed", failed: "Failed", unknown: "Unknown — inspect before resending" }[report.status]}</td>
            </tr>)}</tbody>
          </table></div> : <p className="text-sm">No progress updates recorded for this attempt.</p>}
        </section>}
        {!!agent.work?.output_sections?.length && <section aria-label="Pending Plane output sections" className="space-y-3 rounded-xl border p-5">
          <h2 className="text-lg font-semibold">Description update pending</h2>
          <p className="text-sm text-muted-foreground">Plane cannot protect description updates against simultaneous edits. Your descriptions are left untouched. Saved references are available below; comment delivery is tracked separately above.</p>
          {agent.work.output_sections.map(section => <details key={section.item_id} className="rounded border p-3">
            <summary className="cursor-pointer">Review output references · Work item {section.item_id}</summary>
            <p className="my-2 text-sm">This section has not been added to Plane. Review it alongside the current work item before incorporating references manually.</p>
            <ul className="space-y-2 text-sm">{section.entries.map(entry => <li key={entry.source_id}>
              {entry.link_url ? <a className="underline underline-offset-4" href={entry.link_url}>{entry.link_label}</a> : entry.summary}
            </li>)}</ul>
            <label className="mt-3 block text-sm">Output references
              <textarea readOnly value={section.text} rows={8} className="mt-1 w-full rounded border bg-background p-2 text-sm" />
            </label>
          </details>)}
        </section>}
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
        {!agent.removed_at && <AgentSettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} agent={agent}
          onMutationStart={() => { mutationVersion.current += 1; }}
          onUpdate={(result) => {
            mutationVersion.current += 1;
            setLoaded((previous) => previous.key === key ? { key, agent: result } : previous);
          }} />}
      </>}
    </div>
  );
}

function IconTooltip({ label, children }: { label: string; children: ReactNode }) {
  return <span className="group relative inline-flex">
    {children}
    <span role="tooltip" className="pointer-events-none absolute left-1/2 top-full z-50 mt-2 -translate-x-1/2 whitespace-nowrap rounded-md bg-foreground px-2 py-1 text-xs text-background opacity-0 shadow-md transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
      {label}
    </span>
  </span>;
}

function CompactAgentView({ agent }: { agent: Agent }) {
  const work = agent.work;
  const events = (work?.events ?? []).filter((event) =>
    event.kind !== "work.model"
    && !event.summary.startsWith("Model step ")
    && !event.summary.startsWith("Plane: inspected ")
  ).reverse().slice(0, 20);
  return <div className="space-y-6">
    <ProgressConcernAttention agent={agent} />
    <WorkResults agent={agent} attentionOnly />
    {!agent.removed_at && <WorkQuestions key={`compact-questions:${agent.id}:${agent.soul_revision}`} agentId={agent.id} revision={agent.soul_revision} setup={agent.setup} attentionOnly />}
    <div aria-label="Current agent summary" className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
      {work && <span>Latest attempt: {work.state.replace('_', ' ')}</span>}
      {work?.focus && <><span aria-hidden="true">·</span><span>{["running", "queued", "preparing", "stopping"].includes(work.state) ? "Current" : "Latest"} work:</span>
        <PlanningItemLink agent={agent} itemId={work.focus.item_id} label={work.focus.name} /></>}
    </div>
    <SavedOutputs key={`compact-outputs:${agent.id}`} agent={agent} limit={3} compact />
    <section aria-label="Recent activity" className="space-y-3 rounded-xl border p-5">
      <h2 className="text-lg font-semibold">Recent activity</h2>
      {events.length ? <div className="overflow-x-auto"><table className="w-full text-left text-sm">
        <thead><tr><th className="p-2">Time</th><th className="p-2">Activity</th></tr></thead>
        <tbody>{events.map(event => <tr key={event.id} className="border-t">
          <td className="whitespace-nowrap p-2"><time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString()}</time></td>
          <td className="p-2">{event.summary}</td>
        </tr>)}</tbody>
      </table></div> : <p>No execution activity recorded yet.</p>}
      <Link className="inline-block text-sm underline underline-offset-4" to={`/agents/${encodeURIComponent(agent.id)}?view=full`}>View complete activity and diagnostics</Link>
    </section>
  </div>;
}

function ProgressConcernAttention({ agent }: { agent: Agent }) {
  const concern = agent.progress_concerns?.find((entry) => entry.status === "open");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  if (!concern && !status) return null;
  async function resume() {
    if (!concern || busy) return;
    setBusy(true); setError("");
    try {
      await fetchJSON(agentsEndpoint + "/" + encodeURIComponent(agent.id) + "/progress-concerns/" + encodeURIComponent(concern.id) + "/resume", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ expected_revision: agent.soul_revision, request_id: crypto.randomUUID() }),
      });
      setStatus("Automatic work resumed. The next attempt will use current purpose and project state.");
    } catch {
      setError("Could not confirm resume. Reload the agent before trying again.");
    } finally { setBusy(false); }
  }
  return <section aria-label="Needs your attention" className="space-y-3 rounded-xl border border-amber-500/50 bg-amber-500/5 p-5">
    <h2 className="text-lg font-semibold">Needs your attention</h2>
    {concern && <>
      <h3 className="font-medium">Repeated work without progress</h3>
      <p>{concern.summary}</p>
      <p className="text-sm text-muted-foreground">{concern.attempt_ids.length} consecutive attempts are linked as evidence. Automatic work is suspended.</p>
      <details className="rounded border p-3 text-sm"><summary className="cursor-pointer">Review supporting attempts</summary>
        <ul className="mt-2 space-y-1">{concern.attempt_ids.map((attemptId) => <li key={attemptId}><code className="break-all">{attemptId}</code></li>)}</ul>
      </details>
      <Button disabled={busy} onClick={() => { void resume(); }}>{busy ? "Resuming…" : "Resume automatic work"}</Button>
    </>}
    {status && <p role="status">{status}</p>}
    {error && <p role="alert">{error}</p>}
  </section>;
}

function AgentSettingsDialog({ open, onOpenChange, agent, onMutationStart, onUpdate }: {
  open: boolean; onOpenChange: (open: boolean) => void; agent: Agent;
  onMutationStart: () => void; onUpdate: (agent: Agent) => void;
}) {
  return <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] max-w-3xl overflow-y-auto">
        <DialogHeader><DialogTitle>Agent settings</DialogTitle><DialogDescription>Changes apply to this agent. Current work keeps the settings it started with.</DialogDescription></DialogHeader>
        <AgentModelControls agent={agent} onMutationStart={onMutationStart} onUpdate={onUpdate} />
        <AgentProgressSettings agentId={agent.id} />
        <AgentAutonomySettings agentId={agent.id} />
        <AssignmentReviewSettings key={`${agent.work?.focus?.item_id}:${agent.assignment_review_policies?.find(value=>value.item_id===agent.work?.focus?.item_id)?.revision??0}`} agent={agent} onUpdate={onUpdate} />
        <AgentCadence agentId={agent.id} revision={agent.soul_revision} />
      </DialogContent>
    </Dialog>;
}

function AssignmentReviewSettings({agent,onUpdate}:{agent:Agent;onUpdate:(agent:Agent)=>void}) {
  const focus=agent.work?.focus;
  const policy=focus ? agent.assignment_review_policies?.find(value=>value.item_id===focus.item_id) : undefined;
  const [required,setRequired]=useState(policy?.required??false);
  const [busy,setBusy]=useState(false);
  const [message,setMessage]=useState("");
  async function save(){
    if(!agent.work||!focus||busy)return;
    setBusy(true);setMessage("");
    try{
      const updated=await fetchJSON<Agent>(`${agentsEndpoint}/${encodeURIComponent(agent.id)}/assignment-review`,{
        method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({
          run_id:agent.work.id,required,expected_revision:policy?.revision??0})});
      onUpdate(updated);setMessage("Saved for this exact observed assignment revision.");
    }catch{setMessage("Could not save. The assignment or policy may have changed; reload and try again.");}
    finally{setBusy(false);}
  }
  return <section aria-label="Assignment review settings" className="space-y-3 rounded-xl border p-5">
    <h2 className="text-lg font-semibold">Current assignment review</h2>
    {!focus?<p className="text-sm text-muted-foreground">Available after the agent selects a Plane work item.</p>:<>
      <p className="text-sm">{focus.name}</p>
      <label className="flex items-start gap-3 text-sm"><input type="checkbox" className="mt-1" checked={required} disabled={busy}
        onChange={event=>{setRequired(event.target.checked);setMessage("");}} />
        <span><strong>Require owner review for this assignment</strong><br/><span className="text-muted-foreground">Bound to the currently observed Plane work-item revision. Assignment changes require refreshing this policy.</span></span>
      </label>
      <Button disabled={busy||required===(policy?.required??false)} onClick={()=>void save()}>Save assignment review</Button>
    </>}
    {message&&<p role="status" className="text-sm">{message}</p>}
  </section>;
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
    if (busy.current || (nextAction === "start" && (!validWorkLimits(limits) || !validModelChoice(agent.model_selection)))) return;
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
      {work.state === "interrupted" && <p>The previous process was interrupted after its effects settled. If thinking cadence is enabled, it will continue in a fresh attempt.</p>}
      {work.state === "retryable_failure" && <p>The attempt failed after its effects settled. Thinking cadence will continue with a fresh attempt; the failed attempt remains in history.</p>}
      {work.state === "limit_reached" && <p>This bounded attempt reached its configured limit. If thinking cadence is enabled, the next check-in can continue the work in a new attempt.</p>}
      {work.state === "completed" && <p>This run has finished. Review its results and saved outputs below. Finishing a run does not mean its work has been accepted.</p>}
      {work.state === "unknown" && <p>The run outcome needs checking before any further work.</p>}
      {work.error && <p role="alert" className="whitespace-pre-wrap break-words">{work.error}</p>}
      <dl className="grid gap-2 text-sm sm:grid-cols-[auto_1fr]">
        <dt className="text-muted-foreground">Run limits</dt><dd>{work.limits.timeout_seconds} seconds · {work.limits.max_iterations} model steps</dd>
        <dt className="text-muted-foreground">Run model</dt><dd className="break-words">{work.model_selection ? modelChoiceLabel(work.model_selection) : "Not recorded for this run"}</dd>
        <dt className="text-muted-foreground">Model calls</dt><dd>{work.model_calls}</dd>
        <dt className="text-muted-foreground">Session</dt><dd className="break-all">{work.session_id}</dd>
      </dl>
      <p className="text-xs text-muted-foreground">Each attempt is bounded. Configure Thinking cadence for automatic check-ins after completed work or a normal run limit.</p>
    </> : <form onSubmit={(event) => { event.preventDefault(); void perform("start"); }} className="space-y-4">
      <p className="text-sm text-muted-foreground">Set both limits to let this agent work on its purpose in its private workspace. Work waits for setup if needed.</p>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2"><Label htmlFor="agent-run-seconds">Maximum run time (seconds)</Label><Input id="agent-run-seconds" type="number" min={1} max={3600} step={1} required disabled={action !== null} value={seconds} onChange={(event) => setSeconds(event.target.value)} /></div>
        <div className="space-y-2"><Label htmlFor="agent-run-steps">Maximum model steps</Label><Input id="agent-run-steps" type="number" min={1} max={100} step={1} required disabled={action !== null} value={steps} onChange={(event) => setSteps(event.target.value)} /></div>
      </div>
      {!validModelChoice(agent.model_selection) && <p className="text-sm">Choose a configured model before starting work.</p>}
      <Button type="submit" disabled={action !== null || !validWorkLimits(limits) || !validModelChoice(agent.model_selection)}>{action === "start" ? "Requesting work…" : "Start work"}</Button>
    </form>}
    {error && <p role="alert">{error}</p>}
  </section>;
}

function WorkResults({ agent, attentionOnly = false }: { agent: Agent; attentionOnly?: boolean }) {
  const allResults = agent.work?.results ?? [];
  const results = attentionOnly
    ? allResults.filter((result) => result.review.required && result.acceptance === "not_evaluated")
    : allResults;
  const { hash } = useLocation();
  const selectedId = results.find(result => hash === `#result-${result.id}`)?.id;
  useEffect(() => {
    if (selectedId) document.getElementById(`result-${selectedId}`)?.scrollIntoView({ block: "start" });
  }, [selectedId, hash]);
  if (attentionOnly && !results.length) return null;
  const labels: Record<Exclude<WorkResult["outcome"], "submitted">, string> = {
    discovery: "Discovery", waiting: "Waiting", blocked: "Blocked",
  };
  return <section aria-label={attentionOnly ? "Needs your decision" : "Work results"} className={`space-y-4 rounded-xl border p-5 ${attentionOnly ? "border-amber-500/60 bg-amber-500/5" : ""}`}>
    <h2 className="text-lg font-semibold">{attentionOnly ? "Needs your decision" : "Results"}</h2>
    {!results.length && <p>No results recorded yet.</p>}
    {results.map((result) => <ResultCard key={result.id} agent={agent} result={result}
      label={result.outcome === "submitted" ? (result.review.required ? "Awaiting owner review" : "Submitted deliverable") : labels[result.outcome]} />)}
  </section>;
}

function ResultCard({ agent, result, label }: { agent: Agent; result: WorkResult; label: string }) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function decide(decision: "accepted" | "revision_requested") {
    if (busy || (decision === "revision_requested" && !note.trim())) return;
    setBusy(true); setMessage("");
    try {
      await fetchJSON<Agent>(`${agentsEndpoint}/${encodeURIComponent(agent.id)}/results/${encodeURIComponent(result.id)}/decision`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request_id: crypto.randomUUID(), decision, ...(decision === "revision_requested" ? { note: note.trim() } : {}) }),
      });
      setMessage(decision === "accepted" ? "Accepted this exact result and its listed output versions." : "Revision requested. The agent will receive this as trusted feedback on its next cadence attempt.");
    } catch { setMessage("Could not confirm this decision. Reload the result before retrying."); }
    finally { setBusy(false); }
  }
  return <article id={`result-${result.id}`} className="space-y-3 rounded-lg border p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold">{label}</h3>
        <time className="text-xs text-muted-foreground" dateTime={result.created_at}>{new Date(result.created_at).toLocaleString()}</time>
      </div>
      <p className="whitespace-pre-wrap break-words">{result.summary}</p>
      <section aria-label="Agent evaluation" className="space-y-2 text-sm">
        <h4 className="font-semibold">Agent evaluation</h4>
        <pre className="whitespace-pre-wrap break-words font-sans">{result.evaluation.report}</pre>
        <p className="text-muted-foreground">This is the agent’s assessment. {result.acceptance === "accepted" ? "The owner accepted this exact result." : result.acceptance === "revision_requested" ? "The owner requested a revision." : result.review.required ? "An owner decision is required for this deliverable." : "No owner decision is required."}</p>
      </section>
      {result.outputs.length ? <ul className="space-y-1 text-sm">{result.outputs.map((output) => {
        const metadata = agent.work?.outputs.find((item) => item.output_id === output.output_id && item.version === output.version);
        return <li key={`${output.output_id}:${output.version}`}><Link className="underline underline-offset-4" to={outputVersionLink(agent.id, output)}>
          {metadata?.title ?? "Saved output"} · Version {output.version}
        </Link></li>;
      })}</ul> : <p className="text-sm text-muted-foreground">No saved outputs for this result.</p>}
      <PlanningItemLink agent={agent} itemId={result.item_id} />
      {result.acceptance === "not_evaluated" && result.review.required ? <section aria-label="Owner result decision" className="space-y-3 border-t pt-3">
        {result.review.reason && <p className="text-sm font-medium">{result.review.reason}</p>}
        <p className="text-sm">Accepting applies only to this result and the output versions listed above.</p>
        <div className="flex flex-wrap gap-2"><Button disabled={busy} onClick={() => void decide("accepted")}>Accept result</Button></div>
        <label className="block text-sm">Revision instructions
          <textarea value={note} onChange={event => setNote(event.target.value)} disabled={busy} maxLength={4000} rows={3} className="mt-1 w-full rounded border bg-background p-2" />
        </label>
        <Button disabled={busy || !note.trim()} onClick={() => void decide("revision_requested")}>Request revision</Button>
      </section> : result.owner_decision?.note ? <p className="whitespace-pre-wrap text-sm">Owner note: {result.owner_decision.note}</p> : null}
      {message && <p role="status" className="text-sm">{message}</p>}
    </article>;
}

function PlanningItemLink({ agent, itemId, label = "Open work item" }: { agent: Agent; itemId: string; label?: string }) {
  const setup = agent.setup;
  if (!setup?.plane_origin || !setup.workspace_slug || !setup.project_id) return null;
  return <a className="inline-block text-sm underline underline-offset-4" target="_blank" rel="noreferrer"
    href={`${setup.plane_origin}/${encodeURIComponent(setup.workspace_slug)}/projects/${encodeURIComponent(setup.project_id)}/issues/${encodeURIComponent(itemId)}/`}>{label}</a>;
}

function SavedOutputs({ agent, limit, compact = false }: { agent: Agent; limit?: number; compact?: boolean }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const allOutputs = agent.work?.outputs ?? [];
  const outputs = limit == null ? allOutputs : allOutputs.slice(0, limit);
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

  const label = compact ? "Recent outputs" : "Saved outputs";
  return <section aria-label={label} className="space-y-4 rounded-xl border p-5">
    <h2 className="text-lg font-semibold">{label}</h2>
    {!outputs.length && <p>No output versions saved yet.</p>}
    <div className="space-y-4">{outputs.map((output) => <article key={`${output.output_id}:${output.version}`} className="space-y-2 rounded-lg border p-4">
      <h3 className="font-semibold">{output.title} · Version {output.version}</h3>
      <p className="text-xs text-muted-foreground">{output.format === "markdown" ? "Markdown" : "Plain text"} · <time dateTime={output.created_at}>{new Date(output.created_at).toLocaleString()}</time></p>
      {!compact && <p className="break-all text-xs text-muted-foreground">{output.relative_path}</p>}
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
