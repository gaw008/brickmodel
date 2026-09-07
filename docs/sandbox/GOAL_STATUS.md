# 物理沙盒 Goal 进度

更新时间：2026-09-07 UTC。完整任务合同：[GOAL_BRICK_PHYSICS_SANDBOX.md](../GOAL_BRICK_PHYSICS_SANDBOX.md)。

## 当前状态

- Goal：active；首个实现回合，已取得工作区和模型证据，属于 progress。
- software_status：implementation_in_progress。
- scientific_status：partial_sources_no_complete_raw_sludge_domain；完整原污泥材料域尚未成立。
- deployment_status：offline_research_only。
- 当前阶段：G0 的历史B2故障已定位/修复并提交验证；G1 基础模块已实现；G2 面交换开始，完整时间积分器未实现。
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

## 分工与所有权

| 子任务 | 所有权 | 工作 |
|---|---|---|
| 主代理 | 新 sandbox 包/测试、进度/验收/政策及集成 | 来源图、缺项阻断、材料接口、全局验收 |
| source_evidence | 已完成研究提取；当前gas_transport及tests、transport缓存/报告 | 气体保正通量修复与来源说明 |
| b2_repair | 已完成B2；thermochemistry包/测试/数据/来源报告 | NIST移录、反解精度与溢出修复已完成 |
| physics_architecture | ARCHITECTURE_PROPOSAL；PHYSICS_REVIEW_GAS_TRANSPORT | 气体独立物理/数值审查 |
| code_review_g1_b2 | CODE_REVIEW_* 报告 | evidence/geometry/B2、digitize、材料、thermo已复审；exchanges审查 |

来源代理不写 `B2_ROOT_CAUSE.md`。工作共享同一分支，由主代理统一提交。

## 当前关键缺项

1. 原污泥全周期的成套、适用参数及独立验证覆盖尚待证据核查。
2. 完整能量、热湿迁移、局部氧/载气、压力驱动输运和孔隙/几何反馈尚未实现。
3. B2 历史失败修复只覆盖原synthetic域；不作新模型完整验收。
4. CLI/界面、多代搜索与耦合公开实验验证尚未完成。

## 下一步

1. G1基础模块、来源缓存和复查记录已准备本地阶段提交；本阶段提交可用 `git log -1 -- src/sludge_sandbox` 查询。新实现和证据仍按完整合同继续。
2. 在manufactured模式实现元素配平反应、统一多相储能、有限体积时间积分与同步账本；先封闭反应/两格气体交换与热传导解析验证。
3. 同步补水物性、反应产物与动态收缩的实际来源资格，不依赖它们的求解器/应用开发继续。不可把纯气体热化学包改称湿砖包。

尚未满足合同第 11 节任何“完整实现”结论，不标记 Goal 完成。
