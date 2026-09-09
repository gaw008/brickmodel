# kg/mol终态水量局部修正

已应用ceb76234/test66ae28a7。接收显式绑定的原初状态、政策、ExactAffineEvidence及完整固体kg/液气mol/U面板账本；所有原始终态必须先按分量重算一致。只在全部原局部/累计绝对、gross蒸发fraction、storage/element/mass残差门槛通过后返回等量液→气的局部候选，固体kg、U及其他格对象不变。原旧2*storage residual只是历史数值诊断，不冒称真实元素计量证书。

新增必填Fraction original_liquid_fraction_limit<=1e-8，是额外保守数值策略：本格累计修正不得超过本格原初液量对应比例，不借其他格额度、不替代原gross门槛。累计totals仍需未来控制器从完整历史核实。

源码52项8.97秒、实际非editable安装52项8.79秒通过，92实际模块匹配。独立28项0.32秒及应用SHA核验通过；原失败及修前测试/完整审查归档，逐成员SHA重读一致。

本原语不认证调用者给定的provider/source/完整前缀，不定位或排序根、不切模式、不授予事件提交与续算许可。后续实际采样连接器与完整事件控制器必须补齐这些要求。
