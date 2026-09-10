# 有来源的市政污泥解吸关系实际实现

2026-09-09。新增`sludge_sandbox.amadou_desorption.AmadouDesorption`，按Rosheim原污泥的公开解吸实验提供平衡干基含水量及水活度反算。这是完整热湿内核所需材料关系的一部分，不是完整动态干燥或砖体材料包。

## 来源和边界

[Amadou等2006原论文](https://doi.org/10.2495/AFM06014)的PDF p5 Eq1/Table1给出两组Oswin参数，p2说明原料，p9说明干基。元数据及原值在`data/sandbox/research/amadou2006-desorption/source.json`。独立核读确认30/50°C、k/n及制样条件；原文反向不等号和百分号/分数冲突均显式保留。

接口仅支持原两个温度、活动度分数0.1..0.8以及相应含水量范围，拒绝非有限数、布尔值、错误单位、其他温度和域外数值。输入不clip；浮点采用最短十进制读数语义。80位Decimal只是数值策略，不宣称物理误差界。反算端点以返回的80位前向端点为准，精确相等才返回对应活动度端点，不以epsilon扩大域。

每次操作核查固定来源元数据与原PDF。输出是不可变记录，带原料ID、原输入、数量/单位/基准、方程ID、来源摘要与unknown不确定性。来源图为反算→前向方程→该温度参数行→原论文页/表。注册表适用性为conditional；严格证据模式不能因此把一般市政污泥或工厂原泥判为匹配。

## 实际验证

- 作者源测试28项通过；独立再次运行28项通过，另3项负控通过。
- 非editable重新安装后，`python -m pytest tests/sandbox/test_amadou_desorption.py -q`实际28项通过，0.25秒；XML为`installed-tests.xml`。导入路径在隔离环境site-packages，模块与源码字节相同。
- 实际安装接口在30°C、aw=0.4给出Xeq≈0.09461588564kg水/kg干固体，反算回0.4，三节点来源追溯保存于`installed-example.json`。
- 原PDF第6页16个实验符号已按`DIGITIZATION_PLAN.md`用Poppler26.07.0 SVG重建。独立Fraction坐标传播与100位mpmath复算通过，数值差最大约8.4e-51。16点打印拟合均位于完整符号加定位余量的保守图示包络，最大中心差0.00847693987kg/kg。

最后一项是对作者已拟合数据的重建，**不是独立留出验证**；图示包络不是实验重复散差。独立审查发现数字化脚本最初未绑定原PDF/参数行，已修复并确认读数不变。`CODE_REVIEW.md`记录修复及最终摘要；来源核读与统计复算分别保存。

## 实际使用

在仓库根目录、已安装包且已按数据README合法缓存原PDF的环境中：

```python
from pathlib import Path
from sludge_sandbox.amadou_desorption import AmadouDesorption
from sludge_sandbox.evidence import EvidenceRegistry

root = Path.cwd()
model = AmadouDesorption(
    root / "data/sandbox/research/amadou2006-desorption/source.json", root
)
result = model.moisture(0.4, 30, unit="1", temperature_unit="degC")
trace = EvidenceRegistry.from_dict(model.registry_payload()).trace(result.node_id)
```

缺少原PDF时明确拒绝计算。未获取再分发许可，不把原PDF或SVG放入发布内容。生成记录中的长小数是计算输出精度，不是材料测量精度。

## 完整模型下一步

该实验不能提供连续温度导数/解吸热、吸附滞回或动态扩散率，因此尚未接到纯水化学势/整体U主机，不能只乘活动度而漏掉吸附储能。Rosheim参数不能未经论证迁移到Wang2021或Nylen2024。

另已实际核读[Nylen2024开放研究](https://researchonline.jcu.edu.au/83798/)，保存10组明确原料/尺寸/温度/气速条件及独立表格审核于`data/sandbox/research/nylen2024-drying/`。质量和内部温度来自分开的试验，MR定义缺失、部分图缺原料身份及表格冲突均隔离。下一步应以明确原料的Figure8/9温度场比较为目标，先解决同域热湿本构与独立验证划分；不再反复搜索已受限的Bennamoun入口。

`software_status`：解吸提供器和来源接口已实现并实际安装验证；全周期耦合仍未完成。`scientific_status`：限定原研究的拟合重建，未完成动态外部验证或材料迁移。`deployment_status`：离线研究，不含生产控制资格。Goal第11节仍未满足。
