const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const elements=new Map();
const element=id=>{if(!elements.has(id))elements.set(id,{value:'',textContent:'',replaceChildren(){},addEventListener(){}});return elements.get(id);};
const context=vm.createContext({document:{getElementById:element,querySelector:()=>({content:'token'})},fetch:()=>new Promise(()=>{}),setTimeout(){},structuredClone});
vm.runInContext(fs.readFileSync(process.env.SANDBOX_UI_SCRIPT || require('node:path').resolve(__dirname,'../../src/sludge_sandbox/assets/app.js'),'utf8'),context);
const state=x=>({amounts_mol:[[1],[2]],internal_energy_j:[4,5],mechanical_stretches:x});
const integration=()=>({states:[state([1,2,3]),state([.9,1.8,2.9])],times_s:[0,.1]});
function series(input,quantity){context.input={integration:input};context.quantity=quantity;return JSON.parse(vm.runInContext("JSON.stringify(seriesFor('abcdefgh',input,quantity))",context));}
test('two normal coordinates and one global tangent use actual accepted full vectors',()=>{
 const normal=series(integration(),'normal_stretch');assert.equal(normal.length,2);assert.deepEqual(normal[1].points,[[0,2],[.1,1.8]]);
 const tangent=series(integration(),'tangential_stretch');assert.equal(tangent.length,1);assert.equal(tangent[0].cell,null);assert.equal(tangent[0].global,true);assert.deepEqual(tangent[0].points,[[0,3],[.1,2.9]]);
});
test('whole mechanical series is refused for missing invalid or inconsistent states',()=>{
 const edits=[x=>delete x.states[0].mechanical_stretches,x=>x.states[1].mechanical_stretches.pop(),x=>x.states[1].mechanical_stretches[1]=NaN,x=>x.states[1].mechanical_stretches[0]=0,x=>x.states[1].amounts_mol.pop(),x=>x.states[1].internal_energy_j.pop(),x=>x.times_s.pop(),x=>x.times_s[1]=Infinity,x=>x.times_s[1]=0];
 for(const edit of edits){const x=integration();edit(x);for(const q of ['normal_stretch','tangential_stretch'])assert.deepEqual(series(x,q),[]);}
});
test('display choices map to full mechanical provenance; legacy quantities unchanged',()=>{
 for(const q of ['normal_stretch','tangential_stretch','amounts_mol','temperature_k','pressure_pa','internal_energy_j']){context.q=q;assert.equal(vm.runInContext('traceQuantity(q)',context),q.endsWith('stretch')?'mechanical_stretches':q);}
 assert.deepEqual(series(integration(),'internal_energy_j')[0].points,[[0,4],[.1,4]]);
});
test('rendering common tangent produces no spatial series',()=>{
 context.saved={integration:integration()};context.drawn=[];
 for(const id of ['legend','space-legend'])element(id).append=()=>{};
 context.document.createElement=()=>({style:{}});
 element('quantity').value='tangential_stretch';
 vm.runInContext("results.set('abcdefgh',{result:saved});compared.add('abcdefgh');draw=(svg,series)=>drawn.push(series);renderPlots()",context);
 assert.equal(context.drawn[0].length,1);assert.equal(context.drawn[1].length,0);
 assert.match(element('plot-note').textContent,/一个全局自由度/);
});
