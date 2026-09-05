# 材料设计 v2 B1：1D有限供氧诊断（离线研究）

这是等温、固定几何的 C(s)+O₂→CO₂ 无量纲反应—输运诊断器，不是完整原污泥模型，不给工厂配方、秒数、强度、窑速或生产控制。95%/99%是数值诊断阈值，非生产合格标准。独立 Safety 审核未由实现者自我批准。

唯一实施规范为本目录 STAGE2B1_FROZEN_CONTRACT.md 的冻结快照。只在本目录新增文件，没有修改/导入既有 solver、verifier 或 Stage1 分析代码。

## 直接复跑

依赖：Linux、Python 3.12+ 标准库。无需 pip、NumPy、SciPy、pytest、uv、浏览器、网络、凭据或模型 API。本机系统 Python 没有 pytest，因此使用 stdlib unittest；不修改 Hermes 共享 venv。

从独立worktree根运行（解压复现包后，在包含 experiments 的目录运行）：

```sh
python3 experiments/material_dynamics_v2b1/run.py --out experiments/material_dynamics_v2b1/replay
python3 experiments/material_dynamics_v2b1/audit.py experiments/material_dynamics_v2b1/replay
python3 experiments/material_dynamics_v2b1/run_tests.py
```

检查已保存的默认演示及两张SVG数值映射：`python3 experiments/material_dynamics_v2b1/inspect_results.py`。
该只读检查逐点核对轨迹坐标、逐条核对12情景柱形宽度，并从真实summary计算百分数，不重新生成模型数据。

- 默认一次实际积分全部12个冻结情景，并运行指定3情景7/15/31格与CFL倍率1/0.5/0.25检查、Robin与Dirichlet解析扩散、密闭反应解析参照、C/O量纲/计量检查。
- 输出目录必须位于本独立实验目录内，且尚不存在；已有输出绝不覆盖。再次复跑请改名 `replay2` 等，不删除已有证据。`replay*/`仅用于本地复验且不入git。
- `run_tests.py` 仅发现本目录 `test_*.py`，不会跑旧 full suite；实际测试日志写入 validation/focused_tests.log、validation/test_results.json。也可直接运行 `python3 -m unittest discover -s experiments/material_dynamics_v2b1 -p 'test_*.py' -v`。
- 仅检查一个严格配置：`python3 experiments/material_dynamics_v2b1/run.py --config experiments/material_dynamics_v2b1/inputs/finite_small.json --out experiments/material_dynamics_v2b1/replay_single`。单配置执行积分/库存审计与图表，numerics 标记 `not_run_custom_configuration`，不冒充完整12情景收敛验证。
- `--budget-seconds` 只能收紧180秒预算。1worker/1线程；进程自身限制地址空间≤512MiB，实测峰值RSS与耗时写入 verification.json。时间/步数/输出数超预算为partial/timeout（退出3），数值失败退出2，验证门不通过退出1，完整成功退出0。配置/路径失败使用固定消息，不回显任意输入内容。

## 冻结配置与情景

