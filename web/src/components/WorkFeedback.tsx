import { useEffect, useRef, useState } from 'react';
import { fetchJSON } from '@/lib/api';
import { Button } from '@nous-research/ui/ui/components/button';
type Feedback = { id: string; text: string; status: 'pending' | 'handled'; response: string | null; applicable: boolean; output_id?: string | null; output_version?: number | null };
export function WorkFeedback({ agentId, revision, outputId, outputVersion }: { agentId: string; revision: number; outputId?: string; outputVersion?: number }) {
  const [text, setText] = useState('');
  const [rows, setRows] = useState<Feedback[]>([]);
  const [page, setPage] = useState(0);
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
  useEffect(() => { setPage(0); }, [outputId, outputVersion]);
  const send = async () => {
    setBusy(true); setError('');
    if (!receipt.current || receipt.current.text !== text) receipt.current = { id: crypto.randomUUID(), text };
    try {
      await fetchJSON(`/api/agent-native/agents/${agentId}/feedback`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
        request_id: receipt.current.id, text, expected_revision: revision, ...(outputId ? { output_id: outputId, output_version: outputVersion ?? 1 } : {}) }) });
      setText(''); receipt.current = null;
      setRows(await fetchJSON<Feedback[]>(`/api/agent-native/agents/${agentId}/feedback`));
    } catch { setError('Feedback was not confirmed. Retry unchanged text to reuse its receipt, or reload if the purpose changed.'); }
    finally { setBusy(false); }
  };
  const receipts = outputId ? rows.filter((row) => row.output_id === outputId && row.output_version === (outputVersion ?? 1)) : rows;
  const pageSize = 5;
  const pageCount = Math.max(1, Math.ceil(receipts.length / pageSize));
  const currentPage = Math.min(page, pageCount - 1);
  const visibleReceipts = receipts.slice(currentPage * pageSize, (currentPage + 1) * pageSize);
  return <section aria-label="Feedback for work" className="space-y-3 rounded-xl border p-5">
    <h2 className="text-lg font-semibold">{outputId ? 'Feedback on this output' : 'Feedback for work'}</h2>
    <p className="text-sm text-muted-foreground">{outputId ? 'Your feedback is attached to this exact output version.' : "Direction for the agent's work, within its current purpose."} It does not create an approval gate or replace owner acceptance.</p>
    <label className="block text-sm">Direction for subsequent work
      <textarea className="mt-1 w-full rounded border bg-background p-2" value={text} maxLength={4000} disabled={busy} onChange={e => setText(e.target.value)} />
    </label>
    <Button disabled={busy || !text.trim()} onClick={() => void send()}>Send feedback</Button>
    {error && <p role="alert">{error}</p>}
    <p className="text-sm text-muted-foreground">Feedback receipts</p>
    {!visibleReceipts.length && <p className="text-sm text-muted-foreground">No feedback receipts for this output yet.</p>}
    <ul className="space-y-3">{visibleReceipts.map(row => <li key={row.id} className="rounded border p-3 text-sm">
      <p className="whitespace-pre-wrap">{row.text}</p>
      <p>{!row.applicable ? 'Earlier purpose — not applicable' : row.status === 'handled' ? 'Agent reports handled' : 'Pending'}</p>
      {row.response && <p className="whitespace-pre-wrap">{row.response}</p>}
    </li>)}</ul>
    {receipts.length > pageSize && <nav aria-label="Feedback receipt pages" className="flex items-center justify-between text-sm"><Button disabled={currentPage === 0} onClick={() => setPage(value => Math.max(0, value - 1))}>Previous</Button><span>Page {currentPage + 1} of {pageCount}</span><Button disabled={currentPage === pageCount - 1} onClick={() => setPage(value => Math.min(pageCount - 1, value + 1))}>Next</Button></nav>}
  </section>;
}
