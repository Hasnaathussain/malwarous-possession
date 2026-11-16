// Browser checks for the public-only Possession Atlas; never reads a private viewer.
import {spawn} from 'node:child_process';
import {mkdir, writeFile} from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';

const base = (process.argv[2] || 'http://127.0.0.1:8788').replace(/\/$/, '');
const origin = new URL(base);
assert.ok((origin.hostname === '127.0.0.1' && origin.port === '8788') ||
  (origin.protocol === 'https:' && origin.hostname.endsWith('.vercel.app')),
  'Only the dedicated public preview or a Vercel deployment can be tested');
const manifestResponse = await fetch(`${base}/replays/index.json`);
assert.equal(manifestResponse.status, 200, 'Public replay index is unavailable');
const manifest = await manifestResponse.json();
assert.equal(manifest.schema_version, '1.0');
assert.equal(manifest.sequences.length, 13);
assert.ok(manifest.sequences.every(s => ['public_external', 'synthetic_demo'].includes(s.kind)));
assert.equal(manifest.sequences.filter(s => s.kind === 'public_external').length, 12);

const folder = path.resolve('artifacts_private/website-qa');
await mkdir(folder, {recursive: true});
const port = 19387;
const executable = process.env.ATLAS_QA_BROWSER || 'C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe';
const browser = spawn(executable, ['--headless=new', '--disable-gpu', '--no-first-run',
  '--disable-background-networking', '--disable-sync', '--no-default-browser-check',
  `--remote-debugging-port=${port}`, '--remote-debugging-address=127.0.0.1',
  `--user-data-dir=${path.join(folder, 'profile')}`, '--window-size=1600,1100', 'about:blank'],
  {stdio: 'ignore', windowsHide: true});
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
let socket;
try {
  let target;
  for (let attempt = 0; attempt < 80; attempt++) {
    try { target = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find(p => p.type === 'page'); } catch {}
    if (target) break;
    await sleep(150);
  }
  assert.ok(target, 'QA browser did not start');
  socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });
  let sequence = 0;
  const pending = new Map(), errors = [], requests = [], failedResponses = [];
  socket.onmessage = event => {
    const item = JSON.parse(event.data);
    if (item.id) {
      const job = pending.get(item.id); pending.delete(item.id); clearTimeout(job?.timeout);
      if (item.error) job?.reject(new Error(JSON.stringify(item.error))); else job?.resolve(item.result);
    }
    if (item.method === 'Runtime.exceptionThrown') errors.push(item.params.exceptionDetails.text);
    if (item.method === 'Network.requestWillBeSent') requests.push(item.params.request.url);
    if (item.method === 'Network.responseReceived' && item.params.response.status >= 400) {
      failedResponses.push({url: item.params.response.url, status: item.params.response.status});
    }
  };
  const call = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++sequence;
    const timeout = setTimeout(() => { pending.delete(id); reject(new Error(`Timed out: ${method}`)); }, 15000);
    pending.set(id, {resolve, reject, timeout}); socket.send(JSON.stringify({id, method, params}));
  });
  const evaluate = async expression => {
    const result = await call('Runtime.evaluate', {expression, returnByValue: true, awaitPromise: true});
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
    return result.result.value;
  };
  const waitFor = async (expression, description) => {
    for (let attempt = 0; attempt < 150; attempt++) {
      if (await evaluate(expression)) return;
      await sleep(100);
    }
    throw new Error(`Not ready: ${description}`);
  };
  const click = async id => {
    const point = await evaluate(`(()=>{const e=document.getElementById(${JSON.stringify(id)});e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return{x:r.x+r.width/2,y:r.y+r.height/2}})()`);
    await call('Input.dispatchMouseEvent', {type: 'mousePressed', button: 'left', clickCount: 1, ...point});
    await call('Input.dispatchMouseEvent', {type: 'mouseReleased', button: 'left', clickCount: 1, ...point});
  };
  const screenshot = async name => {
    const result = await call('Page.captureScreenshot', {format: 'png', captureBeyondViewport: false});
    await writeFile(path.join(folder, name), Buffer.from(result.data, 'base64'));
  };
  await call('Runtime.enable'); await call('Network.enable'); await call('Page.enable');
  await call('Network.setCacheDisabled', {cacheDisabled: true});
  await call('Emulation.setDeviceMetricsOverride', {width: 1600, height: 1100, deviceScaleFactor: 1, mobile: false});
  await call('Emulation.setEmulatedMedia', {features: [{name: 'prefers-reduced-motion', value: 'reduce'}]});
  await call('Page.navigate', {url: base});
  await waitFor(`document.getElementById('playButton') && !document.getElementById('playButton').disabled && Number(document.getElementById('frameRange').max)>0`, 'default external replay');
  const initial = await evaluate(`({title:document.title,matchOptions:document.getElementById('matchSelect').options.length,frames:Number(document.getElementById('frameRange').max),benchmarkRows:document.querySelectorAll('#benchmarkRows tr').length})`);
  assert.ok(initial.matchOptions >= 7);
  assert.equal(initial.benchmarkRows, 18);
  assert.ok(initial.frames > 1000);
  await screenshot('desktop-top.png');
  await evaluate(`document.getElementById('replay').scrollIntoView()`);
  await screenshot('desktop-replay.png');
  await evaluate(`document.getElementById('frameInput').value='100';`);
  await click('seekFrameButton');
  assert.equal(Number(await evaluate(`document.getElementById('frameRange').value`)), 100);
  assert.ok((await evaluate(`document.getElementById('measurementList').textContent`)).includes('model evidence'));
  await evaluate(`document.getElementById('timeInput').value='1:00.0'`);
  await click('seekTimeButton');
  assert.equal(Number(await evaluate(`document.getElementById('frameRange').value`)), 1500);
  await evaluate(`document.getElementById('frameInput').value='100'`); await click('seekFrameButton');
  await click('stepForward');
  assert.equal(Number(await evaluate(`document.getElementById('frameRange').value`)), 101);
  await click('stepBack');
  assert.equal(Number(await evaluate(`document.getElementById('frameRange').value`)), 100);
  await click('nextChange');
  assert.ok(Number(await evaluate(`document.getElementById('frameRange').value`)) > 100);
  await click('playButton'); await sleep(400); await click('playButton');
  assert.ok(Number(await evaluate(`document.getElementById('frameRange').value`)) > 100);
  await evaluate(`document.getElementById('scenarioFilter').value='drop40';document.getElementById('scenarioFilter').dispatchEvent(new Event('change'))`);
  assert.equal(await evaluate(`document.querySelectorAll('#benchmarkRows tr').length`), 6);
  await evaluate(`document.getElementById('scenarioFilter').value='all';document.getElementById('scenarioFilter').dispatchEvent(new Event('change'))`);
  await click('shareButton');
  const shared = await evaluate(`document.getElementById('shareLink').value`);
  assert.equal(new URL(shared).origin, origin.origin);
  assert.ok(shared.length > base.length + 5);
  const beforeColor = await evaluate(`document.getElementById('pitchCanvas').toDataURL()`);
  await evaluate(`document.getElementById('homeColor').value='#88aaee';document.getElementById('homeColor').dispatchEvent(new Event('input'))`);
  await sleep(150);
  assert.notEqual(await evaluate(`document.getElementById('pitchCanvas').toDataURL()`), beforeColor);
  for (const id of ['gridToggle', 'trailsToggle', 'regionsToggle', 'referenceToggle']) await click(id);
  assert.equal(await evaluate(`document.getElementById('referenceLane').hidden`), false);
  await evaluate(`document.getElementById('decoder-lab').scrollIntoView()`);
  await waitFor(`document.querySelectorAll('#sandboxRoot input[type=range]').length===3`, 'decoder lab');
  const labBefore = await evaluate(`document.querySelector('#sandboxRoot').textContent`);
  await evaluate(`(()=>{const p=document.querySelector('#sandboxRoot input[type=range]');p.value=50;p.dispatchEvent(new Event('input'))})()`);
  await sleep(200);
  assert.notEqual(await evaluate(`document.querySelector('#sandboxRoot').textContent`), labBefore);
  await screenshot('desktop-lab.png');
  await evaluate(`(()=>{const s=document.getElementById('matchSelect');const o=[...s.options].find(o=>/synthetic|demo/i.test(o.textContent));if(!o)throw new Error('No synthetic choice');s.value=o.value;s.dispatchEvent(new Event('change'))})()`);
  await waitFor(`!document.getElementById('videoPanel').hidden && document.getElementById('syntheticVideo').readyState>=1`, 'synthetic media');
  await evaluate(`document.getElementById('frameRange').value=110;document.getElementById('frameRange').dispatchEvent(new Event('input'))`);
  await sleep(350);
  const mediaTime = await evaluate(`document.getElementById('syntheticVideo').currentTime`);
  const mediaInfo = await evaluate(`(()=>{const v=document.getElementById('syntheticVideo');return {time:v.currentTime,ready:v.readyState,duration:v.duration,src:v.currentSrc,source:v.dataset.sourceUrl,frame:document.getElementById('frameRange').value,seeking:v.seeking,seekable:[...Array(v.seekable.length)].map((_,i)=>[v.seekable.start(i),v.seekable.end(i)])}})()`);
  assert.ok(Math.abs(mediaTime - 11) < .25, `Video clock differs: ${JSON.stringify(mediaInfo)}`);
  await click('playButton'); await sleep(450); await click('playButton');
  const sync = await evaluate(`({frame:Number(document.getElementById('frameRange').value),time:document.getElementById('syntheticVideo').currentTime})`);
  assert.ok(sync.time > 11 && Math.abs(sync.frame / 10 - sync.time) < .2, JSON.stringify(sync));
  assert.ok(/synthetic|software|authored/i.test(await evaluate(`document.getElementById('replay').textContent`)));
  await evaluate(`document.getElementById('videoPanel').scrollIntoView({block:'center'})`);
  await screenshot('desktop-video.png');
  await call('Emulation.setDeviceMetricsOverride', {width: 390, height: 844, deviceScaleFactor: 1, mobile: true});
  await evaluate(`window.scrollTo(0,0)`); await sleep(150);
  const mobile = await evaluate(`({width:innerWidth,body:document.body.scrollWidth,document:document.documentElement.scrollWidth})`);
  assert.ok(mobile.width === 390 && mobile.body <= 391 && mobile.document <= 391, JSON.stringify(mobile));
  await screenshot('mobile-top.png');
  await click('menuToggle');
  assert.equal(await evaluate(`document.getElementById('menuToggle').getAttribute('aria-expanded')`), 'true');
  await click('menuToggle');
  await evaluate(`document.getElementById('replay').scrollIntoView()`); await screenshot('mobile-replay.png');
  await evaluate(`window.atlasExport=null;window.atlasOriginalClick=HTMLAnchorElement.prototype.click;HTMLAnchorElement.prototype.click=function(){if(this.download&&this.href.startsWith('data:image/png'))window.atlasExport={url:this.href,name:this.download};else window.atlasOriginalClick.call(this)}`);
  await click('exportButton');
  const exported = await evaluate(`new Promise((resolve,reject)=>{const e=window.atlasExport;if(!e)return reject(new Error('No field export'));const i=new Image;i.onload=()=>resolve({width:i.width,height:i.height,name:e.name});i.onerror=reject;i.src=e.url})`);
  assert.ok(exported.width >= 1920 && exported.height > 1000 && exported.name.endsWith('.png'));
  for (const width of [320, 768, 1366]) {
    await call('Emulation.setDeviceMetricsOverride', {width, height: 844, deviceScaleFactor: 1, mobile: width < 800});
    await sleep(100);
    const layout = await evaluate(`({width:innerWidth,body:document.body.scrollWidth,document:document.documentElement.scrollWidth})`);
    assert.ok(layout.width === width && layout.body <= width + 1 && layout.document <= width + 1, JSON.stringify(layout));
  }
  assert.deepEqual(errors, [], 'Browser JavaScript exception');
  assert.deepEqual(failedResponses, [], 'Failed application response');
  const external = requests.filter(url => /^https?:/.test(url) && new URL(url).origin !== origin.origin);
  assert.deepEqual(external, [], 'Unexpected external application request');
  console.log(JSON.stringify({status: 'pass', initial, mobile, media_time_s: mediaTime,
    checks: ['public source gate', 'replay load', 'frame seek/step', 'transition jump', 'playback',
      'benchmark scenario filter', 'share URL', 'team colors and display controls', 'interactive decoder lab',
      'synthetic video seek/play clock', '320/390/768/1366px layouts', 'mobile navigation',
      'attributed PNG export', 'browser errors', 'same-origin requests'], screenshots: folder}));
} finally {
  socket?.close(); browser.kill();
}
