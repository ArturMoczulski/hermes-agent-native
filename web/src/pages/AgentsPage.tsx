import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router";
import { agentsEndpoint as endpoint, agentWorkStatus, validWorkLimits, validModelChoice, modelChoiceLabel, autonomyLabels, type Agent, type WorkLimits, type ModelChoice, type DefaultAgentModel } from "@/lib/agent-native";
import { Button } from "@nous-research/ui/ui/components/button";
import { Input } from "@nous-research/ui/ui/components/input";
import { Label } from "@nous-research/ui/ui/components/label";
import { fetchJSON, HERMES_BASE_PATH } from "@/lib/api";
import { usePageHeader } from "@/contexts/usePageHeader";
import { AgentModelPicker, DefaultAgentModelControls } from "@/components/AgentModelControls";

type PendingCreation = { request_id: string; name: string; purpose: string; work?: WorkLimits; model_selection?: ModelChoice; autonomy_level: number };
const creationKey = `${HERMES_BASE_PATH}:agent-native:create`;
const defaultWorkLimits: WorkLimits = { timeout_seconds: 180, max_iterations: 50 };

function restoreCreation(): PendingCreation | null {
  try {
    const value = JSON.parse(sessionStorage.getItem(creationKey) ?? "null") as PendingCreation | null;
    if (value && typeof value.request_id === "string" && value.request_id.length > 0 && value.request_id.length <= 128
      && typeof value.name === "string" && value.name.trim() && value.name.length <= 200
      && typeof value.purpose === "string" && value.purpose.trim() && value.purpose.length <= 20000
      && (value.work === undefined || validWorkLimits(value.work))
      && (value.model_selection === undefined || validModelChoice(value.model_selection))
      && Number.isInteger(value.autonomy_level) && value.autonomy_level >= 1 && value.autonomy_level <= 5) {
      return { request_id: value.request_id, name: value.name, purpose: value.purpose,
        ...(value.model_selection ? { model_selection: { provider: value.model_selection.provider, model: value.model_selection.model,
          ...(value.model_selection.reasoning_effort !== undefined ? { reasoning_effort: value.model_selection.reasoning_effort } : {}) } } : {}),
        ...(value.work ? { work: { timeout_seconds: value.work.timeout_seconds, max_iterations: value.work.max_iterations } } : {}), autonomy_level: value.autonomy_level };
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
  const [defaultModel, setDefaultModel] = useState<DefaultAgentModel | null>(null);
  const [modelSelection, setModelSelection] = useState<ModelChoice | null>(initialRequest?.model_selection ?? null);
  const [choosingModel, setChoosingModel] = useState(false);
  const [purpose, setPurpose] = useState(initialRequest?.purpose ?? "");
  const [autonomyLevel, setAutonomyLevel] = useState(initialRequest?.autonomy_level ?? 5);
  const [timeoutSeconds, setTimeoutSeconds] = useState(String(initialRequest?.work?.timeout_seconds ?? defaultWorkLimits.timeout_seconds));
  const [modelSteps, setModelSteps] = useState(String(initialRequest?.work?.max_iterations ?? defaultWorkLimits.max_iterations));
  const workLimits = { timeout_seconds: Number(timeoutSeconds), max_iterations: Number(modelSteps) };
  const invalidWork = !validWorkLimits(workLimits);
  const modelKnown = modelSelection !== null || defaultModel !== null;
  const missingWorkModel = !validModelChoice(modelSelection ?? defaultModel);
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
    if (submitting.current || !name.trim() || !purpose.trim() || invalidWork || !modelKnown || missingWorkModel) return;
    submitting.current = true;
    setSaving(true);
    setError("");
    const work = workLimits;
    if (pending.current?.name !== name.trim() || pending.current?.purpose !== purpose.trim()
      || pending.current?.work?.timeout_seconds !== work?.timeout_seconds
      || pending.current?.work?.max_iterations !== work?.max_iterations
      || pending.current?.autonomy_level !== autonomyLevel
      || pending.current?.model_selection?.provider !== modelSelection?.provider
      || pending.current?.model_selection?.model !== modelSelection?.model
      || (pending.current?.model_selection?.reasoning_effort ?? "default") !== (modelSelection?.reasoning_effort ?? "default")) {
      pending.current = { name: name.trim(), purpose: purpose.trim(), request_id: crypto.randomUUID(), work, autonomy_level: autonomyLevel, ...(modelSelection ? { model_selection: modelSelection } : {}) };
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
      setTimeoutSeconds(String(defaultWorkLimits.timeout_seconds));
      setModelSteps(String(defaultWorkLimits.max_iterations));
      setModelSelection(null);
      setAutonomyLevel(5);
      pending.current = null;
      void navigate(`/agents/${encodeURIComponent(agent.id)}`);
    } catch {
      setError("Could not confirm creation. Retry with the same name, purpose, model and work limits to avoid a duplicate.");
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
        <p className="rounded-lg border p-3 text-sm">Creating an agent starts its first private bounded work run after setup is ready. You can talk with it at any time.</p>
      </header>
      <DefaultAgentModelControls onChange={setDefaultModel} />
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
        <fieldset aria-label="Model for this agent" className="space-y-3 rounded-lg border p-4" disabled={saving}>
          <legend className="px-1 text-sm font-medium">Model for this agent</legend>
          <p className="break-words text-sm">{modelKnown ? <>{modelSelection ? "Use selected model: " : "Use creation default: "}{modelChoiceLabel(modelSelection ?? defaultModel)}</> : "The default has not been confirmed. Wait for it to load, reload the default, or choose a different model."}</p>
          {missingWorkModel && <p className="text-sm">Choose a configured model before starting work.</p>}
          <div className="flex flex-wrap gap-2">
            <Button type="button" onClick={() => setChoosingModel(true)}>Choose a different model</Button>
            {modelSelection && <Button type="button" onClick={() => setModelSelection(null)}>Use default model</Button>}
          </div>
          <p className="text-xs text-muted-foreground">Each agent keeps its own selection. You can change it later in agent details.</p>
        </fieldset>
        <div className="space-y-2">
          <Label htmlFor="new-agent-autonomy">Autonomy</Label>
          <select id="new-agent-autonomy" value={autonomyLevel} disabled={saving} className="w-full rounded-md border bg-background px-3 py-2"
            onChange={event => setAutonomyLevel(Number(event.target.value))}>
            {Object.entries(autonomyLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
          <p className="text-xs text-muted-foreground">Highly autonomous is the default. The agent keeps working and asks only when a decision is critical or outside its authority.</p>
        </div>
        <details className="rounded-lg border p-4">
          <summary className="cursor-pointer text-sm font-medium">Advanced work limits <span className="ml-2 text-muted-foreground">· 3 minutes · 50 model steps by default</span></summary>
          <fieldset className="mt-4 space-y-3" disabled={saving}>
            <p className="text-sm text-muted-foreground">These safety limits apply to each attempt. Thinking cadence can start a new attempt after a normal limit is reached.</p>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2"><Label htmlFor="agent-run-time">Maximum run time (seconds)</Label><Input id="agent-run-time" type="number" min={1} max={3600} step={1} required value={timeoutSeconds} onChange={(event) => setTimeoutSeconds(event.target.value)} /></div>
              <div className="space-y-2"><Label htmlFor="agent-model-steps">Maximum model steps</Label><Input id="agent-model-steps" type="number" min={1} max={100} step={1} required value={modelSteps} onChange={(event) => setModelSteps(event.target.value)} /></div>
            </div>
            {invalidWork && <p className="text-sm">Enter both limits: 1–3600 seconds and 1–100 model steps.</p>}
          </fieldset>
        </details>
        <Button type="submit" disabled={saving || loading || !name.trim() || !purpose.trim() || invalidWork || !modelKnown || missingWorkModel}>{saving ? "Creating…" : "Create agent"}</Button>
      </form>
      {choosingModel && <AgentModelPicker choice={modelSelection ?? defaultModel} title="Choose a model for this agent" actionLabel="Use model"
        scopeDescription="Only this new agent will use the selected model." onApply={setModelSelection} onClose={() => setChoosingModel(false)} />}
      {error && <div role="alert" className="space-y-2"><p>{error}</p><Button disabled={saving} onClick={() => { setLoading(true); setError(""); setReload((value) => value + 1); }}>Reload agents</Button></div>}
      <section aria-label="Agent list" className="space-y-4">
        <h2 className="text-lg font-semibold">Agents</h2>
        {loading ? <p>Loading agents…</p> : agents.length === 0 && !error ? <p>No agents yet. Create your first agent above.</p> : null}
        {agents.map((agent) => (
          <article key={agent.id} className="space-y-3 rounded-xl border p-5">
            <div className="flex items-center justify-between gap-4"><h3 className="font-semibold"><Link className="underline-offset-4 hover:underline" to={`/agents/${encodeURIComponent(agent.id)}`}>{agent.name}</Link></h3><span className="rounded-full border px-3 py-1 text-sm">{agentWorkStatus(agent)}</span></div>
            <p className="whitespace-pre-wrap break-words">{agent.purpose}</p>
            <p className="break-words text-sm text-muted-foreground">{modelChoiceLabel(agent.model_selection)}</p>
            <p className="break-all text-xs text-muted-foreground">Agent ID: {agent.id} · Purpose revision {agent.soul_revision}</p>
          </article>
        ))}
      </section>
    </div>
  );
}
