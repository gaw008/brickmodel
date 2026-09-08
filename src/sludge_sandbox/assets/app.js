'use strict';
const $ = (id) => document.getElementById(id);
const token = document.querySelector('meta[name="sandbox-token"]').content;
let caseData, selected = null, refreshSequence = 0, traceSequence = 0, artifactSequence = 0;
const compared = new Set();
const results = new Map();
const colors = ['#276650', '#b46b29', '#416c9e', '#9d4d62', '#698243', '#7856a0', '#29868b', '#955c36'];
const statusNames = {completed:'完成',cancelled:'已取消',timed_out:'超时',running:'运行中',preparing:'准备中',terminating:'正在终止',refused:'拒绝启动',run_failed:'计算失败',failed:'失败',supervisor_failed:'监督失败',unverified_result:'结果尚未验证',abnormal_exit:'异常退出'};
function message(text, error=false) { $('message').textContent=text; $('message').className=error?'error':''; }
async function api(path, body, rawText=false) {
  const response = await fetch('/api'+path, {method:body===undefined?'GET':'POST',headers:{'X-Sandbox-Token':token,...(body===undefined?{}:{'Content-Type':'application/json'})},...(body===undefined?{}:{body:JSON.stringify(body)})});
  if(response.ok && rawText)return response.text();
  const value = await response.json();
  if (!response.ok) throw new Error(value.reason || value.error || value.message || JSON.stringify(value));
  return value;
}
function handle(action) { return async(event) => { event?.preventDefault(); try { await action(); } catch(error) { message(error.message,true); } }; }
function fillControls() {
  $('cells').value=String(caseData.grid.cells); $('profile').value=caseData.profile;
  $('transport').value=caseData.transport_mode; $('refinement').value=String(caseData.refinement);
  $('case-json').value=JSON.stringify(caseData,null,2);
}
function controlsToCase() {
  caseData.grid.cells=Number($('cells').value); caseData.profile=$('profile').value;
  caseData.transport_mode=$('transport').value; caseData.refinement=Number($('refinement').value);
  $('case-json').value=JSON.stringify(caseData,null,2);
  return structuredClone(caseData);
}
for (const id of ['cells','profile','transport','refinement']) $(id).addEventListener('change',()=>controlsToCase());
$('apply-json').onclick=handle(async()=>{
  const candidate=JSON.parse($('case-json').value);
  await api('/validate',{case:candidate}); caseData=candidate; fillControls(); message('JSON 编辑已通过结构校验并应用；材料适用性仍未验证。');
});
$('validate').onclick=handle(async()=>{const value=await api('/validate',{case:controlsToCase()}); message('案例结构有效 · '+value.case_sha256.slice(0,12)+'；未执行物理求解。');});
$('case-form').onsubmit=handle(async()=>{
  $('run').disabled=true;
  try { const value=await api('/jobs',{case:controlsToCase(),wall_seconds:Number($('wall').value),grace_seconds:5}); selected=value.id; clearTrace(); compared.clear(); compared.add(selected); message('运行已提交。'); await refresh(); }
  finally { $('run').disabled=false; }
});
$('refresh').onclick=handle(refresh);
$('cancel').onclick=handle(async()=>{if(!selected)return; await api(`/jobs/${selected}/cancel`,{});message('取消请求已记录，等待实际退出确认。');await refresh();});
for (const operation of ['replay','resume']) $(operation).onclick=handle(async()=>{
  if(!selected)return;const value=await api(`/jobs/${selected}/${operation}`,{});selected=value.id;clearTrace();compared.clear();compared.add(selected);message('已提交'+(operation==='resume'?'续算':'重放')+'。');await refresh();
});
$('export').onclick=handle(async()=>{
  if(!selected)return; const id=selected;const report=await api(`/jobs/${id}/export`,undefined,true);if(id!==selected)return;
  // Preserve exact integer ledger fields; JSON.parse/stringify loses integers beyond 2**53.
  $('export-report').value=report;$('export-panel').hidden=false;$('export-panel').open=true;$('export-label').textContent='任务 '+id.slice(0,8)+' 的 JSON 报告';
  const url=URL.createObjectURL(new Blob([report],{type:'application/json'}));
  const link=document.createElement('a');link.href=url;link.download=`sandbox-${id}.json`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  message('JSON 报告已生成并请求下载；未收到浏览器下载确认时，可复制下方报告。报告不含全部来源文件，不能单独重放。');
});
function jobLabel(item) { return item.owned_worker_active ? '本服务正在处理 · '+(statusNames[item.job?.status]||item.job?.status||'排队') : (statusNames[item.job?.status]||item.job?.status||item.error||'尚无保存状态'); }
async function refresh() {
  const sequence=++refreshSequence;
  const value=await api('/jobs'); if(sequence!==refreshSequence)return;
  const focusKey=$('jobs').contains(document.activeElement)?document.activeElement?.dataset?.focusKey:null;
  $('jobs').replaceChildren();
  if(!value.jobs.length) $('jobs').textContent='暂无运行。编辑左侧案例后开始。';
  for(const item of value.jobs) {
    const row=document.createElement('div');row.className='job-row'+(selected===item.id?' active':'');
    const button=document.createElement('button');button.type='button';button.dataset.focusKey=item.id+':select';button.textContent=item.id.slice(0,8)+' · '+jobLabel(item);
    button.onclick=handle(async()=>{selected=item.id;if(!compared.has(selected)){if(compared.size>=2)compared.clear();compared.add(selected);}clearTrace();await refresh();});
    const label=document.createElement('label'),check=document.createElement('input');check.type='checkbox';check.dataset.focusKey=item.id+':compare';check.checked=compared.has(item.id);check.setAttribute('aria-label','比较 '+item.id.slice(0,8));
    check.onchange=handle(async()=>{if(check.checked){if(compared.size>=2){check.checked=false;message('一次最多比较两条记录。',true);return;}compared.add(item.id);}else compared.delete(item.id);await refresh();});
    label.append(check,document.createTextNode('比较'));row.append(button,label);$('jobs').append(row);
  }
  if(focusKey){const target=[...$('jobs').querySelectorAll('[data-focus-key]')].find(node=>node.dataset.focusKey===focusKey);target?.focus({preventScroll:true});}
  const wanted=new Set(compared);if(selected)wanted.add(selected);
  const records=await Promise.all([...wanted].map(async id=>[id,await api(`/jobs/${id}`)]));
  if(sequence!==refreshSequence)return;
  for(const [id,item] of records)results.set(id,item);
  if(selected&&results.has(selected)) {
    const item=results.get(selected);$('selected').hidden=false;$('job-title').textContent='任务 '+selected.slice(0,8);
    $('job-state').textContent=jobLabel(item)+(item.error?' · '+item.error:'');$('job-detail').textContent=JSON.stringify(item.job,null,2);
    $('cancel').disabled=!item.owned_worker_active;$('export').disabled=!item.result;
    $('replay').disabled=!item.result||item.owned_worker_active;
    $('resume').disabled=item.owned_worker_active||item.result?.status!=='cancelled'||!item.result?.integration?.steps?.length;
  }
  renderPlots();
}
function traceQuantity(quantity) {
  return ['normal_stretch','tangential_stretch'].includes(quantity)?'mechanical_stretches':quantity;
}
function mechanicalSeries(id,integration,quantity) {
  const states=integration.states,times=integration.times_s;
  if(!Array.isArray(states)||!states.length||!Array.isArray(times)||times.length!==states.length||
     times.some((time,index)=>!Number.isFinite(time)||(index>0&&time<=times[index-1])))return [];
  const cells=states[0]?.amounts_mol?.length;
  if(!Number.isInteger(cells)||cells<1)return [];
  if(states.some(state=>!Array.isArray(state?.amounts_mol)||state.amounts_mol.length!==cells||
    !Array.isArray(state.internal_energy_j)||state.internal_energy_j.length!==cells||
    !Array.isArray(state.mechanical_stretches)||state.mechanical_stretches.length!==cells+1||
    state.mechanical_stretches.some(value=>!Number.isFinite(value)||value<=0)))return [];
  const tangent=quantity==='tangential_stretch';
  return Array.from({length:tangent?1:cells},(_,index)=>({
    name:id.slice(0,8)+(tangent?' / 公共切向伸长':' / 单元 '+(index+1)+' 法向伸长'),
    points:states.map((state,k)=>[times[k],state.mechanical_stretches[tangent?cells:index]]),
    cell:tangent?null:index,thermal:false,global:tangent,
  }));
}
function seriesFor(id,result,quantity) {
  const integration=result?.integration;if(!integration?.states?.length)return [];
  if(['normal_stretch','tangential_stretch'].includes(quantity))return mechanicalSeries(id,integration,quantity);
  let states=integration.states, times=integration.times_s;
  const thermal=['temperature_k','pressure_pa'].includes(quantity);
  if(thermal) {
    if(!result.initial_snapshot?.[quantity]||!result.final_snapshot?.[quantity])return [];
    states=[result.initial_snapshot,result.final_snapshot];times=[integration.times_s[0],integration.times_s.at(-1)];
  }
  const values=states.map(state=>quantity==='amounts_mol'?state.amounts_mol.map(row=>row[2]):state[quantity]);
  if(values.some(row=>!Array.isArray(row)))return [];
  return values[0].map((_,cell)=>({name:id.slice(0,8)+' / 单元 '+(cell+1),points:values.map((row,index)=>[times[index],row[cell]]),cell,thermal}));
}
function svgNode(name,attrs,text) { const node=document.createElementNS('http://www.w3.org/2000/svg',name);for(const [key,value] of Object.entries(attrs))node.setAttribute(key,String(value));if(text!==undefined)node.textContent=text;return node; }
function draw(svg,series,xlabel,connect=true) {
  svg.replaceChildren();const points=series.flatMap(s=>s.points).filter(p=>p.every(Number.isFinite));
  if(!points.length){svg.append(svgNode('text',{x:30,y:130},'暂无可验证的保存数据'));return;}
  let xmin=Math.min(...points.map(p=>p[0])),xmax=Math.max(...points.map(p=>p[0]));
  let ymin=Math.min(...points.map(p=>p[1])),ymax=Math.max(...points.map(p=>p[1]));
  if(xmin===xmax)xmax=xmin+1;if(ymin===ymax){const pad=Math.max(Math.abs(ymin)*.01,1e-12);ymin-=pad;ymax+=pad;}
  const x=v=>75+(v-xmin)/(xmax-xmin)*530,y=v=>225-(v-ymin)/(ymax-ymin)*195;
  svg.append(svgNode('path',{d:'M75 25V225H610',fill:'none',stroke:'#b8c7b9'}));
  for(let i=0;i<=4;i++){
    const vy=ymin+(ymax-ymin)*i/4;svg.append(svgNode('text',{x:68,y:y(vy)+4,'text-anchor':'end'},vy.toPrecision(8)));
    const vx=xmin+(xmax-xmin)*i/4;svg.append(svgNode('text',{x:x(vx),y:247,'text-anchor':'middle'},vx.toPrecision(6)));
  }
  svg.append(svgNode('text',{x:330,y:272,'text-anchor':'middle'},xlabel));
  series.forEach((s,index)=>{
    const valid=s.points.filter(p=>p.every(Number.isFinite));const color=colors[index%colors.length];
    if(connect&&!s.thermal)svg.append(svgNode('polyline',{points:valid.map(p=>`${x(p[0])},${y(p[1])}`).join(' '),fill:'none',stroke:color,'stroke-width':2}));
    for(const point of valid){const circle=svgNode('circle',{cx:x(point[0]),cy:y(point[1]),r:3,fill:color});circle.append(svgNode('title',{},`${s.name}: ${point[0]}, ${point[1]}`));svg.append(circle);}
  });
}
function renderPlots() {
  const quantity=$('quantity').value;let all=[];const spatial=[];
  for(const id of compared){const item=results.get(id);const series=seriesFor(id,item?.result,quantity);all.push(...series);if(series.length&&!series[0].global)spatial.push({name:id.slice(0,8),points:series.map(s=>[s.cell+1,s.points.at(-1)[1]]),thermal:false});}
  draw($('time-chart'),all,'保存的物理时间（s）');draw($('space-chart'),spatial,'厚度单元编号（非实际距离）');
  $('legend').replaceChildren();for(let i=0;i<all.length;i++){const span=document.createElement('span');span.className='legend-item';span.style.borderColor=colors[i%colors.length];span.textContent=all[i].name;$('legend').append(span);}
  $('space-legend').replaceChildren();for(let i=0;i<spatial.length;i++){const span=document.createElement('span');span.className='legend-item';span.style.borderColor=colors[i%colors.length];span.textContent='空间图 / '+spatial[i].name;$('space-legend').append(span);}
  $('plot-note').textContent=['temperature_k','pressure_pa'].includes(quantity)?'温度和压力仅展示已保存的初态、成功终态点，不补造中间曲线。空间图按单元编号展示。':'折线连接已接受的离散状态，不代表连续解。各单元库存与能量是广延量；不同网格不能直接当作同体积比较。';
  if(quantity==='normal_stretch')$('plot-note').textContent=all.length?'法向伸长无量纲；每个单元一条已接受状态曲线。空间图使用单元编号。':'法向伸长不可用：保存状态缺失、非有限或形状不匹配。';
  if(quantity==='tangential_stretch')$('plot-note').textContent=all.length?'公共切向伸长无量纲；每个运行只有一个全局自由度，不展示切向空间曲线。':'公共切向伸长不可用：保存状态缺失、非有限或形状不匹配。';
}
$('quantity').onchange=()=>{renderPlots();clearTrace();};
function clearTrace() { traceSequence++;artifactSequence++;$('export-panel').hidden=true;$('export-report').value=''; $('sources').replaceChildren();$('trace-detail').textContent='';$('trace-status').textContent='';$('artifact').hidden=true; }
$('trace').onclick=handle(async()=>{
  if(!selected){message('先选择一条运行。',true);return;}
  clearTrace();const generation=traceSequence;
  const id=selected,quantity=$('quantity').value;const trace=await api(`/jobs/${id}/trace?quantity=${encodeURIComponent(traceQuantity(quantity))}`);
  if(generation!==traceSequence||id!==selected||quantity!==$('quantity').value)return;
  $('trace-detail').textContent=JSON.stringify(trace,null,2);$('trace-status').textContent=`任务 ${id.slice(0,8)} · ${quantity}：已校验保存的文件清单，以下是该结果的来源节点。`;
  const graph=trace.dependency_graph;
  for(const node of graph?.nodes||[]) {
    if(node.node_type!=='source')continue;
    const button=document.createElement('button');button.textContent=`${node.kind||node.classification||'unknown'} · ${node.artifact||node.id} · ${node.locator||''} · ${node.availability||'unknown'}`;
    button.disabled=node.availability!=='present'||!node.artifact;
    button.onclick=handle(async()=>{const artifactGeneration=++artifactSequence;const artifact=await api(`/jobs/${id}/artifact?path=${encodeURIComponent(node.artifact)}`);if(generation!==traceSequence||artifactGeneration!==artifactSequence||id!==selected||quantity!==$('quantity').value)return;$('artifact').hidden=false;$('artifact-title').textContent=artifact.path+' · SHA '+artifact.sha256;$('artifact-text').textContent=artifact.text;});
    $('sources').append(button);
  }
});
async function start() {
  const config=await api('/config');caseData=config.case;fillControls();$('case-id').textContent=caseData.case_id+' · '+config.case_sha256.slice(0,12);
  for(const text of config.unknowns){const item=document.createElement('li');item.textContent=text;$('unknowns').append(item);}
  message('已载入验证案例。每个存储目录最多 '+config.maximum_jobs+' 个任务。');await refresh();
  const poll=async()=>{try{await refresh();}catch(error){message('刷新失败：'+error.message,true);}setTimeout(poll,2000);};setTimeout(poll,2000);
}
start().catch(error=>message('启动失败：'+error.message,true));
