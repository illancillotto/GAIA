const { chromium } = require('@playwright/test');
const fs = require('fs');
const path = require('path');
const outDir = path.join(process.cwd(), '..', 'reports', 'mobile-friendly-audit');
fs.mkdirSync(outDir, { recursive: true });
const username = process.env.PLAYWRIGHT_ADMIN_USERNAME;
const password = process.env.PLAYWRIGHT_ADMIN_PASSWORD;
if (!username || !password) {
  throw new Error('Set PLAYWRIGHT_ADMIN_USERNAME and PLAYWRIGHT_ADMIN_PASSWORD to run mobile audit.');
}
const pages = [
  ['/', 'home'], ['/me','me'], ['/catasto','catasto'], ['/ruolo','ruolo'], ['/ruolo/tributi','ruolo-tributi'], ['/gis/catalogo','gis-catalogo'], ['/nas-control','nas-control']
];
(async()=>{
 const browser = await chromium.launch({headless:true});
 const page = await browser.newPage({ viewport:{width:390,height:844}, deviceScaleFactor:2, isMobile:true });
 const consoleMessages=[];
 page.on('console', msg => { if(['error','warning'].includes(msg.type())) consoleMessages.push({type:msg.type(), text:msg.text(), url:page.url()}); });
 page.on('pageerror', err => consoleMessages.push({type:'pageerror', text:String(err), url:page.url()}));
 const results=[];
 await page.goto('http://127.0.0.1:8080/login', {waitUntil:'networkidle'}).catch(()=>{});
 const loginMetrics = await page.evaluate(() => ({
   path: location.pathname,
   innerWidth,
   scrollWidth: document.documentElement.scrollWidth,
   bodyScrollWidth: document.body.scrollWidth,
   viewportMeta: document.querySelector('meta[name="viewport"]')?.getAttribute('content') || null,
   headerNavVisible: [...document.querySelectorAll('header nav')].some(e=>e.getBoundingClientRect().width>0),
 }));
 await page.screenshot({ path: path.join(outDir,'login-mobile.png'), fullPage:true });
 results.push({name:'login', ...loginMetrics, hasSidebar:false, visibleInteractiveCount: await page.locator('a:visible, button:visible, input:visible, select:visible').count(), wideElements: []});
 await page.getByLabel('Username o email').fill(username);
 await page.locator('input#password').fill(password);
 await page.getByRole('button', { name: 'Accedi alla piattaforma' }).click();
 await page.waitForURL('**/', {timeout:20000});
 for(const [p,name] of pages){
   await page.goto('http://127.0.0.1:8080'+p, {waitUntil:'domcontentloaded'});
   await page.waitForLoadState('networkidle', {timeout:10000}).catch(()=>{});
   await page.screenshot({ path: path.join(outDir, name+'-mobile.png'), fullPage:true });
   const metrics = await page.evaluate(() => {
     const visible = sel => [...document.querySelectorAll(sel)].filter(el=>{const r=el.getBoundingClientRect(); const s=getComputedStyle(el); return r.width>0&&r.height>0&&s.visibility!=='hidden'&&s.display!=='none'});
     const sidebar=[...document.querySelectorAll('aside')].find(el=>{const r=el.getBoundingClientRect(); const s=getComputedStyle(el); return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden'});
     const sr=sidebar?.getBoundingClientRect();
     const topbar=document.querySelector('header'); const tr=topbar?.getBoundingClientRect();
     const wide=[...document.body.querySelectorAll('*')].map(el=>{const r=el.getBoundingClientRect(); const s=getComputedStyle(el); return {tag:el.tagName.toLowerCase(), text:(el.textContent||'').replace(/\s+/g,' ').trim().slice(0,100), className: typeof el.className === 'string' ? el.className.slice(0,160) : '', left:Math.round(r.left), right:Math.round(r.right), width:Math.round(r.width), display:s.display, overflowX:s.overflowX};}).filter(i=>i.width>0 && (i.right>innerWidth+2 || i.left<-2)).slice(0,12);
     return {path:location.pathname, innerWidth, scrollWidth:document.documentElement.scrollWidth, bodyScrollWidth:document.body.scrollWidth, hasSidebar:!!sidebar, sidebarWidth:sr?Math.round(sr.width):null, sidebarRight:sr?Math.round(sr.right):null, topbarHeight:tr?Math.round(tr.height):null, visibleInteractiveCount:visible('a,button,input,select,textarea').length, wideElements:wide};
   });
   results.push({name, ...metrics});
 }
 fs.writeFileSync(path.join(outDir,'mobile-audit-results.json'), JSON.stringify({generatedAt:new Date().toISOString(), viewport:{width:390,height:844}, results, consoleMessages}, null, 2));
 await browser.close();
})();
