import {useEffect,useState} from 'react';
import {fetchJSON} from '@/lib/api';
import {Button} from '@nous-research/ui/ui/components/button';
import {Input} from '@nous-research/ui/ui/components/input';

type Cadence={enabled:boolean;interval_seconds:number|null;next_due:string|null};
type Attempt={id:string;state:string;summary:string|null;created_at:string};
export function AgentCadence({agentId,revision}:{agentId:string;revision:number}){
  const [cadence,setCadence]=useState<Cadence>();
  const [attempts,setAttempts]=useState<Attempt[]>([]);
  const [seconds,setSeconds]=useState('');
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const api=`/api/agent-native/agents/${agentId}`;
  useEffect(()=>{
    let active=true;
    const load=async()=>{try{
      const [agent,history]=await Promise.all([fetchJSON<{cadence:Cadence}>(api),fetchJSON<Attempt[]>(`${api}/attempts`)]);
      if(active){setCadence(agent.cadence);setAttempts(history);}
    }catch{if(active)setError('Could not refresh cadence.');}};
    void load();const timer=setInterval(()=>{void load();},1500);
    return()=>{active=false;clearInterval(timer);};
  },[api]);
  async function save(enabled:boolean){
    setBusy(true);setError('');
    try{setCadence(await fetchJSON<Cadence>(`${api}/cadence`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({expected_revision:revision,interval_seconds:Number(seconds||cadence?.interval_seconds),enabled})}));}
    catch{setError('Could not update cadence. Check the interval and current work; paused, failed or uncertain work needs review.');}
    finally{setBusy(false);}
  }
  const blocked=cadence?.enabled&&['failed','unknown','paused','stopping'].includes(attempts[0]?.state);
  return <section aria-label="Thinking cadence" className="space-y-3 rounded-xl border p-5">
    <h2 className="text-lg font-semibold">Thinking cadence</h2>
    <p>{cadence?.enabled?`Enabled · every ${cadence.interval_seconds} seconds`:'Automatic check-ins are off'}</p>
    {blocked&&<p role="status">Check-ins blocked: the latest attempt {attempts[0]?.state==='failed'?'failed':`is ${attempts[0]?.state}`}. Review its activity and outcome. Enabled cadence does not restart stopped or uncertain work.</p>}
    {cadence?.enabled&&!blocked&&cadence.next_due&&<p>Next eligible check-in: {new Date(cadence.next_due).toLocaleString()}. Active work and unresolved outcomes can delay it.</p>}
    <p className="text-sm">Each check-in reviews progress and decides whether to work, ask or wait. It uses the existing run limits. Missed intervals produce at most one check-in; paused work does not restart.</p>
    <label htmlFor="cadence-seconds">Check-in interval (seconds)</label>
    <Input id="cadence-seconds" type="number" min={1} max={2592000} value={seconds} placeholder={String(cadence?.interval_seconds??'')} onChange={e=>setSeconds(e.target.value)}/>
    <Button disabled={busy||!Number(seconds||cadence?.interval_seconds)} onClick={()=>{void save(true);}}>Enable or update cadence</Button>
    <Button disabled={busy||!cadence?.enabled} onClick={()=>{void save(false);}}>Disable cadence</Button>
    {error&&<p role="alert">{error}</p>}
    <h3 className="font-semibold">Recent attempts</h3>
    <p className="text-sm">Latest 20 attempts, newest first.</p>
    <ul>{attempts.map(a=><li key={a.id} className="border-t py-2"><span>{a.state}</span> · <time>{new Date(a.created_at).toLocaleString()}</time><p>{a.summary}</p><code className="text-xs break-all">{a.id}</code></li>)}</ul>
  </section>;
}
