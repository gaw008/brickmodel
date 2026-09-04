"""Deterministic, dependency-free audit exports and light Chinese SVG charts."""
from collections import Counter, defaultdict
import csv
from html import escape
import json
from pathlib import Path
import statistics

from pipeline import HERE, MATERIAL_FIELDS, OBSERVATION_FIELDS, coordinate, number


SHEET_ROLES = {
    'Overview': '材料/温度/实验系列索引；不新增测量样本',
    'Mixing': '干基配方与加水记录；选取干质量作为条件，模板/总计不作试件',
    'Water and Burning': '原始称量及水分/烧失量；标题950–1000为旧模板，实际区块为1020/1030/1050',
    'W&B Figures': '复制原始称量并插入均值/标准差的图表辅助表；不计样本',
    'W&B Figures 2': '组均值/标准差二次汇总；不计样本',
    'High and Diameter': '逐片三方向卡尺读数和源派生均值/体积/收缩',
    'H&D Figures': '原始尺寸的引用/图表辅助及均值；不计样本',
    'H&D Figures 2': '组均值二次汇总与元素关系图辅助；不计样本',
    'Porosity and Density': '三片真空饱水原始称量与源派生物性；干质量链接原始烧成称量',
    'P&D 2': '饱水表引用及均值/标准差；不计样本',
}


def dump_json(path, content):
    Path(path).write_text(json.dumps(content, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def dump_csv(path, rows, fields=None):
    if fields is None:
        fields = list(rows[0]) if rows else []
    with Path(path).open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in row.items()})


def excluded_reason(sid, sheet, cell):
    col, row = coordinate(cell)
    if sid == '30156127':
        if row <= 20:
            return '原表化学组成/LOI标题、间隔或说明'
        if row <= 39:
            return '混配计算标题；非独立XRF样本'
        if row <= 54:
            return '已导入氧化物混配表的转置图表辅助；不计样本'
        return '元素换算常数/换算表；本分析使用氧化物报告基础，不计新样本'
    if sid == '30157066':
        if row <= 32:
            return '仪器导出元数据/标题；条件已另表记录'
        if col == 4 and sheet in ('Pilot-8','Pilot-10','#0262','#0263'):
            return '源百分比Table引用非本地质量列；全部隔离，见derivations.json'
        return '仪器气流/灵敏度辅助通道；不拟合动力学'
    if sid == '30156970':
        return '标题/粒径坐标起点或黏土粉砂阈值画线辅助；不计分布样本'
    if sheet in ('W&B Figures','W&B Figures 2','H&D Figures','H&D Figures 2','P&D 2'):
        return SHEET_ROLES[sheet]
    if sheet == 'Porosity and Density' and row >= 14 and col in (5,8,9,10,18):
        return '同一质量的引用、g转kg或重复孔隙率列；不重复导入'
    return SHEET_ROLES[sheet]+'；本单元格为未选说明、标签、辅助统计或条件记录'


