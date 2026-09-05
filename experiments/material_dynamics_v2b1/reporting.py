"""Generate the Chinese report from actual exports and numerical verification."""
import csv
import json
from pathlib import Path

from plots import event_label


def write_report(out, verification):
    out = Path(out)
    doc = json.loads((out/"summary.json").read_text(encoding="utf-8"))
    scenarios = doc["scenarios"]
    by_id = {s["scenario_id"]:s for s in scenarios}
    audit = json.loads((out/"audit.json").read_text(encoding="utf-8"))
    lines = ["# 材料设计 v2 B1：有限供氧反应—输运诊断", "",
             "## 结论与边界", "",
             "本次实际实现并运行了等温、固定几何的 1D C(s)+O₂→CO₂ 诊断器。"
             "它只是反应—输运诊断增量，未验证真实污泥材料规律，不是原污泥完整质量模型、生产配方或烧成时长预测。"
             "本地实现完成不等于 Safety 批准；独立审核仍由预设子卡执行。", "",
             f'本批导出 {len(scenarios)} 个情景，库存/通量独立审计状态 `{audit["status"]}`；'
             f'数值验证状态 `{verification["numerics"]["status"]}`。所有结果来自本次求解与 CSV 重读，未预填模拟数据。', ""]
    if "finite_small" in by_id and "base" in by_id:
        poor, rich = by_id["finite_small"], by_id["base"]
        p, r = poor["final"], rich["final"]
        lines += ["### 反例：小氧库耗尽，仍有碳", "",
                  f'finite_small：Γ={poor["config"]["Gamma"]:g}，ρ={poor["config"]["reservoir_ratio"]:g}。'
                  f'初始体内氧=1，外库氧={poor["config"]["reservoir_ratio"]:g}，'
                  f'总氧预算={poor["budget"]["total_available_oxygen"]:g}，初始碳={poor["budget"]["initial_solid_carbon"]:g}；'
                  f'因此平均最大转化分数 ≤ {poor["budget"]["max_conversion_upper_bound"]:g}，'
                  f'平均残碳至少 {1-poor["budget"]["max_conversion_upper_bound"]:g}。', "",
                  f'实际 τ={p["tau"]:g}：平均残碳 **{p["carbon_mean"]:.9g}**，最大局部残碳 **{p["carbon_max"]:.9g}**，'
                  f'芯区 u={p["u_core"]:.9g}，外库 u_res={p["u_res"]:.9g}，'
                  f'瞬时 CO₂ 源率 ΓK∫fu dξ={p["co2_source_rate"]:.9g}。'
                  f'累计 CO₂ 生成={p["co2_generated"]:.9g}，体内 CO₂={p["co2_body"]:.9g}，'
                  f'封闭外库 CO₂={p["co2_reservoir"]:.9g}。'
                  '氧库存上界直接排除95%与99%阈值，两个时间均为 null，状态 oxygen_budget_limited。', "",
                  '“瞬时反应率近零就代表燃尽”这个假设不成立：本算例因缺氧而近停，但保留明显固体碳。'
                  '这里的 oxygen_budget_limited 只指这个假设模型的初始预算，不是现实材料物理不可能或产品不合格。', "",
                  "### 对照：持续供氧完成诊断阈值", "",
                  f'base 使用无限外库 u_ext=1、v_ext=0，但 Bi={rich["config"]["Bi"]:g} 的表面膜传递有限。'
                  f'实际平均95%完成 {event_label(rich,95)}，99%完成 {event_label(rich,99)}；'
                  f'τ={r["tau"]:g} 平均残碳={r["carbon_mean"]:.9g}，最大局部残碳={r["carbon_max"]:.9g}。'
                  f'最大局部残碳的99%完成时间为 {rich["t_local_burn99"]:.6g}。'
                  '这只是持续供氧与有限氧总量的机制对照，不是合格配方。', ""]
    lines += ["## 全部离散情景", "",
              "95%/99%是数值诊断阈值，非工厂燃尽或安全标准。所有时间是 τ，不转换成秒或窑内停留时间。"
              "下表同时显示平均与最大局部残碳；局部事件不由均值代替。", "",
              "| 情景 | K / Γ / Bi / 模式 / ρ | 终点平均 f | 终点最大局部 f | 平均95% | 平均99% | 局部99% τ |",
              "|---|---|---:|---:|---|---|---|"]
    for s in scenarios:
        c, f = s["config"], s["final"]
        local = f'{s["t_local_burn99"]:.6g}' if s["t_local_burn99"] is not None else s["t_local_burn99_status"]
        rho = "无" if c["reservoir_ratio"] is None else str(c["reservoir_ratio"])
        lines.append(f'| {s["scenario_id"]} | {c["K"]:g} / {c["Gamma"]:g} / {c["Bi"]:g} / {c["boundary_mode"]} / {rho} | '
                     f'{f["carbon_mean"]:.9g} | {f["carbon_max"]:.9g} | {event_label(s,95)} | {event_label(s,99)} | {local} |')
    with (out/"timeseries.csv").open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if "reaction_fast" in by_id:
        fast = [r for r in rows if r["scenario_id"] == "reaction_fast"]
        peak = max(fast, key=lambda r: float(r["u_surface"])-float(r["u_core"]))
        lines += ["", f'快反应的已采样最大表面—芯区氧差为 {float(peak["u_surface"])-float(peak["u_core"]):.9g}，'
                  f'位于 τ={float(peak["tau"]):g}；该梯度来自计算，不是预设氧贫化曲线。']
    lines += ["", "## 数学范围与离散方法", "",
              "- ξ=x/L∈[0,1] 为两面供气对称半板；固定几何、开孔率和同一常数气体 D。芯部无通量。"
              "D_eff 按总截面积定义，浓度按孔内体积定义，τ_D=ε_o L²/D_eff，τ=t/τ_D；不会重复计算 ε_o。",
              "- Γ=C_s0/(ε_o c_*)，K=kτ_D，Bi=h_m L/D_eff，ρ=V_res/(ε_o A L)。"
              "q=ΓKfu，u_τ=u_ξξ−q，v_τ=v_ξξ+q，f_τ=−q/Γ。"
              "C 是明确的可氧化碳库存，不是TG残渣、LOI或全部原污泥有机物。",
              "- cell-centred FV，Δξ=1/N；最后单元中心至物理表面为半格。膜与半格阻力串联："
              "g=1/(1/Bi+Δξ/2)，J=g(c_last−c_ext)，向外为正；表面值 c_s=c_last−JΔξ/2。",
              "- SSPRK2：y¹=Euler(y,h)，y_next=(y+Euler(y¹,h))/2。各 Euler 子步用共同反应增量与反向边界增量；"
              "h≤0.8/max(2N²+gN+ΓK,K,g/ρ)，sealed 的 g=0。凸组合保持非负性及线性守恒；"
              "发现负库存、非有限量或无法推进时间即失败，不 clip。",
              "- finite 外库真实积分 du_res/dτ=J_u/ρ、dv_res/dτ=J_v/ρ，无补气、无排放、无重置；支持反向交换。"
              "infinite 仅固定外部浓度，并非氧总量有限。sealed 没有虚构外库值。",
              "- 仅称 approximate_equimolar_transport；O₂/CO₂共用 D 与膜系数，保持 u+v=1，"
              "N₂为不参与反应的恒定背景。本增量不复现来源的完整多组分输运。",
              "- u_core 为首单元平均（中心 ξ=1/(2N)），不是精确 ξ=0 的点值；u_surface 为物理表面重建值。"
              "profiles.csv 每个采样时刻保存全部有限体积单元平均。事件用间隔0.1τ的导出采样点线性插值，"
              "原始包围区间最大宽度0.1τ，不宣称小数位等于物理精度。",
              "- t_gen 仅是按初始碳潜力计的CO₂源95%/99%完成，与 t_burn 对应，不代表全部原污泥气体。"
              "co2_net_out 是实际有符号边界积分；finite 的净排出只进入封闭外库，产气结束不等于排出结束。", "",
              "## 实际数值核验", "",
              f'独立审计固定容差1e-6：实际 {audit["scalar_checks"]} 项标量比较，'
              f'最大按初始库存/绝对尺度归一化误差 {audit["max_scaled_error"]:.6g}。'
              f'覆盖 {audit["timeseries_records"]} 条时间记录、{audit["profile_records"]} 条单元记录、'
              f'{audit["boundary_intervals"]} 个边界通量区间。', "",
              "审计从 profiles 的 Γf+v 与 u+v 重算C/O总量；从单独 boundary_flux.csv 累加带符号积分，"
              "并核对 timeseries、外库增量、化学计量上界、事件与 summary。"
              "不读取solver residual，不允许artifact改变容差。"
              "单条库存/通量篡改、移除通量行以及容差注入均在focused tests中应被拒绝。"
              "它不是大型hash框架或完整ODE重放，不能证明协同篡改多个文件后的动力学真实性。"]
    numeric = verification["numerics"]
    if numeric["status"] != "not_run_custom_configuration":
        lines += ["", "### 指定空间/时间收敛", "",
                  "空间比较7→15→31格；时间在15格上采用CFL步长倍率1→0.5→0.25。"
                  "同时比较全轨迹最大差、终点差、均值与最大局部的95%/99%事件。"
                  "事件均未发生标 not_comparable_not_reached，delta=null，不把缺失时间当0。", "",
                  "| 情景 | 15→31最大平均f差 | 最大芯区u差 | 时间0.5→0.25最大平均f差 | 数值门 |",
                  "|---|---:|---:|---:|---|"]
        for sid, value in numeric["convergence"].items():
            space = value["space_comparisons"][1]["max_trajectory_difference"]
            temporal = value["time_comparisons"][1]["max_trajectory_difference"]
            lines.append(f'| {sid} | {space["carbon_mean"]:.6g} | {space["u_core"]:.6g} | {temporal["carbon_mean"]:.6g} | {value["passed"]} |')
        lines += ["", "工程数值门（非材料误差条）：15→31格平均f≤0.005、最大局部f≤0.01、芯区u≤0.015、事件差≤0.05τ；"
                  "时间加密的三个轨迹差均≤1e-4、事件差≤0.005τ。轨迹差较前一级须缩小至0.7倍以下"
                  "（低于1e-10按舍入噪声处理）。门限为代码常量；与1e-6守恒审计及95/99%诊断阈值分离。", "",
                  "### 独立解析参照", "",
                  "无反应初态 u=0,v=1；Neumann芯部，分别使用Robin外表面及单独命名的Dirichlet极限。"
                  "以80项Fourier特征函数级数的单元积分平均对比FV输出；Robin根满足λtanλ=Bi，"
                  "Dirichlet根λ=(m+1/2)π。Dirichlet仅测试入口可用，不能写入正常配置。"]
        for boundary, values in numeric["diffusion"].items():
            errors = ", ".join(f'{r["n_cells"]}格={r["max_cell_average_error"]:.6g}' for r in values)
            lines.append(f'- {boundary}：τ=0.2 的最大单元平均误差 {errors}。')
        errors = ", ".join(f'Γ={r["Gamma"]:g}: {r["max_carbon_error"]:.6g}' for r in numeric["closed_reaction"]["cases"])
        lines += [f'- sealed 均匀反应对独立可分离变量解：全时间最大平均f误差 {errors}；包含充分氧、等计量与缺氧。',
                  '- 量纲指数及 C/O/名义质量（12+32=44）单独代数验证；没有额外失重源或假能量守恒通过。']
    lines += ["", "## 未建模与下一增量证据", "",
              "t_close、开闭孔/收缩、压力、温度场与能量守恒、水分/脱羟/热解、CO及其他挥发物、"
              "强度/黑心分类/排放合规、配方优化、窑速均为 not_modelled，不输出零值伪装预测。", "",
              "全部12默认参数为标注的无量纲机制情景。文献候选CSV仅只读参考："
              "reported不等于本征常数；S09的K0与非整数氧阶单位问题、S02氧拟合温区上限及跨材料迁移"
              "没有被这次运行解决。没有把source K0或跨温区D接成默认值。", "",
              "下一增量至少需要：同一种泥/基料、同批空气或明确O₂气氛的多速率TG、定量逐物种气体与残碳；"
              "配对的尺寸/开孔连通率/热态输运演化；若加入热模型，还需要同材料热物性、反应焓和芯表温度。"
              "机械性能与环境合规需要独立成品测试，不能由本次残碳直接推断。"
              "这些只是证据需求，本卡未实施非等温、多步反应或开闭孔模型。", "",
              "## 复验与数据位置", "",
              "同目录 summary.json、timeseries.csv、profiles.csv、boundary_flux.csv、audit.json、verification.json "
              "为本批原始输出和验证记录；两张SVG直接读取这些导出。脚本、12输入、冻结合同快照及focused tests "
              "与本报告一同进入独立研究worktree本地commit，不依赖2A已清理scratch脚本。复跑命令见上级 README.md。", "",
              "资源实测及完整验证误差见 verification.json；单worker/单线程，目标180秒与512MiB。"
              "超限明确partial/timeout，不以模型不确定性掩盖数值失败。", "",
              "## 来源与采用边界", "",
              "唯一实施规范：上级 STAGE2B1_FROZEN_CONTRACT.md（Manager冻结快照）。"
              "以下公开来源仅用于保留合同所述机制与参数迁移边界，本次不重新提取文献或校准它们：", "",
              "- S02：https://www.mdpi.com/1996-1944/14/17/4942",
              "- S09：https://www.mdpi.com/1996-1073/17/21/5382/htm",
              "- S11：https://orbit.dtu.dk/files/418782101/1-s2.0-S2214509525011854-main.pdf", ""]
    (out/"DIAGNOSTIC_REPORT.md").write_text("\n".join(lines),encoding="utf-8")
