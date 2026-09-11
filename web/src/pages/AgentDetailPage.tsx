import { AgentCadence } from '@/components/AgentCadence';
import { WorkQuestions } from '@/components/WorkQuestions';
import { WorkFeedback } from '@/components/WorkFeedback';
import { AgentProgressSettings } from "@/components/AgentProgressSettings";
import { AgentAutonomySettings } from "@/components/AgentAutonomySettings";
import { useEffect, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { Link, useLocation, useNavigate, useParams, useSearchParams } from "react-router";
import { Button } from "@nous-research/ui/ui/components/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@nous-research/ui/ui/components/dialog";
import { agentsEndpoint, agentWaitingForOwner, agentWorkStatus, validWorkLimits, validModelChoice, outputVersionLink, type Agent, type MediaOutput, type OutputReference, type OutputVersion, type WorkResult, type UsageTotals, modelChoiceLabel } from "@/lib/agent-native";
import { Input } from "@nous-research/ui/ui/components/input";
import { Label } from "@nous-research/ui/ui/components/label";
import { Markdown } from "@/components/Markdown";
import { authedFetch, fetchJSON } from "@/lib/api";
import PlanningWork from "./PlanningWork";
import { AgentModelControls } from "@/components/AgentModelControls";
import { usePageHeader } from "@/contexts/usePageHeader";
import { MonitorPlay, Pause, Play, Settings, SquareKanban } from "lucide-react";

type LoadedAgent = { key: string; agent?: Agent; error?: string };

export default function AgentDetailPage() {
  const { agentId } = useParams<{ agentId: string }>();
  const [pageSearchParams] = useSearchParams();
  const fullView = pageSearchParams.get("view") === "full";
  const requestedTab = pageSearchParams.get("tab");
  const activeTab = requestedTab === "activity" || requestedTab === "settings" ? requestedTab : "work";
  const { setTitle } = usePageHeader();
  const navigate = useNavigate();
  const [retryError, setRetryError] = useState<string | null>(null);
  const [removing, setRemoving] = useState(false);
  const [confirmRemove, setConfirmRemove] = useState(false);
  const [removeError, setRemoveError] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [refreshError, setRefreshError] = useState(false);
  const [reload, setReload] = useState(0);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [resumeNotice, setResumeNotice] = useState<string | null>(null);
  const [togglingAutomaticWork, setTogglingAutomaticWork] = useState(false);
  const [automaticWorkError, setAutomaticWorkError] = useState(false);
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
  const inactive = Boolean(agent?.removed_at || agent?.retirement);

  async function toggleAutomaticWork() {
    if (!agent || inactive || togglingAutomaticWork) return;
    const ownPause = agent.pause?.sources.some((source) => source.source_agent_id === agent.id);
    if (agent.pause?.paused && !ownPause) return;
    setTogglingAutomaticWork(true); setAutomaticWorkError(false); mutationVersion.current += 1;
    try {
      if (!agent.pause?.paused && !agent.cadence?.enabled) {
        const cadence = await fetchJSON<NonNullable<Agent["cadence"]>>(`${agentsEndpoint}/${encodeURIComponent(agent.id)}/cadence`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ expected_revision: agent.soul_revision, interval_seconds: agent.cadence?.interval_seconds ?? 60, enabled: true }),
        });
        const refreshed = await fetchJSON<Agent>(`${agentsEndpoint}/${encodeURIComponent(agent.id)}`);
        mutationVersion.current += 1;
        setLoaded((previous) => previous.key === key && previous.agent
          ? { key, agent: { ...refreshed, cadence } } : previous);
        setResumeNotice("Automatic work enabled. Waiting dependencies still apply and resolving one will wake the agent.");
      } else {
        const result = await fetchJSON<Agent>(`${agentsEndpoint}/${encodeURIComponent(agent.id)}/work/${agent.pause?.paused ? "resume" : "pause"}`, { method: "POST" });
        mutationVersion.current += 1;
        setLoaded((previous) => previous.key === key ? { key, agent: result } : previous);
        if (agent.pause?.paused) {
          const resumed = result.subtree_resume?.resumed_agent_ids.length ?? 0;
          const retained = result.subtree_resume?.still_paused_agent_ids.length ?? 0;
          setResumeNotice(`Automatic work resumed for ${resumed} agent${resumed === 1 ? "" : "s"}.${retained ? ` ${retained} independently paused descendant${retained === 1 ? " remains" : "s remain"} paused.` : ""}`);
        }
      }
    } catch { setAutomaticWorkError(true); }
    finally { setTogglingAutomaticWork(false); }
  }

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
              {!inactive && <IconTooltip label="Agent settings">
                <Button size="icon" className="size-10 border border-border bg-background text-foreground shadow-sm hover:bg-muted" aria-label="Agent settings" onClick={() => setSettingsOpen(true)}><Settings className="size-5" strokeWidth={2.5} aria-hidden="true" /></Button>
              </IconTooltip>}
              {planeUrl && <IconTooltip label="Open project in Plane">
                <a className="inline-flex size-10 items-center justify-center rounded-md border border-border bg-background text-foreground shadow-sm hover:bg-muted" href={planeUrl} target="_blank" rel="noreferrer" aria-label="Open project in Plane"><SquareKanban className="size-5" strokeWidth={2.5} aria-hidden="true" /></a>
              </IconTooltip>}
              {agent.project_preview?.url && <ProjectPreviewButton agentId={agent.id} />}
            </div>
            <div className="flex items-center gap-2">
              <span aria-label="Execution status" className="rounded-full border px-3 py-1 text-sm">{agentWorkStatus(agent)}</span>
              {!fullView && !inactive && <IconTooltip label={agent.pause?.paused ? "Resume automatic work" : agent.cadence?.enabled ? "Pause automatic work" : "Enable automatic work"}>
                <Button size="icon" className="size-10 border border-border bg-background text-foreground shadow-sm hover:bg-muted" disabled={togglingAutomaticWork || Boolean(agent.pause?.paused && !agent.pause.sources.some((source) => source.source_agent_id === agent.id))}
                  aria-label={agent.pause?.paused ? "Resume automatic work" : agent.cadence?.enabled ? "Pause automatic work" : "Enable automatic work"} onClick={() => void toggleAutomaticWork()}>
                  {agent.pause?.paused || !agent.cadence?.enabled ? <Play className="size-5" aria-hidden="true" /> : <Pause className="size-5" aria-hidden="true" />}
                </Button>
              </IconTooltip>}
            </div>
          </div>
          {!fullView && <section aria-label="Agent purpose summary" className="max-w-3xl">
            <p className="text-sm font-medium text-muted-foreground">Purpose</p>
            <p className="whitespace-pre-wrap break-words">{agent.purpose}</p>
          </section>}
          <p className="break-all text-xs text-muted-foreground">{agent.parent_id ? "Child agent" : "Root agent"} · {agent.id}</p>
          {agent.parent_id && <p className="text-sm">Child of <Link className="underline underline-offset-4" to={`/agents/${encodeURIComponent(agent.parent_id)}`}>{agent.parent_id}</Link></p>}
          {agent.child_ids.length > 0 && <p className="text-sm">Children: {agent.child_ids.map((childId, index) => <span key={childId}>{index > 0 && ", "}<Link className="underline underline-offset-4" to={`/agents/${encodeURIComponent(childId)}`}>{childId}</Link></span>)}</p>}
          <div className="flex flex-wrap gap-2">
            {!inactive && <Link className="inline-block rounded-md border px-4 py-2 text-sm underline-offset-4 hover:underline" to={`/agents/${encodeURIComponent(agent.id)}/chat`}>Chat with agent</Link>}
            <Link className="inline-block rounded-md border px-4 py-2 text-sm underline-offset-4 hover:underline"
              to={fullView ? `/agents/${encodeURIComponent(agent.id)}` : `/agents/${encodeURIComponent(agent.id)}?view=full`}>
              {fullView ? "Compact view" : "Full view"}
            </Link>
          </div>
        </header>
        {!fullView && <AgentTabs agentId={agent.id} activeTab={activeTab} />}
        {automaticWorkError && <p role="alert">Could not confirm the automatic-work change. The last confirmed state is still shown; reload and try again.</p>}
        {resumeNotice && <p role="status" className="rounded-xl border border-green-500/50 bg-green-500/5 p-4">{resumeNotice}</p>}
        {agent.pause?.paused && <PauseSummary agent={agent} onMutationStart={() => { mutationVersion.current += 1; }} onResumed={(result) => {
          mutationVersion.current += 1;
          setLoaded((previous) => previous.key === key ? { key, agent: result } : previous);
          const resumed = result.subtree_resume?.resumed_agent_ids.length ?? 0;
          const retained = result.subtree_resume?.still_paused_agent_ids.length ?? 0;
          setResumeNotice(`Automatic work resumed for ${resumed} agent${resumed === 1 ? "" : "s"}.${retained ? ` ${retained} independently paused descendant${retained === 1 ? " remains" : "s remain"} paused.` : ""}`);
        }} />}
        {agent.replacement?.role === "successor" && <ReplacementSummary agent={agent} />}
        {agent.retirement && <RetirementSummary agent={agent} />}
        {!fullView ? activeTab === "work" ? <CompactAgentView agent={agent} /> : activeTab === "activity" ? <AgentActivityTab agent={agent} /> : <AgentSettingsTab agent={agent} onOpenSettings={() => setSettingsOpen(true)} /> : <>
        {inactive ? <p role="status">{agent.retirement ? 'Agent retired. ' : 'Agent removed. '}Autonomous work and conversations are disabled; history is retained. {agent.work?.state === 'stopping' && 'The existing work process is still stopping.'}</p> : <section aria-label="Agent lifecycle actions" className="space-y-5 rounded-xl border p-5">
          <ReplacementControls agent={agent} onReplaced={(successorId) => void navigate(`/agents/${encodeURIComponent(successorId)}`)} />
          <div className="space-y-3 border-t pt-5">
          <Button onClick={() => setConfirmRemove(true)}>Remove agent</Button>
          {confirmRemove && <div className="space-y-3">
            <p>Remove this agent and stop its work? This cannot be undone.</p>
            <p>History, saved outputs and Plane records are retained.</p>
            <Button disabled={removing} onClick={() => { void removeAgent(); }}>{removing ? "Removing…" : "Confirm removal"}</Button>
            <Button disabled={removing} onClick={() => setConfirmRemove(false)}>Cancel</Button>
          </div>}
          {removeError && <p role="alert">Could not confirm removal. Reload or retry; repeating removal is safe.</p>}
          </div>
        </section>}
        {!inactive && <><AgentModelControls key={`model:${agent.id}`} agent={agent}
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
        <PurposeEvaluation agent={agent} />
        <WorkResults key={`results:${agent.id}`} agent={agent} />
        <SavedOutputs key={`outputs:${agent.id}`} agent={agent} />
        </>}
        {!inactive && <AgentSettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} agent={agent}
          onMutationStart={() => { mutationVersion.current += 1; }}
          onUpdate={(result) => {
            mutationVersion.current += 1;
            setLoaded((previous) => previous.key === key ? { key, agent: result } : previous);
          }} />}
      </>}
    </div>
  );
}

