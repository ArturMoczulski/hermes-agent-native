import {test,expect} from '@playwright/test';
const backend='http://127.0.0.1:19219';
const headers={'X-Hermes-Session-Token':'agent-native-local-e2e-only'};
test('owner retries failed work once while retaining the old attempt',async({page,request})=>{
  test.setTimeout(60000);
  await page.addInitScript(()=>{window.__HERMES_SESSION_TOKEN__='agent-native-local-e2e-only';});
  await request.put(backend+'/__e2e__/plane-config',{headers,data:{enabled:true}});
  const r=await request.post(backend+'/api/agent-native/agents',{headers,data:{request_id:crypto.randomUUID(),name:'Recovery test',purpose:'Write a brief. E2E_OUTPUT_REVIEW',work:{timeout_seconds:40,max_iterations:1}}});
  expect(r.status()).toBe(201);
  const {id}=await r.json();const api=backend+'/api/agent-native/agents/'+id;
  try{
    await expect.poll(async()=>(await(await request.get(api,{headers})).json()).work.state,{timeout:30000}).toBe('failed');
    const old=(await(await request.get(api,{headers})).json()).work.id;
    await page.goto('/agents/'+id);
    const region=page.getByRole('region',{name:'Thinking cadence',exact:true});
    await region.getByRole('button',{name:'Retry failed work',exact:true}).click({timeout:10000});
    await expect(region).toContainText('Previous attempts and saved outputs are preserved');
    await page.route('**/api/agent-native/agents/'+id+'/work/retry',route=>route.fulfill({status:409,contentType:'application/json',body:JSON.stringify({detail:'Resolve pending or unknown Plane delivery before continuing work'})}),{times:1});
    await region.getByRole('button',{name:'Start recovery',exact:true}).click();
    await expect(region.getByRole('alert')).toContainText('Recovery was not confirmed');
    expect((await(await request.get(api+'/attempts',{headers})).json()).length).toBe(1);
    await region.getByRole('button',{name:'Start recovery',exact:true}).click();
    await expect.poll(async()=>(await(await request.get(api+'/attempts',{headers})).json()).length).toBe(2);
    const attempts=await(await request.get(api+'/attempts',{headers})).json();
    expect(attempts[1].id).toBe(old);expect(attempts[1].state).toBe('failed');
    expect(attempts[0].id).not.toBe(old);
    await expect(region).toContainText('Recovery requested');
  }finally{await request.delete(api,{headers});}
});