每份 inputs/*.json 严格包含：schema_version=1、scope=dimensionless_reaction_transport_benchmark、scenario_id、K、Gamma、Bi、boundary_mode、reservoir_ratio、n_cells、tau_end、diagnostic_thresholds=[0.95,0.99]。

拒绝缺失/未知/重复字段、负值、NaN/Inf、错误类型、非法模式和不一致外库。finite 必须正ρ；infinite/sealed 的 reservoir_ratio 必须null。实现另作有界资源约束：2≤n_cells≤127、预估≤1,000,000步、≤5,000输出区间；超出不伪装物理不可行。默认采样间隔0.1τ。不得由配置扩大固定1e-6审计容差。

共同 K=1、Γ=2、Bi=1、infinite、N=15、τ_end=20，只覆盖下列变化：

| scenario_id | 覆盖 |
|---|---|
| base | 无 |
| reaction_slow | K=0.1 |
| reaction_fast | K=10 |
| carbon_low | Γ=0.25 |
| carbon_high | Γ=8 |
| film_weak | Bi=0.1 |
| film_strong | Bi=10 |
| sealed | sealed |
| finite_small | finite, ρ=0.25 |
| finite_medium | finite, ρ=1 |
| finite_large | finite, ρ=10 |
| no_reaction | K=0 |

这些全部是数值机制情景，不是实测或文献拟合参数。2A候选表未自动进入输入，没有把 reported K0 解释成本征速率常数或拼接不同材料/温区的 D。

## 方程与数值保证

ξ=x/L∈[0,1] 为对称半板，D_eff 按总截面积定义，c 按孔内体积定义。

- τ_D=ε_o L²/D_eff；τ=t/τ_D。Γ=C_s0/(ε_o c_*)，K=kτ_D，Bi=h_m L/D_eff，ρ=V_res/(ε_o A L)。
- q=ΓKfu；u_τ=u_ξξ−q；v_τ=v_ξξ+q；f_τ=−q/Γ。每一份碳消耗/O₂消耗/CO₂生成使用同一摩尔增量，没有独立失重源。
- 芯面通量为零。表面向外为正，J_i=Bi(c_s−c_ext)。cell-centred FV 对最后半格与膜阻力串联：g=1/(1/Bi+Δξ/2)，J=g(c_last−c_ext)，c_s=c_last−JΔξ/2。Bi=0取g=0。
- infinite固定外部 u=1、v=0，但膜传递有限；finite真实积分外库并等量反向转移，不补气/排放/重置；sealed无交换/外库。
- SSPRK2为两个Forward Euler子步的凸组合，更新反应和边界库存时使用相同积分权重。h≤0.8/max(2N²+gN+ΓK,K,g/ρ)（sealed g=0；非finite没有g/ρ），保证本初值域下Euler子步非负。无clip、无负库存归零；检测到负/非有限状态直接失败。
- 两气体共同常数D与Bi，仅称 approximate_equimolar_transport。本域u+v=1；finite的u_res+v_res=1。等温由外部恒温约束，不声称能量闭合。

边界积分在 boundary_flux.csv 保存每两个采样时刻之间的实际 SSPRK2 有符号积分，不使用稀疏采样的端点梯形近似替代内部积分。

## 文件与审计

- model.py：严格配置；solver.py：独立FV/SSPRK2。
- diagnostics.py：平均/最大局部碳、库存、95/99%事件、明确的not_modelled。
- export.py：summary.json、timeseries.csv、profiles.csv、boundary_flux.csv。
- audit.py：仅重读上述导出与Config校验，不import solver/diagnostics，不相信solver residual。
- verification.py：独立Fourier扩散与密闭解析参照，以及有限的空间/时间收敛。数值门见源文件常量及诊断报告，不由artifact控制。
- plots.py、reporting.py：从导出生成两张中文浅色SVG和 DIAGNOSTIC_REPORT.md。
- run.py：有界单线程离线运行入口；run_tests.py：持久测试日志入口。
- artifacts/：已实际运行的一套默认12情景原始轨迹与报告；validation/：命令输出、资源实测及测试日志。

CSV固定列详见冻结合同；额外边界通量文件是独立审计所需的最小支持文件。profiles保存每个采样时刻的全部单元平均，xi为单元中心。u_core是第一个单元平均而不是ξ=0精确点值；u_surface为Robin半格重建的真实表面值。不存在外库的CSV值留空/JSON用null，不伪造0。

审计从剖面重算 C_body=∫(Γf+v)dξ、O_body=∫(u+v)dξ；finite加外库ρv_res和ρ(u_res+v_res)，infinite用实际净边界积分闭合。审计同时重算固体碳损失、耗氧、CO₂生成/净排出、外库每区间转移、计量上界、采样完整性和缺失事件。容差固定为1e-6，按非零初始库存/绝对尺度归一化。单条库存/通量修改、通量行删除、NaN、假局部完成标志、把缺失事件改成0及容差注入均有回归测试。

审计不是大型hash/完整ODE语义重放，不保证识别联合重写全部库存与通量的攻击。独立解析/半解析参照负责检验离散算法；两者均不等于真实材料标定。

## 事件、科学限制与下一步

事件按导出0.1τ采样点首次跨越碳阈值线性插值，时间包围区间最大宽度0.1τ，不能把许多小数位当物理精度。t_burn95/t_burn99由平均剩余碳触发；t_local_burn95/t_local_burn99由最大局部剩余碳触发，速率下降不触发任何燃尽事件。未达到是null及明确状态；收敛比较中双null为not_comparable_not_reached，不当0计算误差。

t_gen只表示本模型CO₂源按初始碳潜力完成95/99%，不是原污泥所有气体。净排出另以实际有符号积分记录；finite只传入封闭外库，不是环境排放。finite平均转化≤min(1,(1+ρ)/Γ)，sealed≤min(1,1/Γ)。

不建模t_close/开闭孔/收缩、压力、温度场与能量、自由水/脱羟/热解、CO/其他挥发物、强度、黑心分类、合规、配方、窑速。来源与后续所需联合证据见报告。既无生产部署/设备连接，也无公开发布、push、merge、OCI/付费API或模型训练。

回滚：本地提交仅新增本实验目录；未改核心/Stage1及任何服务。需要撤销时，由Manager审核后revert该独立新增提交或停止使用该实验，不改写历史、不执行reset --hard。复现包为git archive导出的已提交本目录，不依赖任务scratch存活。
