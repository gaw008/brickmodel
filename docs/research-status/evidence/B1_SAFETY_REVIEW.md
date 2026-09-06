# PASS — 仅批准 research_diagnostic_scope

任务：t_c787a990。独立 Safety 审核，不是实现者自我批准。
待审提交：d051c0982835dbe54fc4f509f1819661b85de055。
基线：2620afe40faaf592fbb42b39e3a6a6a351009ad8。

结论：冻结 B1 等温、固定几何、C(s)+O₂→CO₂、共同常数 D/Bi 的无量纲 1D 研究诊断通过。没有阻断该冻结研究范围的修复项。不批准生产、工厂参数/秒数/配方、黑心或强度分类、排放合规、真实原污泥动力学校准，也不自动批准 B2。

## 1. 门控、合同和独立性

- 实际读取本卡、两个父卡、完整评论与历史摘要、附件清单；父实现 t_2c9cc3d9 为 done。Stage1 父卡 t_c6aa7e5f 为 done，且最新完成记录明确 `PASS / approved_for_research_stage1 / approved=true`。没有把 done 单独当批准，也没有重复认证或修改依赖图。
- 完整读取 Manager 的 STAGE2B1_FROZEN_CONTRACT.md；与提交内快照逐字节一致。SHA256：9d04fb234f2228381fe20f5c248161c58595f000e451986f68c2b2944a26bffd。
- Git diff 相对基线只有 48 个新增文件，全部位于 experiments/material_dynamics_v2b1/。冷读 16 个 Python 文件，包括求解、审计、诊断、导出、图表、报告及全部 focused tests。未修改实现、输入或已提交产物。
- 复现包 SHA256 为 4d7875d30e634e325cdeb2536b966470fb8540eb292dc6630aa1bfcfe31a0d8c。检查无绝对路径、越界、链接或特殊文件后，在 /tmp/t_c787a990-review/copy 解压；48 个普通文件均与 Git blob 完全一致。
- 工作树三份 CSV 是 CRLF，而 Git/archive 为 LF；已独立证明仅行尾差异，不是数据差异。原文件字节哈希在审核末尾重新核对。
- 2A 四个持久附件 SHA256 与上游记录一致；抽读 K0 非整数氧阶单位、O₂ 拟合温区、跨材料迁移边界。12 个 JSON 参数由冻结表逐项独立重建并核对，没有把文献候选当已标定本征常数。本次没有重新校准或全量复核 2A 文献原始试验。

## 2. 冷读物理与离散合同

证据路径均相对 experiments/material_dynamics_v2b1/：

- README.md:55–64、diagnostics.py:23–32、solver.py:65–86：由 ε c_t = D_eff c_xx − k C_s u 代入 τ_D=εL²/D_eff，得到扩散系数 1、反应系数 ΓK；固体方程为 −Kfu。ρ=V_res/(εAL) 导出外库系数 1/ρ，没有重复 ε。审核员另以任意代数测试量独立检验系数相等，未输出工厂物理时间映射。
- solver.py:35–50、65–86：半格与膜阻力串联，g=1/(1/Bi+Δξ/2)，向外通量 J=g(c_last−c_ext)；体内为 −J/Δξ，finite 外库为 +J/ρ。独立非均匀状态一步检验同时覆盖 O₂ 向内、向外交换与 CO₂ 相反交换，最大误差低于 2e−17。
- solver.py:91–163：SSPRK2 使用两个保正 Euler 子步的凸平均；反应、气体库存、外库和通量账本采用相同增量及权重；CFL 含扩散/反应/外库损失约束。源码没有库存 clip；发现负/非有限库存即失败。finite 外库只初始化一次、随后真实积分；sealed 无外库；infinite 固定外部浓度且没有有限总氧声明。
- diagnostics.py:35–101、audit.py:182–222：碳均值和最大局部残余分开；95/99%事件由库存阈值触发而非瞬时速率，未发生保持 null。首单元平均不冒充精确中心点，表面值由 Robin 半格重建；事件精度明确受 0.1τ 采样包围限制。
- diagnostics.py:4–22、报告:42–85：共同 D/Bi 明确限制为 approximate_equimolar_transport；t_close、压力、温度场、能量、孔关闭、强度及生产变量均 not_modelled。没有能量闭合或完整原污泥模型声明。

## 3. 实际命令与结果

所有计算串行、离线，在独立临时副本执行；未运行旧 full suite，未安装依赖。

1. `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/t_c787a990-review/copy/experiments/material_dynamics_v2b1/run_tests.py`
   - exit 0；14 tests，0 failures/errors/skips；unittest 计时 64.513 秒。真实日志与 test_results.json 已保存。
