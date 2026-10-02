# P56 原P45同次RHS：能量操作证据

P56原P45操作证据已实际保存并闭窗。仅原12格declared_zero旧/新两模式，原生构造/初态及每模式1次完整RHS；原诊断Udot AST节点单次观察，原乘法、np.sum(axis=1)、左结合顺序和dtype保持，cached与decoded分别保存。实际2026-10-02T18:55:11.350023+00:00至2026-10-02T18:55:12.552424+00:00，监督1.202414125s/CPU1.015555s，rc0回收、未超时。独立1job/worker/attempt、2constructor/2nativeRHS，0Jac/ODE/独立extraoperators；原内部calls逐模式/阶段持久。两模式全12格净U、原生state及Ca状态/cached/decoded均逐值重现历史；这是新观察而非恢复历史内存。原signed最大差−1.4210855350476714e−14W、old净向量尺度4.6751916143275985e−6W、relative3.039630569777313e−9>原1e−11，仍FAIL。i7固体小计A_s差−2^−46W已定位于原decoded乘积和物种归约：输入精确乘积差−3.8780693134327255e−15W、乘法舍入差−6.0291690463418724e−15W、归约舍入差−4.303616355427406e−15W，精确分解残差0。i7Ccal/us/ug/cap相同且dT/db/dpore差0；后续五次原加法舍入差0，最终另含弹性差−6.352747104407253e−22W。未观察NumPy内部C-level每次加法，不唯一指认其内部索引。当前没有改物理核的证据，不能推论核在所有状态无缺陷。原科学核及旧642完整根记录、全部old live合同保持；新增11观察policy至653=144literature509assumed0measured。P45原FAIL和P34/P40/P44/P50撤回/P51失败保留；P54空间/P55时间只按原范围保持。历史名义余水.135892078740%>.1%和0实测保持，0新名义尝试。独立势导数、八阶段、三方案反演UQ/完整CLI/whole模型仍未完成。首次必要字节1958323B含旧新冻结源和原输入；后来分解/报告/行政另实测，不能代替最终总量。Git/Drive增量、实际恢复及历史容量分列；不自动修核或启动下轮。

新增离线生产观察入口 `scripts/run_calcium_energy_observation.py`。其输入为本轮冻结根合同和原P45根/probe/旧新源；只执行原declared_zero上下文各一次native constructor、initial_state和完整RHS。profile截获原已产生系数；原诊断表达式用AST包装返回同一值，保存原乘积/np.sum与每层原加法结果。未整跑旧probe，未调用其额外references_from_initial热力学链，未执行check/assert、positive或原4上下文。实际原内部thermal/phase/mechanical/rates/source调用全部在计数文件分列，两继承RHS入口各模式属于一次完整RHS。

两模式全12格Udot、原生state、Ca状态及cached/decoded数值逐值重现历史。原最大signed差−1.4210855350476714e−14W，原分母4.6751916143275985e−6W，原允许绝对差4.6751916143275984e−17W，relative3.039630569777313e−9>1e−11，继续FAIL。这是新作业的重现，不是历史内存或丢失字段恢复；历史result/probe/source不改。

第8格（i=7）Ccal/us/ug/cap逐值相同，dT/db/dpore差0。原calcite功率乘积从−68.74814529359237变为−68.74814529359239W，rounded差为−2^−46W；原lime乘积从−4.303616355427406e−15变为−0.0W。两者保存rounded乘积差的精确和与原np.sum结果差分别保存，不能直接当同一个量。

| i7固体小计差来源 | signed W | 保存binary64值的精确有理数 |
|---|---|---|
| exact_product_total_delta | -3.8780693134327255e-15 | -614504611612459/158456325028528675187087900672 |
| multiplication_rounding_total_delta | -6.0291690463418724e-15 | -238839992514773/39614081257132168796771975168 |
| species_reduction_rounding_delta | -4.3036163554274058e-15 | -681935232013697/158456325028528675187087900672 |
| solid_subtotal_delta | -1.4210854715202004e-14 | -1/70368744177664 |
| decomposition_signed_residual | +0 | 0/1 |

输入精确乘积变化来自原decoded tangent变化；系数差在i7为0。乘法舍入变化与np.sum聚合舍入变化另列，三部分精确闭合为A_s差−2^−46W。原后续五次左加法的舍入差均0，主差沿原局部subtotal传递；最终另含弹性差−3/2^72W，合成净U差−67108867/2^72W。i2的A_s/U差0，i3/i5仅剩原弹性差。没有最终全局sum导致i7主差的证据。

以上唯一定位到输入乘积、乘法与物种归约三个层级；没有观察NumPy内部C-level每个加法指令，不能唯一指出内部加法索引。精确有理数和描述性fsum只处理保存值，0模型调用，不替代原算法、vector、分母或1e−11。当前没有需要修改物理核的依据；也不证明所有状态下核无缺陷，不授独立势微分、动态守恒或全模型资格。高质量诊断求和若未来确有需要，须另明示改变算法并保留原结果，不能以目标PASS为依据；本轮未实施。

实际启动2026-10-02T18:55:11.350023+00:00，回收2026-10-02T18:55:12.552424+00:00；1.202414125s/CPU1.015555s，300秒唯一截止2026-10-02T19:00:11.350023+00:00未重置。首次必要字节1958323B包含两份45文件源533168/534874B、原root374061B/probe15814B和本轮输入源/结果；新增122076B保存分解和报告/admin收据最终另计。P56新增11policy记录至653，旧642完整记录和全部旧live合同保持，measured显式0；首次declaration省略0计数仅格式，非有实测。

原raw状态/乘积字段只在ignored runs与必要私有增量，Git仅入口、根声明及必要汇总/文档。证据 `runs/full-cycle/p56-calcium-energy-operation-observation/result.json`、`saved-operation-decomposition.json`、`call-counts.json`、`execution.json`。正常Git/push/remote与本P56原Drive增量actualpayload最终事实读 `runs/full-cycle/p56-calcium-energy-operation-observation-final-delivery-state.json`；metadata不是字节恢复/owneraccess，原压缩件保留，历史容量未解决。声明至本记录行政723.650s与科学耗时分列。

下一有价值候选：同原298.15K低温direct_transient、既有26格27面、原物理和.025s/.5s输出，单独将time_scale完整记录登记为6，把10s阶段延长至60s以观察供气/库存耗减/耦合是否仍闭合。它仍是synthetic/assumed数值时长扩展，T290..350K/压力适用域保持，不将合成L扩到高温烧成或真实砖；超域保留未资格/失败，不clip或放宽。121保存点及所有必要输入源估计约6MiB，建议另分配1job/worker/attempt/constructor/ODE、900s和8MiB上限，须先精确估计并根登记；不续用本P56的300s/3MiB，也未启动或授予一般时间/空间精度。0名义尝试/拟合/UQ/搜索/全八阶段批次/.0125s/52格。
