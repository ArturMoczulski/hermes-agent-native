import {test,expect} from '@playwright/test';
const backend='http://127.0.0.1:19219';
const headers={'X-Hermes-Session-Token':'agent-native-local-e2e-only'};
test('enabled cadence explains why a stopped attempt cannot continue',async({page,request})=>{
  test.setTimeout(60000);
  await page.addInitScript(()=>{window.__HERMES_SESSION_TOKEN__='agent-native-local-e2e-only';});
  await request.put(`${backend}/__e2e__/plane-config`,{headers,data:{enabled:true}});
  const r=await request.post(`${backend}/api/agent-native/agents`,{headers,data:{request_id:crypto.randomUUID(),name:'Bounded run',purpose:'Write a story.',work:{timeout_seconds:1,max_iterations:10}}});
  expect(r.status()).toBe(201);const a=await r.json();const api=`${backend}/api/agent-native/agents/${a.id}`;
  try{
    expect((await request.post(`${api}/cadence`,{headers,data:{expected_revision:1,enabled:true,interval_seconds:2}})).ok()).toBe(true);
    await page.goto(`/agents/${a.id}`);
    await expect.poll(async()=>(await(await request.get(api,{headers})).json()).work.state,{timeout:30000}).toBe('paused');
    const cadence=page.getByRole('region',{name:'Thinking cadence',exact:true});
    await expect(cadence).toContainText('Check-ins blocked: the latest attempt is paused.');
    await expect(cadence).not.toContainText('Next eligible check-in:');
  }finally{await request.post(`${api}/work/pause`,{headers});}
});
