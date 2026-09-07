import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router";
import { agentsEndpoint as endpoint, agentWorkStatus, validWorkLimits, type Agent, type WorkLimits } from "@/lib/agent-native";
import { Button } from "@nous-research/ui/ui/components/button";
import { Input } from "@nous-research/ui/ui/components/input";
import { Label } from "@nous-research/ui/ui/components/label";
import { fetchJSON, HERMES_BASE_PATH } from "@/lib/api";
import { usePageHeader } from "@/contexts/usePageHeader";

type PendingCreation = { request_id: string; name: string; purpose: string; work?: WorkLimits };
const creationKey = `${HERMES_BASE_PATH}:agent-native:create`;

function restoreCreation(): PendingCreation | null {
  try {
    const value = JSON.parse(sessionStorage.getItem(creationKey) ?? "null") as PendingCreation | null;
    if (value && typeof value.request_id === "string" && value.request_id.length > 0 && value.request_id.length <= 128
      && typeof value.name === "string" && value.name.trim() && value.name.length <= 200
      && typeof value.purpose === "string" && value.purpose.trim() && value.purpose.length <= 20000
      && (value.work === undefined || validWorkLimits(value.work))) {
      return { request_id: value.request_id, name: value.name, purpose: value.purpose,
        ...(value.work ? { work: { timeout_seconds: value.work.timeout_seconds, max_iterations: value.work.max_iterations } } : {}) };
    }
  } catch { /* Storage can be unavailable; submission will check before any write. */ }
  return null;
}

