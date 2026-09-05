import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Button } from "@nous-research/ui/ui/components/button";
import { Input } from "@nous-research/ui/ui/components/input";
import { Label } from "@nous-research/ui/ui/components/label";
import { fetchJSON } from "@/lib/api";
import { usePageHeader } from "@/contexts/usePageHeader";

type Agent = {
  id: string;
  name: string;
  purpose: string;
  soul_revision: number;
  execution: "not_started";
};
const endpoint = "/api/agent-native/agents";

export default function AgentsPage() {
  const { setTitle } = usePageHeader();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [name, setName] = useState("");
  const [purpose, setPurpose] = useState("");
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const pending = useRef<{ input: string; id: string } | null>(null);
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
    if (submitting.current || !name.trim() || !purpose.trim()) return;
    submitting.current = true;
    setSaving(true);
    setError("");
    setNotice("");
    const input = JSON.stringify({ name: name.trim(), purpose: purpose.trim() });
    if (pending.current?.input !== input) {
      pending.current = { input, id: crypto.randomUUID() };
    }
    try {
      const agent = await fetchJSON<Agent>(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...JSON.parse(input), request_id: pending.current.id }),
      });
      setAgents((existing) => [...existing.filter((a) => a.id !== agent.id), agent]);
      setName("");
      setPurpose("");
      pending.current = null;
      setNotice(`${agent.name} created. Work has not started.`);
    } catch {
      setError("Could not confirm creation. Retry with the same name and purpose to avoid a duplicate.");
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
        <p className="rounded-lg border p-3 text-sm">Agents created here are not started. Autonomous execution is not connected yet.</p>
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
        <Button type="submit" disabled={saving || loading || !name.trim() || !purpose.trim()}>{saving ? "Creating…" : "Create agent"}</Button>
      </form>
      {error && <div role="alert" className="space-y-2"><p>{error}</p><Button variant="outline" disabled={saving} onClick={() => { setLoading(true); setError(""); setReload((value) => value + 1); }}>Reload agents</Button></div>}
      <p role="status" className="text-sm">{notice}</p>
      <section aria-label="Agent list" className="space-y-4">
        <h2 className="text-lg font-semibold">Agents</h2>
        {loading ? <p>Loading agents…</p> : agents.length === 0 && !error ? <p>No agents yet. Create your first agent above.</p> : null}
        {agents.map((agent) => (
          <article key={agent.id} className="space-y-3 rounded-xl border p-5">
            <div className="flex items-center justify-between gap-4"><h3 className="font-semibold">{agent.name}</h3><span className="rounded-full border px-3 py-1 text-sm">Not started</span></div>
            <p className="whitespace-pre-wrap break-words">{agent.purpose}</p>
            <p className="break-all text-xs text-muted-foreground">Agent ID: {agent.id} · Purpose revision {agent.soul_revision}</p>
          </article>
        ))}
      </section>
    </div>
  );
}
