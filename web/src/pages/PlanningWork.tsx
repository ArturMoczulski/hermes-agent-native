import { useEffect, useState } from "react";
import { Button } from "@nous-research/ui/ui/components/button";
import { agentsEndpoint, type Agent, type AgentPlanning } from "@/lib/agent-native";
import { fetchJSON } from "@/lib/api";

// Plane descriptions are untrusted rich text. An inert template is used only to
// extract readable text; its nodes, attributes and links never enter the page.
function descriptionText(html: string | null | undefined): string {
  if (!html) return "";
  const template = document.createElement("template");
  template.innerHTML = html;
  template.content.querySelectorAll("script,style,iframe,object,embed,template").forEach((node) => node.remove());
  template.content.querySelectorAll("br,p,div,li,h1,h2,h3,h4,blockquote,tr").forEach((node) => node.append("\n"));
  return template.content.textContent?.trim() ?? "";
}

function planeLink(data: AgentPlanning, tail = "issues/"): string | undefined {
  try {
    const origin = new URL(data.plane_origin);
    if (!["http:", "https:"].includes(origin.protocol)) return undefined;
    return `${origin.origin}/${encodeURIComponent(data.workspace_slug)}/projects/${encodeURIComponent(data.project.id)}/${tail}`;
  } catch { return undefined; }
}