def audit(study):
    sheets, row_audit, formula_audit = [], [], []
    checks = {(d['source_id'],d['sheet'],d['cell']):d for d in study.derivations}
    for sid, book in study.books.items():
        for name, ws in book.items():
            nonempty = {a:c for a,c in ws.cells.items() if c.value is not None or c.formula is not None}
            by_row = defaultdict(list)
            for a,c in nonempty.items():
                by_row[coordinate(a)[1]].append((a,c))
                if c.formula is not None:
                    check = checks.get((sid,name,a))
                    formula_audit.append({'source_id':sid,'file':study.files[sid],'sheet':name,'cell':a,
                        'formula':c.formula,'shared_anchor':c.shared_anchor,'cached_value':c.value,
                        'cache_kind':c.kind, 'external_reference': '[' in c.formula and '!' in c.formula,
                        'verification': 'diagnostic_only' if check and check.get('role') else
                            'recomputed_match' if check and check['verified'] else 'recomputed_mismatch' if check else 'not_recomputed'})
            selected = sum((sid,name,a) in study.used for a in nonempty)
            formulas = [c for c in nonempty.values() if c.formula is not None]
            sheets.append({'source_id':sid,'file':study.files[sid],'sheet':name,'state':ws.state,
                'dimension':ws.dimension,'merged_ranges':ws.merged_ranges,
                'nonempty_rows':len(by_row),'nonempty_cells':len(nonempty),
                'explicit_blank_cells':len(ws.cells)-len(nonempty),
                'formula_cells':len(formulas), 'shared_formula_cells':sum(c.shared_anchor is not None for c in formulas),
                'formula_missing_cache':sum(c.value is None for c in formulas),
                'error_cells':sum(c.kind=='e' for c in nonempty.values()),
                'selected_cells':selected,'excluded_cells':len(nonempty)-selected,
                'role':SHEET_ROLES.get(name, '原料XRF/源混配/元素辅助' if sid=='30156127' else '粒径分布及累计/画线辅助' if sid=='30156970' else '单升温速率N2-TGA原始曲线')})
            for row, cells in sorted(by_row.items()):
                used = [a for a,c in cells if (sid,name,a) in study.used]
                excluded = {a:excluded_reason(sid,name,a) for a,c in cells if (sid,name,a) not in study.used}
                row_audit.append({'source_id':sid,'file':study.files[sid],'sheet':name,'row':row,
                    'nonempty_cells':len(cells), 'selected_cells':len(used),'excluded_cells':len(excluded),
                    'selected_addresses':used, 'excluded_addresses_and_reasons':excluded})
    return sheets,row_audit,formula_audit


def registry(study):
    entries = []
    for sid in study.books:
        meta = json.loads((study.input_dir/(sid+'-metadata.json')).read_text())
        entries.append({'source_id':sid,'url':'https://api.figshare.com/v2/articles/'+sid,'doi':meta['doi'],
            'authors':[a['full_name'] for a in meta['authors']], 'year':2025,
            'license':meta['license'], 'title':meta['title'], 'description_verbatim':meta['description'],
            'files':[x for x in study.input_hashes if '/'+sid+'/' in x['file']],
            'material_classes':['clay','sewage_sludge_ash','unknown'] if sid!='30156970' else ['sewage_sludge_ash','unknown'],
            'atmosphere':'N2; metadata 50 ml/min purge' if sid=='30157066' else 'unknown/not_applicable_to_measurement',
            'geometry':'powder in Al2O3 crucible; recorded mass per curve in conditions.json' if sid=='30157066' else
                'small pressed discs; nominal 4 g green; actual mm readings in observations.csv' if sid=='30157108' else
                '1.6 g powder + 10 g flux fused bead' if sid=='30156127' else 'dried/milled powder dispersed in ethanol',
            'coverage':'single DTU study; within-study associations only; source identity is declared rather than independent chain-of-custody',
            'not_transferable':['raw sewage sludge oxidation','full brick/tunnel kiln behavior','certified strength','factory emissions compliance'],
            'normalization':'preserve source oxide+LOI basis; no normalization to oxide-only total or phase fractions' if sid=='30156127' else None})
    ref = json.loads((HERE/'raw-sludge-crossref.json').read_text())['message']
    entries.append({'source_id':'raw-sludge-en16186634','url':'https://www.mdpi.com/1996-1073/16/18/6634',
        'doi':ref['DOI'],'title':ref['title'][0],'authors':[a.get('given','')+' '+a.get('family','') for a in ref['author']],
        'year':2023,'license':ref.get('license'), 'material_classes':['raw_sewage_sludge'],
        'preparation':'Astana municipal sludge dried 105 C 24 h; not SSA',
        'atmosphere':'air TG at 15 C/min; kinetic TG at 10/15/20 C/min in N2; separate BFB combustion in air',
        'geometry':'TG dry powder; BFB pellets 0.55±0.05 g at 850 C; not clay-bound full bricks',
        'coverage':'methods and results text read; supplementary raw numerical curves NOT obtained; not imported as measurements',
        'not_transferable':['N2 apparent activation energy is not air oxidation rate law','BFB residence time is not kiln firing time','emissions are not factory compliance'],
        'evidence_file':'../literature_evidence.md'})
    return {'schema_version':'1.0','scope':'research_stage1_pending_independent_review', 'entries':entries,
        'primary_paper':{'doi':'10.1016/j.cscm.2025.e05387','url':'https://www.sciencedirect.com/science/article/pii/S2214509525011854',
            'access':'abstract/highlights/data-availability read; NOT full text; DTU open PDF HTTP403, web_extract failed, Wayback429',
            'open_pdf_url':'https://orbit.dtu.dk/files/418782101/1-s2.0-S2214509525011854-main.pdf'},
        'identity_rules':{'resolved':'Overview!B6:B7,E6:E9 + XRF!B1:G1,B26:M28 + TGA!B16; Av/P1 and Ly/P2 from README',
            'ambiguous':'all A2P / #0179 / PSD Silica Sand labels; preserved, no quantitative pairing',
            'unresolved_global_notes':'P&D!M4:M5 legacy E21-F21-G21-H21/#0010 labels; no evidence of actual chain-of-custody; row-local sample IDs and exact mass references used, confidence limited'},
        'evidence_boundary':['Raw SSA is incinerated ash, not raw sewage sludge','No fitted model or external validation in this stage',
            'No strength proxy, threshold, optimal recipe, production approval, or continuous feasible window']}


