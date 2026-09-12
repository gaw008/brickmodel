# 动态 k 最小 Column 接法：静态复核（1页）

**有条件 APPROVE：同意动态k最小接法进入实现。中点证据保留方案已明确，设计层面的MEDIUM项关闭；以所述接线与回归真正落地为条件。** 这是候选API设计审核，不是未落地代码/材料验证的通过声明；未检索、运行EOS或改生产。

读取当前 `source_wet_column.py` SHA256 `85f3c47d40ffdc7b9ac473dd248809152b9b9ffb204ee7f213662b29cd27c9db`；共享核 `mass_wet_transport.py` SHA256 `4d2dc3518ad9d52a38029a72e032210a284da3cc25da2e99c54f204c17ab7503`。provider草稿尚未取得，本报告不替代其代码审核。

[MEDIUM，设计层面已关闭] **保留真实中点导热证据**

位置：`source_wet_column.py:_integrals / integrate_source_column`。当前非Liquid的face子类被转换成普通`ColumnFaceIntegral`，新ConductivityPoint/G/σ字段会消失；`run.observations`只保存末态`last`，进账通量却来自`middle`。因此不能用末态k证明本步积分用了什么k。已确认采用`ConductivityColumnFaceIntegral`保留真实`middle`的两侧point、G、实际Q/σ及dt、provider身份；原共享Q积分/能量聚合保持。若记录Δt·σ，只称中点熵产生求积，不能称已测得整步ΔS。预测器记录与接受步证据继续分开。

其余接线条件：

1. keyword-only provider字段只加在Arlabosse子类；None分支的原binding元组、参数布局和结果行为保持。provider非None时严格实际类型及`mixed_source_exploratory`配对；混合分类不能放行普通/旧programmed类型。明确的(0,0)静态k禁用约定正确，临时`replace(WetFace,...)`仍满足原核exact-type守卫且不改存储face。
2. 完成全部inverse后**逐格求一次**provider(T,W)，再配到相邻面；W从同一Nc/M/md定义取得，不含气相水。每格都做域检查，包括N=1；已确认provider来源从逐格校验加入全局`rates.source_ids`，N=1同样包含，不能只在内部面循环追加。状态变化后每次求值重新检查，不缓存初态k。最终`column._check()`也应重核provider身份；provenance区分原件、插值/温度冻结与气相/相变制造来源。
3. 共享核返回的`conduction_w`作为唯一Q；总`energy_w`已含它，新增子类仅附记录，不再加一次Q。G=A/(dL/kL+dR/kR)>0，σ=Q(1/TR−1/TL)≥0仅指这条热支路。用`Q·(TL−TR)/(TL·TR)`或精确表示差计算σ，避免直接倒数相减吞掉小温差；对非有限/非零量下溢按数值失败处理，不clip成“物理零”。同温Q=σ=0应正常。
4. k名义域为本次明确W=.30–.80及35–95°C；节点实验条、温度未知、跨材料误差仍分开。若inverse温度括区跨出provider域，结果只能标称名义域内或拒绝，不能仅凭中心T宣称整个不确定区间受支持。压力仍由原storage约束；k不产生额外压力模型。

最低接线回归：无provider旧结果/身份；非零静态k拒绝；N=1越域及来源；内部格越域；同一库存演化使中点k改变；左右交换Q反号且σ不变；导热只入账一次；实际U反解与水/能量共享账；旧exact/programmed拒绝。该阶段增加真实状态驱动的内部导热与本地湿热反馈，不宣称凝聚水格间迁移或总体熵审计已完成。
