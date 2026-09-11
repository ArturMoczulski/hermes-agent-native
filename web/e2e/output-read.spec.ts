import {test,expect} from './fixtures';
const backend='http://127.0.0.1:19219';
const headers={'X-Hermes-Session-Token':'agent-native-local-e2e-only'};
test('native worker reviews full saved output and reassesses stale question without failing',async({page,request})=>{
  test.setTimeout(90000);
  await page.addInitScript(()=>{window.__HERMES_SESSION_TOKEN__='agent-native-local-e2e-only';});
  await request.put(`${backend}/__e2e__/plane-config`,{headers,data:{enabled:true}});
  const r=await request.post(`${backend}/api/agent-native/agents`,{headers,data:{request_id:crypto.randomUUID(),name:'Full story reviewer',purpose:'Review the entire saved story. E2E_OUTPUT_REVIEW',work:{timeout_seconds:180,max_iterations:18}}});
  expect(r.status()).toBe(201);const {id}=await r.json();const api=`${backend}/api/agent-native/agents/${id}`;
  try{
    await page.goto(`/agents/${id}`);
    await expect.poll(async()=>(await(await request.get(api,{headers})).json()).work?.state,{timeout:40000}).toBe('completed');
    await expect(page.getByText('Reviewed full story and reassessed changed criteria',{exact:false}).first()).toBeVisible();
    const a=await(await request.get(api,{headers})).json();
    expect(a.work.outputs.some((output:{byte_count:number})=>output.byte_count>18000)).toBe(true);
  }finally{await request.post(`${api}/work/pause`,{headers});}
});
