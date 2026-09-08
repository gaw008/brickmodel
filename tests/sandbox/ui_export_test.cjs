/* Browser-independent regression for lossless report export and job binding. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const clientPath = process.env.SANDBOX_UI_SCRIPT || path.resolve(__dirname, '../../src/sludge_sandbox/assets/app.js');
const source = fs.readFileSync(clientPath, 'utf8');

function client(exportResponse) {
  const elements = new Map();
  const element = id => {
    if (!elements.has(id)) elements.set(id, {value:'',textContent:'',hidden:true,addEventListener(){},replaceChildren(){}});
    return elements.get(id);
  };
  const blobs = [];
  const context = vm.createContext({
    document:{getElementById:element,querySelector:()=>({content:'test-token'}),createElement:()=>({click(){}})},
    fetch: url => url==='/api/config'?new Promise(()=>{}):exportResponse(url),
    Blob:class { constructor(parts){this.parts=parts;blobs.push(parts.join(''));} },
    URL:{createObjectURL:()=> 'blob:test',revokeObjectURL(){}},
    setTimeout(){},structuredClone,
  });
  vm.runInContext(source,context,{filename:clientPath});
  vm.runInContext("selected='job-a'",context);
  return {context,element,blobs,export:()=>element('export').onclick()};
}

test('export preserves integer ledger JSON exactly without a Number roundtrip', async()=>{
  const raw='{"result":{"ledger":{"numerator":9007199254740993,"denominator":1152921504606846976}},"manifest":{"files":{}}}';
  let parsed=0;
  const app=client(async()=>({ok:true,text:async()=>raw,json:async()=>{parsed++;return JSON.parse(raw);}}));
  await app.export();
  assert.equal(app.element('export-report').value,raw);
  assert.equal(app.blobs[0],raw);
  assert.equal(parsed,0);
  assert.match(app.element('message').textContent,/请求下载/);
});

test('late export cannot be attributed to a newly selected job', async()=>{
  let release;
  const response=new Promise(resolve=>{release=resolve;});
  const app=client(()=>response);
  const pending=app.export();
  vm.runInContext("selected='job-b';clearTrace()",app.context);
  release({ok:true,text:async()=>'{"result":{"status":"completed"}}',json:async()=>({result:{status:'completed'}})});
  await pending;
  assert.equal(app.element('export-report').value,'');
  assert.equal(app.element('export-panel').hidden,true);
  assert.equal(app.blobs.length,0);
});
