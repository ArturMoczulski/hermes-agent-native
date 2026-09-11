import { test, expect } from './fixtures';
const backend='http://127.0.0.1:19219';
const headers={'X-Hermes-Session-Token':'agent-native-local-e2e-only'};
test('agent asks a question and uses the retained owner answer in saved work',async({page,request})=>{
  test.setTimeout(90000);
  await page.addInitScript(()=>{window.__HERMES_SESSION_TOKEN__='agent-native-local-e2e-only';});
  await request.put(`${backend}/__e2e__/plane-config`,{headers,data:{enabled:true}});
  const created=await request.post(`${backend}/api/agent-native/agents`,{headers,data:{request_id:crypto.randomUUID(),name:'Asking writer',purpose:'Write drafts. E2E_QUESTION_HOLD',work:{timeout_seconds:180,max_iterations:12}}});
  expect(created.status()).toBe(201);
  const {id}=await created.json();
  const api=`${backend}/api/agent-native/agents/${id}`;
  try {
    await page.goto(`/agents/${id}`);
    const questions=page.getByRole('region',{name:'Needs your answer',exact:true});
    await expect(questions).toContainText('What kind of ending would you like?',{timeout:30000});
    const overview=page.getByRole('region',{name:'Current work overview',exact:true});
    await expect(overview).toContainText('Stage: Working');
    await expect(overview.getByRole('link',{name:'Discover purpose and plan first work'})).toHaveAttribute('href',/\/issues\/[0-9a-f-]+\/$/);
    expect(await questions.evaluate((question, current) => Boolean(question.compareDocumentPosition(current as Node) & Node.DOCUMENT_POSITION_FOLLOWING), await overview.elementHandle())).toBe(true);
    await expect(questions.getByRole('link',{name:'Open affected work item'})).toHaveAttribute('href',/\/issues\/[0-9a-f-]+\/$/);
    await expect.poll(async()=>{const e=await(await request.get(`${backend}/__e2e__/writer-evidence/${id}`,{headers})).json();return e.comments.filter((c:{comment_html:string})=>c.comment_html.includes('What kind of ending would you like?')).length;}).toBe(1);
    await questions.getByLabel('Your answer').fill('A hopeful ending with a reunited family.');
    await questions.getByRole('button',{name:'Send answer'}).click();
    await expect(questions).not.toBeVisible();
    await page.getByRole('link',{name:'Full view'}).click();
    const history=page.getByRole('region',{name:'Questions for you',exact:true});
    await expect(history).toContainText('Answered');
    await page.reload();
    await expect(history).toContainText('A hopeful ending with a reunited family.');
    await expect(history.getByText('What kind of ending would you like?',{exact:true})).toHaveCount(1);
    await request.post(`${backend}/__e2e__/release-model`,{headers,data:{marker:'E2E_QUESTION_HOLD'}});
    await expect.poll(async()=>(await(await request.get(api,{headers})).json()).work.state,{timeout:30000}).toBe('completed');
    const output=(await(await request.get(api,{headers})).json()).work.outputs[0];
    await page.goto(`/agents/${id}?output=${output.output_id}&version=1`);
    await expect(page.getByRole('region',{name:'Recent outputs',exact:true})).toContainText('A hopeful ending with a reunited family.');
  } finally {
    await request.post(`${api}/work/pause`,{headers});
    await request.post(`${backend}/__e2e__/release-model`,{headers,data:{marker:'E2E_QUESTION_HOLD'}});
  }
});
