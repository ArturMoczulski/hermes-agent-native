import { useEffect, useState } from "react";
import { Link } from "react-router";
import { Button } from "@nous-research/ui/ui/components/button";
import { ModelPickerDialog, type ModelOptionsResponse } from "@/components/ModelPickerDialog";
import { fetchJSON } from "@/lib/api";
import { agentModelsEndpoint, agentsEndpoint, modelChoiceLabel, reasoningEffortLabel, type Agent, type DefaultAgentModel, type ModelChoice } from "@/lib/agent-native";

export function AgentModelPicker({ choice, title, actionLabel = "Save", scopeDescription, onApply, onClose }: {
  choice?: ModelChoice | null;
  title: string;
  actionLabel?: string;
  scopeDescription: string;
  onApply(choice: ModelChoice): Promise<void> | void;
  onClose(): void;
}) {
  const [effort, setEffort] = useState(choice?.reasoning_effort ?? "default");
  const [capabilities, setCapabilities] = useState<ReasoningCapabilities | null>(null);
  return <ModelPickerDialog title={title} hideGlobal selectCurrentModel actionLabel={actionLabel} scopeDescription={scopeDescription}
    selectionAllowed={(selection) => capabilities?.key === reasoningKey(selection) && capabilities.efforts.includes(effort)}
    selectionControls={(selection) => <AgentReasoningControl selection={selection} effort={effort} onChange={setEffort} onLoaded={setCapabilities} />}
    loader={async (options) => {
      const inventory = await fetchJSON<ModelOptionsResponse>(`${agentModelsEndpoint}/options${options?.refresh ? "?refresh=true" : ""}`);
      return { ...inventory, provider: choice?.provider ?? "", model: choice?.model ?? "",
        providers: inventory.providers?.map((provider) => ({ ...provider, is_current: provider.slug === choice?.provider })) };
    }}
    onApply={({ provider, model }) => onApply({ provider, model, reasoning_effort: effort })} onClose={onClose} />;
}

type ReasoningCapabilities = { key: string; efforts: string[]; default_label: string; message: string | null };
function reasoningKey(selection: ModelChoice): string { return JSON.stringify([selection.provider, selection.model]); }

function AgentReasoningControl({ selection, effort, onChange, onLoaded }: {
  selection: ModelChoice; effort: string; onChange(value: string): void; onLoaded(value: ReasoningCapabilities): void;
}) {
  const { provider, model } = selection;
  const key = reasoningKey(selection);
  const [loaded, setLoaded] = useState<{ key: string; options?: ReasoningCapabilities; error?: boolean } | null>(null);
  const [reload, setReload] = useState(0);
  const current = loaded?.key === key ? loaded : null;
  useEffect(() => {
    if (!provider || !model) return;
    let active = true;
    void fetchJSON<Omit<ReasoningCapabilities, "key">>(`${agentModelsEndpoint}/reasoning?${new URLSearchParams({ provider, model })}`)
      .then((result) => {
        if (!Array.isArray(result.efforts) || !result.efforts.includes("default")) throw new Error("Invalid reasoning options");
        if (active) {
          const options = { ...result, key };
          setLoaded({ key, options }); onLoaded(options);
        }
      }).catch(() => {
        if (active) {
          setLoaded({ key, error: true });
          onLoaded({ key, efforts: [], default_label: "Hermes default", message: null });
        }
      });
    return () => { active = false; };
  }, [provider, model, key, reload, onLoaded]);
  if (!provider || !model) return <p className="text-xs text-muted-foreground">Choose a model to configure its reasoning effort.</p>;
  if (current?.error) return <div role="alert" className="space-y-2 text-sm">
    <p>Could not load reasoning options for this model. Check the connection and retry.</p>
    <Button onClick={() => setReload((value) => value + 1)}>Reload reasoning options</Button>
  </div>;
  const options = current?.options;
  const allowed = options?.efforts.includes(effort);
  return <div className="space-y-2 text-sm">
    <label className="font-medium" htmlFor="agent-reasoning-effort">Reasoning effort</label>
    <select id="agent-reasoning-effort" value={effort} disabled={!options}
      className="w-full rounded-md border bg-background px-3 py-2" onChange={(event) => onChange(event.target.value)}>
      {!allowed && <option value={effort} disabled>{reasoningEffortLabel(effort)}{options ? " — not supported" : ""}</option>}
      {options?.efforts.map((value) => <option key={value} value={value}>{value === "default" ? options.default_label : reasoningEffortLabel(value)}</option>)}
    </select>
    {!options && <p role="status" className="text-xs text-muted-foreground">Loading supported reasoning levels…</p>}
    {options && !allowed && <p role="alert">Choose a supported reasoning effort for this model. Your previous choice has not been changed.</p>}
    {options?.message && <p className="text-xs text-muted-foreground">{options.message}</p>}
    <p className="text-xs text-muted-foreground">Higher effort can take longer and use more model tokens. Hermes default keeps the native behavior for this model; it does not mean reasoning is off.</p>
  </div>;
}

