# 旧水相转移AST断言与当前重构的关系

只读审计；没有修改水代码、测试期望或仓库。当前`water_phase_transfer.py`的HEAD与工作区Git blob均为`a260c366aec47eaea5d9c1917bca27945f9bb996`。因此本次CurrentSlab身份修复没有改动水相转移实现。实际31passed/1failed结果和原XML应继续保留，不能写成整个文件通过。

失败断言在`tests/sandbox/test_deforming_wet_admission.py:156`，它将归档旧版与当前`evaluate`、`_dry_diagnostic`、`with_depleted_cells`整个函数AST逐字比较，注释还宣称evaluate完全未变。当前evaluate已经拆为先`_check_interface_state`、单次`base_model.evaluate`、再`_assemble_transfer`；新增autonomous入口也复用检查和组装。这是旧结构断言失效，不是刚发现相变公式被身份适配器修改。

`check_stale_water.py`实际独立解析并比较AST，结果保存在`STALE_WATER_AST.json`：

- 旧evaluate前两个语句与新`_check_interface_state`完整函数体相同。
- 旧evaluate水列索引、reaction副本、diagnostics初始化及完整逐格化学循环，与新`_assemble_transfer`前四个语句相同。
- `_dry_diagnostic`、`with_depleted_cells`和构造器源匹配`storage,k,mode`循环完整AST均相同。
- 整个evaluate的AST确实不同。组装尾部还增加了`mechanical_rates_per_s`转发与实际base.source_ids并集；这属于旧基线以后新增的上下文传递，不能声称除了函数提取之外绝无差异。

这些结构证据定位了失败原因，但不是新的真实活跃水相物理验证。建议以后以如下行为回归替代“完整函数源码永远不变”，且保留旧失败及明确变更理由：

1. 使用合法构造的现有源匹配host，对已有测试中的正驱动力、负驱动力、零蒸汽和接近平衡条件，断言液相/蒸汽增量等摩尔相反、压力按实际当前气体体积算、有限蒸汽熵产生非负；零蒸汽不伪造有限化学势。可复用`test_water_phase_transfer`已有实际用例，不再建立另一套模拟化学真值。
2. 明确检查“接口检查→单次base求解→单次组装”顺序。非法无液相/干界面有液体时在base调用之前拒绝；关闭系数时完整保留base能量/库存上下文。用合法对象上的计数spy记录调用，不能跳过构造或身份校验。
3. 对干接口分别验证严格模式下液体重现、过饱和、未知平衡驱动的原DomainExit；亚稳无成核模式保留显式状态与零相变率。这验证政策行为，而非函数缩进/位置。
4. 对已有直接FreeSolidSlab合法对象，在相同状态下比较常规与autonomous入口的相变诊断和库存/能量账本。机械速率、功率分项和动态source_ids必须被保留；热量不得再次添加潜热。autonomous入口仍只接受明确支持的直接freehost。
5. 如继续保留结构保护，只针对尚要求完全不变的源匹配/化学循环做带历史说明的补充检查；不能仅将旧整函数期望换成新AST然后称行为已验证。

最小身份修复的准入证据应单列正式12项身份测试、原current-halfcell修复回归及既有free测试。该旧AST测试仍是已知测试维护项，不应通过删测试、改水公式、关闭源校验或扩大身份接受域消除。
