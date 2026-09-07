import { useEffect, useState } from "react";
import { Link } from "react-router";
import { Button } from "@nous-research/ui/ui/components/button";
import { ModelPickerDialog, type ModelOptionsResponse } from "@/components/ModelPickerDialog";
import { fetchJSON } from "@/lib/api";
import { agentModelsEndpoint, agentsEndpoint, modelChoiceLabel, type Agent, type DefaultAgentModel, type ModelChoice } from "@/lib/agent-native";

export function AgentModelPicker({ choice, title, actionLabel = "Save", scopeDescription, onApply, onClose }: {
  choice?: ModelChoice | null;
  title: string;
  actionLabel?: string;
  scopeDescription: string;
  onApply(choice: ModelChoice): Promise<void> | void;
  onClose(): void;
}) {
  return <ModelPickerDialog title={title} hideGlobal actionLabel={actionLabel} scopeDescription={scopeDescription}
    loader={async (options) => {
      const inventory = await fetchJSON<ModelOptionsResponse>(`${agentModelsEndpoint}/options${options?.refresh ? "?refresh=true" : ""}`);
      return { ...inventory, provider: choice?.provider ?? "", model: choice?.model ?? "",
        providers: inventory.providers?.map((provider) => ({ ...provider, is_current: provider.slug === choice?.provider })) };
    }}
    onApply={({ provider, model }) => onApply({ provider, model })} onClose={onClose} />;
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
