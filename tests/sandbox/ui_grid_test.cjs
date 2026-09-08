const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const elements=new Map();
function element(id){if(!elements.has(id))elements.set(id,{value:'',textContent:'',replaceChildren(){},addEventListener(){}});return elements.get(id);}
const select={options:[{value:'2'},{value:'4'}],selected:'2',get value(){return this.selected;},set value(x){this.selected=this.options.some(o=>o.value===String(x))?String(x):'';},replaceChildren(...options){this.options=options;this.selected=options[0]?.value||'';},addEventListener(){}};
elements.set('cells',select);
const context=vm.createContext({document:{getElementById:element,querySelector:()=>({content:'token'}),createElement:()=>({})},fetch:()=>new Promise(()=>{}),setTimeout(){},structuredClone});
vm.runInContext(fs.readFileSync(process.env.SANDBOX_UI_SCRIPT||require('node:path').resolve(__dirname,'../../src/sludge_sandbox/assets/app.js'),'utf8'),context);
const FREE='manufactured_reacting_wet_free_slab_v1',OLD='manufactured_reacting_wet_prescribed_slab_v1';
function configure(model,cells){context.input={model_id:model,grid:{cells},profile:'gradient',transport_mode:'coupled',refinement:0};vm.runInContext('caseData=structuredClone(input);fillControls()',context);}
test('free eight survives actual select option semantics and JSON roundtrip',()=>{configure(FREE,8);assert.deepEqual(select.options.map(x=>x.value),['2','4','8']);assert.equal(select.value,'8');assert.equal(vm.runInContext('controlsToCase().grid.cells',context),8);assert.equal(JSON.parse(element('case-json').value).grid.cells,8);});
test('legacy restores only two/four and rejects unsupported value before mutation',()=>{configure(OLD,4);assert.deepEqual(select.options.map(x=>x.value),['2','4']);select.value='8';assert.equal(select.value,'');assert.throws(()=>vm.runInContext('controlsToCase()',context),/网格数量/);assert.equal(vm.runInContext('caseData.grid.cells',context),4);});
test('invalid model or grid is never silently coerced',()=>{assert.throws(()=>configure(OLD,8),/网格数量/);assert.throws(()=>configure(FREE,6),/网格数量/);assert.throws(()=>configure('unknown',2),/不支持/);});