export function DefaultAgentModelControls({ onChange }: { onChange(model: DefaultAgentModel): void }) {
  const [current, setCurrent] = useState<DefaultAgentModel | null>(null);
  const [editing, setEditing] = useState<DefaultAgentModel | null>(null);
  const [error, setError] = useState(false);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let active = true;
    void fetchJSON<DefaultAgentModel>(`${agentModelsEndpoint}/default`).then((model) => {
      if (active) { setCurrent(model); onChange(model); setError(false); }
    }).catch(() => { if (active) setError(true); });
    return () => { active = false; };
  }, [reload, onChange]);
  return <section aria-label="Default agent model" className="space-y-3 rounded-xl border p-5">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h2 className="text-lg font-semibold">Default agent model</h2>
      <Button disabled={!current || error} onClick={() => setEditing(current)}>Change default model</Button>
    </div>
    <p className="break-words text-sm">{current ? modelChoiceLabel(current) : error ? "Default unavailable" : "Loading default…"}</p>
    <p className="text-sm text-muted-foreground">Copied into newly created agents. Existing agents keep their own selection when this default changes.</p>
    <Link to="/models" className="text-sm underline underline-offset-4">Manage provider connections</Link>
    {error && <div role="alert" className="space-y-2"><p>Could not load the default model. Check your connection and retry.</p><Button onClick={() => setReload((value) => value + 1)}>Reload default</Button></div>}
    {editing && <AgentModelPicker choice={editing} title="Choose the default agent model" scopeDescription="Applies only to agents created afterward."
      onClose={() => setEditing(null)} onApply={async (choice) => {
        try {
          const model = await fetchJSON<DefaultAgentModel>(`${agentModelsEndpoint}/default`, {
            method: "PUT", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...choice, expected_revision: editing.revision }),
          });
          setCurrent(model); onChange(model);
        } catch {
          setReload((value) => value + 1);
          throw new Error("Could not confirm the default change. Close and reopen this picker to review the latest setting before retrying.");
        }
      }} />}
  </section>;
}

export function AgentModelControls({ agent, onMutationStart, onUpdate }: {
  agent: Agent;
  onMutationStart(): void;
  onUpdate(agent: Agent): void;
}) {
  const [editing, setEditing] = useState<{ choice: ModelChoice | null; revision: number } | null>(null);
  return <section aria-label="Agent model" className="space-y-3 rounded-xl border p-5">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h2 className="text-lg font-semibold">Agent model</h2>
      <Button onClick={() => setEditing({ choice: agent.model_selection ?? null, revision: agent.model_selection?.revision ?? 0 })}>Change agent model</Button>
    </div>
    <p className="break-words text-sm">{modelChoiceLabel(agent.model_selection)}</p>
    {agent.model_selection && <p className="text-xs text-muted-foreground">Selection revision {agent.model_selection.revision} · {agent.model_selection.source === "default" ? "Copied from the creation default" : agent.model_selection.source === "legacy" ? "Retained from existing configuration" : "Chosen for this agent"}</p>}
    <p className="text-sm text-muted-foreground">Applies to the next work run or chat message. An active attempt keeps the model it started with. Identity, purpose, planning and conversation history stay with this agent.</p>
    {!!agent.model_activity?.length && <dl className="grid gap-2 text-sm sm:grid-cols-[auto_1fr]">
      {agent.model_activity.map((activity) => <div key={activity.kind} className="contents">
        <dt className="text-muted-foreground">{activity.kind === "work" ? "Latest work attempt" : "Latest chat message"}</dt>
        <dd className="break-words">{modelChoiceLabel(activity)} <span className="text-xs text-muted-foreground">· selection {activity.revision}</span></dd>
      </div>)}
    </dl>}
    {editing && <AgentModelPicker choice={editing.choice} title="Choose this agent’s model" scopeDescription="Applies to the next work run or chat message."
      onClose={() => setEditing(null)} onApply={async (choice) => {
        onMutationStart();
        try {
          onUpdate(await fetchJSON<Agent>(`${agentsEndpoint}/${encodeURIComponent(agent.id)}/model`, {
            method: "PUT", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...choice, expected_revision: editing.revision }),
          }));
        } catch {
          throw new Error("Could not confirm the model change. Close and reopen this picker to review the latest setting before retrying.");
        }
      }} />}
  </section>;
}
