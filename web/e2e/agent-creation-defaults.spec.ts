import {test,expect} from '@playwright/test';

const backend='http://127.0.0.1:19219';
const headers={'X-Hermes-Session-Token':'agent-native-local-e2e-only'};

test('agent creation starts bounded work with collapsed 180 second and 50 step defaults',async({page,request})=>{
  await page.addInitScript(()=>{window.__HERMES_SESSION_TOKEN__='agent-native-local-e2e-only';});
  await request.put(`${backend}/__e2e__/plane-config`,{headers,data:{enabled:false}});
  await page.goto('/agents');
  await expect(page.getByLabel('Autonomy',{exact:true})).toHaveValue('3');
  await expect(page.getByLabel('Maximum run time (seconds)',{exact:true})).toBeHidden();
  await expect(page.getByText('3 minutes · 50 model steps',{exact:false})).toBeVisible();
  await page.getByLabel('Agent name').fill('Default bounded worker');
  await page.getByLabel('Purpose').fill('Develop a small reusable fantasy setting.');
  await page.getByRole('button',{name:'Create agent'}).click();
  await expect(page).toHaveURL(/\/agents\/[0-9a-f-]+$/);
  const id=page.url().split('/').pop()!;
  const agent=await(await request.get(`${backend}/api/agent-native/agents/${id}`,{headers})).json();
  expect(agent.work.limits).toEqual({timeout_seconds:180,max_iterations:50});
  expect(agent.autonomy.level).toBe(3);
  await expect(page.getByText('180 seconds · 50 model steps',{exact:true})).toBeVisible();
  await request.post(`${backend}/api/agent-native/agents/${id}/work/pause`,{headers});
});

test('owner chooses creation autonomy and revises it in agent details',async({page,request})=>{
  await page.addInitScript(()=>{window.__HERMES_SESSION_TOKEN__='agent-native-local-e2e-only';});
  await request.put(`${backend}/__e2e__/plane-config`,{headers,data:{enabled:false}});
  await page.goto('/agents');
  await page.getByLabel('Agent name').fill('Cautious worker');
  await page.getByLabel('Purpose').fill('Prepare reusable research notes.');
  await page.getByLabel('Autonomy',{exact:true}).selectOption('2');
  await page.getByRole('button',{name:'Create agent'}).click();
  await expect(page).toHaveURL(/\/agents\/[0-9a-f-]+$/);
  const id=page.url().split('/').pop()!;
  const setting=page.getByRole('region',{name:'Agent autonomy settings',exact:true});
  await expect(setting.getByLabel('Eagerness to continue independently')).toHaveValue('2');
  await setting.getByLabel('Eagerness to continue independently').selectOption('4');
  await setting.getByRole('button',{name:'Save autonomy level'}).click();
  await expect(setting).toContainText('next admitted work attempt');
  expect((await(await request.get(`${backend}/api/agent-native/agents/${id}`,{headers})).json()).autonomy.level).toBe(4);
  await request.post(`${backend}/api/agent-native/agents/${id}/work/pause`,{headers});
});

test('advanced creation limits can override both defaults',async({page})=>{
  await page.addInitScript(()=>{window.__HERMES_SESSION_TOKEN__='agent-native-local-e2e-only';});
  await page.goto('/agents');
  await page.getByText('Advanced work limits',{exact:false}).click();
  await expect(page.getByLabel('Maximum run time (seconds)',{exact:true})).toHaveValue('180');
  await expect(page.getByLabel('Maximum model steps',{exact:true})).toHaveValue('50');
});
