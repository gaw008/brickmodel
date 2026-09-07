# 显式可选水物性后端

默认 `load_water_properties(directory)` 仍使用已固定的 Python IAPWS1.5.5。HEOS 接口是可选的离线研究功能，不能据此认定原污泥材料或整个烧成过程已获验证。当前只接受已审查安装构建的清单；不同操作系统/构建需要独立核查，不能改清单哈希绕过检查。

```python
from pathlib import Path
from sludge_sandbox.water_properties import load_water_properties
from sludge_sandbox.water_chemical_potential import WaterChemicalPotential

sources = Path("data/sandbox/water")
selection = dict(
    backend="heos",
    backend_manifest=sources / "heos-8.0.0-approved-manifest.json",
)
water = load_water_properties(sources, **selection)
state = water.state_tp(300.0, 100000.0, phase="liquid")
chemical = WaterChemicalPotential(sources, **selection)
print(state.enthalpy_j_mol)
print(state.source_ids)
print(water.implementation.canonical_json)
```

调用环境必须另外具备与清单逐文件匹配的 CoolProp8.0.0。现有默认 `water` 依赖组不会自动安装或启用它；当前实际 HEOS 测试在已经核查的独立研究环境执行。依赖缺失、清单不匹配或不支持的 selector 都会明确失败，不退回另一后端。完整可选依赖锁定及其他平台验证仍需后续完成。

此实现明确为混合实现：真实液/汽 EOS 使用 HEOS，理想水汽、理想熵及低温比热正性系数证明保留已核查的 Python IAPWS 实现。物理参考态 `WaterReference` 不包含软件身份；返回状态的 `implementation` 及 provider 的来源资产映射携带独立身份。不同后端不能悄悄共用化学/反应/跨单元/目标状态身份。普通 Python 状态的该字段为 None，因此 dataclass/asdict 的结构有显式新增字段；不宣称所有历史 JSON 字节都保持不变。默认 provider 的 canonical 身份已与原绑定记录比较一致。

`water_implementation_v1.json` 是 `implementation.canonical_json` 所表示的派生文档，其 SHA-256 位于 `source_asset_sha256`。摘要同时绑定 schema、provider 名称/版本、source IDs、完整定义、内核/转换/理想调用层代码、参考与运行版本。新增来源 ID 的查询入口是 `data/sandbox/water/heos-8.0.0-source.json`，可继续定位许可证、软件文档、固定构建清单、原始流体定义和 IAPWS 来源。

已有证据包括受限温压网格、官方公式检查、局部导数、部分故障与共享实例测试，以及一次原门槛的制造测试闭合储能逆解。这些不能代替实际湿态完整积分、变形/耗尽组合、开放输运、完整材料外部验证或性能基准。尤其不能因为使用 C++ 后端就宣称整体模拟已经加速。

当前实现对每个公开操作保留配置和流体定义的前后检查、实例锁及警告拒绝。构造时同时核验原始流体字符串和规范化 JSON；运行中直接比较原始字符串 SHA，避免反复解析，格式变化同样会拒绝。温压计算内部的饱和计算共享该次操作的完整事务，没有状态缓存。实现改变对应新的内核与清单摘要，历史结果保留历史身份。

新增验证范围是固定相库存、规定压缩的四步 0..1/64 秒湿态前缀，采用独立 Python 熵参照及原能量/温压门槛；不是活动相变、自由烧结或全周期。原时间上限失败及两步优化证据见 `research/heos-runtime-optimization/`，不能将局部耗时改善外推为所有模拟的速度保证。

## 共存迭代数值修复

当前版本以原Newton方向做最多六次半分回溯，接受双门槛通过或最大归一化残差严格下降；8个外层状态不变，最多43对共存EOS评估。原1e-4Pa/1e-6J/kg共存门槛和源/分支/稳定性守卫不变。新实现身份已更新；原失败温度、邻点、30状态/7导数及实际规定变形/活动相变/耗尽夹具复验见 [证据包](research/heos-coexistence-backtracking/README.md)。此处后续实际覆盖补充前述早期范围，仍不证明任意状态收敛或真实材料全周期。
