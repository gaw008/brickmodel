# 条件相对供热比较所用的原始模拟结果

这里保存三份既有 `TPResult` 的**原字节副本**，供离线重算相对热量；不是三份实验数据，也没有为制作本目录重新求平衡。原文件位置、SHA、归档和共同来源见 [manifest.json](manifest.json)。

- `lambda0-result.json`：原 Cedrone 条件元素池、零外加气的结果。
- `lambda-quarter-result.json`：公开有限供氧入口的 λ=1/4 结果。
- `lambda1-result.json`：原有限供氧比较的 λ=1 结果。

全部结果在800 K、1 bar，按原1 kg论文报告样本的CHONS子池计算。严格干基、灰矿物分配、差减氧误差及实际原料适用性仍未知。0.292 kg灰分等外置部分没有被重新标记为惰性矿物；石墨不是实测残炭。

共同材料表见[原始数据与基准解释](../cedrone2024-element-pool-v1/README.md)，热化学来源见[限定相集](../tp-equilibrium-v1/source.json)，公式和实际验证见[供热比较报告](../../../../docs/sandbox/research/cedrone-relative-heat-v1/REPORT.md)。原基线与最新入口之间的序列化元数据变化已在上一阶段实际比较，完整物理结果相同。

这些副本允许从新检出的仓库重算条件热差，不需要开发机临时目录或重新调用Cantera。它们不提供绝对原料焓，不是验证模型自身准确性的外部证据，材料与训练资格均保持false。