COLORS = {'Ref':'#77828e','P1-Raw':'#33849c','P1-ED':'#b77238','P2-Raw':'#55884d','P2-ED':'#8663a0'}


def svg_text(x,y,text,size=15,**attrs):
    attributes = ' '.join(f'{k.replace("_","-")}="{escape(str(v),quote=True)}"' for k,v in attrs.items())
    return f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" {attributes}>{escape(str(text))}</text>'


def figures(groups, output):
    chart_rows = []
    for name, tradeoff in [('observation_comparison.svg',False),('treatment_tradeoff.svg',True)]:
        parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="790" viewBox="0 0 1200 790">',
            '<rect width="1200" height="790" fill="#fafaf7"/>',
            '<g fill="#263744" font-family="Noto Sans CJK SC,Microsoft YaHei,PingFang SC,sans-serif">']
        title = '致密化与尺寸变化：处理并非单向改善' if tradeoff else '相同基料与名义烧成温度下的吸水率对比'
        parts.append(svg_text(44,48,title,26,font_weight=600))
        parts.append(svg_text(44,78,'文献观测的组统计｜0 或 30% 干基 SSA｜排除身份冲突 A2P｜不外推连续可行域',15))
        for j,label in enumerate(COLORS):
            x=60+j*211
            parts.append(f'<rect x="{x}" y="102" width="14" height="14" fill="{COLORS[label]}"/>')
            parts.append(svg_text(x+22,114,'无灰参照' if label=='Ref' else label,14))
        for panel,matrix in enumerate(('Y','R')):
            x0,y0,w,h = 110+panel*574,188,432,360
            parts.append(svg_text(x0,156,'Y：高碳酸盐黄砖基料' if matrix=='Y' else 'R：低碳酸盐红砖基料',18,font_weight=600))
            parts.append(svg_text(x0,177,'吸水率（质量 %）',13))
            for tick in (5,10,15,20,25):
                y=y0+h-(tick-5)/20*h
                parts.append(f'<line x1="{x0}" x2="{x0+w}" y1="{y}" y2="{y}" stroke="#dce1e3"/>')
                parts.append(svg_text(x0-16,y+5,tick,12,text_anchor='end'))
            parts.append(f'<path d="M{x0} {y0} V{y0+h} H{x0+w}" stroke="#697a86" fill="none"/>')
            ticks=(0,2,4,6,8,10) if tradeoff else (1020,1030,1050)
            for tick in ticks:
                x = x0+(tick+0.7)/11.4*w if tradeoff else x0+65+(temp_index(tick))*150
                parts.append(svg_text(x,y0+h+24,tick,12,text_anchor='middle'))
            parts.append(svg_text(x0+w/2,y0+h+52,'直径烧成收缩（%）；正值为收缩' if tradeoff else '名义最高烧成温度（°C）',14,text_anchor='middle'))
            for g in [g for g in groups if g['matrix_id']==matrix]:
                label=g['group_id'].split('|')[1]
                ti=temp_index(g['firing_temperature_C'])
                x = x0+(g['diameter_shrinkage_mean']+0.7)/11.4*w if tradeoff else x0+65+ti*150+(list(COLORS).index(label)-2)*13
                y = y0+h-(g['water_absorption_mean']*100-5)/20*h
                color=COLORS[label]
                group_id=escape(g['group_id'],quote=True)
                parts.append(f'<g data-series="{group_id}"><title>{group_id}: mean water absorption={g["water_absorption_mean"]*100:.4f}%; mean diameter shrinkage={g["diameter_shrinkage_mean"]:.4f}%; n_water=3, n_shrinkage=7; source 30157108</title>')
                if not tradeoff:
                    e=g['water_absorption_sd']*100/20*h
                    parts.append(f'<path d="M{x} {y-e} V{y+e} M{x-3} {y-e} H{x+3} M{x-3} {y+e} H{x+3}" stroke="{color}"/>')
                if tradeoff and ti==1:
                    parts.append(f'<rect x="{x-4.5}" y="{y-4.5}" width="9" height="9" fill="{color}" stroke="#ffffff"/>')
                elif tradeoff and ti==2:
                    parts.append(f'<path d="M{x} {y-6} L{x+6} {y+4} L{x-6} {y+4} Z" fill="{color}" stroke="#ffffff"/>')
                else:
                    parts.append(f'<circle cx="{x}" cy="{y}" r="4.8" fill="{color}" stroke="#ffffff"/>')
                parts.append('</g>')
                chart_rows.append({'figure':name,'group_id':g['group_id'],'n_water':g['n_water'],
                    'n_shrinkage':g['n_shrinkage'] if tradeoff else None,
                    'water_specimens':g['water_specimens'],'shrinkage_specimens':g['shrinkage_specimens'] if tradeoff else [],
                    'x_value':g['diameter_shrinkage_mean'] if tradeoff else g['firing_temperature_C'],
                    'y_value':g['water_absorption_mean']*100,'y_unit':'mass %',
                    'evidence_status':'model_derived','expression':'mean of within-series source-derived disc values; absorption kg/kg * 100'})
        if tradeoff:
            caption='每点为同系列组均值：横轴 7 片，纵轴其中 3 片；不是逐片相关或独立批次验证。'
            shape='圆点 1020°C  ·  方点 1030°C  ·  三角 1050°C；不连线、不设最优边界。'
        else:
            caption='每点 3 片的均值 ± 样本标准差；组内离散不是跨工厂置信区间；横向错开仅为可读性。'
            shape='30 个有效系列，90 片饱水试件；温度离散取样，不插值。'
        parts.extend([svg_text(44,644,caption,14),svg_text(44,669,shape,14),
            svg_text(44,694,'气氛、升温速率、保温时长未确认；小圆片不是整砖；吸水率不能替代强度认证。',14),
            svg_text(44,732,'数据：DTU · Feldthus, Kirkelund, Ottosen, Bertelsen (2025) · CC BY 4.0',13),
            svg_text(44,755,'DOI: 10.11583/DTU.30157108；关联论文 10.1016/j.cscm.2025.e05387；重分析与制图：材料设计 v2',12),
            '</g></svg>'])
        (output/name).write_text('\n'.join(parts),encoding='utf-8')
    dump_csv(output/'chart_data.csv',chart_rows)
    return chart_rows


