// Optional local runner. Requires an existing Playwright package + Chromium.
import {pathToFileURL} from 'node:url';
import verify from './browser.mjs';
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE ? pathToFileURL(process.env.PLAYWRIGHT_MODULE).href : 'playwright');
const browser=await chromium.launch({headless:true});
try{const page=await browser.newPage();await page.goto('http://127.0.0.1:8765');console.log(JSON.stringify(await verify(page),null,2));}finally{await browser.close();}
