# 诊断失败时的状态保存与最终结果查询

旧 `test_diagnostic_failure_retains_accepted_solver_states` 在原基线实际失败：虽然末端诊断失败且没有 final_snapshot，测试仍要求 trace 把已接受库存返回为最终结果。生产 `trace_run` 及 `test_partial_run_trace.py` 的现有合同明确禁止这一替代。

本次只修正旧测试：直接断言已保存 `integration.states[-1].amounts_mol` 等于原完整库存；另断言 trace 的 value 和 result_pointer 均为 null，原因是 `final_snapshot_unavailable`。没有更改求解器、生产查询逻辑、库存值或验证容差。

实际执行 `PYTHONPATH=src /private/tmp/brick-water-backend-probe/venv/bin/python -m pytest -q tests/sandbox/test_run_service.py tests/sandbox/test_partial_run_trace.py`：47 passed / 0.65 s。原失败日志与此次 JUnit XML 保存于本目录，原始字节校验见 manifest.json。

独立代码审查由 Tesla 完成：核对直接库存断言未削弱、查询断言与当前生产及部分运行测试一致，并读取 XML 确认 errors=0、failures=0；结论 APPROVE。该审查仅涉及此测试合同修正，不是物理材料验证。
