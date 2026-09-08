import { useEffect, useState } from "react";
import { Button } from "@nous-research/ui/ui/components/button";
import { fetchJSON } from "@/lib/api";
import { agentsEndpoint, autonomyLabels, type Agent, type AutonomySettings } from "@/lib/agent-native";

export function AgentAutonomySettings({ agentId }: { agentId: string }) {
  const [current, setCurrent] = useState<AutonomySettings | null>(null);
  const [level, setLevel] = useState(5);
  const [reload, setReload] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState(false);
  const endpoint = `${agentsEndpoint}/${encodeURIComponent(agentId)}/autonomy`;
  useEffect(() => {
    let active = true;
    void fetchJSON<AutonomySettings>(endpoint).then(value => {
      if (active) { setCurrent(value); setLevel(value.level); setError(false); setMessage(""); }
    }).catch(() => { if (active) { setError(true); setMessage("Autonomy settings unavailable. Reload to try again."); } });
    return () => { active = false; };
  }, [endpoint, reload]);
  async function save() {
    if (!current) return;
    setBusy(true); setMessage("");
    try {
      const agent = await fetchJSON<Agent>(endpoint, { method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ level, expected_revision: current.revision }) });
      setCurrent(agent.autonomy); setLevel(agent.autonomy.level); setError(false);
      setMessage("Saved. The new level applies to the next admitted work attempt.");
    } catch { setError(true); setMessage("Could not confirm the change. Reload settings before retrying."); }
    finally { setBusy(false); }
  }
  return <section aria-label="Agent autonomy settings" className="space-y-3 rounded-xl border p-5">
    <h2 className="text-lg font-semibold">Autonomy</h2>
    <label htmlFor="agent-autonomy" className="block text-sm font-medium">Eagerness to continue independently</label>
    <select id="agent-autonomy" value={level} disabled={!current || busy || error}
      className="w-full rounded-md border bg-background px-3 py-2"
      onChange={event => { setLevel(Number(event.target.value)); setMessage(""); }}>
      {Object.entries(autonomyLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
    </select>
    <p className="text-sm text-muted-foreground">Level 1 asks for acceptance after most deliverables. Level 5 keeps working across outputs and milestones, asking only for extremely consequential decisions, actions outside its authority, or choices unsafe to infer. Explicit owner and policy gates always apply.</p>
    <Button disabled={!current || busy || error || current.level === level} onClick={() => void save()}>Save autonomy level</Button>
    {message && <p role={error ? "alert" : "status"} className="text-sm">{message}</p>}
    {error && <Button disabled={busy} onClick={() => setReload(value => value + 1)}>Reload autonomy settings</Button>}
  </section>;
}
