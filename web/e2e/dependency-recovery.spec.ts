
import {test,expect} from '@playwright/test';
const backend='http://127.0.0.1:19219';
const headers={'X-Hermes-Session-Token':'agent-native-local-e2e-only'};
test('temporary Plane outage waits then completes without an owner retry',async({page,request})=>{
  test.setTimeout(60000);
  await page.addInitScript(()=>{window.__HERMES_SESSION_TOKEN__='agent-native-local-e2e-only';});
  await request.put(backend+'/__e2e__/plane-config',{headers,data:{enabled:true,temporary_read_outage:true}});
  const r=await request.post(backend+'/api/agent-native/agents',{headers,data:{request_id:crypto.randomUUID(),name:'Outage recovery',purpose:'Review a complete saved output. E2E_OUTPUT_REVIEW',work:{timeout_seconds:45,max_iterations:18}}});
  expect(r.status()).toBe(201);const {id}=await r.json();const api=backend+'/api/agent-native/agents/'+id;
  try{
    await expect.poll(async()=>(await(await request.get(api,{headers})).json()).work.state,{timeout:25000}).toBe('completed');
    await page.goto('/agents/'+id);
    await expect(page.getByText('Waiting for Plane', {exact:false}).first()).toBeVisible({timeout:15000});
    const a=await(await request.get(api,{headers})).json();
    expect(a.work.events.some((e:{kind:string})=>e.kind==='work.dependency_recovered')).toBe(true);
    expect((await(await request.get(api+'/attempts',{headers})).json()).length).toBe(1);
    expect(a.work.outputs.length).toBe(1);
  }finally{await request.delete(api,{headers});}
});
