# 有限外加 O₂/N₂：仅两个新增 TP 点的运行登记

此文件在实际执行前登记。执行文件是同目录 `run_finite_oxygen.py`；真实执行由 ROOT 的 `launch.py` 监督启动。作者目前只做保存数据、Fraction 算术和制造后端检查，没有构相、调用 EOS 或求平衡。

## 固定工况与新增调用数

- λ=0 只读复用 `../cedrone-execution/native01/{INPUT,RESULT,OBSERVABLES,STATUS}.json`，不再求解。
- 仅按 λ=1/4、λ=1 的顺序新增两次 `solve_tp`，各自从原 Cedrone 五元素池加上本点有限 O₂/N₂ 重新构造；不能从前点返回库存继续加气。每个调用创建新的 pool，已固定 core 每次创建独立后端。
- 每点 T=800 K、P=100000 Pa，18 个气体加 C(gr)，原 1bar NASA7 派生物性与原 element_basis 初始化。显式 VCS，没有 auto、fallback、重试或额外扫描。第一点任一失败便停止第二点。
- 原 `TPPolicy` 保持：rtol 请求 1e-10、max_steps=1000、maximum_elapsed_s=10 s，其余参数与已通过基线相同。VCS 的 TP 原生实现不消费传入 err；保存 policy.definition 中原先明确的实际内部容差与源码说明，不能把请求 rtol 当作 VCS 实际收敛容差。
- 每点模块 10 s，整个 driver 30 s；ROOT 外监督 40 s，终止后的清理等待 5 s。这些预算不因 profile 或失败扩大。外监督采用既有进程组清理约定，不新增跨会话逃逸进程的保证。

## 精确加料和原样本基准

使用原打印五元素质量 m=(.360,.053,.222,.058,.011) kg，合计 .704 kg；实际 A 从已保存基线 provider 取 binary64 原子量再精确转 Fraction。顺序 C,H,O,N,S，b=1000m/A，所有新点保持原 1 kg 报告样本基准。

`D=bC+bH/4+bS−bO/2`，`O₂add=λD`，`N₂add=(79/21)λD`；仅 O、N 原子增量分别为二倍该分子数。21/79 是明确虚拟干混合气摩尔比。D 只引用 C→CO₂/H→H₂O/S→SO₂/N→N₂ 的形式计量产品，不是实际燃尽需氧量；参考产品向量不是平衡目标。N₂ 也不被强制视为化学惰性。

两个新模型输入质量分别约 1.95840314198 kg、5.72161256793 kg，准确值由同级 `../finite-oxygen-design/MATERIAL_ARITHMETIC.json` 逐项核对。每点保存原 b、λ、D、O₂/N₂ 分子数、五元素增量和总数、O₂/N₂ 质量及 `.704+Madd`。质量账不能继续用 .704 kg，也不能把灰或水再补入 Gibbs 池。

## 绑定与原有数值门

`INPUTS` 固定并核对上述基线四件、其原监督 metadata/status、公开 printed-pool、设计四件和当前 core 文件的实际 SHA；读取的同一字节复制进新 `native01/inputs/`。已通过基线的实际模块为 `da382eead7211e5a91a1630fbe30a75a8c7feca9cb1af6814398c57f8914849c`。运行时必须导入已登记非 editable runtime 的相同模块路径/字节，provider、policy、来源、物种顺序和实际原子量与基线完全对应。基线监督必须 completed/0、输入前后 SHA 相同、leader 已回收。新执行结束再核固定输入，ROOT 外监督还绑定新脚本/PLAN/runtime/来源。

原 module 全部元素、非负、T/P、来源物性、名义 G 下界/KKT 与时间门仍须通过，raw result 完整保留。薄 driver 再核实际返回库存、请求的 b、provider 与来源对应，并用同一实际原子组成和原子量重算：

`r=Σa n−bλ`，每元素 `|r|≤10⁻¹⁰(1+|bλ|)`；

`Mout−(.704+Madd)=ΣA r/1000`（Fraction 恒等式），并检查其绝对值不大于实际残差三角界、不大于原元素容差传播界。传播界不是新的材料误差或可调门。

不把 λ=1 时 C(gr) 消失、产品单调性、特定气体比例设为通过门。

## 同一次首点 profiling

仅 λ=1/4 的那一次 `solve_tp` 用 `cProfile.Profile` 包裹；没有任何为 profiling 新增的 solve。首点记录的 `solve_elapsed_s` 以及 driver elapsed 包括 profiler 开销；第二点不 profile，不能把两点耗时差直接解释成纯物理复杂度差。

调用返回后先独占写 `point01/RESULT.json`，再保存返回状态和实际调用时间。若 driver 已超时，保留结果并停止后续；未超时才写 `first_solve.prof` 和按 cumulative 排列前 80 项的 `first_solve_profile.txt`。profile 保存错误也终止后续，但已写 RESULT 保留。profile 可区分 Python 调用成本；未细分的原生 C++ 成本不伪称已经定位到内部算法。

## 保存、失败和最终比较

输出目录固定新建 `native01`，存在即拒绝。先保存 STATUS 和来源输入前缀；每点调用前保存 INPUT，并把该行持久化为 about_to_call；这只声明调用准备，不承诺返回或写出成功。返回后完整 RESULT 先保存，再做 profile/资源/外部算术检查。返回后的行先标 `returned_unchecked`，另保留 `module_status`；仅完成本层全部检查才标 `completed`。异常、超时、模块失败、profile 或后验保存失败均记录非零终态，不启动后续点。I/O 本身失败时不能承诺文件完整；已经独占保存的原结果不会被重写。

`COMPARISON.json` 从开始就保留三行：λ=0 明示 reused，两个新增点起初 not_run。每个成功行保留全部 19 个绝对 mol/原样本 kg、模型 kg 和 18 个气相摩尔分数，C(gr) mol/kg/碳原子占比，以及逐元素残差和质量身份/传播界。不只保存主物种，不归一化样本表，不用阈值删除小正数。

灰 .292 kg、Cl .0005 kg、n.d. Br 及 .0035 kg 打印缺口仍在外置记录；O 差减/矿物分配与严格干基未知。不重复加入残留水。本比较是限定相集合下的条件组成响应；C(gr) 不是实测 char，标准态 H/G 差不是炉热耗/放热，输出不等于实际排放，没有材料/训练资格或完整烧砖模型完成声明。

作者非 EOS 证据在 `author-tests/`：初始 missing-file RED 保留；profile 保存失败行错误标为 completed 的实际 RED 也保留，之后最小修复 GREEN；另有精确加料/质量、基线复用、首次失败停止、超时保留返回、两次制造库存 dispatch 的有限检查。制造返回只测薄入口和账本，不能作为材料或 Cantera 求解验证。
