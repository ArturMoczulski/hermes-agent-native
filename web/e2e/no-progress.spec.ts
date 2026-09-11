import {test,expect} from './fixtures';

const backend='http://127.0.0.1:19219';
const headers={'X-Hermes-Session-Token':'agent-native-local-e2e-only'};

test('three unproductive cadence failures suspend automatic work for owner review',async({page,request})=>{
  test.setTimeout(60000);
  await page.addInitScript(()=>{window.__HERMES_SESSION_TOKEN__='agent-native-local-e2e-only';});
  await request.put(`${backend}/__e2e__/plane-config`,{headers,data:{enabled:false}});
  const created=await request.post(`${backend}/api/agent-native/agents`,{headers,data:{
    request_id:crypto.randomUUID(),name:'Looping writer',purpose:'Write a story.',
    work:{timeout_seconds:30,max_iterations:1}}});
  expect(created.status()).toBe(201);
  const agent=await created.json();
  const api=`${backend}/api/agent-native/agents/${agent.id}`;
  try{
    expect((await request.post(`${api}/cadence`,{headers,data:{
      expected_revision:1,enabled:true,interval_seconds:1}})).ok()).toBe(true);
    await request.put(`${backend}/__e2e__/plane-config`,{headers,data:{enabled:true}});
    await expect.poll(async()=>{
      const value=await(await request.get(api,{headers})).json();
      return {attempts:(await(await request.get(`${api}/attempts`,{headers})).json()).length,
        cadence:value.cadence.enabled,concerns:value.progress_concerns?.length??0};
    },{timeout:30000}).toEqual({attempts:3,cadence:false,concerns:1});

    await page.goto(`/agents/${agent.id}`);
    const concern=page.getByRole('region',{name:'Needs your attention',exact:true});
    await expect(concern).toContainText('Repeated work without progress');
    await expect(concern).toContainText('3 consecutive attempts');
    await concern.getByRole('button',{name:'Resume automatic work',exact:true}).click();
    await expect(concern).toContainText('Automatic work resumed');
    await expect.poll(async()=>(await(await request.get(api,{headers})).json()).progress_concerns[0].status).toBe('resolved');
  }finally{await request.post(`${api}/work/pause`,{headers});}
});
