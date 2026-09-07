# 物理沙盒 Goal 进度

更新时间：2026-09-07 UTC。完整任务合同：[GOAL_BRICK_PHYSICS_SANDBOX.md](../GOAL_BRICK_PHYSICS_SANDBOX.md)。

## 当前状态

- Goal：active；持续实现中，本回合已修补数值缺陷并完成阶段提交，属于 progress。
- software_status：implementation_in_progress。
- scientific_status：partial_sources_no_complete_raw_sludge_domain；完整原污泥材料域尚未成立。
- deployment_status：offline_research_only。
- 当前阶段：G0 历史B2故障已修复；G1 基础模块已提交；G2 守恒积分、配平反应、刚性气热、独立账本、纯水适配器已通过有界验证与独立复审；完整湿砖全周期未实现。
- 基线：`4b4f2d3`；分支：`codex/physics-sandbox-v1`。
- 开始时已有未跟踪文件仅 `docs/GOAL_BRICK_PHYSICS_SANDBOX.md`，为本 Goal 合同，保留并纳入本任务。
- 当前工作目录 `/Users/wanggaoying/Desktop/brickmodel-github`；未修改 Hermes、同步任务或远程仓库。

## 已核对

- 适用父目录及仓库无 AGENTS.md；Git 历史与既有研究记录已读取。
- 已读取完整任务合同、模型架构/公式/参数与研究状态、B1 冻结合同、B2 推导/失败范围。
- 早期 VME 的固定有效热容能量恒等式、累计供氧上界、synthetic 黏度/收缩/性能关系不能直接承担新模型的材料结论。
- 当前机器 macOS arm64；系统 Python 3.14.2，使用 Python 3.12.13 的隔离 `.venv`。锁定 numpy/scipy/pytest/Pillow 已安装。使用 `UV_CACHE_DIR=/private/tmp/brick-sandbox-uv-cache`。

## 本轮已实现与验证

- 本地阶段提交 `0634e80b1fa4d69c195022f1c7ecd79a16110fe2`：B2 暴露量积分曲率步长界、真实失败审计、Darwin RSS换算与回归；没有改原1e-6门槛。
- 实际提交绑定 `run_tests.py`：14单元测试，全部8类NUM门槛通过，34次focused积分；77.61s、41.52MiB。实际default 22情景完成，绑定bound；15.92s、94.63MiB。独立audit 322204 checks通过，最大暴露误差6.9171e-8。
- 完整原始源码/输入/结果/验证打包在 `research/b2-bound-0634e80/reproduction.tar.gz`（565成员），摘要和命令在同目录 `summary.json`。这是实际绑定验证和离线包，未宣称对离线包做了全部重新积分。旧失败原样保留。
- `sludge_sandbox` 新包：证据DAG/分类/域/未知阻断、单位、干湿料账目与独立分析类别、相容半板几何；所有制造值仅是测试。
- NIST四气体10段80个Shomate系数核读与移录；真实表点/导数/能量反解测试。原始接缝保留，能量间隙、多解及浮点精度不足会拒绝；没有低温水汽/液水/固体补值。
- 实际集成基础测试：`PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_evidence.py tests/sandbox/test_units.py tests/sandbox/test_materials.py tests/sandbox/test_geometry.py tests/sandbox/test_thermochemistry.py -q --junitxml=docs/sandbox/research/g1-core-tests.xml`，122 passed。
- 公开研究：7篇候选资料、Wang 12条件186图中实验符号派生读数、Mohajerani24终态值、Nowicki9拟合率等。条件冲突/基准争议均隔离；没有拼成完整原污泥材料包。
- 气体中心修正曾从零物种格移出物质，已添加先失败回归并改为correction drift成分上风，79测试与独立150场景/450方向复查通过；不能靠无限减步长补救。物质焓接口有10项实际测试，net与diff/adv分项必须一致。
- 干净非editable冻结离线安装已实际验证：从/private/tmp运行，未用PYTHONPATH，site-packages真实导入；最终211 sandbox测试通过。报告 `VALIDATION_REPORT.md`，原始XML `research/g1-installed-final-tests.xml`。仍未完成全流程CLI/UI安装验收。
- `WORLD_SPEC`、`EVIDENCE_POLICY`、`VALIDATION_PLAN`、`SUPPORTED_DOMAIN`、`KNOWN_GAPS`、方程映射已建立并明确已实现/未实现。

平台细节：本地工具回合会使 `.venv` 文件隐藏，Python3.12跳过隐藏 `.pth`，editable导入不稳定。开发显式 `PYTHONPATH=src`；最终必须另测干净非editable安装，不能靠该路径声明安装验收。外部`/usr/bin/time -l`曾因sandbox kern.clockrate/sysctl被拒绝，内部RSS/耗时单独报告，未反复重跑掩盖该问题。

