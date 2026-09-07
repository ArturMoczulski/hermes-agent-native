import type { Agent } from '@/lib/agent-native';
import { useEffect, useState } from 'react';
import { fetchJSON } from '@/lib/api';
import { Button } from '@nous-research/ui/ui/components/button';
type Question = { id: string; item_id: string; question: string; answer: string | null; applicable: boolean };
function Answer({ question, agentId, revision, refresh, setup }: { question: Question; agentId: string; revision: number; refresh: () => void; setup: Agent["setup"] }) {
  const [text,setText]=useState('');
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  let itemUrl: string | undefined;
  try {
    const origin = new URL(setup?.plane_origin || '');
    if (['http:', 'https:'].includes(origin.protocol) && !origin.username && !origin.password && setup?.workspace_slug && setup.project_id)
      itemUrl = `${origin.origin}/${encodeURIComponent(setup.workspace_slug)}/projects/${encodeURIComponent(setup.project_id)}/issues/${encodeURIComponent(question.item_id)}/`;
  } catch { /* Setup has no verified Plane address. */ }
  const send=async()=>{
    setBusy(true);setError('');
    try {
      await fetchJSON(`/api/agent-native/agents/${agentId}/questions/${question.id}/answer`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({expected_revision:revision,answer:text})});
      refresh();
    } catch {setError('Answer not confirmed. Retry unchanged text or refresh to review an existing answer.');}
    finally {setBusy(false);}
  };
  return <article className="space-y-2 rounded border p-3 text-sm">
    <p>{question.question}</p><p className="text-muted-foreground">{itemUrl ? <a className="underline" href={itemUrl}>Open affected work item</a> : `Work item: ${question.item_id}`}</p>
    {!question.applicable && <p>Earlier purpose — no longer applicable</p>}
    {question.answer!==null ? <><p>Answered</p><p className="whitespace-pre-wrap">{question.answer}</p></> : question.applicable && <>
      <label className="block">Your answer<textarea className="mt-1 w-full rounded border bg-background p-2" disabled={busy} maxLength={4000} value={text} onChange={e=>setText(e.target.value)} /></label>
      <Button disabled={busy||!text.trim()} onClick={()=>void send()}>Send answer</Button>
    </>}
    {error && <p role="alert">{error}</p>}
  </article>;
}
export function WorkQuestions({agentId,revision,setup}:{agentId:string;revision:number;setup:Agent["setup"]}){
  const [questions,setQuestions]=useState<Question[]>([]);
  const [error,setError]=useState(false);
  const [reload,setReload]=useState(0);
  useEffect(()=>{
    let active=true;
    const load=async()=>{try {const rows=await fetchJSON<Question[]>(`/api/agent-native/agents/${agentId}/questions`);if(active){setQuestions(rows);setError(false);}}catch{if(active)setError(true);}};
    void load();const timer=setInterval(()=>void load(),2000);
    return()=>{active=false;clearInterval(timer);};
  },[agentId,reload]);
  return <section aria-label="Questions for you" className="space-y-3 rounded-xl border p-5">
    <h2 className="text-lg font-semibold">Questions for you</h2>
    <p className="text-sm text-muted-foreground">Up to 20 questions, unanswered first. Answers are retained without restarting paused or completed work. The agent checks task applicability before using them.</p>
    {error && <p role="alert">Question updates unavailable; displayed records may be stale.</p>}
    {!questions.length && !error && <p className="text-sm">No questions recorded.</p>}
    {questions.map(q=><Answer key={q.id} setup={setup} question={q} agentId={agentId} revision={revision} refresh={()=>setReload(n=>n+1)} />)}
  </section>;
}
