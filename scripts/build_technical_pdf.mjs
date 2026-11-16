// Typeset the fixed, public-safe HTML source with Chromium. No target inputs.
import {spawn} from 'node:child_process';
import {mkdir, writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import path from 'node:path';
import assert from 'node:assert/strict';
const root = path.resolve(import.meta.dirname, '..');
const folder = path.join(root, 'artifacts_private/pdf-build');
await mkdir(folder, {recursive:true});
const exe = process.env.ATLAS_QA_BROWSER || 'C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe';
const port = 19402;
const browser = spawn(exe, ['--headless=new','--disable-gpu','--no-first-run','--disable-background-networking',
  '--allow-file-access-from-files',`--remote-debugging-port=${port}`,'--remote-debugging-address=127.0.0.1',
  `--user-data-dir=${path.join(folder,'profile')}`,'about:blank'], {stdio:'ignore',windowsHide:true});
const pause = ms => new Promise(r=>setTimeout(r,ms));
let socket;
try {
  let target;
  for(let i=0;i<80;i++) { try { target=(await(await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find(p=>p.type==='page'); } catch {} if(target)break;await pause(100); }
  assert.ok(target,'Chromium did not start. Set ATLAS_QA_BROWSER to its executable.');
  socket=new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r,j)=>{socket.onopen=r;socket.onerror=j});
  let sequence=0; const pending=new Map();
  socket.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);pending.delete(m.id);clearTimeout(p?.timer);m.error?p?.reject(new Error(JSON.stringify(m.error))):p?.resolve(m.result)}};
  const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++sequence;const timer=setTimeout(()=>{pending.delete(id);reject(new Error(`Timed out: ${method}`))},15000);pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params}))});
  await call('Page.enable');await call('Runtime.enable');await call('Network.enable');
  await call('Network.setBlockedURLs',{urls:['http://*','https://*']});
  await call('Emulation.setEmulatedMedia',{media:'print'});
  await call('Page.navigate',{url:pathToFileURL(path.join(root,'docs/Malwarous.html')).href});
  let ready=false;
  for(let i=0;i<80;i++){const r=await call('Runtime.evaluate',{expression:"document.readyState==='complete' && [...document.images].every(i=>i.complete&&i.naturalWidth>0)",returnByValue:true});if(r.result.value){ready=true;break}await pause(100)}
  assert.ok(ready,'Document or its approved figures failed to load');
  const sizes=await call('Runtime.evaluate',{expression:"[...document.querySelectorAll('.page')].map(p=>({height:p.clientHeight,content:p.scrollHeight,footer:p.querySelector('.footer').getBoundingClientRect().top,bodyBottom:Math.max(...[...p.children].filter(e=>!e.classList.contains('footer')).map(e=>e.getBoundingClientRect().bottom))}))",returnByValue:true});
  assert.equal(sizes.result.value.length,4);assert.ok(sizes.result.value.every(p=>p.content<=p.height+1 && p.bodyBottom < p.footer-8),JSON.stringify(sizes.result.value));
  const pdf=await call('Page.printToPDF',{printBackground:true,preferCSSPageSize:true,displayHeaderFooter:false,generateTaggedPDF:true});
  await writeFile(path.join(root,'submission/Malwarous.pdf'),Buffer.from(pdf.data,'base64'));
  console.log(JSON.stringify({status:'built',source:'docs/Malwarous.html',output:'submission/Malwarous.pdf',pages:4,overflow:'none',rendering:'Chromium; font/renderer versions can affect PDF bytes'}));
} finally {socket?.close();browser.kill();}
