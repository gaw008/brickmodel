# 保存面短时生产运行入口

`scripts/run_saved_reference_transient.py` 从 `public_reference_cases.saved_reference_transient` 读取冻结源码、完整case和必要输出路径，以既有 `model.integrate()` 完成声明过程。预算在根 `validation.saved_reference_transient.*`，外部沿既有固定deadline监督/回收流程。它不增加独立RHS/Jac/本构算子、搜索或拟合；正常solver及native summary调用真实计数。

case的合法整记录构造顺序为既有P46/P44物理合同、P49保存13格mode3、baseline数值设置；输入在科学启动前冻结。observer读取原summary返回locals及原热导函数return，区分内面与边界、gas/water向外和heat into-left/into-brick；C采样保持0。原始量没有新归一尺度或阈值。

P51唯一实际attempt在最终JSON序列化处失败，数值未落盘。当前源补接已有 `plain(result)` 类型转换，仅静态核对、未重跑。已关闭科学窗口，本文不构成运行授权或新预算。原始冻结source及错误留存，完整失败、计数和资格边界见 `docs/FULL_CYCLE_P51_SAVED_REFERENCE_TRANSIENT.json/.md`。