2. `/usr/bin/time -v -o /tmp/t_c787a990-review/replay_resource.log python3 -B /tmp/t_c787a990-review/copy/experiments/material_dynamics_v2b1/run.py --out /tmp/t_c787a990-review/copy/experiments/material_dynamics_v2b1/safety_replay`
   - exit 0；12 情景全部 integrated，整体 passed。内部 34.947415 秒；外部 wall 35.04 秒；RSS 42276 KiB（41.285156 MiB）；1 worker/1 thread。
   - 实际运行 base/reaction_fast/finite_small 的 7/15/31 格、时间步倍率 1/0.5/0.25、Robin/Dirichlet 扩散与 sealed 解析验证。
3. `python3 -B /tmp/t_c787a990-review/copy/experiments/material_dynamics_v2b1/audit.py /tmp/t_c787a990-review/copy/experiments/material_dynamics_v2b1/safety_replay`
   - exit 0；107116 比较，固定 tolerance=1e−6，最大归一化误差 1.0658141e−14。
4. `python3 -B /tmp/t_c787a990-review/independent_exports.py`
   - exit 0；审核员独立 119238 项数值比较，含库存、事件和 SVG 坐标检查。该脚本不导入 solver/diagnostics/audit/verification。
   - 全量核对 2412 条 timeseries、36180 条 profiles、2400 条边界区间；逐时刻重建碳元素、氧原子、名义质量、耗氧/产 CO₂、外库转移及预算上界。库存相关最大归一化差约 1.06e−14；图形单独按坐标舍入容差检查。
   - 8 个确定性产物内容一致（CSV 行尾归一化），verification.json 的完整 numerics 字段一致；时间戳/资源实测不要求逐字节相同。
5. `python3 -B /tmp/t_c787a990-review/independent_numerics.py`
   - exit 0；审核员自行推导 Robin 根的另一等价形式及级数系数，没有导入实现的 verification.py。
   - Bi=0.1/1/10 × N=7/15/31，共 9 组 Robin 解析对照均随网格缩小误差；31 格最大误差分别 5.60662e−6、7.48652e−5、1.98235e−4。
   - Γ=0.25/1/2/8 共 4 组 sealed 解析对照，最大 f 误差均低于 2e−6；包含充分氧、等计量与缺氧。
   - 另外独立重跑三个冻结收敛情景，直接从状态重算均值、最大局部值、芯区和事件；保存 3015 条加密轨迹记录，不将双 null 事件当零误差。全部满足原代码固定数值门。
6. `python3 -B /tmp/t_c787a990-review/adversarial_checks.py`
   - exit 0；14 种审计篡改都获得预期 exit 1 / export_audit_rejected / tolerance=1e−6：单条剖面残碳、时间序列库存、有限库库存、边界积分、删除区间、负库存、NaN、缺失事件伪装0、假局部完成、假压力、假能量闭合、顶层容差、配置容差、嵌套大容差叠加库存篡改。
   - 不提供 audit.json/verification.json 的正常对照仍通过，证明不是依靠已报告 residual/pass 字段。
   - 5 条 CLI 安全/失败路径：拒绝覆盖已有输出且哈希不变、拒绝目录外输出、拒绝符号链接逃逸、非法配置固定错误信息不回显测试内容、超时明确 partial/timeout 且 exit 3。
7. `git diff --check 2620afe40faaf592fbb42b39e3a6a6a351009ad8 HEAD`
   - exit 0；最终 Git/字节完整性结果见 final_integrity.json。

## 4. 实际机制结论

这些都是无量纲假设情景，不是生产建议。

- finite_small：Γ=2，ρ=0.25，初始氧预算 1.25；最大转化上界 0.625，平均残碳下界 37.5%。τ=20 独立重算平均残碳 37.50026368%，最大局部残碳 38.93442961%，源率约 3.01654e−6；95%/99%均 null / oxygen_budget_limited。正确区分“缺氧近停”与“燃尽”。
- sealed：平均残碳约 50.00000005%，满足最大转化 0.5 的计量上界；未误报燃尽。
- base：平均95%阈值 τ=5.24990544，99%阈值 τ=7.15921140；局部99%阈值 τ=7.46309435。仅表明持续供氧的对照结果。
- film_weak：平均残碳 0.85489706%，最大局部残碳 1.06558952%。平均99%已达，但局部99%未达；没有用均值掩盖局部残碳。
- finite_medium：氧预算允许完全转化，但到 τ=20 平均残碳仍 5.35391167%；not_reached_by_horizon 与氧预算不足区分正确。
- no_reaction：u=1、v=0、f=1 精确不变；没有伪造完成时间。
- 两张 SVG 全部 16 条曲线/3216 对坐标、24 个柱形均与真实 CSV 数值相符；中文免责声明存在，无 script、foreignObject、外链、外部资源或事件处理属性。未做 GUI/CJK 字体像素级检查。

