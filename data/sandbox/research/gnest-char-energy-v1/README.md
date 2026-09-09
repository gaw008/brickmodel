# GNEST 同研究端点燃料能量

`source_facts.json` 保存核读数据、条件、来源位置和原始资产身份；`evidence_registry.json` 给出原始热值/产率、SI转换和保留燃料能量的依赖链；`result.json` 保存名义计算结果。

查询使用 `EvidenceRegistry.from_dict(json.load(...)).trace("GNEST_RETAINED_CHAR_LHV_PER_DRY_FEED")`。实际安装查询证据和可复算脚本见 `docs/sandbox/research/gnest-char-energy-v1`。

这些是公开研究特定制备污泥的离散端点，非通用原泥参数包，亦不进入MixedCell。温压反解、动力学或反应热不得以这些燃料能量结果代替。来源缓存路径仅说明实际核读资产位置；全文未再分发。
