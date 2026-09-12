# 唯一一次算子成本探针：静态审查

APPROVE。最终脚本与原 PROBE_PLAN 的范围、阈值和次数一致，可以启动登记的唯一一次构造及双格算子调用。本结论是静态审核，不是探针结果。审查时 `probe01/`、`supervised-probe01/` 均未存在，未导入或执行 driver、EOS 或 native。

## 最终输入身份

| 文件 | SHA256 |
|---|---|
| `PROBE_PLAN.md` | `df20dec9783cd1cf9e845c480514dcae4d37b84da0011579e1fc78afcb0e59a9` |
| `native_case.py` | `da1db8d86ec03d365070703e517c5d6bd4c06956060e011f8113153753378d85` |
| `probe_driver.py` | `1dc6660223cbb4a40e8f5aa392a10421b63157f73602926c080bed762f4788b7` |
| `run_supervised_probe01.py` | `b3dfc81501f7c160076ec66bafcd6ab59f134361219d1751cfb9b00e58b51476` |

另以只读 SHA 比较确认 `install/SOURCE_FREEZE.json` 的 **173 个**包文件分别与当前源码、安装包相同。该检查仅用标准库读取字节，未导入物理包。机器记录为 `PROBE_STATIC_SNAPSHOT.json`。

## 核对结果与已补项

- 两格初态 T=330/333 K、凝聚水 0.2/0.225 mol、每格干质量 0.01 kg、可用流体体积 1e−5 m³、厚度各 0.02 m、面积 0.001 m²。气体库存、导热/扩散/渗透与相变系数在 case 明文定义；未代入跨材料论文的 D/k。
- 同一个 wet 模型提供实际 Python liquid/vapor/chemical 对象。新刚性包装与气相输运使用共同参考；原 dry 313.15 K 相对参考仍明确保留。无 HEOS，无步进积分、事件恢复或自动重试。
- 机械括号 80–120 kPa；新条件域 90–110 kPa，温度括号 325–338 K。原压力容差、内能/温度反解容差、条件数值包络均未改变。包络明确不是独立 EOS 误差证书。
- `make_case` 每返回一格 point 后保存构造前缀；构造完成保存 INITIAL；唯一一次 `column.evaluate(initial)` 返回后先保存 EVALUATION，再判断验收。若后格失败，早先已构造点仍在 CONSTRUCTION_PREFIX。原异常保存 FAILURE；独立目录 `exist_ok=False` 防止覆盖已有探针。
- 验收补上 Fraction 从返回完整 U 与原 target 重算残差，绑定逆解保存 target/residual，并使用原能量门；温度与已保存初态对照。另核活度乘纯水平衡压、纯水查询的当前液压、摩尔质量、水参考及 implementation。共享内面与封闭端面、非零传热/相变及 false 资格有显式断言。
- operator 计时从 INITIAL 保存后、真正调用前开始；最终内部 wall 判断与保存的 total_seconds 采用同一 `finished`。原内部 90 s 目标、外层 110 s 硬限与 5 s 清理不变。内部时钟不是阻断式计时器，超时回收责任仍在外层既有进程组监督器。
- 外层以固定解释器 `-I` 和移除 PYTHONPATH 调用固定 driver；driver 通过明确文件路径加载本例 `native_case.py`，不依赖隔离模式下被移除的脚本搜索路径。
- 监督输入包括三个脚本、PROBE_PLAN、安装冻结清单及监督器；wet model 与其直接/上游来源资产；五个水来源资产；气体质量事实/原缓存、元素约定及 NIST 热化学 JSON；全部源码与安装 `sludge_sandbox` 文件和安装 `iapws` 文件，排除运行生成的 pycache。既有监督器会比对前后输入，输入改变不会维持 complete。

此前报告的目标/平衡压核对不足、计时口径和构造前缀保存缺项，均已由父任务在首次物理执行前补齐。没有要求扩大原预算或更改物理条件。

限制：此探针只给出本例构造与一次实际算子的成本和条件一致性。即使通过，也没有动态路径、时间/空间收敛、真实泥料传输校准、液流或全周期烧成的验收含义。监督仍继承现有进程组隔离边界，不宣称能收容主动逃离会话的任意子进程。

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — 最终静态探针方案无未解决发现；实际运行结果尚不存在。