## 5. 安全必查与权限

- Secrets/PII：12 输入为机制数字和受限标识，不包含人员记录。48 个新增文本文件凭据模式扫描无命中，16 个 Python AST 解析通过；没有读取 .env、OAuth 文件或实际凭据。扫描是有界检查，不是对整个主机无泄漏的保证。
- 认证/授权：离线 CLI 无登录或远程服务；没有改变订阅、模型、权限或审核门控。
- 输入/注入/路径：严格配置拒绝缺失、重复、未知、非有限和非法边界字段；无 eval/exec/shell=True。路径/软链接逃逸及既有输出防覆盖已真实测试。这里只批准受控本地 CLI，不批准多用户不可信上传服务。
- 文件副作用：CLI 默认不覆盖已有产物；run_tests.py 会重写所在副本 validation 日志，所以仅在临时副本运行。审核员未修改原实现。未执行用户数据删除或回滚；测试库仅清理自己创建的临时 fixture。
- 网络/依赖/费用：新增 imports 仅 stdlib 和本目录模块，无网络 SDK、设备接口、收费 API 或新依赖。没有新建/升配 OCI、切 Anthropic、发送外部消息、公开发布、push、merge、部署、设备/训练/金融控制。
- 既有系统：B1 diff 未触及核心 solver/verifier、Stage1 或 Hermes/Cloudflare/WhatsApp 配置；没有启动/停止现有服务。没有做全主机生产服务审计。
- 主仓库 master 与 Stage1 分支仍分别是 eef479c、2620afe。Stage1 独立工作树路径在本次检查时已不存在，实际 git worktree list 也不列出它；不虚称该目录当前仍 clean。Stage1 内容由本树中的基线和未移动分支核对，完整 Stage1 科学审核依其明确上游结论，本卡不重做。
- 回滚：没有部署或服务修改需要回滚。可停止使用该孤立实验；若未来决定撤销代码，由 Manager 审核后 revert 新增提交，不执行 reset --hard 或历史改写。本次没有实际回滚。

## 6. 非阻断记录、未覆盖与残余风险

当前冻结范围没有 required changes。以下不扩展本次批准：

1. LOW，缩短预算的失败遥测显示的是全局上限。
   - Evidence：run.py:27–31、116–130；`--budget-seconds 0.000001` 实际正确在 simulation 阶段返回 partial/timeout/exit3，但 failure.resources.wall_budget_seconds=180.0；只有正常结束分支回写实际 args 值（run.py:111）。
   - Required fix：当前默认180秒冻结演示不要求返工；若将该字段用于自定义预算运营监控，须区分 active_budget_seconds 与 ceiling，或在失败路径记录实际 args 值。本记录不是认可其为有效预算的精确遥测。
   - Retest：缩短预算后触发超时，断言非零退出、partial/timeout，同时输出实际预算；默认180秒成功路径继续通过。
2. 真实材料适用性未验证：没有原污泥本征动力学、多组分气体、热效应、孔关闭、压力、强度、排放、实际厂内时间/配比验证。数值守恒/收敛不等于科学校准。
3. 审计只重建导出库存/积分通量及诊断；不是完整 ODE replay，不能保证识别协同重写所有原始轨迹和通量。不可拿本报告为不可信上传文件提供真实性认证。
4. 数值批准以固定12情景及明确额外测试域为证据；自定义 CLI 的 `audit_only` 不能继承全部默认收敛结论。未穷举所有极端浮点参数或不可信并发文件系统。
5. SVG 已做结构、数据与静态内容审查，未做 GUI/CJK 像素可读性检查。2A 文献不在本次重新提取或材料标定范围。
6. 原实现中 safety_review=pending_independent_child 为提交时状态；审核员没有改写历史产物。这份报告及本卡最终 handoff 才是当前独立审核结论。

## 7. 审核过程中的诚实记录

- 初次 reviewer preflight 用工作树字节哈希直接比较 archive CSV 失败；随后核读限定 .gitattributes 和 validation/README.md，确认 CRLF/LF 规范化，并逐一核对 Git blob 与仅行尾差异。只修改 reviewer 脚本，没有改实现或放宽数据比较。
- 组合 Git 状态检查最后一步因 Stage1 工作树路径不存在返回 exit128；随后单独读取真实 worktree list 和保留分支/commit，按可验证状态记录。没有重建或删除工作树。
- 未伪造命令输出、图形数据、材料参数或文献原始数据。

证据包包含 reviewer 脚本、原提交复现包、fresh 原始产物、focused test 日志、资源日志、独立数值/库存/图表证据与各攻击的真实返回。后续模块仍须 Manager/Planner 冻结新合同，再由 Engineer 实现并独立 Safety 审核。