export default function AgentsPage() {
  const { setTitle } = usePageHeader();
  const navigate = useNavigate();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [initialRequest] = useState(restoreCreation);
  const [name, setName] = useState(initialRequest?.name ?? "");
  const [purpose, setPurpose] = useState(initialRequest?.purpose ?? "");
  const [timeoutSeconds, setTimeoutSeconds] = useState(initialRequest?.work ? String(initialRequest.work.timeout_seconds) : "");
  const [modelSteps, setModelSteps] = useState(initialRequest?.work ? String(initialRequest.work.max_iterations) : "");
  const wantsWork = timeoutSeconds !== "" || modelSteps !== "";
  const workLimits = { timeout_seconds: Number(timeoutSeconds), max_iterations: Number(modelSteps) };
  const invalidWork = wantsWork && !validWorkLimits(workLimits);
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const pending = useRef<PendingCreation | null>(initialRequest);
  const submitting = useRef(false);

  useEffect(() => {
    setTitle("Agents");
    return () => setTitle(null);
  }, [setTitle]);

  useEffect(() => {
    let active = true;
    void fetchJSON<Agent[]>(endpoint).then((result) => {
      if (active) setAgents(result);
    }).catch(() => {
      if (active) setError("Could not load agents. Check your connection and sign-in, then retry.");
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [reload]);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting.current || !name.trim() || !purpose.trim() || invalidWork) return;
    submitting.current = true;
    setSaving(true);
    setError("");
    const work = wantsWork ? workLimits : undefined;
    if (pending.current?.name !== name.trim() || pending.current?.purpose !== purpose.trim()
      || pending.current?.work?.timeout_seconds !== work?.timeout_seconds
      || pending.current?.work?.max_iterations !== work?.max_iterations) {
      pending.current = { name: name.trim(), purpose: purpose.trim(), request_id: crypto.randomUUID(), ...(work ? { work } : {}) };
    }
    try {
      // Persist before POST: a committed response can be lost across a reload.
      // If storage fails, do not send a write whose retry identity we cannot keep.
      sessionStorage.setItem(creationKey, JSON.stringify(pending.current));
    } catch {
      setError("Could not preserve the creation request. Enable browser session storage and retry; nothing was sent.");
      submitting.current = false;
      setSaving(false);
      return;
    }
    try {
      const agent = await fetchJSON<Agent>(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(pending.current),
      });
      sessionStorage.removeItem(creationKey);
      setAgents((existing) => [...existing.filter((a) => a.id !== agent.id), agent]);
      setName("");
      setPurpose("");
      setTimeoutSeconds("");
      setModelSteps("");
      pending.current = null;
      void navigate(`/agents/${encodeURIComponent(agent.id)}`);
    } catch {
      setError("Could not confirm creation. Retry with the same name, purpose and work limits to avoid a duplicate.");
    } finally {
      submitting.current = false;
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-4xl space-y-8 p-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold">Your agents</h1>
        <p className="text-muted-foreground">Give each agent a purpose to keep and develop over time.</p>
        <p className="rounded-lg border p-3 text-sm">Create an agent to talk with it, or set both work limits to start its first private writing run after setup is ready.</p>
      </header>
      <form onSubmit={(event) => void create(event)} className="space-y-4 rounded-xl border p-5">
        <h2 className="text-lg font-semibold">Create an agent</h2>
        <div className="space-y-2">
          <Label htmlFor="agent-name">Agent name</Label>
          <Input id="agent-name" value={name} onChange={(e) => setName(e.target.value)} required maxLength={200} disabled={saving} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="agent-purpose">Purpose</Label>
          <textarea id="agent-purpose" className="min-h-28 w-full rounded-md border bg-background p-3" value={purpose} onChange={(e) => setPurpose(e.target.value)} required maxLength={20000} disabled={saving} placeholder="What should this agent work toward?" />
        </div>
        <fieldset className="space-y-3 rounded-lg border p-4" disabled={saving}>
          <legend className="px-1 text-sm font-medium">First writing run (optional)</legend>
          <p className="text-sm text-muted-foreground">Set both limits to let the agent plan and write in its private workspace. Leave both blank to create it for conversation. This starts one run; automatic continuation is not enabled.</p>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2"><Label htmlFor="agent-run-time">Maximum run time (seconds)</Label><Input id="agent-run-time" type="number" min={1} max={3600} step={1} required={wantsWork} value={timeoutSeconds} onChange={(event) => setTimeoutSeconds(event.target.value)} /></div>
            <div className="space-y-2"><Label htmlFor="agent-model-steps">Maximum model steps</Label><Input id="agent-model-steps" type="number" min={1} max={100} step={1} required={wantsWork} value={modelSteps} onChange={(event) => setModelSteps(event.target.value)} /></div>
          </div>
          {invalidWork && <p className="text-sm">Enter both limits: 1–3600 seconds and 1–100 model steps.</p>}
        </fieldset>
        <Button type="submit" disabled={saving || loading || !name.trim() || !purpose.trim() || invalidWork}>{saving ? "Creating…" : "Create agent"}</Button>
      </form>
      {error && <div role="alert" className="space-y-2"><p>{error}</p><Button disabled={saving} onClick={() => { setLoading(true); setError(""); setReload((value) => value + 1); }}>Reload agents</Button></div>}
      <section aria-label="Agent list" className="space-y-4">
        <h2 className="text-lg font-semibold">Agents</h2>
        {loading ? <p>Loading agents…</p> : agents.length === 0 && !error ? <p>No agents yet. Create your first agent above.</p> : null}
        {agents.map((agent) => (
          <article key={agent.id} className="space-y-3 rounded-xl border p-5">
            <div className="flex items-center justify-between gap-4"><h3 className="font-semibold"><Link className="underline-offset-4 hover:underline" to={`/agents/${encodeURIComponent(agent.id)}`}>{agent.name}</Link></h3><span className="rounded-full border px-3 py-1 text-sm">{agentWorkStatus(agent)}</span></div>
            <p className="whitespace-pre-wrap break-words">{agent.purpose}</p>
            <p className="break-all text-xs text-muted-foreground">Agent ID: {agent.id} · Purpose revision {agent.soul_revision}</p>
          </article>
        ))}
      </section>
    </div>
  );
}
