// Read-only browser verification of this local deployment using existing owner-session cookies.
const {chromium,expect}=require('@playwright/test');
const fs=require('fs'); const os=require('os');
(async()=>{
 const h=os.homedir()+'/.local/share/agent-native/plane/';
 const p=JSON.parse(fs.readFileSync(h+'planning-context.json'));
 const cookies=JSON.parse(fs.readFileSync(h+'owner-cookies.json'));
 const browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || undefined});
 try {
 const context=await browser.newContext({viewport:{width:1440,height:1000}});
 await context.addCookies(Object.entries(cookies).map(([name,value])=>({name,value,url:p.base_url})));
 const page=await context.newPage();
 await page.goto(p.base_url+'/agent-native/projects/'+p.project_id+'/issues/',{waitUntil:'domcontentloaded'});
 try { await expect(page.getByText('Run Plane locally and establish the Builder planning home',{exact:true})).toBeVisible({timeout:12000}); } catch(e) { console.log('Visible page:',page.url(),(await page.locator('body').innerText()).slice(0,3500)); await page.screenshot({path:h+'ui-check.png'}); throw e; }
 await expect(page.getByText('Implement scoped Plane planning operations for managed agents',{exact:true})).toBeVisible();
 await page.screenshot({path:h+'board-verified.png',fullPage:true});
 console.log('PASS: owner browser sees API-created project and backlog',page.url());
 await page.goto(p.base_url+'/agent-native/projects/'+p.project_id+'/cycles/'+p.cycle_id+'/',{waitUntil:'domcontentloaded'});
 await expect(page.getByText('Run Plane locally and establish the Builder planning home',{exact:true})).toBeVisible({timeout:30000});
 await expect(page.getByText('Verify Plane backup, restore and reconnect behavior',{exact:true})).toBeVisible();
 console.log('PASS: owner browser sees first-cycle work');
 } finally {await browser.close()}
})().catch(e=>{console.error(e.message);process.exit(1)});
