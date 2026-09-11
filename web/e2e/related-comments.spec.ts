import {test,expect} from './fixtures';
const backend='http://127.0.0.1:19219';
const headers={'X-Hermes-Session-Token':'agent-native-local-e2e-only'};
test('native worker consults previous task discussion without losing current focus',async({page,request})=>{
  test.setTimeout(90000);
  await page.addInitScript(()=>{window.__HERMES_SESSION_TOKEN__='agent-native-local-e2e-only';});
  await request.put(`${backend}/__e2e__/plane-config`,{headers,data:{enabled:true}});
  const r=await request.post(`${backend}/api/agent-native/agents`,{headers,data:{request_id:crypto.randomUUID(),name:'Related discussion',purpose:'Continue the series. E2E_RELATED_COMMENTS',work:{timeout_seconds:180,max_iterations:10}}});
  expect(r.status()).toBe(201);const {id}=await r.json();const api=`${backend}/api/agent-native/agents/${id}`;
  try{
    await page.goto(`/agents/${id}`);
    await expect.poll(async()=>(await(await request.get(api,{headers})).json()).work?.state,{timeout:30000}).toBe('completed');
    const a=await(await request.get(api,{headers})).json();
    expect(a.work.focus.item_id).not.toBe(a.setup.discovery_item_id);
    expect(a.work.focus.name).toBe('Draft next story');
    await expect(page.getByText('Reviewed foundation while working on next story',{exact:false}).first()).toBeVisible();
  }finally{await request.post(`${api}/work/pause`,{headers});}
});
