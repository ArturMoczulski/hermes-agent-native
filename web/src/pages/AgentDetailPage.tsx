import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { Button } from "@nous-research/ui/ui/components/button";
import { agentsEndpoint, type Agent } from "@/lib/agent-native";
import { fetchJSON } from "@/lib/api";
import { usePageHeader } from "@/contexts/usePageHeader";

type LoadedAgent = { key: string; agent?: Agent; error?: string };

export default function AgentDetailPage() {
  const { agentId } = useParams<{ agentId: string }>();
  const { setTitle } = usePageHeader();
  const [reload, setReload] = useState(0);
  const [loaded, setLoaded] = useState<LoadedAgent>({ key: "" });
  const key = `${agentId}:${reload}`;
  const current = loaded.key === key ? loaded : undefined;
  const agent = current?.agent;

  useEffect(() => {
    let active = true;
    void fetchJSON<Agent>(`${agentsEndpoint}/${encodeURIComponent(agentId ?? "")}`)
      .then((result) => { if (active) setLoaded({ key, agent: result }); })
      .catch(() => {
        if (active) setLoaded({ key, error: "Could not load this agent. Check the link, your connection and sign-in, then retry." });
      });
    return () => { active = false; };
  }, [agentId, key]);

  useEffect(() => {
    setTitle(agent?.name ?? "Agent");
    return () => setTitle(null);
  }, [agent?.name, setTitle]);

  const startup = agent?.startup;
  const staleRequest = startup && startup.soul_revision !== agent?.soul_revision;

  return (
    <div className="mx-auto w-full max-w-4xl space-y-6 p-6">
      <Link to="/agents" className="text-sm underline underline-offset-4">All agents</Link>
      {!current && <p role="status">Loading agent…</p>}
      {current?.error && <div role="alert" className="space-y-3"><p>{current.error}</p><Button onClick={() => setReload((value) => value + 1)}>Retry</Button></div>}
      {agent && <>
        <header className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h1 className="text-2xl font-semibold">{agent.name}</h1>
            <span aria-label="Execution status" className="rounded-full border px-3 py-1 text-sm">Not started</span>
          </div>
          <p className="break-all text-xs text-muted-foreground">Root agent · {agent.id}</p>
        </header>
        <section aria-label="Agent purpose" className="space-y-3 rounded-xl border p-5">
          <h2 className="text-lg font-semibold">Purpose</h2>
          <p className="whitespace-pre-wrap break-words">{agent.purpose}</p>
          <p className="text-xs text-muted-foreground">Purpose revision {agent.soul_revision}</p>
        </section>
        <section aria-label="Startup request" className="space-y-3 rounded-xl border p-5">
          <h2 className="text-lg font-semibold">{startup ? "First review requested" : "No startup request recorded"}</h2>
          {startup ? <>
            <p>Your agent is saved and its first review has been requested. Work has not started: agent execution is not connected yet.</p>
            <dl className="grid gap-2 text-sm sm:grid-cols-[auto_1fr]">
              <dt className="text-muted-foreground">Requested</dt><dd><time dateTime={startup.requested_at}>{new Date(startup.requested_at).toLocaleString()}</time></dd>
              <dt className="text-muted-foreground">Cause</dt><dd>Agent creation</dd>
              <dt className="text-muted-foreground">Purpose revision</dt><dd>{startup.soul_revision}</dd>
              <dt className="text-muted-foreground">Request ID</dt><dd className="break-all">{startup.id}</dd>
            </dl>
            {staleRequest && <p role="status">The purpose changed after this request. It cannot authorize work on the current purpose.</p>}
          </> : <p>This agent was saved before startup requests were recorded. Opening this page does not start it.</p>}
        </section>
        <section aria-label="Agent activity" className="space-y-3 rounded-xl border p-5">
          <h2 className="text-lg font-semibold">Activity</h2>
          <p>No execution sessions or stories yet.</p>
          <p className="text-sm text-muted-foreground">Created <time dateTime={agent.created_at}>{new Date(agent.created_at).toLocaleString()}</time></p>
        </section>
      </>}
    </div>
  );
}
