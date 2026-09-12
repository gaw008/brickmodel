# ROOT：公开有限氧入口与构相表示的唯一实际验收

当前阶段基线为c0eb242。以下计划在运行前登记；代码冻结/独审/正式安装通过后
才执行，不另做Element、构相、预热、平衡或性能探针。

## 唯一调用

用独立Python3.12.13 runtime，在/private/tmp且无PYTHONPATH运行仓库公开
examples/sandbox/run_cedrone_oxygen.py，参数为--source-root实际仓库根、
--output-dir本目录/native01、--lambda 1/4。必须是全新输出目录。
一次入口只查五个独立Element，再对新原池加料请求进行一次solve_tp；不能
先求λ0。内部worker使用公开入口的既有监督器接线，模块10s、worker30s、
监督40s加5s清理均不放宽。ROOT执行进程退出后回收终态，并查看保存原文件。

固定800K、100000Pa、原18气体+C(gr)、原NASA系数与1bar派生来源、VCS、
element_basis、原全部物理与数值门。新相构造仅把同一完整映射改成safe/pure
block YAML；源/model/策略不改，provider明确新表示法和实际ruamel版本。
每次仍新建可变相。原子量来自同次实际ct.Element读数，须与同次初末相A
精确一致，任何失败保留已返回结果/读数前缀，非零退出且不重试。

## 验收与原点对照

原参考为../finite-oxygen-execution/native01/point01/{INPUT,RESULT,OBSERVABLES}.json。
原完整字节保持，原kernel及安装字节另在../construction-design/*before*。
新结果不能标成旧core/旧构相表示。先核本次原门、源/provider、实际Element
及相A、各19物种库存/模型质量/气分数、精确五元素与质量账；再核新旧：

- 温压、原名义m/b、加O/N/D、总质量及所有源/相定义应相同。basis/source-ID的
  入口说明可以增加当前Element来源，但不得改变物理基准或未知/资格。
- 完整初末loaded_definition、原子量、所有NASA系数/参考压/温域/相密度应相同；
  未变的标准h/s/Cp/g逐项报告float.hex是否相同，另以原独立NASA800K参考门
  2e-10+5e-12*abs(reference)核无量纲值，共152项，不靠序列化回读替代实际物性。
- 实际库存若位级相同如实报告；比较门沿用原双初猜的名义数值规则：各物种
  |n_new−n_old| <= 1e-8 + 1e-7*max(|n_new|,|n_old|) mol；G差不大于
  1e-7*R*800*sum(b) J。不得以更快抵消任何原门失败或临时放宽比较门。
- 新construction_timings_s和elapsed/provider序列化元数据单独比较，不计为
  物理状态差。已有首点带cProfile、新入口没有同样剖析，不能由两点耗时比
  推出稳定性能分布或所有场景加速；本次明确分别记录serialize、gas、graphite、
  Mixture初始化及模块/worker/监督总成本。

保存独审只读取这次实际产物与已冻结参考，不再求解。原返回零/小正数全部
保留，C(gr)不称真实char/燃尽；HHV校正、初料能量、矿物、有限时间和完整
Goal第11节均继续未满足。若本次失败，保存失败并基于具体原因决定下一步，
不在本次执行中切换其它构造方式或循环benchmark。
