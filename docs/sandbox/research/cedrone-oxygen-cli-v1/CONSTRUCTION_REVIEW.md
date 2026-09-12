# 最小构相差异独立审查

结论：**APPROVE**。没有发现需要阻止本候选的实际缺陷。范围仅相对 `c0eb242` 的核心、测试、依赖声明与锁文件四项差异；未重审既有 VCS 数学，也未执行构相、EOS、安装或旧测试。

完整冻结 `derived` 仍先接受 `json.dumps(..., allow_nan=False)` 检查，再由每次新建的 safe/pure YAML writer 输出；显式 block 布局与关闭 mapping 排序，未剪裁、转换或修改源对象。两个全新 Solution 继续使用同一完整文本，Mixture、T/P/绝对 kmol 赋值顺序不变；没有缓存相。独立 AST 比较确认 `_loaded`、`equilibrate` 及全部其他原顶层定义未变，因此来源、状态、物性、元素/G 和资源接受路径保留。

实际 serializer 版本及布局设置进入 provider 身份，物理 model/source 身份不冒充改变。`ruamel-yaml==0.19.1` 在 equilibrium extra 中成为直接依赖；锁文件仅新增这两条依赖关系，已锁版本与分发文件未变。

完成的 serialize、gas、graphite、Mixture/初态阶段耗时立即进入 partial；后续失败仍由原 solve 异常路径冻结该前缀。正常快照复制计时映射，初末结果不携带可变计时别名。这些是完成阶段的观测耗时，未包含 `_loaded`、snapshot 或失败中断阶段的完整耗时，不应当成 prepare 的完整分解或新的预算证书。

实读作者 XML/log：24 项通过，0 失败/错误/跳过，日志 0.18 s。其中新增完整递归类型、键序、全部 float.hex、负零/NO 检查及三项非有限拒绝。独立完成 6 组被动 AST/身份/记录核对；未重跑该套测试。Python YAML 往返不等于 C++ 读入物性已验证：ROOT 原计划的一次 CLI 实际调用仍须保留全部原门，并报告实际结果，当前不声称更快。

最终 SHA：
- `src/sludge_sandbox/tp_equilibrium.py`: `c7b5914070fa55cd0dbf0e0c18230b7b708ddcdbcd57ff80009c00798e184376`
- `tests/sandbox/test_tp_equilibrium.py`: `61f1e104fbbb0e8aa85cc2ed0edac8648f2f4e15e94336ad58daed77e55e7f01`
- `pyproject.toml`: `02dae96cd7aab07eab8b97ac42bca35c5f10974a86542ba6749e402c88ccf342`
- `uv.lock`: `dfcc10d199da4ee91f048581d3b6bb0140800f61add2b23870c77f92f779c0d8`

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — 仅本次最小差异；无 EOS、性能或材料资格升级。
