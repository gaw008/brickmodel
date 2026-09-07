# B2 给温反应—输运（B2-1.0.1）

仅 synthetic 假设研究；production_approved=false。G0与B2-BIND-001由Manager单独批准，CONTRACT.md/B2_HANDOFF.md的历史pending字节不改。独立Safety尚需另审。

## 运行（Python3.12，纯标准库，串行）

先进入本目录，不依赖主项目venv/numpy/scipy，不联网、不安装。

python3 -B run_tests.py --out validation/tests001 --budget-seconds 300
python3 -B run.py --suite frozen --out validation/demo001 --budget-seconds 180 --verification validation/tests001/verification.json
python3 -B audit.py validation/demo001
python3 -B run.py --suite frozen --out validation/timeout001 --budget-seconds 0.000001
python3 -B reproduce.py --run validation/demo001 --tests validation/tests001 --out validation/replay001
python3 -B build_repro.py --run validation/demo001 --tests validation/tests001 --out validation/b2-repro001.tar.gz

先提交源代码，再产生证据。同一次源码/本版合同/完整展开输入与实际指名覆盖全部绑定，才允许passed_frozen_suite；无--verification只能not_run。--config使用合法完整JSON但始终audit_only/not_verified_for_custom_case，即使同名W03。默认/配置互斥，输出仅新建模块相对目录，拒绝覆盖、绝对路径、..和链接。显式畸形/schema evidence exit2，身份不符exit1/not_run，数值/审计失败exit1，超时/资源exit3。

## 数学与数值

半板cell-average FV，a_D=d/ell²、b=Bi_ref/ell，半格/膜串联g；两阶段SSPRK2在t和t+h求系数，端点最坏损失和stage状态复核，步长截断至knots/0.1τ采样时刻；负库存拒步，不clip。反应和双向有限库通量账本与RK阶段同步。共同τ、c_star和孔隙固定，不包含p/RT重标定。

独立reference/oracle.py只import math；A-SEALED独立Simpson+闭式，A-DIFF独立扩散时间与cell平均级数。reference/b1/model.py、solver.py是已审B1文件的只读字节副本；只有R01–R04安全副本哨兵重跑，不改B1或旧全套。verification.py将每次完整输入、raw、参考误差和命令保留。

## 资源与复现

focused额外积分：B2 30次（2历史暴露量回归+3sealed+6diffusion+4回归+15收敛），B1 4次，共34次≤40；run_tests 实测计入单元测试中的积分调用。默认22情景；不自动加case/网格/重跑失败全套。单thread/worker，RSS512MiB，单例含拒步1000000步；tests300s、demo180s、每角色累计900s。外部/usr/bin/time统计与内部active/ceiling需同时报告。

2026-09-07 数值修复：原保存运行的 W07 在 τ=1.5 因 H=∫K dτ 的梯形积分误差超过固定1e-6而被拒绝；新增基于K二阶导数上界的步长限制，绝对积分误差预算1e-7。库存和通量仍用原SSPRK2阶段权重，不修改历史合同、容差或失败产物。macOS的ru_maxrss按字节换算，Linux按KiB换算。根因、推导及新验证见 ../../docs/sandbox/research/B2_ROOT_CAUSE.md。该修复不提供真实材料参数或新增热场。

reproduce.py是预先规定的离线新副本验证：复制当前源码和真正消费的tests/demo；重跑轻量测试及同22默认demo，沿用该源码下保存的真实focused证据（不增加32次focused求解）。比较11个确定性产物的真实字节；资源与时间戳重新测量。不修改旧tests/demo，也不是补绑定的第二次finalize。最终包保持原模块相对引用，包含SOURCE_SNAPSHOT.json作为离线字节定位，不将其当数字签名或Safety批准。包不包含攻击测试的符号链接，但保留创建/拒绝这些链接的测试源和结果。

## 科学限制与审核

未知原泥/基料到Γ、K、d的映射；不给供应商排名/最佳配方/秒数/强度。S02/S09只是关系结构背景，候选不执行，详见CONTRACT.md §3。guard0.005是保守报告缓冲，不是连续域误差证明。有限氧上界是必要条件，不是燃尽或材料合格。C/O/名义质量审计不等于完整ODE真实性，不能保证发现任意协同改写。

源码完整清单、合同SHA、输入canonical UTF-8+LF和实际覆盖由binding.py运行实算；生成输出与缓存不进入源码身份。模块.gitattributes禁用自动行尾转换以保持冻结字节。源码提交之后不得再改代码去继承旧PASS。无部署；失败保留证据并停止使用，撤销提交须Manager决定revert，禁止reset历史或删除旧模块。
