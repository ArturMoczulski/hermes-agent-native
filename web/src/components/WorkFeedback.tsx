import { useEffect, useRef, useState } from 'react';
import { fetchJSON } from '@/lib/api';
import { Button } from '@nous-research/ui/ui/components/button';
type Feedback = { id: string; text: string; status: 'pending' | 'handled'; response: string | null; applicable: boolean };
export function WorkFeedback({ agentId, revision }: { agentId: string; revision: number }) {
  const [text, setText] = useState('');
  const [rows, setRows] = useState<Feedback[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const receipt = useRef<{ id: string; text: string } | null>(null);
  useEffect(() => {
    let active = true;
    const load = async () => {
      try { const result = await fetchJSON<Feedback[]>(`/api/agent-native/agents/${agentId}/feedback`); if (active) setRows(result); }
      catch { if (active) setError('Feedback updates unavailable. Previously loaded receipts may be stale.'); }
    };
    void load(); const timer = setInterval(() => void load(), 2000);
    return () => { active = false; clearInterval(timer); };
  }, [agentId]);
  const send = async () => {
    setBusy(true); setError('');
    if (!receipt.current || receipt.current.text !== text) receipt.current = { id: crypto.randomUUID(), text };
    try {
      await fetchJSON(`/api/agent-native/agents/${agentId}/feedback`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
        request_id: receipt.current.id, text, expected_revision: revision }) });
      setText(''); receipt.current = null;
      setRows(await fetchJSON<Feedback[]>(`/api/agent-native/agents/${agentId}/feedback`));
    } catch { setError('Feedback was not confirmed. Retry unchanged text to reuse its receipt, or reload if the purpose changed.'); }
    finally { setBusy(false); }
  };
  return <section aria-label="Feedback for work" className="space-y-3 rounded-xl border p-5">
    <h2 className="text-lg font-semibold">Feedback for work</h2>
    <p className="text-sm text-muted-foreground">Direction for the agent's work, within its current purpose. This does not interrupt or resume work. Use Pause to stop immediately. Handling is the agent's report, not owner acceptance.</p>
    <label className="block text-sm">Direction for subsequent work
      <textarea className="mt-1 w-full rounded border bg-background p-2" value={text} maxLength={4000} disabled={busy} onChange={e => setText(e.target.value)} />
    </label>
    <Button disabled={busy || !text.trim()} onClick={() => void send()}>Send feedback</Button>
    {error && <p role="alert">{error}</p>}
    <p className="text-sm text-muted-foreground">Latest 20 receipts</p>
    <ul className="space-y-3">{rows.map(row => <li key={row.id} className="rounded border p-3 text-sm">
      <p className="whitespace-pre-wrap">{row.text}</p>
      <p>{!row.applicable ? 'Earlier purpose — not applicable' : row.status === 'handled' ? 'Agent reports handled' : 'Pending'}</p>
      {row.response && <p className="whitespace-pre-wrap">{row.response}</p>}
    </li>)}</ul>
  </section>;
}