export default function PlanningWork({ agent }: { agent: Agent }) {
  const [refresh, setRefresh] = useState(0);
  const [state, setState] = useState<{ data?: AgentPlanning; error?: string; selectionId?: string | null; requestKey?: string }>({});
  const focus = agent.work?.focus;
  const activation = agent.setup?.activation_id;
  const ready = agent.setup?.status === "ready";
  const requestKey = `${agent.id}:${agent.soul_revision}:${activation}:${focus?.selection_id}:${refresh}`;
  const loading = state.requestKey !== requestKey;

  useEffect(() => {
    if (!ready || !activation) return;
    let active = true;
    const controller = new AbortController();
    void fetchJSON<AgentPlanning>(`${agentsEndpoint}/${encodeURIComponent(agent.id)}/planning`, { signal: controller.signal })
      .then((data) => {
        if (!active) return;
        if (data.agent_id !== agent.id || data.soul_revision !== agent.soul_revision || data.setup_activation_id !== activation) {
          setState({ requestKey, error: "The planning scope changed. Refresh planning to check the current project." });
          return;
        }
        setState({ data, selectionId: focus?.selection_id ?? null, requestKey });
      })
      .catch((error: unknown) => {
        if (!active) return;
        const status = error instanceof Error ? Number(error.message.split(":", 1)[0]) : 0;
        if ([401, 403, 404, 409].includes(status)) {
          setState({ requestKey, error: status === 409 ? "Planning is not configured for this agent’s current setup." : "Planning access or scope could not be verified. Refresh after checking this agent’s setup." });
        } else {
          setState((old) => ({ data: old.data, selectionId: old.selectionId, requestKey, error: "Planning is unavailable. Check the connection and refresh planning." }));
        }
      });
    return () => { active = false; controller.abort(); };
  }, [agent.id, agent.soul_revision, activation, ready, focus?.selection_id, requestKey]);

  const data = state.data;
  const matchingSelection = state.selectionId === (focus?.selection_id ?? null);
  const currentItem = matchingSelection ? data?.items.find((item) => item.id === focus?.item_id) : undefined;
  const selectedCycle = data?.cycles.find((cycle) => cycle.id === focus?.cycle_id);
  const currentState = data?.states.find((item) => item.id === currentItem?.state);
  const selectionDescription = descriptionText(focus?.description_html);
  const latestDescription = descriptionText(currentItem?.description_html);
  const changed = !!currentItem && (currentItem.name !== focus?.name || currentItem.description_html !== focus?.description_html);
  const activeFocus = focus && ["preparing", "running"].includes(agent.work?.state ?? "") && focus.soul_revision === agent.soul_revision;
  const projectHref = data ? planeLink(data) : undefined;

  return <section aria-label="Work planning" className="space-y-5 rounded-xl border p-5">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h2 className="text-lg font-semibold">Work planning</h2>
      <Button disabled={!ready || loading} onClick={() => setRefresh((value) => value + 1)}>
        {ready && loading ? "Refreshing planning…" : "Refresh planning"}
      </Button>
    </div>
    {!ready ? <p>Planning is not ready. The agent’s private Plane project must be configured first.</p> : <>
      {state.error && <p role="alert">{state.error}{data ? " Showing stale planning data from the last successful check." : ""}</p>}
      {loading && !data && <p role="status">Loading planning…</p>}
      {data && <>
        <p className="text-xs text-muted-foreground">{state.error ? "Last successful planning check" : "Planning checked"} <time aria-label="Planning checked time" dateTime={data.observed_at}>{new Date(data.observed_at).toLocaleString()}</time>. Use Refresh planning to see changes in Plane.</p>
        <div className="space-y-2">
          <h3 className="font-semibold">Project · {data.project.name}</h3>
          <h4 className="text-sm font-semibold">Project brief</h4>
          <p className="whitespace-pre-wrap break-words text-sm">{data.project.description || "No project brief recorded yet."}</p>
          {projectHref && <a className="inline-block text-sm underline underline-offset-4" href={projectHref} target="_blank" rel="noreferrer">Open project in Plane</a>}
        </div>
        <div className="space-y-3">
          <h3 className="font-semibold">Planning cycles</h3>
          {!data.cycles.length && <p className="text-sm">No cycles recorded yet.</p>}
          {data.cycles.map((cycle) => <article key={cycle.id} className="space-y-2 rounded-lg border p-3">
            <h4 className="text-sm font-semibold">{cycle.name}</h4>
            <p className="whitespace-pre-wrap break-words text-sm">{cycle.description || "No cycle goal recorded yet."}</p>
            {planeLink(data, `cycles/${encodeURIComponent(cycle.id)}/`) && <a className="text-sm underline underline-offset-4" href={planeLink(data, `cycles/${encodeURIComponent(cycle.id)}/`)} target="_blank" rel="noreferrer">Open cycle in Plane</a>}
          </article>)}
        </div>
      </>}
    </>}
    <div className="space-y-3 border-t pt-4">
      <h3 className="font-semibold">{focus ? (activeFocus ? "Current work item" : "Last selected work item") : "No work item selected"}</h3>
      {!focus && <p className="text-sm">{!agent.work ? "Initial review pending. The setup discovery task is available, but the agent has not selected work yet." : "No selection was recorded for this run. A planning item’s priority or status does not establish what the agent is working on."}</p>}
      {focus && <>
        <p className="font-medium">{focus.name}</p>
        <dl className="grid gap-2 text-sm sm:grid-cols-[auto_1fr]">
          <dt className="text-muted-foreground">Selected</dt><dd><time dateTime={focus.selected_at}>{new Date(focus.selected_at).toLocaleString()}</time></dd>
          <dt className="text-muted-foreground">Cycle at selection</dt><dd>{focus.cycle_id ? (selectedCycle?.name ?? focus.cycle_id) : "No cycle selected"}</dd>
          <dt className="text-muted-foreground">Purpose revision at selection</dt><dd>{focus.soul_revision}</dd>
          {currentState && <><dt className="text-muted-foreground">Plane status at last check</dt><dd>{currentState.name}</dd></>}
        </dl>
        <div className="space-y-2"><h4 className="text-sm font-semibold">Requirements at selection</h4><p className="whitespace-pre-wrap break-words text-sm">{selectionDescription || "No requirements recorded at selection."}</p></div>
        {data && matchingSelection && !currentItem && <p role="status" className="text-sm">The selected work item is missing from the current planning snapshot. Its recorded selection is retained above.</p>}
        {data && !matchingSelection && <p role="status" className="text-sm">This planning check belongs to an earlier work selection. Refresh planning to compare this selection with Plane.</p>}
        {changed && <div className="space-y-2 rounded-lg border p-3">
          <p role="status" className="text-sm font-semibold">Requirements differ from the last Plane check.</p>
          <h4 className="text-sm font-semibold">Requirements at last Plane check</h4>
          <p className="text-sm">{currentItem?.name}</p>
          <p className="whitespace-pre-wrap break-words text-sm">{latestDescription || "No requirements in that planning snapshot."}</p>
          <p className="text-sm text-muted-foreground">This view does not confirm that the active run has adopted these changes.</p>
        </div>}
        {data && matchingSelection && planeLink(data, `issues/${encodeURIComponent(focus.item_id)}/`) && <a className="inline-block text-sm underline underline-offset-4" href={planeLink(data, `issues/${encodeURIComponent(focus.item_id)}/`)} target="_blank" rel="noreferrer">Open selected work item in Plane</a>}
      </>}
    </div>
    <p className="text-sm text-muted-foreground">Work decision handling and child-agent controls are not available yet.</p>
  </section>;
}
