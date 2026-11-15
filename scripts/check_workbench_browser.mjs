// Synthetic/public-only browser QA. Never capture private_local bundles.
import {spawn} from 'node:child_process';
import {mkdir, writeFile} from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';

const base = process.argv[2] || 'http://127.0.0.1:8765';
assert.equal(new URL(base).hostname, '127.0.0.1', 'QA only supports loopback');
const bundle = await (await fetch(`${base}/api/bundle`)).json();
assert.ok(['synthetic_demo','public_external'].includes(bundle.dataset.kind),
          'Refusing browser capture of restricted local data');
const folder = path.resolve('artifacts_private/v2/browser-qa');
await mkdir(folder, {recursive:true});
const browserPath = process.env.WORKBENCH_QA_BROWSER ||
  'C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe';
const port = 19223;
const browser = spawn(browserPath, ['--headless=new','--disable-gpu','--no-first-run',
  '--disable-background-networking','--disable-sync','--no-default-browser-check',
  `--remote-debugging-port=${port}`, '--remote-debugging-address=127.0.0.1',
  `--user-data-dir=${path.join(folder,'profile')}`, '--window-size=1600,1100','about:blank'],
  {stdio:'ignore', windowsHide:true});
const sleep = ms => new Promise(r=>setTimeout(r,ms));
let socket;
try {
  let target;
  for(let n=0;n<100;n++) {
    try { target=(await(await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find(t=>t.type==='page'); }
    catch {}
    if(target) break;
    await sleep(200);
  }
  assert.ok(target, 'Headless browser did not expose its local page');
  socket=new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
  let sequence=0;
  const pending=new Map(), errors=[], requests=[];
  socket.onmessage=event=>{
    const item=JSON.parse(event.data);
    if(item.id) {
      const p=pending.get(item.id);pending.delete(item.id);
      if(item.error)p?.reject(new Error(JSON.stringify(item.error)));else p?.resolve(item.result);
    }
    if(item.method==='Runtime.exceptionThrown')errors.push(item.params.exceptionDetails.text);
    if(item.method==='Network.requestWillBeSent')requests.push(item.params.request.url);
  };
  const call=(method,params={})=>new Promise((resolve,reject)=>{
    const id=++sequence;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}));
  });
  const evaluate=async expression=>{
    const result=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
    if(result.exceptionDetails)throw new Error(JSON.stringify(result.exceptionDetails));
    return result.result.value;
  };
  const click=async id=>{
    const point=await evaluate(`(()=>{const r=document.getElementById(${JSON.stringify(id)}).getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()`);
    await call('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',clickCount:1,...point});
    await call('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',clickCount:1,...point});
  };
  await call('Runtime.enable');await call('Network.enable');await call('Page.enable');
  await call('Emulation.setDeviceMetricsOverride',{width:1600,height:1100,deviceScaleFactor:1,mobile:false});
  await call('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
  await call('Page.navigate',{url:base});
  let ready=false;
  for(let n=0;n<100;n++){
    ready=await evaluate(`!!document.getElementById('application') && !document.getElementById('application').hidden`);
    if(ready)break;await sleep(100);
  }
  assert.ok(ready,'Application failed to load');
  const initial=await evaluate(`({title:document.title,events:document.querySelectorAll('#eventRows tr').length,
      benchmarks:document.querySelectorAll('#benchmarkRows tr').length,
      versions:document.getElementById('versionSelect').options.length})`);
  assert.ok(initial.events>0 && initial.benchmarks>=2 && initial.versions>=2);
  const toolbar=await evaluate(`(()=>{const e=document.getElementById('split'),r=e.getBoundingClientRect(),s=getComputedStyle(e);
    return {innerWidth,media:matchMedia('(max-width: 1050px)').matches,text:e.textContent,
      width:r.width,scrollWidth:e.scrollWidth,clientWidth:e.clientWidth,maxWidth:s.maxWidth,overflow:s.overflow};})()`);
  const expectedLedger=new Set(bundle.matches.flatMap(item=>(item.benchmarks||[]).map(b=>
    JSON.stringify([item.provenance?.match||item.id,b])))).size;
  await evaluate(`document.getElementById('allMatches').checked=true;
    document.getElementById('allMatches').dispatchEvent(new Event('change'))`);
  assert.equal(await evaluate(`document.querySelectorAll('#benchmarkRows tr').length`),expectedLedger,
    'All-match benchmark ledger lost or duplicated a declared record');
  await evaluate(`document.getElementById('allMatches').checked=false;
    document.getElementById('allMatches').dispatchEvent(new Event('change'))`);
  await evaluate(`document.getElementById('zoomSelect').value='30';
    document.getElementById('zoomSelect').dispatchEvent(new Event('change'));
    document.getElementById('scrubber').value=60;document.getElementById('scrubber').dispatchEvent(new Event('input'));`);
  const axes=await evaluate(`['axisStart','axisEnd'].map(id=>document.getElementById(id).textContent)`);
  const timeFromLabel=s=>s.split(':').reduce((a,v)=>a*60+Number(v),0);
  assert.equal(timeFromLabel(axes[1])-timeFromLabel(axes[0]),30,'Zoom range is not thirty seconds');
  await evaluate(`(()=>{const c=document.getElementById('evidenceChart'),r=c.getBoundingClientRect(),s=getComputedStyle(c);
    const pl=parseFloat(s.paddingLeft)||0,pr=parseFloat(s.paddingRight)||0;
    const x=(55+(c.width-17))/2,content=r.width-pl-pr;
    c.dispatchEvent(new MouseEvent('click',{clientX:r.left+pl+x/c.width*content,
      clientY:r.top+r.height/2,bubbles:true}));})()`);
  const evidenceTime=Number(await evaluate(`document.getElementById('scrubber').value`));
  assert.ok(Math.abs(evidenceTime-(timeFromLabel(axes[0])+15))<.05,'Evidence click did not use zoomed time mapping');
  await evaluate(`document.getElementById('zoomSelect').value='120';
    document.getElementById('zoomSelect').dispatchEvent(new Event('change'));`);
  const rate=bundle.matches[0].provenance?.fps ?? bundle.matches[0].media?.fps;
  if(Number.isFinite(rate) && rate>0){
    await evaluate(`document.getElementById('scrubber').value=12.01;
      document.getElementById('scrubber').dispatchEvent(new Event('input',{bubbles:true}));`);
    const beforeStep=Number(await evaluate(`document.getElementById('scrubber').value`));
    await evaluate(`document.getElementById('forwardFrame').click()`);
    const afterStep=Number(await evaluate(`document.getElementById('scrubber').value`));
    const expectedStep=(Math.floor(beforeStep*rate+1e-7)+1)/rate;
    assert.ok(Math.abs(afterStep-expectedStep)<.001,
      'Frame step did not advance from the displayed frame when between frame times');
    await evaluate(`document.getElementById('backFrame').click()`);
    assert.ok(Math.abs(Number(await evaluate(`document.getElementById('scrubber').value`))-12)<.001,
      'Backward frame step did not return to the displayed frame');
    await evaluate(`document.getElementById('scrubber').value=0;
      document.getElementById('scrubber').dispatchEvent(new Event('input',{bubbles:true}));
      document.getElementById('backFrame').click();`);
    assert.equal(Number(await evaluate(`document.getElementById('scrubber').value`)),0,
      'Frame stepping crossed the beginning of the match');
    await evaluate(`document.getElementById('scrubber').value=Number(document.getElementById('scrubber').max);
      document.getElementById('scrubber').dispatchEvent(new Event('input',{bubbles:true}));
      document.getElementById('forwardFrame').click();`);
    assert.equal(Number(await evaluate(`document.getElementById('scrubber').value`)),bundle.matches[0].duration_s,
      'Frame stepping moved backward from the match end');
    await evaluate(`document.getElementById('frameSeek').value=123;document.getElementById('goFrame').click()`);
    assert.ok(Math.abs(Number(await evaluate(`document.getElementById('scrubber').value`))-123/rate)<.001);
    await evaluate(`document.getElementById('forwardFrame').click()`);
    assert.match(await evaluate(`document.getElementById('frameClock').textContent`),/Frame 124/);
    await evaluate(`document.getElementById('backFrame').click()`);
    assert.match(await evaluate(`document.getElementById('frameClock').textContent`),/Frame 123/);
  }
  const configured=await evaluate(`!!document.getElementById('video').getAttribute('src')`);
  if(configured){
    let mediaReady=false;
    for(let n=0;n<100;n++){
      mediaReady=await evaluate(`document.getElementById('video').readyState>=1`);
      if(mediaReady)break;await sleep(100);
    }
    assert.ok(mediaReady,'Configured synthetic/public video did not load');
  }
  await evaluate(`document.getElementById('scrubber').value=20;
    document.getElementById('scrubber').dispatchEvent(new Event('input',{bubbles:true}));`);
  assert.match(await evaluate(`document.getElementById('clock').textContent`),/00:20/);
  await evaluate(`window.__qaTimelineNode=document.querySelector('.timeline-track')`);
  await click('play');await sleep(800);
  await click('play');
  assert.ok(Number(await evaluate(`document.getElementById('scrubber').value`))>20.2,'Playback did not advance');
  assert.ok(await evaluate(`window.__qaTimelineNode===document.querySelector('.timeline-track')`),
    'Playback unnecessarily rebuilt timeline DOM');
  await evaluate(`document.getElementById('eventFilter').value='errors';
    document.getElementById('eventFilter').dispatchEvent(new Event('change'));
    document.getElementById('nextEvent').click();`);
  assert.ok((await evaluate(`document.getElementById('eventStatus').textContent`)).length>0);
  const media=await evaluate(`({configured:!!document.getElementById('video').getAttribute('src'),
    ready:document.getElementById('video').readyState,time:document.getElementById('video').currentTime})`);
  await evaluate(`document.getElementById('scrubber').value=10;
    document.getElementById('scrubber').dispatchEvent(new Event('input'));`);
  await sleep(300);
  if(media.configured){
    const mapping=bundle.matches[0].media;
    const actual=await evaluate(`document.getElementById('video').currentTime`);
    assert.ok(Math.abs(actual-(10+(mapping?.offset_s||0)))<.25,'Video and pitch clock diverged');
  }
  const keyboard=await evaluate(`(()=>{
    const play=document.getElementById('play'),slider=document.getElementById('scrubber');
    play.focus();document.dispatchEvent(new KeyboardEvent('keydown',{code:'Space',bubbles:true}));
    const focused=play.textContent.includes('Play');play.blur();
    const repeatEvent=new KeyboardEvent('keydown',{code:'Space',bubbles:true,cancelable:true,repeat:true});
    document.dispatchEvent(repeatEvent);
    const repeated=play.textContent.includes('Play');
    const repeatPrevented=repeatEvent.defaultPrevented;
    document.dispatchEvent(new KeyboardEvent('keydown',{code:'Space',bubbles:true}));
    const started=play.textContent.includes('Pause');
    document.dispatchEvent(new KeyboardEvent('keydown',{code:'Space',bubbles:true,repeat:true}));
    const held=play.textContent.includes('Pause');
    document.dispatchEvent(new KeyboardEvent('keydown',{code:'Space',bubbles:true}));
    const before=Number(slider.value);document.dispatchEvent(new KeyboardEvent('keydown',{code:'ArrowRight',bubbles:true}));
    const after=Number(slider.value);slider.focus();
    document.dispatchEvent(new KeyboardEvent('keydown',{code:'ArrowRight',bubbles:true}));
    const inputIgnored=Number(slider.value)===after;slider.blur();
    return {focused,repeated,repeatPrevented,started,held,arrowDelta:after-before,inputIgnored};
  })()`);
  assert.deepEqual(keyboard,{focused:true,repeated:true,repeatPrevented:true,started:true,held:true,arrowDelta:1,inputIgnored:true},
    'Keyboard shortcuts interfered with focused controls or repeated Space');
  await evaluate(`window.scrollTo(0,document.body.scrollHeight);document.activeElement?.blur()`);
  const scrollBeforeRepeat=Number(await evaluate(`window.scrollY`));
  await call('Input.dispatchKeyEvent',{type:'keyDown',key:' ',code:'Space',windowsVirtualKeyCode:32,nativeVirtualKeyCode:32,autoRepeat:true});
  await sleep(40);
  const scrollAfterRepeat=Number(await evaluate(`window.scrollY`));
  await call('Input.dispatchKeyEvent',{type:'keyUp',key:' ',code:'Space',windowsVirtualKeyCode:32,nativeVirtualKeyCode:32});
  assert.equal(scrollAfterRepeat,scrollBeforeRepeat,'Holding Space scrolled the page while the play shortcut was active');
  await sleep(120);
  await evaluate(`document.getElementById('scrubber').dispatchEvent(new Event('input',{bubbles:true}))`);
  const finalVideoStatus=await evaluate(`document.getElementById('videoStatus').textContent`);
  if(media.configured)assert.match(finalVideoStatus,/Synchronized/,'Final video readout was not synchronized');
  await evaluate(`window.scrollTo(0,0)`);
  await sleep(40);
  const accessibility=await evaluate(`({pitchRole:document.getElementById('pitch').getAttribute('role'),
    pitchLabel:document.getElementById('pitch').getAttribute('aria-label'),
    evidenceDescription:document.getElementById('evidenceChart').getAttribute('aria-describedby'),
    retryInitiallyHidden:document.getElementById('retryLoad').hidden,
    reducedMotion:matchMedia('(prefers-reduced-motion: reduce)').matches,
    transitionDuration:getComputedStyle(document.getElementById('play')).transitionDuration})`);
  assert.equal(accessibility.pitchRole,'img');
  assert.match(accessibility.pitchLabel,/home.*away.*ball/i);
  assert.equal(accessibility.evidenceDescription,'evidenceDescription');
  assert.equal(accessibility.retryInitiallyHidden,true);
  assert.equal(accessibility.reducedMotion,true);
  assert.equal(accessibility.transitionDuration,'1e-05s');
  const capture=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
  await writeFile(path.join(folder,'desktop.png'),Buffer.from(capture.data,'base64'));
  const layout=await call('Page.getLayoutMetrics');
  const content=layout.cssContentSize;
  const fullCapture=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,
    clip:{x:0,y:0,width:content.width,height:content.height,scale:1}});
  await writeFile(path.join(folder,'desktop-full.png'),Buffer.from(fullCapture.data,'base64'));
  await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  await sleep(200);
  const mobile=await evaluate(`({width:innerWidth,scroll:document.documentElement.scrollWidth})`);
  assert.ok(mobile.scroll<=mobile.width+1,'Mobile page overflows horizontally');
  const mobileShot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
  await writeFile(path.join(folder,'mobile.png'),Buffer.from(mobileShot.data,'base64'));
  await call('Network.setBlockedURLs',{urls:[`${base}/api/bundle`]});
  await call('Page.reload',{ignoreCache:true});
  let retryVisible=false;
  for(let n=0;n<100;n++){
    retryVisible=await evaluate(`!document.getElementById('retryLoad').hidden`);
    if(retryVisible)break;await sleep(50);
  }
  assert.ok(retryVisible,'Bundle load failure did not expose retry');
  assert.match(await evaluate(`document.getElementById('loadingMessage').textContent`),/retry/i);
  await call('Network.setBlockedURLs',{urls:[]});
  await evaluate(`document.getElementById('retryLoad').click()`);
  for(let n=0;n<100;n++){
    ready=await evaluate(`!!document.getElementById('application') && !document.getElementById('application').hidden`);
    if(ready)break;await sleep(50);
  }
  assert.ok(ready,'Retry did not load the permitted bundle');
  assert.deepEqual(errors,[],'Browser JavaScript error');
  const external=requests.filter(url=>!url.startsWith(base) && !url.startsWith('data:'));
  assert.deepEqual(external,[],'Application requested an external resource');
  console.log(JSON.stringify({status:'pass',dataset_kind:bundle.dataset.kind,initial,media,
    mobile,all_match_ledger_rows:expectedLedger,keyboard,accessibility,finalVideoStatus,toolbar,
    checks:['load and retry','timeline/evidence zoom mapping','stable playback DOM','frame jump/step and bounds when fps supplied','scrub','playback','keyboard focus and repeat','screen-reader descriptions','error navigation','all-match benchmark ledger','media clock when configured',
      'mobile overflow','JavaScript errors','application external requests'],screenshots:folder}));
} finally {
  socket?.close();browser.kill();
}
