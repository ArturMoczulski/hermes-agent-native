import {test,expect} from '@playwright/test';
const backend='http://127.0.0.1:19219';
const headers={'X-Hermes-Session-Token':'agent-native-local-e2e-only'};
test('non-retryable failure is diagnosed without a meaningless owner retry',async({page,request})=>{
  test.setTimeout(60000);
  await page.addInitScript(()=>{window.__HERMES_SESSION_TOKEN__='agent-native-local-e2e-only';});
  await request.put(backend+'/__e2e__/plane-config',{headers,data:{enabled:true}});
  const r=await request.post(backend+'/api/agent-native/agents',{headers,data:{request_id:crypto.randomUUID(),name:'Recovery test',purpose:'Write a brief. E2E_FRAMEWORK_FAILURE',work:{timeout_seconds:40,max_iterations:10}}});
  expect(r.status()).toBe(201);
  const {id}=await r.json();const api=backend+'/api/agent-native/agents/'+id;
  try{
    expect((await request.post(api+'/cadence',{headers,data:{expected_revision:1,enabled:false,interval_seconds:60}})).ok()).toBe(true);
    await expect.poll(async()=>(await(await request.get(api,{headers})).json()).work.state,{timeout:30000}).toBe('failed');
    await page.goto('/agents/'+id+'?tab=work');
    const region=page.getByRole('region',{name:'Current work overview',exact:true});
    await expect(region).toContainText('failed without a safe automatic recovery path');
    await expect(region.getByRole('button',{name:'Retry failed work',exact:true})).toHaveCount(0);
    expect((await(await request.get(api+'/attempts',{headers})).json()).length).toBe(1);
  }finally{await request.delete(api,{headers});}
});