## G2 已完成的有界能力

| 本地提交 | 实现与验证 |
|---|---|
| `e3dda49` | 配平反应、库存分辨率守卫；49测试、独立复审通过 |
| `a18310b` | 13份IAPWS原始/派生资产；33个官方数值独立重算 |
| `e259c29` | 守恒积分器28测试、刚性气热26测试；实际stage时刻、累计舍入、正性/取消/超时与独立审核 |
| `8bb92ca` | 独立精确加权审计37测试；系统/单元分步和前缀，保留权重舍入与局部漂移反例 |
| `2842691` | 来源门禁IAPWS适配器78测试；Cp/Cv导数和SI有限性修补，独立66状态复验 |
| `f2f2f31` | 刚性气相导热7个实际收敛案例；空间阶1.967/1.992、时间阶2.012/2.006；独立解析审核 |

水适配器使用IAPWS原生R与同相统一参考偏移；未与混合载气/高温Shomate拼接。审计器检查存储U账本，不冒充多相热物性重建。收敛案例为明确制造解，不是现实砖试验。

收敛脚本提交前 `git diff --cached --check` 曾报告文件末尾多一空行，编排未在该非零结果后停止提交。保留这项格式检查失败记录；不把它称为通过，也未改变绑定数值产物的源码字节。独立数值审核与源hash验证通过。

## 完整安装复验与来源增量

从 `/private/tmp` 在 `/private/tmp/brick-sandbox-g2-install-20260907` 运行冻结、非editable、离线安装；无PYTHONPATH。最后实际429测试通过（16.01s，0失败/跳过），13个实际site-packages模块源码hash与工作区一致。证据：`research/g2-installed-final-tests.xml`、`research/g2-installed-final-identity.json`。较早排除审计/水模块的314测试与11模块hash快照作为历史证据保留，不能混作最终版本。

Baloi2025出版商HTML/JATS原文、5组配比/终态热物性及派生提取已独立审核通过；4份清单资产逐一核验bytes/hash。详见 `research/BALOI2025_COVERAGE.md`、`research/CODE_REVIEW_BALOI2025.md`。体积配比没有擅自转质量；烧后低温有效cp没有冒充湿坯/高温热容。

独立代理的早期额度错误已终止；实际账户限额重新读取后可继续，未使用重置信用。恢复后的水、收敛和Baloi审核均完成。审核是代码/数值独立核查，不是外部科学专家认证。

## 当前关键缺项

1. 同一原污泥材料域的成套组成、产物、参考能、湿热/烧结/力学关系及独立实验覆盖尚未闭合。
2. 纯水与载气、固体的统一储能及热湿耦合尚未实现；纯水EOS不是泥中吸附/毛细本构。
3. 烧结、闭孔/渗透演变、几何反馈和冷却应力尚未实现。
4. 全周期CLI/界面、可恢复批量运行、多代搜索与公开实验预测对照尚未完成。

## 当前增量检查点

- `34dbfe1`：Baloi成对来源与提取独立审核后本地提交。
- `a0f5697`：保存429测试安装证据、广延mol/J世界定义和当时支持域。
- `622d376`：连续边界程序41测试及独立审核，真实积分节点/解析能量检查通过。
- `7d3aaca`：显式理想水汽转换28测试，独立2071温点审核，保留h和生成能参考，固定R的u/Cv差及来源公开。
- 新增后完整冻结非editable离线重装：498 passed in1.99s，15安装模块hash与工作区一致；证据 `research/g2-installed-boundary-vapor-tests.xml`、`research/g2-installed-boundary-vapor-identity.json`。未修改已绑定G1/G2原源码来刷新旧报告。

## 下一步与所有权

全部当前有界子任务已完成，暂无运行中的子代理或待审批代码。主代理继续推进以下实际任务：

1. 按 `MULTIPHASE_STORAGE_DESIGN.md` 实现显式固/液/气储能接口与固定相库存的温度反演；零库存相不强加物性温域，不用sum Cv冒充含压力闭合的dU/dT。
2. 将已完成边界程序通过正确的对流/辐射和动态完整气体库组装到当前核；不能把炉气温度当材料表面Dirichlet温度。
3. 显式处理液体压力/气孔体积机械闭合，再建设有依据的相平衡/传质；纯水饱和压力不能自动代替含载气化学势条件。
4. 扩展有来源的连续Cp积分气体热量模型并保留原Shomate接缝偏移；继续同域固体/原泥材料资料和公开实验留出验证。
先完成无需猜测材料值的边界和统一储能，再逐项接有证据热湿机制；继续原泥材料来源与公开验证。缺证项保持未完成，不把广延库存换算、来源hash或制造解当作真实材料资格。

尚未满足合同第11节的完整实现条件，Goal保持active。
