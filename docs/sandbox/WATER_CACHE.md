# 单条目饱和求解缓存

实现依据 [WATER_CACHE_DESIGN.md](research/WATER_CACHE_DESIGN.md)。这是原水 provider 内部的计算优化，物理定义、293–500 K域、100 MPa TP域、来源门禁和 NumericalLimits 均未改变。

每个 WaterProperties 仅保存一个成功的饱和求解快照。缓存键包含规范化后的精确温度、reference 对象身份、来源映射值、数值政策值、backend身份和实际 IAPWS95 callable 身份。温度不舍入，A/A/B/A发生三次求解；不同实例不共享缓存。invalid T 在查缓存前拒绝。

快照由 frozen dataclass组成，只包含求解 T/P/x 以及两相 rho/h/u/s/cp/cv 数值，不持有可变的上游状态。缓存字段不参与 provider equality/hash/repr，不改变原 provider 不可哈希事实；没有直接使用 lru_cache(self)。命中跳过饱和非线性求解，但仍通过当前模型运行两次 `_state` 与密度次序/Gibbs检查。因此预热后 `_Helmholtz` / `_phir` / `_phi0` 注入错误仍可触发当前验证；返回完整pair不是直接从缓存取出。

只在原有检查全部成功后一次写入完整条目，失败不写入成功缓存。替换求解器 callable 或数值/参考/来源身份会 miss。source身份比对用于防止复用旧结果，不代替已有构造时源码和资产验证，也不承诺抵御任意进程内篡改。没有新增源文件运行时重复读盘或全局线程安全保证；不同线程可能重复计算miss，但不会获得半写入快照。

## 验证记录

新测试先运行：2 failed / 6 passed，失败为两次同温度仍发生两次真实饱和求解。实现后新增回归达到17项：精确相邻float温度、容量1、实例隔离、frozen快照、预热后求解器失败/警告、三类当前EOS故障注入、来源/reference/政策变化、失败重试及域检查。

计数证据：同温度连续两次 `saturation_pair`，真实饱和构造次数=1，当前 `_Helmholtz` 检查次数=4。未减少验证次数，未缓存失败为成功。所有数值结果仍由原验收门槛约束。

实际命令：

```
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_water_cache.py tests/sandbox/test_water_properties.py tests/sandbox/test_water_response.py tests/sandbox/test_ideal_water_vapor.py tests/sandbox/test_water_chemical_potential.py -q
```

结果：180 passed in 1.38s（17缓存+78原水+21响应+28桥+36化学势）。主代理末尾另做闭合系统实际profile与安装复验，此处不预报加速比例或完整系统已通过。

独立审核发现一个新错误类别回归：预热后删除 IAPWS95 callable，缓存身份读取曾在原保护外抛 AttributeError。补明确单项 RED 后修复为原 `WaterNumericalError('iapws_solver_failed')`；最终上述同命令181 passed in 1.38s（缓存18项）。原180项记录保留为修补前历史。