function ReplacementSummary({ agent }: { agent: Agent }) {
  const replacement = agent.replacement;
  if (!replacement || replacement.role !== "successor") return null;
  return <section aria-label="Replacement handoff" className="space-y-2 rounded-xl border p-5">
    <h2 className="font-semibold">Successor agent</h2>
    <p>This is a clean agent identity replacing <Link className="underline underline-offset-4" to={`/agents/${encodeURIComponent(replacement.predecessor_id ?? "")}`}>{replacement.predecessor_id}</Link>. Review the predecessor's retained work and outputs when they are relevant.</p>
    <p><strong>Handoff reason:</strong> {replacement.reason}</p>
    <p className="whitespace-pre-wrap"><strong>Selected handoff:</strong> {replacement.handoff}</p>
  </section>;
}

function PauseSummary({ agent, onMutationStart, onResumed }: { agent: Agent; onMutationStart: () => void; onResumed: (agent: Agent) => void }) {
  const ownPause = agent.pause?.sources.some((source) => source.source_agent_id === agent.id);
  const ancestor = agent.pause?.sources.find((source) => source.source_agent_id !== agent.id);
  const [resuming, setResuming] = useState(false);
  const [error, setError] = useState(false);
  async function resume() {
    setResuming(true); setError(false); onMutationStart();
    try {
      onResumed(await fetchJSON<Agent>(`${agentsEndpoint}/${encodeURIComponent(agent.id)}/work/resume`, { method: "POST" }));
    } catch { setError(true); }
    finally { setResuming(false); }
  }
  return <section role="status" aria-label="Agent paused" className="space-y-2 rounded-xl border border-amber-500/50 bg-amber-500/5 p-5">
    <h2 className="font-semibold">Automatic work is paused</h2>
    <p>{ownPause
      ? "This agent and every active descendant are paused. Thinking cadence and new autonomous work will not restart until the applicable pause is resumed."
      : <>This agent is paused through ancestor <Link className="underline underline-offset-4" to={`/agents/${encodeURIComponent(ancestor?.source_agent_id ?? "")}`}>{ancestor?.source_agent_id}</Link>. Thinking cadence and new autonomous work will not restart until that pause is resumed.</>}</p>
    {agent.work?.state === "stopping" && <p>The current work process is still stopping; its history remains available.</p>}
    {ownPause && <Button disabled={resuming} onClick={() => void resume()}>{resuming ? "Resuming…" : "Resume automatic work"}</Button>}
    {error && <p role="alert">Could not resume automatic work. Reload and try again; repeating this request is safe.</p>}
  </section>;
}

function IconTooltip({ label, children }: { label: string; children: ReactNode }) {
  return <span className="group relative inline-flex">
    {children}
    <span role="tooltip" className="pointer-events-none absolute left-1/2 top-full z-50 mt-2 -translate-x-1/2 whitespace-nowrap rounded-md bg-foreground px-2 py-1 text-xs text-background opacity-0 shadow-md transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
      {label}
    </span>
  </span>;
}

