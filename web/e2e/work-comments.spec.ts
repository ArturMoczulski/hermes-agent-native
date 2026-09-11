import {test,expect} from './fixtures';
const backend='http://127.0.0.1:19219';
const headers={'X-Hermes-Session-Token':'agent-native-local-e2e-only'};
test('agent reviews an incoming Plane comment and posts one correlated reply',async({page,request})=>{
  test.setTimeout(90000);
  await page.addInitScript(()=>{window.__HERMES_SESSION_TOKEN__='agent-native-local-e2e-only';});
  await request.put(`${backend}/__e2e__/plane-config`,{headers,data:{enabled:true}});
  const created=await request.post(`${backend}/api/agent-native/agents`,{headers,data:{request_id:crypto.randomUUID(),name:'Comment reviewer',purpose:'Review draft feedback. E2E_COMMENTS_HOLD',work:{timeout_seconds:180,max_iterations:12}}});
  expect(created.status()).toBe(201);
  const {id}=await created.json();
  const api=`${backend}/api/agent-native/agents/${id}`;
  const evidence=async()=>(await(await request.get(`${backend}/__e2e__/writer-evidence/${id}`,{headers})).json());
  try {
    await page.goto(`/agents/${id}`);
    await expect.poll(async()=>(await evidence()).model_requests.some((r:{hold_marker:string})=>r.hold_marker==='E2E_COMMENTS_HOLD'),{timeout:30000}).toBe(true);
    const comment=await(await request.post(`${backend}/__e2e__/comment/${id}`,{headers})).json();
    await request.post(`${backend}/__e2e__/release-model`,{headers,data:{marker:'E2E_COMMENTS_HOLD'}});
    await expect.poll(async()=>(await(await request.get(api,{headers})).json()).work.state,{timeout:30000}).toBe('completed');
    await expect.poll(async()=>(await evidence()).comments.filter((c:{comment_html:string})=>c.comment_html.includes('I will revise the draft')).length).toBe(1);
    const reply=(await evidence()).comments.find((c:{comment_html:string})=>c.comment_html.includes('I will revise the draft'));
    expect(reply.comment_html).toContain(comment.id);
    await page.reload();
    await expect(page.getByText(/I will revise the draft to address your comment/).first()).toBeVisible();
  } finally {
    await request.post(`${api}/work/pause`,{headers});
    await request.post(`${backend}/__e2e__/release-model`,{headers,data:{marker:'E2E_COMMENTS_HOLD'}});
  }
});
