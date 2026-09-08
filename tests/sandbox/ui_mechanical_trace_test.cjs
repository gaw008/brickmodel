/* Browser-independent regression for mechanical trace routing and stale responses. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const clientPath = process.env.SANDBOX_UI_SCRIPT || path.resolve(__dirname, '../../src/sludge_sandbox/assets/app.js');
const source = fs.readFileSync(clientPath, 'utf8');

for (const quantity of ['normal_stretch', 'tangential_stretch']) {
  test(`${quantity}: actual trace handler preserves full vector and rejects stale quantity response`, async () => {
    const elements = new Map();
    const calls = [];
    let resolveResponse;
    const element = id => {
      if (!elements.has(id)) {
        elements.set(id, {
          value: '', textContent: '', hidden: true,
          replaceChildren() {}, addEventListener() {}, append() {},
        });
      }
      return elements.get(id);
    };
    const context = vm.createContext({
      document: {
        getElementById: element,
        querySelector: () => ({content: 'test-token'}),
      },
      fetch: url => {
        if (url === '/api/config') return new Promise(() => {});
        calls.push(url);
        return new Promise(resolve => { resolveResponse = resolve; });
      },
      setTimeout() {},
      structuredClone,
    });
    vm.runInContext(source, context, {filename: clientPath});
    vm.runInContext("selected='job-a'", context);
    element('quantity').value = quantity;

    let pending = element('trace').onclick();
    assert.equal(calls.at(-1), '/api/jobs/job-a/trace?quantity=mechanical_stretches');
    const payload = {
      quantity: 'mechanical_stretches',
      pointer: '/integration/states/1/mechanical_stretches',
      value: [.9, 1.8, 2.9],
      dependency_graph: {nodes: []},
    };
    resolveResponse({ok: true, json: async () => payload});
    await pending;
    assert.deepEqual(JSON.parse(element('trace-detail').textContent), payload);

    pending = element('trace').onclick();
    element('quantity').value = quantity === 'normal_stretch'
      ? 'tangential_stretch' : 'normal_stretch';
    resolveResponse({ok: true, json: async () => payload});
    await pending;
    assert.equal(element('trace-detail').textContent, '');
  });
}
