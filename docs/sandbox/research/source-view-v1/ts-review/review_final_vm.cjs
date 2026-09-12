'use strict';
// Independent presentation/async harness. Fake DOM and manufactured JSON only;
// executes current application JavaScript, never Python, HTTP or physics.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const crypto = require('node:crypto');
const repo = '/Users/wanggaoying/Desktop/brickmodel-github';
const source = fs.readFileSync(repo + '/src/sludge_sandbox/assets/app.js', 'utf8');
const html = fs.readFileSync(repo + '/src/sludge_sandbox/assets/index.html', 'utf8');
class Element {
  constructor(tag = 'div') { this.tag = tag; this.children = []; this._text = ''; this._value = null; this.dataset = {}; this.style = {}; this.hidden = false; this.disabled = false; }
  get textContent() { return this._text + this.children.map(child => child.textContent ?? '').join(''); }
  set textContent(value) { this._text = String(value); this.children = []; }
  get value() { if (this.tag === 'select') return this._value === null ? (this.children[0]?.value ?? '') : (this.children.some(child => child.value === this._value) ? this._value : ''); return this._value ?? ''; }
  set value(value) { this._value = String(value); }
  set innerHTML(_) { throw new Error('HTML execution sink reached'); }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; this._text = ''; if (this.tag === 'select') this._value = null; }
  querySelector(selector) { if (selector === 'tbody') return this.tbody; return null; }
  querySelectorAll() { return []; }
  setAttribute(name, value) { this[name] = String(value); }
  addEventListener() {}
  contains() { return false; }
  focus() {}
  click() { this.clicked = true; }
}
function harness() {
  const elements = new Map([...html.matchAll(/<([\w-]+)[^>]*\bid="([^"]+)"[^>]*>/g)].map(match => [match[2], new Element(match[1])]));
  elements.get('source-values').tbody = new Element('tbody');
  const requests = [], timers = [], blobs = [];
  const fakeURL = class extends URL {};
  fakeURL.createObjectURL = blob => { blobs.push(blob); return 'blob:review'; };
  fakeURL.revokeObjectURL = () => {};
  const context = vm.createContext({document: {getElementById: id => elements.get(id), querySelector: () => ({content: 'fixture-token'}), createElement: tag => new Element(tag), createElementNS: (_ns, tag) => new Element(tag), createTextNode: text => ({textContent: text}), activeElement: null},
    URLSearchParams, URL: fakeURL, Blob, structuredClone, setTimeout: (callback, delay) => timers.push({callback, delay}),
    fetch: (url, options) => new Promise((resolve, reject) => requests.push({url, options, resolve, reject})),
  });
  vm.runInContext(source, context, {filename: 'app.js'});
  const run = code => vm.runInContext(code, context);
  const settle = async (request, value, ok = true) => { request.resolve({ok, json: async () => value, text: async () => value}); await new Promise(resolve => setImmediate(resolve)); };
  const fail = async (request, reason) => { request.reject(new Error(reason)); await new Promise(resolve => setImmediate(resolve)); };
  return {elements, requests, timers, blobs, run, settle, fail, context};
}
const exact = {numerator: '1208925819614629174706195', denominator: '3'};
const injection = '<img src=x onerror=globalThis.reviewXss=true>';
function value(index = 0, status = 'complete_observation') {
  const complete = status === 'complete_observation';
  const cell = {cell_index: 0, temperature_k: 300, internal_energy_j: 0, pressure_pa: 100000, temperature_error_bound_k: null};
  return {schema: 'source_run_view_v1', result: {status: 'cancelled', numerical_comparison_completed: false, numerical_event_accepted: false, material_qualified: false, training_eligible: false, full_firing_cycle: false},
    study: {capture_count: 3, record_sha256: 'old-verified-record', failed_capture_indices: [1, 2], unreturned_capture_indices: [], stages: {},
      selected_capture: {capture_index: index, ordinal: index + 1, role: 'trial_' + index, phase: 'fixture', capture_status: status, return_identity: complete ? 'saved_return' : 'no_saved_return', time: exact,
        observation: complete ? {time: exact, cell_count: 1, selected_cell_index: null, cells: [cell]} : null}},
    capture_page: {offset: 0, limit: 50, items: [0, 1, 2].map(capture_index => ({capture_index, ordinal: capture_index + 1, phase: 'fixture', role: 'trial_' + capture_index, status: capture_index === 0 ? 'complete_observation' : 'failed', cell_count: capture_index === 0 ? 1 : null, return_identity: capture_index === 0 ? 'saved_return' : 'no_saved_return'})), next_offset: null},
    assets: [{asset_id: 'a'.repeat(64), path: 'assets/' + injection + '.html', sha256: 'fixture-hash', text_available: true}], artifact_hashes_verified: true, source_assets_verified: false,
    source_trace: {builder_event: {status: 'recorded_hash_bound'}, cells: [{cell_index: 0, source_links: [{source_id: injection, status: 'unknown'}]}]}, capabilities: {inspect: true, export: true, execute: false, restore: false}};
}
const outcomes = [];
async function check(name, fn) { await fn(); outcomes.push({name, status: 'passed'}); }
(async () => {
  await check('exact rational string and unknown value survive rendered DOM; trial not plotted', async () => {
    const h = harness(); h.context.fixture = value(); h.run('renderSource(fixture)');
    assert.ok(h.elements.get('source-clock').textContent.includes(exact.numerator));
    assert.ok(h.elements.get('source-clock').textContent.includes('"denominator":"3"'));
    assert.ok(h.elements.get('source-capture-state').textContent.includes('trial_0'));
    assert.ok(h.elements.get('source-capture-state').textContent.includes('不自动等同于接受状态'));
    assert.ok(h.elements.get('source-values').tbody.textContent.includes('未知'));
    assert.equal(h.elements.get('time-chart').children.length, 0);
    h.run('showSourceTrace(0,"temperature_k")');
    assert.equal(h.elements.get('source-links').children[0].textContent, injection + ' · 关联未知');
    assert.equal(h.run('globalThis.reviewXss'), undefined);
  });
  await check('failed and no-saved-return capture erase previous observation rows', async () => {
    const h = harness(); h.context.fixture = value(); h.run('renderSource(fixture)');
    h.context.fixture = value(1, 'failed'); h.run('renderSource(fixture)');
    assert.equal(h.elements.get('source-values').tbody.children.length, 0);
    assert.ok(h.elements.get('source-capture-state').textContent.includes('failed'));
    assert.ok(h.elements.get('source-capture-state').textContent.includes('未保存返回'));
  });
  await check('older successful study response cannot replace later selection', async () => {
    const h = harness();
    const first = h.run('loadSource(new URLSearchParams({capture_index:"0"}))');
    const second = h.run('loadSource(new URLSearchParams({capture_index:"2"}))');
    await h.settle(h.requests[2], value(2, 'failed')); await second;
    await h.settle(h.requests[1], value()); await first;
    assert.ok(h.elements.get('source-capture-state').textContent.includes('原观测索引 2'));
  });
  await check('late source asset response cannot overwrite later source selection', async () => {
    const h = harness(); h.context.fixture = value(); h.run('renderSource(fixture)');
    const asset = h.elements.get('source-asset-open').onclick();
    const selection = h.run('loadSource(new URLSearchParams({capture_index:"2"}))');
    await h.settle(h.requests[2], value(2, 'failed')); await selection;
    await h.settle(h.requests[1], {path: injection, sha256: 'fixture', text: injection}); await asset;
    assert.equal(h.elements.get('source-asset-text').hidden, true);
  });
  await check('export preserves original JSON bytes including unsafe numeric literals', async () => {
    const h = harness(); const raw = '{"numerator":1208925819614629174706195,"text":"原字节"}\n';
    const exportCall = h.elements.get('source-export').onclick(); await h.settle(h.requests[1], raw); await exportCall;
    assert.equal(h.elements.get('source-export-text').value, raw);
    assert.equal(await h.blobs[0].text(), raw);
  });
  await check('view-only startup has no automatic study/job poll or launch request', async () => {
    const h = harness(); await h.settle(h.requests[0], {case: null, unknowns: [], source_run_mounted: true});
    await h.settle(h.requests[1], value());
    assert.deepEqual(h.requests.map(item => item.url), ['/api/config', '/api/source-run']);
    assert.equal(h.timers.length, 0);
    assert.equal(h.elements.get('case-workspace').hidden, true);
    assert.equal(h.elements.get('trajectory-panel').hidden, true);
    assert.ok(h.requests.every(item => item.options.method === 'GET'));
  });
  await check('current revalidation failure clears verified snapshot, source state, export and controls', async () => {
    const h = harness(); h.context.fixture = value(); h.run('renderSource(fixture)');
    h.elements.get('source-export-text').value = 'old export'; h.elements.get('source-export-panel').hidden = false;
    const refresh = h.elements.get('source-refresh').onclick();
    assert.ok(h.elements.get('source-status').textContent.includes('上次成功快照'));
    await h.settle(h.requests[1], {reason: 'artifact_hash_mismatch:assets/fixture-source.txt'}, false); await refresh;
    assert.equal(h.run('sourceData'), null);
    assert.equal(h.elements.get('source-summary').textContent.includes('"artifact_hashes_verified": true'), false);
    assert.ok(h.elements.get('source-status').textContent.includes('校验失败'));
    assert.equal(h.elements.get('source-values').tbody.children.length, 0);
    assert.equal(h.elements.get('source-export-text').value, '');
    assert.equal(h.elements.get('source-export-panel').hidden, true);
    for (const id of ['source-capture', 'source-cell', 'source-inspect', 'source-prev', 'source-next', 'source-query', 'source-asset-select', 'source-asset-open', 'source-export']) assert.equal(h.elements.get(id).disabled, true, id);
    const retry = h.elements.get('source-refresh').onclick(); await h.settle(h.requests[2], value()); await retry;
    assert.notEqual(h.run('sourceData'), null);
    assert.equal(h.elements.get('source-export').disabled, false);
    assert.equal(h.elements.get('source-asset-open').disabled, false);
    assert.ok(h.elements.get('message').textContent.includes('已重新校验'));
  });
  for (const oldResult of ['failure', 'success']) {
    await check('obsolete refresh ' + oldResult + ' preserves latest selection and notification', async () => {
      const h = harness(); h.context.fixture = value(); h.run('renderSource(fixture)');
      const older = h.elements.get('source-refresh').onclick();
      h.elements.get('source-capture').value = '2'; const newer = h.elements.get('source-capture').onchange();
      await h.settle(h.requests[2], value(2, 'failed')); await newer;
      h.run('message("LATEST_SELECTION_OK")');
      await h.settle(h.requests[1], oldResult === 'success' ? value() : {reason: 'OLD_REQUEST_ERROR'}, oldResult === 'success'); await older;
      assert.equal(h.elements.get('message').textContent, 'LATEST_SELECTION_OK');
      assert.ok(h.elements.get('source-capture-state').textContent.includes('原观测索引 2'));
    });
  }
  for (const oldResult of ['failure', 'success']) {
    await check('obsolete startup ' + oldResult + ' preserves later refresh success message', async () => {
      const h = harness(); await h.settle(h.requests[0], {case: null, unknowns: [], source_run_mounted: true});
      const newer = h.elements.get('source-refresh').onclick();
      await h.settle(h.requests[2], value(2, 'failed')); await newer;
      const expected = h.elements.get('message').textContent;
      assert.ok(expected.includes('已重新校验'));
      await h.settle(h.requests[1], oldResult === 'success' ? value() : {reason: 'OLD_STARTUP_ERROR'}, oldResult === 'success');
      assert.equal(h.elements.get('message').textContent, expected);
      assert.ok(h.elements.get('source-capture-state').textContent.includes('原观测索引 2'));
    });
  }
  for (const action of ['asset', 'export']) {
    for (const oldResult of ['failure', 'success']) {
      await check('obsolete ' + action + ' ' + oldResult + ' cannot overwrite latest selection or notification', async () => {
        const h = harness(); h.context.fixture = value(); h.run('renderSource(fixture)');
        const older = h.elements.get(action === 'asset' ? 'source-asset-open' : 'source-export').onclick();
        const newer = h.elements.get('source-refresh').onclick();
        await h.settle(h.requests[2], value(2, 'failed')); await newer;
        const expected = h.elements.get('message').textContent;
        const payload = action === 'asset' ? {path: 'old-source', sha256: 'old-sha', text: 'old text'} : '{"old": true}';
        await h.settle(h.requests[1], oldResult === 'success' ? payload : {reason: 'OLD_' + action + '_ERROR'}, oldResult === 'success'); await older;
        assert.equal(h.elements.get('message').textContent, expected);
        assert.ok(h.elements.get('source-capture-state').textContent.includes('原观测索引 2'));
        assert.equal(h.elements.get('source-asset-text').hidden, true);
        assert.equal(h.elements.get('source-export-text').value, '');
        assert.equal(h.blobs.length, 0);
      });
    }
  }
  for (const action of ['asset', 'export']) {
    await check('current ' + action + ' failure invalidates current verification', async () => {
      const h = harness(); h.context.fixture = value(); h.run('renderSource(fixture)');
      const operation = h.elements.get(action === 'asset' ? 'source-asset-open' : 'source-export').onclick();
      await h.settle(h.requests[1], {reason: 'artifact_hash_mismatch:fixture'}, false); await operation;
      assert.equal(h.run('sourceData'), null);
      assert.equal(h.elements.get('source-summary').textContent.includes('"artifact_hashes_verified": true'), false);
      assert.equal(h.elements.get('source-export').disabled, true);
      assert.equal(h.elements.get('source-asset-open').disabled, true);
      assert.ok(h.elements.get('message').textContent.includes('artifact_hash_mismatch'));
    });
  }
  await check('latest failed refresh cannot be resurrected by an older successful response', async () => {
    const h = harness(); h.context.fixture = value(); h.run('renderSource(fixture)');
    const older = h.elements.get('source-refresh').onclick();
    const newer = h.elements.get('source-refresh').onclick();
    await h.settle(h.requests[2], {reason: 'CURRENT_HASH_FAILURE'}, false); await newer;
    const expected = h.elements.get('message').textContent;
    await h.settle(h.requests[1], value()); await older;
    assert.equal(h.run('sourceData'), null);
    assert.equal(h.elements.get('message').textContent, expected);
    assert.equal(h.elements.get('source-summary').textContent.includes('"artifact_hashes_verified": true'), false);
  });
  const output = {node: process.version, app_sha256: crypto.createHash('sha256').update(source).digest('hex'), scope: 'independent reviewer execution of actual final JS using original VM harness plus bounded async fix cases; no browser or physics', checks: outcomes};
  fs.writeFileSync('/private/tmp/source-view-v1/ts-review/FINAL_VM_RESULTS.json', JSON.stringify(output, null, 2) + '\n');
  process.stdout.write(JSON.stringify(output, null, 2) + '\n');
})().catch(error => { process.stderr.write(error.stack + '\n'); process.exitCode = 1; });
