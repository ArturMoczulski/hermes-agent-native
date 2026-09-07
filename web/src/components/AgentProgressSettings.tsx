import { useEffect, useState } from "react";
import { Button } from "@nous-research/ui/ui/components/button";
import { fetchJSON } from "@/lib/api";
import { agentsEndpoint } from "@/lib/agent-native";

type Settings = { verbosity: "concise" | "standard" | "detailed"; revision: number };
export function AgentProgressSettings({ agentId }: { agentId: string }) {
  const [current, setCurrent] = useState<Settings | null>(null);
  const [choice, setChoice] = useState<Settings["verbosity"]>("standard");
  const [reload, setReload] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState(false);
  const endpoint = `${agentsEndpoint}/${encodeURIComponent(agentId)}/progress-settings`;
  useEffect(() => {
    let active = true;
    void fetchJSON<Settings>(endpoint).then(value => {
      if (active) { setCurrent(value); setChoice(value.verbosity); setError(false); setMessage(""); }
    }).catch(() => { if (active) { setError(true); setMessage("Reporting settings unavailable. Reload to try again."); } });
    return () => { active = false; };
  }, [endpoint, reload]);
  async function save() {
    if (!current) return;
    setBusy(true); setMessage("");
    try {
      const value = await fetchJSON<Settings>(endpoint, { method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ verbosity: choice, expected_revision: current.revision }) });
      setCurrent(value); setChoice(value.verbosity); setError(false); setMessage("Saved. Applies to subsequent progress reports.");
    } catch { setError(true); setMessage("Could not confirm the change. Reload settings before retrying."); }
    finally { setBusy(false); }
  }
  return <section aria-label="Progress reporting settings" className="space-y-3 rounded-xl border p-5">
    <h2 className="text-lg font-semibold">Progress reporting settings</h2>
    <label htmlFor="progress-verbosity" className="block text-sm font-medium">Progress verbosity</label>
    <select id="progress-verbosity" value={choice} disabled={!current || busy || error}
      className="w-full rounded-md border bg-background px-3 py-2"
      onChange={event => { setChoice(event.target.value as Settings["verbosity"]); setMessage(""); }}>
      <option value="concise">Concise</option><option value="standard">Standard</option><option value="detailed">Detailed</option>
    </select>
    <p className="text-sm text-muted-foreground">Standard includes meaningful checkpoints. Detailed adds smaller updates. Concise skips those updates; work selection and blockers are always reported. Reports summarize work, not private reasoning.</p>
    <Button disabled={!current || busy || error || current.verbosity === choice} onClick={() => void save()}>Save reporting settings</Button>
    {message && <p role={error ? "alert" : "status"} className="text-sm">{message}</p>}
    {error && <Button disabled={busy} onClick={() => setReload(value => value + 1)}>Reload reporting settings</Button>}
  </section>;
}
