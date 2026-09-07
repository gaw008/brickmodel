# 相同温度饱和计算的有界缓存设计（尚未实现）

本轮只读审查 `water_properties.py` 与 `CLOSED_STORAGE_PERFORMANCE.md` / `closed-storage-profile.json`。profile 是带 profiler 的单次制造流体腔反解，205 次 `state_tp` 都调用 `saturation_pair`，不能据此承诺生产加速比例。缓存不扩大物理温压域，也不改变已有误差门槛。

## 当前对象与风险

`WaterProperties` 是 frozen dataclass，但没有 slots，有 `__dict__`；它持有可变 IAPWS 模块与模型实例。实际 `hash(water)` 抛 `TypeError: unhashable type: 'dict'`，不能直接在实例方法加 `lru_cache` 并以 self 为 key。也不要为性能改成全局按温度缓存或强行重定义 provider hash，这会牵涉现有等价语义与不同实例来源归属。

`SaturationPair`、两相 `WaterState` 及 `WaterReference` 都是 frozen dataclass，正常 API 下仅有不可变标量/元组嵌套，可复用或重建；来源映射为 MappingProxyType。缓存内部可变容器必须 `compare=False, hash=False, repr=False`，且不得作为物性公开可变字段。这个不可变性声明不抵御 `object.__setattr__` 等任意进程内修改。

数值政策 `NumericalLimits` 是 frozen，但 provider 字段和上游函数可由测试故障注入替换。当前测试会 monkeypatch `_backend.IAPWS95`、`_model._Helmholtz`、`_model._phir` 和 `_model._phi0`。在首次成功后返回旧的完整饱和对，会让新注入的非收敛、NaN 或坏热容绕过本应执行的门禁。仅按 T 缓存完整 pair 因而不适合直接上线。

## 推荐最小第一步：缓存已验证的饱和求解快照，命中仍检查两相 EOS

采用每 provider 一个条目的私有缓存，不使用全局池。一个压力闭合中连续试算温度固定，容量1已覆盖主要热点；不同温度直接替换，不做温度舍入。先做此版并重跑 profile，再决定是否值得增加 LRU 或缓存整个 pair。

具体流程：

1. `saturation_pair` 入口先执行现有 `_temperature`，拒绝 bool、NaN、无穷与域外；只用规范化后的精确 float 作为温度键。
2. 缓存条目保留温度、来源/参考/政策身份快照以及实际求解器 callable 引用。实例本身隔离来源；显式比较 reference 对象身份、source_asset_sha256 当前值、NumericalLimits 值、backend 与 IAPWS95 callable 身份，变动时弃用旧条目。保存 callable 对象并用 `is`，不要只保存 `id`，也不要用短命 bound-method 对象作为身份。该检查不代替构造时的源码/资产验证。
3. miss 时按原 `_solve(T=T,x=.5)` 完整运行，保留 status、warning、返回 T 和 x 的验证。仅在所有现有两相 EOS、热容、机械稳定、压力、h−u、Gibbs 检查成功后写入条目。
4. 不缓存可变的完整 IAPWS raw 对象。将实际求解温度/质量分数/压力与两相 `rho,h,u,s,cp,cv` 复制为私有 frozen 数值快照。命中后从快照执行现有 `_state` 两次及原最终密度次序/Gibbs检查，以当前 model、reference、numerical_limits 重建 pair。这样 `_Helmholtz` / `_phir` / `_phi0` 的故障注入和 mutable 模型系数改变仍有当前验证路径；不需要尝试为整个上游 Python 对象图做不可靠通用 fingerprint。
5. 失败不写新条目，不把异常当成功值。政策/来源/求解器身份改变后旧条目不再可用。缓存不吞掉原 `WaterDomainError` / `WaterNumericalError` / `WaterSourceError` 类别。

这个方案消除的是重复饱和非线性求解，而非所有 EOS 派生计算。若要缓存完整 SaturationPair 并跳过 `_state`，需另定义可验证的上游实现与系数不变性契约，或明确禁用故障注入环境的缓存；不能只列几个函数地址就声称深层依赖永远不变。本轮不建议为省去这两次检查增加复杂框架。

命中时复核模型，不等于重新读取磁盘全部来源；现有 provider 也是构造时验证资产和安装版本。缓存不能自行把原契约升级为每次调用完整源码认证。任意模块内部函数或系数被进程内恶意修改的普遍防护不属于本轮目标。

并发方面：允许同温度 miss 重复计算，但不允许读取半写入条目。用一个完整不可变条目一次替换；不要在调用 EOS 时持有全局锁。现有 `warnings.catch_warnings` 的跨线程行为不是此缓存可宣称解决的问题。不要新增全局线程安全承诺。

## 先登记的验证

- 同实例同 T 连续两次：计数实际 `IAPWS95(T,x=.5)` 构造，只执行一次；两次 pair 的全部数值、来源身份和残差与无缓存路径一致。TP 查询仍各自解真实压力状态，不缓存成饱和密度。
- 两个独立 provider 同 T 各自 miss，结果 reference 分别是各自对象，不能串用。构造缺失/错误来源仍拒绝。
- 容量1序列 A,A,B,A 对应三次饱和求解；用 `math.nextafter(A,+inf)` 证实不做粗温度合并。不同输入表示规范化成相同有效 float 可以共享。
- 预热后分别 patch IAPWS95 为非收敛/警告/坏状态、patch `_Helmholtz` 为 NaN、patch `_phir` / `_phi0` 为不一致热容，仍得到原错误类别。必须是先预热再注入，现有每例新 fixture 不足以覆盖缓存失效。
- 预热后换更严格数值政策、reference 或来源映射：失效并重新运行，不继续返回旧认可状态。失败之后修复后可重试；失败本身不能占据成功缓存。
- 禁止修改返回 pair/state/reference；缓存字段不影响 repr、dataclass equality 或现有不可哈希性质。不必为可逆优化扩展公开 API。
- 运行原水78项、response21项、水汽桥/化学势以及实际 rigid closure/storage 回归；比较闭合 P/U/T、实际残差、最终括区和条件误差资格。数值容差保持原值。
- 对相同 profile fixture 记录优化后饱和 **求解次数**、`saturation_pair` 调用次数（后者可能仍205）、EOS检查次数及独立不带 profiler 的重复计时。每次计时注明冷/热缓存，不用一次最快值作为吞吐保证。

本轮没有代码修改、没有新性能测量、没有实施后的通过声明。实测对象性质探针命令使用 `PYTHONPATH=src .venv/bin/python` 加载 `data/sandbox/water`：provider 有 `__dict__` / 无 slots / 不可 hash；返回 pair 可 hash。后续实现应独立审核并绑定源码哈希后再比较 profile。
