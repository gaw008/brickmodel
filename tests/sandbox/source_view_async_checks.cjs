'use strict';
// Author regression adapted from the independent reviewer harness; original preserved in scratch.
// Presentation/async harness. Fake DOM and manufactured JSON only;
// executes current application JavaScript, never Python, HTTP or physics.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const crypto = require('node:crypto');
const repo = require('node:path').resolve(__dirname, '../..');
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
  const observations = [];
  {
    const h = harness(); h.context.fixture = value(); h.run('renderSource(fixture)');
    const refresh = h.elements.get('source-refresh').onclick();
    await h.settle(h.requests[1], {reason: 'artifact_hash_mismatch:assets/fixture-source.txt'}, false); await refresh;
    observations.push({name: 'failed revalidation clears old verified summary and controls', message: h.elements.get('message').textContent,
      sourceStatus: h.elements.get('source-status').textContent, summaryStillVerified: h.elements.get('source-summary').textContent.includes('"artifact_hashes_verified": true'),
      oldDataRetained: h.run('sourceData !== null'), clearedRows: h.elements.get('source-values').tbody.children.length});
    assert.equal(observations.at(-1).summaryStillVerified, false);
    assert.equal(observations.at(-1).oldDataRetained, false);
    assert.equal(h.elements.get('source-asset-select').children.length, 0);
    assert.equal(h.elements.get('source-export').disabled, true);
  }
  {
    const h = harness(); h.context.fixture = value(); h.run('renderSource(fixture)');
    const oldRefresh = h.elements.get('source-refresh').onclick();
    h.elements.get('source-capture').value = '2'; const newerSelection = h.elements.get('source-capture').onchange();
    await h.settle(h.requests[2], value(2, 'failed')); await newerSelection;
    h.context.note = 'LATEST_SELECTION_OK'; h.run('message(note)');
    await h.settle(h.requests[1], {reason: 'OLD_REQUEST_ERROR'}, false); await oldRefresh;
    observations.push({name: 'stale source request failure cannot overwrite current notification', message: h.elements.get('message').textContent, selectedCaptureState: h.elements.get('source-capture-state').textContent});
    assert.equal(h.elements.get('message').textContent, 'LATEST_SELECTION_OK');
  }
  await check('obsolete asset error does not overwrite latest successful selection', async () => {
    const h = harness(); h.context.fixture = value(); h.run('renderSource(fixture)');
    const asset = h.elements.get('source-asset-open').onclick();
    const selection = h.run('loadSource(new URLSearchParams({capture_index:"2"}))');
    await h.settle(h.requests[2], value(2, 'failed')); await selection;
    h.run('message("NEW_SELECTION_OK")');
    await h.fail(h.requests[1], 'OLD_ASSET_ERROR'); await asset;
    assert.equal(h.elements.get('message').textContent, 'NEW_SELECTION_OK');
    assert.ok(h.elements.get('source-capture-state').textContent.includes('原观测索引 2'));
  });
  await check('obsolete successful refresh does not publish its completion message', async () => {
    const h = harness(); h.context.fixture = value(); h.run('renderSource(fixture)');
    const refresh = h.elements.get('source-refresh').onclick();
    const selection = h.run('loadSource(new URLSearchParams({capture_index:"2"}))');
    await h.settle(h.requests[2], value(2, 'failed')); await selection;
    h.run('message("NEW_SELECTION_OK")');
    await h.settle(h.requests[1], value()); await refresh;
    assert.equal(h.elements.get('message').textContent, 'NEW_SELECTION_OK');
  });
  await check('current asset failure invalidates verification and suppresses pending old export', async () => {
    const h = harness(); h.context.fixture = value(); h.run('renderSource(fixture)');
    const exportCall = h.elements.get('source-export').onclick();
    const asset = h.elements.get('source-asset-open').onclick();
    await h.fail(h.requests[2], 'CURRENT_ASSET_HASH_MISMATCH'); await asset;
    assert.equal(h.run('sourceData'), null);
    assert.equal(h.elements.get('source-summary').textContent.includes('"artifact_hashes_verified": true'), false);
    await h.settle(h.requests[1], '{"old":"report"}'); await exportCall;
    assert.equal(h.elements.get('source-export-panel').hidden, true);
    assert.equal(h.blobs.length, 0);
    assert.ok(h.elements.get('message').textContent.includes('CURRENT_ASSET_HASH_MISMATCH'));
  });
  const output = {node: process.version, app_sha256: crypto.createHash('sha256').update(source).digest('hex'), scope: 'actual JS in independent manufactured DOM/JSON harness, not browser/E2E/physical validation', checks: outcomes, observations};
  process.stdout.write(JSON.stringify(output, null, 2) + '\n');
})().catch(error => { process.stderr.write(error.stack + '\n'); process.exitCode = 1; });