def temp_index(temp):
    return (1020,1030,1050).index(temp)


def markdown_table(headers, rows):
    def line(values):
        return '| '+' | '.join(str(v).replace('|',' / ') for v in values)+' |'
    return '\n'.join([line(headers),line(['---']*len(headers))]+[line(row) for row in rows])


def reports(study, output, groups, sheets, counts):
    by_id = {g['group_id']:g for g in groups}
    contrasts=[]
    for matrix in ('Y','R'):
        for plant in ('P1','P2'):
            raw=by_id[f'{matrix}|{plant}-Raw|1050']
            ed=by_id[f'{matrix}|{plant}-ED|1050']
            contrasts.append([matrix,plant,f'{raw["water_absorption_mean"]*100:.3f}',f'{ed["water_absorption_mean"]*100:.3f}',
                f'{(ed["water_absorption_mean"]-raw["water_absorption_mean"])*100:+.3f}',
                f'{ed["diameter_shrinkage_mean"]-raw["diameter_shrinkage_mean"]:+.3f}'])
    psd=[]
    for label in ('#0262','Pilot-8','#0263','Pilot-10'):
        curve=[r for r in study.materials if r['source_id']=='30156970' and r['original_label']==label and r['property']=='psd_cumulative_volume']
        crossing=next(r for r in curve if r['value']>=50)
        row=coordinate(crossing['cell'])[1]
        size=study.books['30156970']['Sheet2'].value(f'E{row}')
        psd.append([label, f'{size:.3f}',f'{crossing["value"]:.3f}',f'Sheet2!E{row}, {crossing["cell"]}'])
    recomputations=[]
    for sid in study.books:
        checks=[d for d in study.derivations if d['source_id']==sid and not d.get('role')]
        if checks:
            recomputations.append([sid,len(checks),sum(d['verified'] for d in checks),
                f'{max(abs(d["difference"]) for d in checks):.3g}', '独立重算源缓存，绝对容差1e-8（各自源单位）'])
    pd_example=next(d for d in study.derivations if d['source_id']=='30157108' and d['sheet']=='Porosity and Density' and d['cell']=='M14')
    count_rows=[[k,json.dumps(v,ensure_ascii=False) if isinstance(v,dict) else v] for k,v in counts.items()]
    replacements={
        'PELLET_COUNT':counts['pellet_specimens'],'WATER_COUNT':counts['water_test_specimens'],
        'AMBIGUOUS_PELLETS':counts['ambiguous_pellet_specimens'],'GROUP_COUNT':counts['resolved_groups'],
        'SHEET_COUNT':counts['sheets'],'AUDIT_ROWS':counts['audit_rows'],'FORMULA_COUNT':counts['formula_cells'],
        'MISSING_MATERIALS':counts['missing_material_values'],'TGA_DIAGNOSTICS':counts['tga_local_percent_diagnostics'],
        'TGA_MISMATCHES':counts['tga_local_percent_mismatches'], 'TEMP_DELTA':1050-1020,
        'COUNT_TABLE':markdown_table(['计数项（不是同一统计粒度）','值'],count_rows),
        'SHEET_TABLE':markdown_table(['来源','Sheet','非空行','非空格','选取','排除','公式','缺缓存','错误'],
            [[s['source_id'],s['sheet'],s['nonempty_rows'],s['nonempty_cells'],s['selected_cells'],s['excluded_cells'],s['formula_cells'],s['formula_missing_cache'],s['error_cells']] for s in sheets]),
        'RECOMPUTATION_TABLE':markdown_table(['来源','源检查数','匹配','最大绝对差','说明'],recomputations),
        'POROSITY_RECALC':repr(pd_example['recomputed_value']),'POROSITY_CACHE':repr(pd_example['cached_value']),
        'ED_CONTRAST_TABLE':markdown_table(['基料','灰来源','Raw吸水%','ED吸水%','吸水差pp','直径收缩差pp'],contrasts),
        'PSD_TABLE':markdown_table(['原始标签','50%交叉粒径坐标 μm','累计体积%','源地址'],psd),
        'R_P2_1020_WATER':f'{by_id["R|P2-Raw|1020"]["water_absorption_mean"]*100:.3f}',
        'R_REF_1050_WATER':f'{by_id["R|Ref|1050"]["water_absorption_mean"]*100:.3f}',
        'R_P2_1020_SHRINK':f'{by_id["R|P2-Raw|1020"]["diameter_shrinkage_mean"]:.3f}',
        'R_REF_1050_SHRINK':f'{by_id["R|Ref|1050"]["diameter_shrinkage_mean"]:.3f}',
        'GROUP_TABLE':markdown_table(['系列','最高温度°C','直径收缩%','吸水质量%','开放孔隙体积%','干密度kg/m3'],
            [[g['group_id'],g['firing_temperature_C'],f'{g["diameter_shrinkage_mean"]:.3f}',
              f'{g["water_absorption_mean"]*100:.3f}',f'{g["open_porosity_mean"]*100:.3f}',f'{g["dry_density_mean"]:.1f}'] for g in groups])}
    for name in ['DATA_AUDIT.md','DIRECTION_REPORT.md','MODEL_GAP_PRIORITY.md']:
        text=(HERE/'templates'/name).read_text()
        for key,value in replacements.items():
            text=text.replace('{{'+key+'}}',str(value))
        if '{{' in text:
            raise ValueError('unresolved report placeholder')
        (output/name).write_text(text+'\n'+(HERE/'sources_block.md').read_text(),encoding='utf-8')


