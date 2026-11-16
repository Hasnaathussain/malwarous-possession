import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { runInNewContext } from 'node:vm';

const source = readFileSync(new URL('../website/analytics.js', import.meta.url), 'utf8');
const analyticsPath = '/_vercel/insights/script.js';
const speedPath = '/_vercel/speed-insights/script.js';

function runAnalytics({ hostname = 'atlas.vercel.app', webdriver = false, appendFailure = null } = {}) {
  const attempted = [];
  const appended = [];
  const created = [];
  const window = {};
  const document = {
    createElement(tag) {
      assert.equal(tag, 'script');
      const script = {
        async: false,
        src: '',
        onerror: null,
        removed: false,
        remove() { this.removed = true; },
      };
      created.push(script);
      return script;
    },
    head: {
      append(script) {
        attempted.push(script.src);
        if (script.src === appendFailure) throw new Error(`Append failed for ${script.src}`);
        appended.push(script);
      },
    },
  };
  runInNewContext(source, {
    location: { hostname, href: `https://${hostname}/replay?share=secret#frame=120` },
    navigator: { webdriver },
    window,
    document,
    URL,
  }, { filename: 'website/analytics.js' });
  return { window, document, attempted, appended, created };
}

function beforeSendFor(window, name) {
  const queuedCalls = window[`${name}q`];
  assert.ok(Array.isArray(queuedCalls), `${name} queue should be created`);
  assert.equal(queuedCalls.length, 1);
  assert.equal(queuedCalls[0][0], 'beforeSend');
  assert.equal(typeof queuedCalls[0][1], 'function');
  return queuedCalls[0][1];
}

test('registers independent same-origin Web Analytics and Speed Insights scripts', () => {
  const result = runAnalytics();
  assert.deepEqual(result.attempted, [analyticsPath, speedPath]);
  assert.equal(result.appended.length, 2);
  assert.ok(result.appended.every(script => script.async));
  assert.equal(result.appended[0].src, analyticsPath);
  assert.equal(result.appended[1].src, speedPath);
  beforeSendFor(result.window, 'va');
  beforeSendFor(result.window, 'si');
});

test('both beforeSend callbacks remove query strings and fragments while preserving other event fields', () => {
  const { window } = runAnalytics();
  const event = { url: 'https://atlas.vercel.app/replay?share=secret&frame=120#frame=120', metric: 'LCP' };
  for (const name of ['va', 'si']) {
    const redacted = beforeSendFor(window, name)(event);
    assert.equal(redacted.url, 'https://atlas.vercel.app/replay');
    assert.equal(redacted.metric, 'LCP');
    assert.equal(redacted.url.includes('share='), false);
    assert.equal(redacted.url.includes('frame='), false);
  }
});

test('drops malformed and missing event URLs instead of forwarding them', () => {
  const { window } = runAnalytics();
  for (const name of ['va', 'si']) {
    const beforeSend = beforeSendFor(window, name);
    assert.equal(beforeSend({ url: 'https://[malformed' }), null);
    assert.equal(beforeSend({ metric: 'CLS' }), null);
  }
});

test('skips localhost and webdriver sessions before creating either tracker', () => {
  const local = runAnalytics({ hostname: 'localhost' });
  assert.deepEqual(local.attempted, []);
  assert.equal(local.window.va, undefined);
  assert.equal(local.window.si, undefined);

  const automated = runAnalytics({ webdriver: true });
  assert.deepEqual(automated.attempted, []);
  assert.equal(automated.window.va, undefined);
  assert.equal(automated.window.si, undefined);
});

test('an analytics script append failure does not prevent the Speed Insights attempt', () => {
  const result = runAnalytics({ appendFailure: analyticsPath });
  assert.deepEqual(result.attempted, [analyticsPath, speedPath]);
  assert.deepEqual(result.appended.map(script => script.src), [speedPath]);
  assert.equal(result.created[0].removed, true);
  beforeSendFor(result.window, 'va');
  beforeSendFor(result.window, 'si');
});

test('a Speed Insights append failure does not undo the Web Analytics script', () => {
  const result = runAnalytics({ appendFailure: speedPath });
  assert.deepEqual(result.attempted, [analyticsPath, speedPath]);
  assert.deepEqual(result.appended.map(script => script.src), [analyticsPath]);
  assert.equal(result.created[1].removed, true);
  beforeSendFor(result.window, 'va');
  beforeSendFor(result.window, 'si');
});
