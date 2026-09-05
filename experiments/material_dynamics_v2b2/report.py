"""中文研究结论来自本次数据，不预设早升温或包络排序反转。"""
from collections import Counter
from scenarios import matrix


def generate(out,diagnostics,screening,manifest):
    by={d['scenario_id']:d for d in diagnostics}; statuses=Counter(r['screening_status'] for r in screening)
    lines=['# 给温反应—输运与条件化原料研究报告','',
           '## 条件方向与限制（先读）','',
           '这是外部空间均匀给温、固定孔隙/壁几何、固定参考浓度的 synthetic 无量纲实验，不是真实污泥配方、供应商筛选或烧成秒数。',
           '寻找原料时，应联合核对干基可氧化需氧负荷、基料—原泥配对、氧化时序、壁/肋厚和热态输运；本轮没有识别这些真实材料映射。',
           '低负荷、提前升温、较小壁厚的方向必须以本页实际配对为条件，不能保证普遍改善；U0/U1只是假设包，不是概率区间或最坏界。',
           '恒摩尔浓度源库不等于恒压空气；不建能量、压力、热膨胀流、孔关闭、收缩、强度、裂纹或排放模型。physical_time_seconds=null，material_mapping=unknown_real_material。','',
           '## 已验证事实：当前运行','',
           f"- 绑定状态：{manifest['binding_status']}；原因：{manifest['binding_reason']}。",
           f"- 实际源提交：{manifest['source_commit']}。合同：B2-1.0.1；详见 manifest.json 的逐文件实算SHA256与完整展开输入。",
           f"- focused证据：{manifest.get('focused_evidence')}。当前raw文件与audit身份均见manifest；无证据时不升级。",
           f"- 离散筛选状态计数（逐情景，不是供应商）：{dict(statuses)}。",
           '- 数值标签只对应本次实际代表覆盖与逐例库存审计，不代表24门全部批准；独立Safety尚待单独审核，production_approved=false。','',
           '| 情景 | Γ | 最大局部剩余 f | 平均剩余 f | 芯部氧 u | 数值验证 | 条件筛选 |',
           '|---|---:|---:|---:|---:|---|---|']
    for r in screening:
        lines.append(f"| {r['scenario_id']} | {r['Gamma']:g} | {r['f_max']:.8g} | {r['f_mean']:.8g} | {r['u_core']:.8g} | {r['numerical_validation']} | {r['screening_status']} |")
    lines+=['','## 实际配对与可证伪反例','', '以下差值均为后者减前者，正差表示所列后者局部残余更多；不是材料因果证明。']
    for group in ('timing_pairs','length_pairs'):
        lines+=['', '### '+('给温程序配对' if group=='timing_pairs' else '壁厚配对（共同τ，不是磨细颗粒）')]
        for a,b in matrix()['scenario_manifest'][group]:
            if a in by and b in by:
                va=by[a]['at_end']; vb=by[b]['at_end']
                min_a=min(row['u_core'] for row in _rows(out,a)); min_b=min(row['u_core'] for row in _rows(out,b))
                lines.append(f"- {a}→{b}：末态 f_max 差={vb['f_max']-va['f_max']:.8g}；实际采样最小芯部氧分别 {min_a:.8g}/{min_b:.8g}。")
    timing=matrix()['scenario_manifest']['timing_pairs']; valid=[(a,b) for a,b in timing if a in by and b in by]
    worse=[(a,b) for a,b in valid if by[a]['at_end']['f_max']>by[b]['at_end']['f_max']+1e-6]
    if valid:
        lines.append('本离散域观察到早升温末态残余更多的配对：'+str(worse) if worse else '本离散域未观察到“早升温使末态局部残余更高”的反转；这不能证明连续域或真实材料必然如此。')
    for sid in ('R03','C03','R04'):
        if sid in by:
            d=by[sid]
            lines.append(f"- {sid}：氧预算转化上界={d['conversion_upper_bound']}；末态剩余均值={d['at_end']['f_mean']:.8g}；末态源率={d['at_end']['source_rate']:.8g}；平均99事件={d['events']['mean99']}；局部99事件={d['events']['local99']}。")
    lines+=['','## 合理推断与待验证假设','',
            '- 仅在同一基料代理、供氧边界和给温窗口内讨论负荷—输运条件。finite总氧库存的必要上界不因提前反应而改变；反应近停不是燃尽。',
            '- f_max是最大cell平均，不是连续场严格最大值；事件由0.1τ输出包围区间插值，null表示未发生，不是0误差。guard=0.005是报告缓冲，不是已证明的全域误差界。',
            '- 不把PSD磨细当作减小壁半厚；脱水不自动降低干基可氧化碳Γ。预氧化/混配可能改变孔隙、塑性、多组分气体和排放，这些联动未建模。',
            '- S02输运拟合限环境温度至500°C，A600异常；S09为N2预热后切气的873–1273K颗粒准等温试验，40–60%转化拟合、80/100%O2自热排除；非整数分压阶与K0单位未解决。没有把这些候选参数迁为B2材料常数（原来源定位见CONTRACT.md §3）。',
            '- 守恒审计仅重建导出库存/通量/派生指标，不是完整ODE真实性或任意协同篡改检测。独立数学参考、源码身份、实际重跑是不同证据层。',
            '- thermal_profiles.svg / conditional_screening.svg 来自CSV，结构和坐标可复算；未做GUI/CJK像素验收。','',
            '## 证据与复现','',
            'manifest.json → 完整inputs、raw_result_files、current_audit、focused_evidence、coverage；verification.json → 本次逐情景标签；test_results.json → 原24门与未执行独立审核；resources.json → 计算机墙钟/RSS，不是过程时间。',
            '复现顺序与离线封包见README.md。无部署；失败则停止使用隔离模块并保留证据，撤销提交须Manager批准revert，不删除B1/Stage1或改写历史。']
    (out/'THERMAL_DIAGNOSTIC_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def _rows(out,sid):
    import csv
    with (out/'timeseries.csv').open() as f:
        return [{k:(float(v) if k=='u_core' else v) for k,v in r.items()} for r in csv.DictReader(f) if r['scenario_id']==sid]