def export(study, output):
    output.mkdir(parents=True,exist_ok=True)
    groups=study.summarize()
    dump_csv(output/'materials.csv',study.materials,MATERIAL_FIELDS)
    dump_csv(output/'observations.csv',study.observations,OBSERVATION_FIELDS)
    dump_json(output/'derivations.json',study.derivations)
    dump_json(output/'material_evidence.json',study.material_evidence)
    dump_json(output/'source_imputations.json', {'readings':study.imputations,
        'summary_exclusions':[{'specimen_id':s,'property':p,'reason':'depends on source-imputed reading'} for s,p in sorted(study.summary_exclusions)]})
    dump_json(output/'conditions.json',study.conditions)
    dump_json(output/'source_registry.json',registry(study))
    dump_csv(output/'group_summary.csv',groups)
    sheets,rows,formulas=audit(study)
    dump_json(output/'sheet_audit.json',sheets)
    dump_csv(output/'row_audit.csv',rows)
    dump_csv(output/'formula_audit.csv',formulas)
    charts=figures(groups,output)
    counts={'workbooks':len(study.books),'sheets':len(sheets),'materials_rows':len(study.materials),
        'observations_rows':len(study.observations),'audit_rows':len(rows),'formula_cells':len(formulas),
        'pellet_specimens':len({r['specimen_id'] for r in study.observations if r['source_id']=='30157108'}),
        'resolved_groups':len(groups),'water_test_specimens':len({r['specimen_id'] for r in study.observations if r['property']=='water_absorption'}),
        'source_mixture_profiles':len({r['specimen_id'] for r in study.observations if r['source_id']=='30156127'}),
        'tga_curves':len(study.books['30157066']), 'psd_distributions':6,
        'ambiguous_pellet_specimens':len({r['specimen_id'] for r in study.observations if r['source_id']=='30157108' and r['evidence_status']=='identity_ambiguous'}),
        'ambiguous_observations':sum(r['evidence_status']=='identity_ambiguous' for r in study.observations),
        'missing_material_values':sum(r['value'] is None for r in study.materials),
        'source_imputed_dimension_readings':len(study.imputations),
        'source_imputed_specimens':len({i['specimen_id'] for i in study.imputations}),
        'observation_status_counts':dict(Counter(r['evidence_status'] for r in study.observations)),
        'source_recomputations':len([d for d in study.derivations if not d.get('role')]),
        'source_recomputation_mismatches':len([d for d in study.derivations if not d.get('role') and not d['verified']]),
        'tga_local_percent_diagnostics':len([d for d in study.derivations if d.get('role')]),
        'tga_local_percent_mismatches':len([d for d in study.derivations if d.get('role') and not d['verified']]),
        'chart_series_counts':dict(Counter(r['figure'] for r in charts))}
    reports(study,output,groups,sheets,counts)
    return counts
