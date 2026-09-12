# dynamic01 有限静态审查

APPROVE。两步 midpoint 动态脚本与原登记模型、误差门和预算一致，无未解决的静态发现。只解析与阅读脚本，未导入 driver、调用 EOS、运行积分、安装或修改生产；没有重跑 probe01。

首次读取脚本时动态输出目录尚未存在；最终 SHA 快照时 `dynamic01/` 与 `supervised-dynamic01/` 已创建。本文不声称全程未启动，也不包含本次动态结果判断。本审查没有轮询进程或读取动态结果。

## 最终字节

| 文件 | SHA256 |
|---|---|
| `DYNAMIC_PLAN.md` | `fc95bbc20b463ab6f899f3379a58ccb1c6826679b65a61c953517f37d7e575e1` |
| `dynamic_driver.py` | `5f84b716573bc9f680b3e43844bb1414e45265ecbce71d391d11dd19bf22690b` |
| `run_supervised_dynamic01.py` | `5289712e0619a6534c645e6e9b4ba7966051ec165d2738a297cb2522529a573d` |
| 不变的 `native_case.py` | `da1db8d86ec03d365070703e517c5d6bd4c06956060e011f8113153753378d85` |

机器快照在 `DYNAMIC_STATIC_SNAPSHOT.json`。三个 Python 脚本的标准库 AST 解析通过，未执行其内容。生产仍引用此前审查与安装冻结的 173 文件模型；本轮没有为相同代码重复整套测试。

## 核对内容

- **范围及次数**：不变的两格制造几何/输运案例，真实同一 Python 水提供者；0.05 的实际 binary64 表示作为精确 Fraction 时长，两次 midpoint 接受步、六次 RHS。不是将十进制 0.05 与其 binary64 值混用。检查 3 状态、2 观察、2 账本、6 attempted/completed 及精确终点。
- **完整 U**：每个接受点以 Fraction 重算返回总 U 减原状态 U，绑定逆解 target 与保存 residual，再加原 energy_error 检查 1e−5 J；温度反解界保持 1e−6 K。未改用定压 H 或增加第二次潜热源。
- **逐格账本**：共享面左入右出，凝聚水减相变、水蒸气加相变，各自带一次已记录投影残差；内部气体和热量使用同一组 face integrals。面能量由传导、扩散携带焓、对流携带焓及分解残差重新组成，符号正确。
- **整体与前缀**：逐接受步及相对初态的累计 U、水和两个惰性气体独立重算，扣除明确已接受的投影残差后要求精确相等。预测步的物理转移不混入已接受账本。报告的累计数值预算含积分器原本计入的预测算术成本，其验证沿用冻结实现，不冒称已给出截断误差证书。
- **实际状态门**：每个接受点检查 T/W/P 条件域、当前液压查询、活度乘纯水平衡压、化学残差和库存；源模型/训练 false 保留。末态 T 相对初态变化必须超过最终逆解界加原登记的 1e−6 K，压力和凝聚水变化则是非相等检查，不宣称压力变化已超过完整不确定度。
- **活动性断言**：父任务已补直接检查内部扩散/对流携带焓至少一项非零，并将熵产生门改为严格 `>0`，与原计划文字一致。传热、气体迁移和局部相变仍分别有非零门；没有更改原计划或增加参数拟合。
- **失败保存**：逐格 construction prefix，完整 INITIAL，再保存返回 RUN 后才作验收。失败或不完整 run 不能凭部分 zip 循环获得通过，因为 status、数量和终点有独立门；随后保存失败 ACCEPTANCE 或 FAILURE。独立目录拒绝覆盖先前结果。
- **资源与隔离**：60 s 原积分器预算，80 s driver 检查与保存 elapsed 共用同一标量，外层 100 s 加 5 s 回收；没有自动重试或提升预算。原监督器以固定解释器 `-I`、去 PYTHONPATH 执行固定脚本；显式加载本例 case。监督输入保留计划、脚本、冻结清单、来源资产、源码/安装包、iapws 和监督器，前后输入改变不能维持 complete。

保存结构已用原 probe 的被动 JSON 核实：点的温度与压力路径是 `point.fluid.mechanical.temperature_k`、`point.fluid.mechanical.pressure_pa`。顶层属性不会随 dataclass 字段序列化；本 driver 在运行内使用活对象属性合法，后续保存审查必须按上述真实字段读取。

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — 有限动态脚本可执行；实际完成、保存结果和输入身份仍待终态后的独立审计，不代表材料资格或时空收敛。