function ProjectPreviewButton({ agentId }: { agentId: string }) {
  const [opening, setOpening] = useState(false);
  const [error, setError] = useState(false);
  async function openPreview() {
    if (opening) return;
    const preview = window.open("about:blank", "_blank");
    if (preview) preview.opener = null;
    setOpening(true); setError(false);
    try {
      const launch = await fetchJSON<{ url: string }>(`${agentsEndpoint}/${encodeURIComponent(agentId)}/preview-launch`, { method: "POST" });
      if (preview) preview.location.replace(launch.url);
      else window.location.assign(launch.url);
    } catch {
      preview?.close(); setError(true);
    } finally { setOpening(false); }
  }
  return <span>
    <IconTooltip label="Open playable project preview">
      <Button size="icon" className="size-10 border border-border bg-background text-foreground shadow-sm hover:bg-muted"
        disabled={opening} aria-label="Open playable project preview" onClick={() => void openPreview()}>
        <MonitorPlay className="size-5" strokeWidth={2.5} aria-hidden="true" />
      </Button>
    </IconTooltip>
    {error && <span role="alert" className="sr-only">Could not open the project preview. Reload and try again.</span>}
  </span>;
}

function AgentTabs({ agentId, activeTab }: { agentId: string; activeTab: "work" | "activity" | "settings" }) {
  const tabs: Array<{ id: "work" | "activity" | "settings"; label: string }> = [
    { id: "work", label: "Work" },
    { id: "activity", label: "Activity" },
    { id: "settings", label: "Settings" },
  ];
  return <nav aria-label="Agent view" className="flex border-b border-border">
    {tabs.map((tab) => <Link key={tab.id} to={`/agents/${encodeURIComponent(agentId)}?tab=${tab.id}`}
      aria-current={activeTab === tab.id ? "page" : undefined}
      className={`border-b-2 px-4 py-2 text-sm ${activeTab === tab.id ? "border-foreground font-medium" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
      {tab.label}
    </Link>)}
  </nav>;
}

function AgentActivityTab({ agent }: { agent: Agent }) {
  const [sort, setSort] = useState<"newest" | "oldest">("newest");
  const events = [...(agent.work?.events ?? [])].sort((left, right) =>
    sort === "newest"
      ? right.created_at.localeCompare(left.created_at)
      : left.created_at.localeCompare(right.created_at));
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const pageCount = Math.max(1, Math.ceil(events.length / pageSize));
  const currentPage = Math.min(page, pageCount - 1);
  const visibleEvents = events.slice(currentPage * pageSize, (currentPage + 1) * pageSize);
  return <section aria-label="Agent activity" className="space-y-3 rounded-xl border p-5">
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
      <h2 className="text-lg font-semibold">Activity</h2>
        <p className="text-sm text-muted-foreground">{sort === "newest" ? "Most recent activity first." : "Oldest activity first."} Open the complete view for diagnostics and lifecycle history.</p>
      </div>
      <div className="flex flex-wrap gap-3 text-sm text-muted-foreground">
        <label>Sort<select aria-label="Activity sort order" className="ml-2 rounded-md border bg-background px-2 py-1 text-foreground" value={sort} onChange={(event) => { setSort(event.target.value as "newest" | "oldest"); setPage(0); }}>
          <option value="newest">Newest first</option><option value="oldest">Oldest first</option>
        </select></label>
        <label>Rows per page<select aria-label="Activity rows per page" className="ml-2 rounded-md border bg-background px-2 py-1 text-foreground" value={pageSize} onChange={(event) => { setPageSize(Number(event.target.value)); setPage(0); }}>
          {[20, 50, 100].map((size) => <option key={size} value={size}>{size}</option>)}
        </select></label>
      </div>
    </div>
    {events.length ? <div className="overflow-x-auto"><table className="w-full text-left text-sm">
      <thead><tr><th className="p-2">Time</th><th className="p-2">Activity</th></tr></thead>
      <tbody>{visibleEvents.map((event) => <tr key={event.id} className="border-t">
        <td className="whitespace-nowrap p-2"><time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString()}</time></td>
        <td className="p-2">{event.summary}</td>
      </tr>)}</tbody>
    </table></div> : <p>No execution activity recorded yet.</p>}
    {events.length > pageSize && <nav aria-label="Activity pages" className="flex items-center justify-between text-sm"><Button disabled={currentPage === 0} onClick={() => setPage(value => Math.max(0, value - 1))}>Previous</Button><span>Page {currentPage + 1} of {pageCount}</span><Button disabled={currentPage === pageCount - 1} onClick={() => setPage(value => Math.min(pageCount - 1, value + 1))}>Next</Button></nav>}
    <Link className="inline-block text-sm underline underline-offset-4" to={`/agents/${encodeURIComponent(agent.id)}?view=full`}>Open complete activity and diagnostics</Link>
  </section>;
}

function AgentSettingsTab({ agent, onOpenSettings }: { agent: Agent; onOpenSettings: () => void }) {
  return <section aria-label="Agent settings summary" className="space-y-4 rounded-xl border p-5">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 className="text-lg font-semibold">Settings</h2>
        <p className="text-sm text-muted-foreground">Configuration that governs this agent’s identity and automatic work.</p>
      </div>
      <Button onClick={onOpenSettings}>Edit agent settings</Button>
    </div>
    <dl className="grid gap-3 text-sm sm:grid-cols-[auto_1fr]">
      <dt className="text-muted-foreground">Purpose revision</dt><dd>{agent.soul_revision}</dd>
      <dt className="text-muted-foreground">Automatic work</dt><dd>{agent.cadence?.enabled ? `Every ${agent.cadence.interval_seconds ?? "?"} seconds` : "Disabled"}</dd>
      <dt className="text-muted-foreground">Autonomy level</dt><dd>{agent.autonomy?.level ?? 3} of 5</dd>
      <dt className="text-muted-foreground">Model</dt><dd>{agent.model_selection ? modelChoiceLabel(agent.model_selection) : "Hermes default"}</dd>
      <dt className="text-muted-foreground">Workspace</dt><dd className="break-all">{agent.project_workspace?.root ?? "Not configured"}</dd>
    </dl>
  </section>;
}

function CompactAgentView({ agent }: { agent: Agent }) {
  const work = agent.work;
  const events = (work?.events ?? []).filter((event) =>
    event.kind !== "work.model"
    && !event.summary.startsWith("Model step ")
    && !event.summary.startsWith("Plane: inspected ")
  ).reverse().slice(0, 20);
  return <div className="space-y-6">
    {!agent.removed_at && !agent.retirement && <WorkQuestions key={`compact-questions:${agent.id}:${agent.soul_revision}`} agentId={agent.id} revision={agent.soul_revision} setup={agent.setup} attentionOnly />}
    <OwnerAttentionAction agent={agent} />
    <ProgressConcernAttention agent={agent} />
    <WorkResults agent={agent} attentionOnly />
    <CompactWorkOverview agent={agent} />
    <SavedOutputs key={`compact-outputs:${agent.id}`} agent={agent} compact />
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

function OwnerAttentionAction({ agent }: { agent: Agent }) {
  const attention = agent.automatic_work;
  const concern = agent.progress_concerns?.some((entry) => entry.status === "open");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const failed = agent.work?.state === "failed";
  if (!attention || attention.state !== "owner_attention" || concern) return null;

  async function retryFailedWork() {
    if (!failed || !agent.work || busy) return;
    setBusy(true); setStatus(""); setError("");
    try {
      await fetchJSON(`${agentsEndpoint}/${encodeURIComponent(agent.id)}/work/retry`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ expected_revision: agent.soul_revision, expected_run_id: agent.work.id }),
      });
      setStatus("Recovery requested. A fresh attempt will inspect the current project state before continuing.");
    } catch {
      setError("Recovery was not confirmed. Open the activity details, resolve any unresolved delivery, then reload and try again.");
    } finally { setBusy(false); }
  }

  return <section aria-label="Needs your attention" className="space-y-3 rounded-xl border border-amber-500/50 bg-amber-500/5 p-5">
    <h2 className="text-lg font-semibold">Needs your attention</h2>
    <div>
      <h3 className="font-medium">What needs attention</h3>
      <p>{attention.blocker ?? "The framework has paused automatic work pending an owner decision."}</p>
    </div>
    {agent.work && <div>
      <h3 className="font-medium">Latest attempt</h3>
      <p className="whitespace-pre-wrap text-sm">{agent.work.error ?? agent.work.summary ?? `Attempt ended with state “${agent.work.state}”.`}</p>
    </div>}
    <div>
      <h3 className="font-medium">What you can do</h3>
      <p>{attention.release_condition ?? "Review the activity and provide direction before resuming."}</p>
    </div>
    <div className="flex flex-wrap items-center gap-3">
      {failed && <Button disabled={busy} onClick={() => { void retryFailedWork(); }}>{busy ? "Requesting recovery…" : "Retry failed work"}</Button>}
      <Link className="text-sm underline underline-offset-4" to={`/agents/${encodeURIComponent(agent.id)}?view=full`}>Open activity and diagnostics</Link>
    </div>
    {status && <p role="status">{status}</p>}
    {error && <p role="alert">{error}</p>}
  </section>;
}

function CompactWorkOverview({ agent }: { agent: Agent }) {
  const work = agent.work;
  const evaluation = work?.purpose_evaluations?.[0];
  const requiredReviews = work?.results.filter(result => result.review.required && result.acceptance === "not_evaluated") ?? [];
  const recentSteps = (work?.progress ?? []).filter(item =>
    !item.summary.startsWith("Selected work item:") && !item.summary.startsWith("Attempt ")
  ).slice(0, 3);
  const active = Boolean(work && ["running", "queued", "preparing", "stopping"].includes(work.state));
  const readinessStage: Record<string, string> = {
    ready: "Ready to start", working: "Working", scheduled: "Waiting for next check-in",
    owner_paused: "Paused", waiting_owner_review: "Waiting for your review",
    waiting_owner_answer: "Waiting for your answer", waiting_retry: "Waiting to retry", owner_attention: "Needs your attention",
    framework_reconciliation: "Framework recovery needed", framework_failure: "Framework failure", automatic_off: "Automatic work off",
    setup: "Preparing agent", not_configured: "Work not configured", retired: "Retired", removed: "Removed",
  };
  const stage = agent.automatic_work ? readinessStage[agent.automatic_work.state]
    : agent.retirement ? "Retired"
    : agent.removed_at ? "Removed"
    : agent.pause?.paused ? "Paused"
    : work?.state === "running" ? "Working"
    : ["queued", "preparing"].includes(work?.state ?? "") ? "Starting"
    : work?.state === "stopping" ? "Stopping"
    : work?.state === "completed" && agent.cadence?.enabled ? agentWaitingForOwner(agent) ? "Waiting for your decision" : "Waiting for next check-in"
    : work?.state === "completed" ? "Automatic work off"
    : work ? work.state.replace("_", " ") : "Not started";
  const currentDirection = agent.automatic_work?.blocker
    ?? (active
    ? work?.focus?.name ?? work?.summary ?? "Reviewing its purpose and project state."
    : evaluation?.judgment === "clarify" ? "Waiting for your answer before dependent work can continue."
    : evaluation?.judgment === "wait" ? (evaluation.uncertainty || "Waiting for new information before continuing.")
    : work?.focus?.name ?? work?.summary ?? "No current work direction has been recorded.");
  const currentMilestone = work?.focus?.name ?? (work ? "A milestone has not been selected yet." : "No milestone has been selected yet.");
  const detailedWork = work?.summary && work.summary !== work?.focus?.name ? work.summary : null;
  const nextDirection = requiredReviews.length
    ? `Review ${requiredReviews[0].summary}`
    : evaluation?.judgment === "clarify"
    ? "Continue after you answer the question shown above."
    : active
    ? "Continue the selected work and report the next meaningful checkpoint."
    : agent.automatic_work?.release_condition
    ? agent.automatic_work.release_condition
    : agent.cadence?.enabled
    ? "Review the project again at the next eligible check-in."
    : "Enable automatic work or give the agent new direction.";
  return <section aria-label="Current work overview" className="space-y-3 rounded-xl border p-5">
    <div className="flex flex-wrap items-start justify-between gap-3"><h2 className="text-lg font-semibold">Work direction</h2><UsageSummary usage={agent.usage.agent} /></div>
    <p className="text-sm"><strong>Stage:</strong> {stage}</p>
    <div><h3 className="text-sm font-semibold">Current milestone</h3><p className="whitespace-pre-wrap text-sm">{currentMilestone}</p></div>
    <div><h3 className="text-sm font-semibold">Working on now</h3><p className="whitespace-pre-wrap text-sm">{currentDirection}</p></div>
    {detailedWork && <div><h3 className="text-sm font-semibold">Current detail</h3><p className="whitespace-pre-wrap text-sm">{detailedWork}</p></div>}
    {recentSteps.length > 0 && <div><h3 className="text-sm font-semibold">Latest progress on this work</h3><ul className="list-disc space-y-1 pl-5 text-sm">{recentSteps.map(step => <li key={step.operation_id}>{step.summary.replace(/^Agent reports:\s*/, "")}</li>)}</ul></div>}
    <div><h3 className="text-sm font-semibold">Up next</h3><p className="whitespace-pre-wrap text-sm">{nextDirection}</p></div>
    {evaluation?.judgment === "wait" && agent.cadence?.enabled && <p className="text-sm text-muted-foreground">Automatic work remains enabled, but no model is running while the agent waits for new information.</p>}
    {work && <p className="text-xs text-muted-foreground">Latest bounded attempt: {work.state.replace("_", " ")}</p>}
    {work?.focus ? <PlanningItemLink agent={agent} itemId={work.focus.item_id} label={work.focus.name} />
      : <p className="text-sm text-muted-foreground">No work item selected.</p>}
  </section>;
}

function UsageSummary({ usage }: { usage: UsageTotals }) {
  const tokens = usage.input_tokens + usage.output_tokens;
  const amount = usage.actual_cost_usd ?? usage.estimated_cost_usd;
  const cost = usage.cost_kind === "included" ? "Included"
    : amount == null ? "Cost unavailable"
    : `${usage.cost_kind === "estimated" ? "~" : ""}$${amount.toFixed(amount < 0.01 ? 4 : 2)}`;
  const title = usage.record_count
    ? `${usage.api_calls.toLocaleString()} model calls · ${usage.input_tokens.toLocaleString()} input · ${usage.output_tokens.toLocaleString()} output · ${usage.reasoning_tokens.toLocaleString()} reasoning · ${cost}`
    : "No completed managed model run has reported usage yet.";
  return <div aria-label="Model usage" title={title} className="text-right text-sm">
    <p className="font-medium">{tokens.toLocaleString()} tokens</p>
    <p className="text-xs text-muted-foreground">{cost}</p>
  </div>;
}

function RetirementSummary({ agent }: { agent: Agent }) {
  const retirement = agent.retirement;
  if (!retirement) return null;
  const evaluation = agent.work?.purpose_evaluations?.find(value => value.id === retirement.evaluation_id);
  return <section aria-label="Retirement decision" className="space-y-3 rounded-xl border p-5">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h2 className="text-lg font-semibold">Agent retired</h2>
      <time className="text-sm text-muted-foreground" dateTime={retirement.retired_at}>{new Date(retirement.retired_at).toLocaleString()}</time>
    </div>
    <p>{agent.replacement?.role === "predecessor"
      ? <>The owner replaced this agent and retired its former subtree. Successor: <Link className="underline underline-offset-4" to={`/agents/${encodeURIComponent(agent.replacement.successor_id ?? "")}`}>{agent.replacement.successor_id}</Link>. Its history and outputs remain available.</>
      : retirement.source === "parent"
      ? <>This agent retired with its subtree after parent <Link className="underline underline-offset-4" to={`/agents/${encodeURIComponent(retirement.decision_agent_id ?? "")}`}>{retirement.decision_agent_id}</Link> completed its purpose. Its history and outputs remain available.</>
      : "The agent ended its ongoing role after the framework verified its latest whole-purpose evaluation. Its history and outputs remain available."}</p>
    {agent.replacement?.role === "predecessor" && <p><strong>Replacement reason:</strong> {agent.replacement.reason}</p>}
    {evaluation ? <>
      <p><strong>Final assessment:</strong> {evaluation.next_action}</p>
      {evaluation.evidence.length > 0 && <div><p className="font-medium">Evidence</p><ul className="list-disc space-y-1 pl-5">{evaluation.evidence.map((item, index) => <li key={index}>{item}</li>)}</ul></div>}
      <p className="text-sm text-muted-foreground">No remaining obligations, unanswered questions, required reviews, unresolved effects, or recorded uncertainty blocked retirement.</p>
    </> : retirement.evaluation_id ? <p className="text-sm text-muted-foreground">Retirement evaluation {retirement.evaluation_id}</p> : null}
  </section>;
}

function ReplacementControls({ agent, onReplaced }: { agent: Agent; onReplaced: (successorId: string) => void }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(`${agent.name} successor`);
  const [purpose, setPurpose] = useState(agent.purpose);
  const [reason, setReason] = useState("");
  const [handoff, setHandoff] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const requestId = useRef(crypto.randomUUID());
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy || !name.trim() || !purpose.trim() || !reason.trim() || !handoff.trim()) return;
    setBusy(true); setError("");
    try {
      const result = await fetchJSON<{ successor: Agent }>(`${agentsEndpoint}/${encodeURIComponent(agent.id)}/replace`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request_id: requestId.current, name: name.trim(), purpose: purpose.trim(), reason: reason.trim(), handoff: handoff.trim() }),
      });
      onReplaced(result.successor.id);
    } catch { setError("Could not confirm replacement. Review unresolved questions and decisions, then retry the same request."); }
    finally { setBusy(false); }
  }
  return <div className="space-y-3">
    <Button onClick={() => setOpen(value => !value)} aria-expanded={open}>Replace agent</Button>
    {open && <form aria-label="Replace agent" className="space-y-3" onSubmit={event => void submit(event)}>
      <p className="text-sm">A clean successor will start under the same parent with copied model, autonomy, cadence and run limits. This agent and its descendants will retire; their history remains linked and readable.</p>
      <label className="block text-sm">Successor name<Input value={name} onChange={event => setName(event.target.value)} maxLength={200} disabled={busy} /></label>
      <label className="block text-sm">Successor purpose<textarea className="mt-1 min-h-28 w-full rounded-md border bg-background p-3" value={purpose} onChange={event => setPurpose(event.target.value)} maxLength={20000} disabled={busy} /></label>
      <label className="block text-sm">Reason for replacement<textarea className="mt-1 w-full rounded-md border bg-background p-3" value={reason} onChange={event => setReason(event.target.value)} maxLength={4000} disabled={busy} /></label>
      <label className="block text-sm">Selected handoff<textarea className="mt-1 min-h-24 w-full rounded-md border bg-background p-3" value={handoff} onChange={event => setHandoff(event.target.value)} maxLength={8000} disabled={busy} placeholder="Relevant context, outputs and unfinished assignments the successor should inspect" /></label>
      <Button type="submit" disabled={busy || !name.trim() || !purpose.trim() || !reason.trim() || !handoff.trim()}>{busy ? "Replacing…" : "Create successor and retire old subtree"}</Button>
      {error && <p role="alert">{error}</p>}
    </form>}
  </div>;
}

function PurposeEvaluation({agent}:{agent:Agent}) {
  const value=agent.work?.purpose_evaluations?.[0];
  if(!value)return null;
  const labels={continue:"Continue working",wait:"Waiting with purpose active",clarify:"Clarification needed",retire_candidate:"Purpose may be complete"};
  return <section aria-label="Purpose evaluation" className="space-y-3 rounded-xl border p-5">
    <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-lg font-semibold">Purpose evaluation</h2><span className="rounded-full border px-3 py-1 text-sm">{labels[value.judgment]}</span></div>
    <p><strong>Next:</strong> {value.next_action}</p>
    {!!value.remaining_obligations.length&&<div><h3 className="text-sm font-semibold">Remaining obligations</h3><ul className="list-disc pl-5 text-sm">{value.remaining_obligations.map(item=><li key={item}>{item}</li>)}</ul></div>}
    {value.uncertainty&&<p className="text-sm"><strong>Uncertainty:</strong> {value.uncertainty}</p>}
    <time className="text-xs text-muted-foreground" dateTime={value.created_at}>{new Date(value.created_at).toLocaleString()}</time>
  </section>;
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
        <PurposeSettings agent={agent} onMutationStart={onMutationStart} onUpdate={onUpdate} />
        <ProjectWorkspaceSettings agent={agent} onUpdate={onUpdate} />
        <AgentModelControls agent={agent} onMutationStart={onMutationStart} onUpdate={onUpdate} />
        <AgentProgressSettings agentId={agent.id} />
        <AgentAutonomySettings agentId={agent.id} />
        <AssignmentReviewSettings key={`${agent.work?.focus?.item_id}:${agent.assignment_review_policies?.find(value=>value.item_id===agent.work?.focus?.item_id)?.revision??0}`} agent={agent} onUpdate={onUpdate} />
        <AgentCadence agentId={agent.id} revision={agent.soul_revision} />
      </DialogContent>
    </Dialog>;
}

function ProjectWorkspaceSettings({ agent, onUpdate }: { agent: Agent; onUpdate: (agent: Agent) => void }) {
  const [root, setRoot] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function grant(event: FormEvent) {
    event.preventDefault();
    if (busy || !root.trim() || agent.project_workspace?.active) return;
    setBusy(true); setMessage("");
    try {
      const project_workspace = await fetchJSON<NonNullable<Agent["project_workspace"]>>(`${agentsEndpoint}/${encodeURIComponent(agent.id)}/workspace`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ expected_revision: agent.soul_revision, root: root.trim() }),
      });
      onUpdate({ ...agent, project_workspace });
      setMessage("Coding workspace granted. Repository tools will be limited to this root.");
    } catch {
      setMessage("Could not grant this workspace. Confirm the directory exists and is not already assigned.");
    } finally { setBusy(false); }
  }
  return <form aria-label="Project workspace settings" onSubmit={(event) => void grant(event)} className="space-y-3 rounded-xl border p-5">
    <h2 className="text-lg font-semibold">Coding workspace</h2>
    {agent.project_workspace?.active ? <>
      <p className="text-sm text-muted-foreground">This agent can use bounded repository tools only inside:</p>
      <p className="break-all rounded-md bg-muted p-3 font-mono text-sm">{agent.project_workspace.root}</p>
    </> : <>
      <p className="text-sm text-muted-foreground">Grant an existing project directory. This does not grant access to the Agent Native repository or First Builder instructions.</p>
      <Label htmlFor="project-workspace-root">Project workspace root</Label>
      <Input id="project-workspace-root" value={root} onChange={(event) => { setRoot(event.target.value); setMessage(""); }} placeholder="/absolute/path/to/project" disabled={busy} />
      <Button type="submit" disabled={busy || !root.trim()}>{busy ? "Granting…" : "Grant coding workspace"}</Button>
    </>}
    {message && <p role="status" className="text-sm">{message}</p>}
  </form>;
}

function PurposeSettings({ agent, onMutationStart, onUpdate }: {
  agent: Agent; onMutationStart: () => void; onUpdate: (agent: Agent) => void;
}) {
  const [purpose, setPurpose] = useState(agent.purpose);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const changed = purpose.trim() !== agent.purpose;
  async function save(event: FormEvent) {
    event.preventDefault();
    if (busy || !changed || !purpose.trim()) return;
    setBusy(true); setMessage(""); onMutationStart();
    try {
      const updated = await fetchJSON<Agent>(`${agentsEndpoint}/${encodeURIComponent(agent.id)}/purpose`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ expected_revision: agent.soul_revision, purpose: purpose.trim() }),
      });
      onUpdate(updated);
      setPurpose(updated.purpose);
      setMessage("Purpose changed. Obsolete work authority ended; retained history still belongs to the earlier revision.");
    } catch {
      setMessage("Could not change the purpose. Reload the current revision and try again.");
    } finally { setBusy(false); }
  }
  return <form aria-label="Purpose settings" onSubmit={(event) => void save(event)} className="space-y-3 rounded-xl border p-5">
    <h2 className="text-lg font-semibold">Purpose</h2>
    <p className="text-sm text-muted-foreground">Changing purpose immediately ends authority for work using the previous revision. Prior history and outputs remain available.</p>
    <Label htmlFor="agent-purpose-setting">Agent purpose</Label>
    <textarea id="agent-purpose-setting" className="min-h-28 w-full rounded-md border bg-background p-3" value={purpose}
      onChange={(event) => { setPurpose(event.target.value); setMessage(""); }} required maxLength={20000} disabled={busy} />
    <Button type="submit" disabled={busy || !changed || !purpose.trim()}>{busy ? "Changing purpose…" : "Change purpose and stop obsolete work"}</Button>
    {message && <p role="status" className="text-sm">{message}</p>}
  </form>;
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
  const hold = (work as typeof work & { hold?: { item_id: string; reason: string } | null })?.hold;

  async function toggleCurrentHold() {
    if (busy.current || !work) return;
    busy.current = true; setError(null); onMutationStart();
    try {
      const suffix = hold ? '/work/hold/release' : '/work/hold';
      const result = await fetchJSON<Agent>(`${agentsEndpoint}/${encodeURIComponent(agent.id)}${suffix}`, {
        method: 'POST', ...(hold ? {} : { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ reason: 'Owner paused this work item to provide direction.' }) }),
      });
      onUpdate(result);
    } catch { setError('Could not update the current work hold. Reload and try again.'); }
    finally { busy.current = false; }
  }

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
      <div className="flex gap-2">{work?.focus && <Button disabled={action !== null} onClick={() => void toggleCurrentHold()}>{hold ? 'Resume current work' : 'Hold current work'}</Button>}{canPause && <Button disabled={action !== null} onClick={() => { void perform("pause"); }}>{action === "pause" ? "Requesting pause…" : "Pause agent"}</Button>}</div>
    </div>
    {canPause && <p className="text-sm text-muted-foreground">Pause stops automatic work for this agent and every active descendant.</p>}
    {work ? <>
      {hold && <p role="status" className="rounded border p-3 text-sm">Current work is held for owner direction. Automatic work remains enabled and will resume this item after you release the hold. Reason: {hold.reason}</p>}
      {work.summary && <p className="whitespace-pre-wrap break-words">{work.summary}</p>}
      {work.state === "queued" && agent.setup?.status !== "ready" && <p>The request is saved. Work will begin after the private workspace and Plane project are ready.</p>}
      {work.state === "stopping" && <p role="status">Stopping the current run. Pause will be confirmed after it stops.</p>}
      {work.state === "paused" && <p>The run is paused. It will not restart automatically.</p>}
      {work.state === "interrupted" && <p>The previous process was interrupted after its effects settled. If thinking cadence is enabled, it will continue in a fresh attempt.</p>}
      {work.state === "retryable_failure" && <p>The attempt failed after its effects settled. Thinking cadence will continue with a fresh attempt; the failed attempt remains in history.</p>}
      {work.state === "failed" && agent.automatic_work?.state === "framework_failure" && <p role="status">This attempt failed without a safe automatic recovery path. Inspect the diagnostics and repair the framework or dependency before continuing; no owner retry decision is required.</p>}
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
      {work.focus && <WorkFeedback agentId={agent.id} revision={agent.soul_revision} />}
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
      <PlanningItemLink agent={agent} itemId={result.item_id} />
      {result.review.required && result.acceptance === "not_evaluated" && <p className="text-sm font-medium">Review the exact saved output in the Saved outputs panel, then accept it or request revision.</p>}
      {result.owner_decision?.note && <p className="whitespace-pre-wrap text-sm">Owner note: {result.owner_decision.note}</p>}
    </article>;
}

function PlanningItemLink({ agent, itemId, label = "Open work item" }: { agent: Agent; itemId: string; label?: string }) {
  const setup = agent.setup;
  if (!setup?.plane_origin || !setup.workspace_slug || !setup.project_id) return null;
  return <a className="inline-block text-sm underline underline-offset-4" target="_blank" rel="noreferrer"
    href={`${setup.plane_origin}/${encodeURIComponent(setup.workspace_slug)}/projects/${encodeURIComponent(setup.project_id)}/issues/${encodeURIComponent(itemId)}/`}>{label}</a>;
}

function SavedOutputs({ agent, compact = false }: { agent: Agent; compact?: boolean }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [page, setPage] = useState(0);
  const [defaultSelectionDismissed, setDefaultSelectionDismissed] = useState(false);
  const allOutputs = agent.work?.outputs ?? [];
  const allMedia = agent.work?.media_outputs ?? [];
  const entries = [...allOutputs.map(output => ({ kind: 'output' as const, created_at: output.created_at, output })), ...allMedia.map(media => ({ kind: 'media' as const, created_at: media.created_at, media }))]
    .sort((a, b) => b.created_at.localeCompare(a.created_at));
  const pageSize = 5;
  const pageCount = Math.max(1, Math.ceil(entries.length / pageSize));
  const currentPage = Math.min(page, pageCount - 1);
  const visible = entries.slice(currentPage * pageSize, (currentPage + 1) * pageSize);
  const requestedOutputId = searchParams.get("output");
  const requestedVersion = searchParams.get("version");
  const mediaId = searchParams.get("media");
  const hasExplicitSelection = requestedOutputId !== null || requestedVersion !== null || mediaId !== null;
  const newest = entries[0];
  const defaultOutput = !hasExplicitSelection && !defaultSelectionDismissed && newest?.kind === "output" ? newest.output : null;
  const defaultMedia = !hasExplicitSelection && !defaultSelectionDismissed && newest?.kind === "media" ? newest.media : null;
  const outputId = requestedOutputId ?? defaultOutput?.output_id ?? null;
  const version = requestedVersion ?? (defaultOutput ? String(defaultOutput.version) : null);
  const hasTextSelection = outputId !== null || version !== null;
  const uniqueSelection = defaultOutput !== null || (searchParams.getAll("output").length === 1 && searchParams.getAll("version").length === 1);

  function select(output: OutputReference | null) {
    if (output) setDefaultSelectionDismissed(false);
    setSearchParams((previous) => {
      const next = new URLSearchParams(previous);
      next.delete("output");
      next.delete("version");
      next.delete("media");
      if (output) { next.set("output", output.output_id); next.set("version", String(output.version)); }
      return next;
    });
  }
  function selectMedia(artifact: MediaOutput | null) {
    if (artifact) setDefaultSelectionDismissed(false);
    setSearchParams((previous) => {
      const next = new URLSearchParams(previous);
      next.delete("output"); next.delete("version"); next.delete("media");
      if (artifact) next.set("media", artifact.artifact_id);
      return next;
    });
  }
  function closeSelection() {
    setDefaultSelectionDismissed(true);
    select(null);
  }
  const selectedMedia = allMedia.find((artifact) => artifact.artifact_id === mediaId) ?? defaultMedia;

  const label = compact ? "Recent outputs" : "Saved outputs";
  return <section aria-label={label} className="space-y-4 rounded-xl border p-5">
    <h2 className="text-lg font-semibold">{label}</h2>
    {!entries.length && <p>No output versions saved yet.</p>}
    {hasTextSelection && <OutputReader key={`${outputId}:${version}:${uniqueSelection}`} agent={agent} showOptionalReview={!compact}
      outputId={outputId} requestedVersion={version} uniqueSelection={uniqueSelection} onClose={closeSelection} />}
    {selectedMedia && <SelectedMediaOutput agent={agent} artifact={selectedMedia} onClose={closeSelection} />}
    <div className="space-y-4">{visible.map((entry, index) => {
      if (entry.kind === 'media') {
        const artifact = entry.media;
        const selected = selectedMedia?.artifact_id === artifact.artifact_id;
        return <article key={artifact.artifact_id} className="space-y-3 rounded-lg border p-4">
        <details open={currentPage === 0 && index === 0}><summary className="cursor-pointer font-semibold">{artifact.title} <span className="ml-2 text-xs font-normal text-muted-foreground">Feedback available</span></summary>
        <p className="text-xs text-muted-foreground">{artifact.mime_type} · {(artifact.byte_count / 1024).toFixed(1)} KB · <time dateTime={artifact.created_at}>{new Date(artifact.created_at).toLocaleString()}</time></p>
        <PlanningItemLink agent={agent} itemId={artifact.item_id} />
        {selected ? <p className="text-sm text-muted-foreground">Viewing this output above.</p> : <Button onClick={() => selectMedia(artifact)}>View output</Button>}
        </details>
      </article>;
      }
      const output = entry.output;
      return <article key={`${output.output_id}:${output.version}`} className="space-y-2 rounded-lg border p-4"><details open={currentPage === 0 && index === 0}><summary className="cursor-pointer font-semibold">{output.title} · Version {output.version} <span className="ml-2 text-xs font-normal text-muted-foreground">Feedback available</span></summary>
      <p className="text-xs text-muted-foreground">{output.format === "markdown" ? "Markdown" : "Plain text"} · <time dateTime={output.created_at}>{new Date(output.created_at).toLocaleString()}</time></p>
      {!compact && <p className="break-all text-xs text-muted-foreground">{output.relative_path}</p>}
      <PlanningItemLink agent={agent} itemId={output.item_id} />
      {!hasTextSelection || outputId !== output.output_id || version !== String(output.version) ? <div><Button onClick={() => select(output)}>Read output</Button></div> : <p className="text-sm text-muted-foreground">Reading this output above.</p>}
    </details></article>;
    })}</div>
    {entries.length > pageSize && <nav aria-label="Saved outputs pages" className="flex items-center justify-between text-sm"><Button disabled={currentPage === 0} onClick={() => setPage(value => Math.max(0, value - 1))}>Previous</Button><span>Page {currentPage + 1} of {pageCount}</span><Button disabled={currentPage === pageCount - 1} onClick={() => setPage(value => Math.min(pageCount - 1, value + 1))}>Next</Button></nav>}
  </section>;
}

function SelectedMediaOutput({ agent, artifact, onClose }: { agent: Agent; artifact: MediaOutput; onClose: () => void }) {
  const source = `${agentsEndpoint}/${encodeURIComponent(agent.id)}/media/${encodeURIComponent(artifact.artifact_id)}`;
  return <article aria-label="Selected media output" className="space-y-4 border-t pt-5">
    <div className="flex items-start justify-between gap-3">
      <div><h3 className="text-xl font-semibold">{artifact.title}</h3><p className="text-sm text-muted-foreground">{artifact.mime_type} · {(artifact.byte_count / 1024).toFixed(1)} KB</p></div>
      <Button onClick={onClose}>Close output</Button>
    </div>
    <AuthenticatedMedia artifact={artifact} source={source} />
    <PlanningItemLink agent={agent} itemId={artifact.item_id} />
    <WorkFeedback agentId={agent.id} revision={agent.soul_revision} outputId={artifact.artifact_id} outputVersion={1} />
  </article>;
}

function AuthenticatedMedia({ artifact, source, compact = false }: { artifact: MediaOutput; source: string; compact?: boolean }) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [imageOpen, setImageOpen] = useState(false);

  useEffect(() => {
    let active = true;
    let createdUrl: string | null = null;
    setObjectUrl(null);
    setFailed(false);
    void authedFetch(source).then(async (response) => {
      if (!response.ok) throw new Error(`Media request failed with ${response.status}`);
      const blob = await response.blob();
      if (!active) return;
      createdUrl = URL.createObjectURL(blob);
      setObjectUrl(createdUrl);
    }).catch(() => { if (active) setFailed(true); });
    return () => {
      active = false;
      if (createdUrl) URL.revokeObjectURL(createdUrl);
    };
  }, [source]);

  if (failed) return <p role="alert" className="text-sm">Could not load this media. Check your connection and sign-in, then reload.</p>;
  if (!objectUrl) return <p role="status" className="text-sm text-muted-foreground">Loading media…</p>;
  const previewClass = compact ? "max-h-80" : "max-h-[32rem]";
  return <div className="space-y-3">
    {artifact.mime_type.startsWith("image/") && <>
      <button type="button" className="block max-w-full cursor-zoom-in rounded-md text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        aria-label={`View ${artifact.title} full size`} onClick={() => setImageOpen(true)}>
        <img className={`${previewClass} max-w-full rounded-md border object-contain`} src={objectUrl} alt={artifact.title} />
      </button>
      <Dialog open={imageOpen} onOpenChange={setImageOpen}>
        <DialogContent className="flex h-[90vh] w-[95vw] !max-w-[95vw] flex-col overflow-hidden p-4 sm:p-6">
          <DialogHeader className="shrink-0 pr-8">
            <DialogTitle>{artifact.title}</DialogTitle>
            <DialogDescription>Image preview. Use the close button or press Escape to return.</DialogDescription>
          </DialogHeader>
          <div className="min-h-0 flex-1 overflow-auto">
            <img className="h-full w-full object-contain" src={objectUrl} alt={artifact.title} />
          </div>
        </DialogContent>
      </Dialog>
    </>}
    {artifact.mime_type.startsWith("audio/") && <audio className="w-full" controls preload="metadata" src={objectUrl}>Audio preview is unavailable.</audio>}
    {artifact.mime_type.startsWith("video/") && <video className={`${previewClass} max-w-full rounded-md border`} controls preload="metadata" src={objectUrl}>Video preview is unavailable.</video>}
    <div className="flex flex-wrap gap-3">
      <a className="text-sm underline underline-offset-4" href={objectUrl} target="_blank" rel="noreferrer">{compact ? "Open media evidence" : "Open media"}</a>
      {!compact && <a className="text-sm underline underline-offset-4" href={objectUrl} download={artifact.filename}>Download</a>}
    </div>
  </div>;
}

type LoadedOutput = { key: string; output?: OutputVersion; error?: boolean };

function OutputReader({ agent, outputId, requestedVersion, uniqueSelection, showOptionalReview, onClose }: {
  agent: Agent; outputId: string | null; requestedVersion: string | null; uniqueSelection: boolean; showOptionalReview: boolean; onClose: () => void;
}) {
  const agentId = agent.id;
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
  const result = agent.work?.results.find((candidate) => candidate.outputs.some(
    (reference) => reference.output_id === output.output_id && reference.version === output.version));
  return <article aria-label="Output reader" className="space-y-4 border-t pt-5">
    <div className="flex items-start justify-between gap-3"><h3 className="text-xl font-semibold">{output.title} · Version {output.version}</h3><Button onClick={onClose}>Close output</Button></div>
    <a className="inline-block text-sm underline underline-offset-4" href={outputVersionLink(agentId, output)}>Link to this version</a>
    {output.format === "markdown" ? <Markdown content={output.content} /> : <pre className="whitespace-pre-wrap break-words text-sm">{output.content}</pre>}
    <WorkFeedback agentId={agent.id} revision={agent.soul_revision} outputId={output.output_id} outputVersion={output.version} />
    {result && (showOptionalReview || result.review.required || result.acceptance !== "not_evaluated") && <OutputReview agent={agent} result={result} />}
    {output.evaluation != null && <section aria-label="Saved version evaluation" className="space-y-2 border-t pt-4">
      <h4 className="font-semibold">Agent evaluation</h4>
      <p className="text-xs text-muted-foreground">The agent’s assessment of this saved version. It is evidence, not an owner decision.</p>
      <pre className="whitespace-pre-wrap break-words text-sm">{typeof output.evaluation === "string" ? output.evaluation : typeof output.evaluation.report === "string" ? output.evaluation.report : JSON.stringify(output.evaluation, null, 2)}</pre>
    </section>}
  </article>;
}

function OutputReview({ agent, result }: { agent: Agent; result: WorkResult }) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function decide(decision: "accepted" | "revision_requested") {
    if (busy || (decision === "revision_requested" && !note.trim())) return;
    setBusy(true); setMessage("");
    try {
      await fetchJSON<Agent>(`${agentsEndpoint}/${encodeURIComponent(agent.id)}/results/${encodeURIComponent(result.id)}/decision`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request_id: crypto.randomUUID(), decision, expected_criteria_revision: result.criteria_revision, ...(decision === "revision_requested" ? { note: note.trim() } : {}) }),
      });
      setMessage(decision === "accepted" ? "Accepted this exact output version." : "Revision requested. The agent will receive your instructions on its next cadence attempt.");
    } catch { setMessage("Could not confirm this decision. Reload the output before retrying."); }
    finally { setBusy(false); }
  }
  const status = result.acceptance === "accepted" ? "Accepted by owner"
    : result.acceptance === "revision_requested" ? "Revision requested"
    : result.review.required ? "Owner approval required" : "Review optional";
  return <section aria-label="Output review" className="space-y-3 rounded-lg border p-4">
    <div className="flex flex-wrap items-center justify-between gap-2"><h4 className="font-semibold">Output review</h4><span className="rounded-full border px-3 py-1 text-sm">{status}</span></div>
    <p className="text-sm">{result.review.required
      ? result.review.reason ?? "This exact output version requires an owner decision before dependent work continues."
      : "No owner decision is required. The agent may continue its authorized work."}</p>
    {result.review.required && result.acceptance === "not_evaluated" && <>
      <p className="text-sm">Your decision applies only to this result and its listed output versions.</p>
      <Button disabled={busy} onClick={() => void decide("accepted")}>Accept output</Button>
      <label className="block text-sm">Revision instructions
        <textarea value={note} onChange={event => setNote(event.target.value)} disabled={busy} maxLength={4000} rows={3} className="mt-1 w-full rounded border bg-background p-2" />
      </label>
      <Button disabled={busy || !note.trim()} onClick={() => void decide("revision_requested")}>Request revision</Button>
    </>}
    {result.owner_decision?.note && <p className="whitespace-pre-wrap text-sm">Owner note: {result.owner_decision.note}</p>}
    {message && <p role="status" className="text-sm">{message}</p>}
  </section>;
}
