import {test,expect} from '@playwright/test';
const backend='http://127.0.0.1:19219';
const headers={'X-Hermes-Session-Token':'agent-native-local-e2e-only'};
test('a normal run time limit remains eligible for the next cadence attempt',async({page,request})=>{
  test.setTimeout(60000);
  await page.addInitScript(()=>{window.__HERMES_SESSION_TOKEN__='agent-native-local-e2e-only';});
  await request.put(`${backend}/__e2e__/plane-config`,{headers,data:{enabled:true}});
  const r=await request.post(`${backend}/api/agent-native/agents`,{headers,data:{request_id:crypto.randomUUID(),name:'Bounded run',purpose:'Write a story.',work:{timeout_seconds:1,max_iterations:10}}});
  expect(r.status()).toBe(201);const a=await r.json();const api=`${backend}/api/agent-native/agents/${a.id}`;
  try{
    expect((await request.post(`${api}/cadence`,{headers,data:{expected_revision:1,enabled:true,interval_seconds:2}})).ok()).toBe(true);
    const first=a.work.id;
    await page.goto(`/agents/${a.id}?view=full`);
    await expect.poll(async()=>{
      const attempts=await(await request.get(`${api}/attempts`,{headers})).json();
      return attempts.length>=2&&attempts.some((attempt:{id:string,state:string})=>attempt.id===first&&attempt.state==='limit_reached');
    },{timeout:30000}).toBe(true);
    const cadence=page.getByRole('region',{name:'Thinking cadence',exact:true});
    await expect(cadence).not.toContainText('Check-ins blocked');
    await expect(cadence).toContainText('limit_reached');
  }finally{await request.post(`${api}/work/pause`,{headers});}
});

test('a settled failed attempt continues automatically on cadence',async({page,request})=>{
  test.setTimeout(60000);
  await page.addInitScript(()=>{window.__HERMES_SESSION_TOKEN__='agent-native-local-e2e-only';});
  await request.put(`${backend}/__e2e__/plane-config`,{headers,data:{enabled:false}});
  const r=await request.post(`${backend}/api/agent-native/agents`,{headers,data:{
    request_id:crypto.randomUUID(),name:'Self-recovering writer',purpose:'Write a story.',
    work:{timeout_seconds:30,max_iterations:1}}});
  expect(r.status()).toBe(201);const a=await r.json();const api=`${backend}/api/agent-native/agents/${a.id}`;
  try{
    expect((await request.post(`${api}/cadence`,{headers,data:{expected_revision:1,enabled:true,interval_seconds:2}})).ok()).toBe(true);
    await request.put(`${backend}/__e2e__/plane-config`,{headers,data:{enabled:true}});
    await expect.poll(async()=>{
      const attempts=await(await request.get(`${api}/attempts`,{headers})).json();
      return attempts.some((attempt:{state:string})=>attempt.state==='retryable_failure')&&attempts.length>=2;
    },{timeout:30000}).toBe(true);
    await page.goto(`/agents/${a.id}?view=full`);
    const cadence=page.getByRole('region',{name:'Thinking cadence',exact:true});
    await expect(cadence).toContainText('retryable_failure');
    await expect(cadence).not.toContainText('Check-ins blocked');
  }finally{await request.post(`${api}/work/pause`,{headers});}
});

test('a work-service restart retains the interrupted attempt and continues once',async({page,request})=>{
  test.setTimeout(60000);
  await page.addInitScript(()=>{window.__HERMES_SESSION_TOKEN__='agent-native-local-e2e-only';});
  await request.put(`${backend}/__e2e__/plane-config`,{headers,data:{enabled:true}});
  const marker='E2E_WRITER_HOLD_RESTART_CONTINUITY';
  const r=await request.post(`${backend}/api/agent-native/agents`,{headers,data:{
    request_id:crypto.randomUUID(),name:'Restarted writer',purpose:`Write a story. ${marker}`,
    work:{timeout_seconds:300,max_iterations:20}}});
  expect(r.status()).toBe(201);const a=await r.json();const api=`${backend}/api/agent-native/agents/${a.id}`;
  const first=a.work.id;
  try{
    expect((await request.post(`${api}/cadence`,{headers,data:{expected_revision:1,enabled:true,interval_seconds:2}})).ok()).toBe(true);
    await expect.poll(async()=>(await(await request.get(`${backend}/__e2e__/model-holds/${marker}`,{headers})).json()).entered,{timeout:30000}).toBe(true);
    const restarted=await request.post(`${backend}/__e2e__/restart-work-service`,{headers});
    expect(restarted.status()).toBe(200);
    await expect.poll(async()=>{
      const attempts=await(await request.get(`${api}/attempts`,{headers})).json();
      return attempts.length===2&&attempts.some((attempt:{id:string,state:string})=>attempt.id===first&&attempt.state==='interrupted');
    },{timeout:30000}).toBe(true);
    const attempts=await(await request.get(`${api}/attempts`,{headers})).json();
    expect(new Set(attempts.map((attempt:{id:string})=>attempt.id)).size).toBe(2);
    await page.goto(`/agents/${a.id}?view=full`);
    await expect(page.getByRole('region',{name:'Thinking cadence',exact:true})).not.toContainText('Check-ins blocked');
  }finally{await request.post(`${api}/work/pause`,{headers});}
});
