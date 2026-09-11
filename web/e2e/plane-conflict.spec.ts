import {test,expect} from './fixtures';
const backend='http://127.0.0.1:19219';
const headers={'X-Hermes-Session-Token':'agent-native-local-e2e-only'};
test('native work rereads a rejected conflict and completes the same attempt',async({page,request})=>{
  test.setTimeout(90000);
  await page.addInitScript(()=>{window.__HERMES_SESSION_TOKEN__='agent-native-local-e2e-only';});
  await request.put(`${backend}/__e2e__/plane-config`,{headers,data:{enabled:true}});
  const created=await request.post(`${backend}/api/agent-native/agents`,{headers,data:{request_id:crypto.randomUUID(),name:'Conflict recovery',purpose:'Plan useful work. E2E_CONFLICT_RECOVERY',work:{timeout_seconds:180,max_iterations:12}}});
  expect(created.status()).toBe(201);
  const {id}=await created.json();const api=`${backend}/api/agent-native/agents/${id}`;
  try{
    await page.goto(`/agents/${id}`);
    await expect.poll(async()=>(await(await request.get(api,{headers})).json()).work?.state,{timeout:45000}).toBe('completed');
    const a=await(await request.get(api,{headers})).json();
    expect(a.work.events.some((e:{kind:string})=>e.kind==='work.conflict')).toBe(true);
    expect(a.work.focus.cycle_id).toBeTruthy();
    await expect(page.getByText('Recovered from refreshed conflict state',{exact:false}).first()).toBeVisible();
    expect(a.work.model_calls).toBeLessThanOrEqual(10);
    expect(await(await request.get(`${api}/attempts`,{headers})).json()).toHaveLength(1);
  }finally{await request.post(`${api}/work/pause`,{headers});}
});
