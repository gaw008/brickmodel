# CLI 薄层独立审查

结论：APPROVE。审查范围为用户示例入口及其独立监督计划；未运行应用、EOS、native 或重复作者测试。

- 必需参数、正有限载气和分量下溢检查先于物性导入；`open("x")` 拒绝已有文件和链接。已核读作者 12 项非 EOS 检查原记录。
- 来源构造、325–338 K / 90–110 kPa 域及 U 1e−5 J、名义 T 括区 1e−6 K 等策略与已审查 case 一致。默认载气 0.00032 mol 按精确 21/79 再投影，记录实际分量与残差；不将其末位差异隐藏为旧 case 的逐字重放。
- 先保存输入、来源、实际初态/点，再调用 flash；保存返回对象或具名失败的 trials、counts 和最后返回 provider/context。总水取实际 Nc+Nv 的 Fraction；初态目标使用完整 U，无额外潜热。
- 原 MEDIUM 提示问题已修：序列化失败保留原字节的说明已收窄，I/O 故障明确“输出文件可能不完整”。写入机制不承诺原子恢复。`FINDING01.json` 写于并发修正后，所记候选 SHA 是修正后字节；原问题对应 53fda7…ed929，此时序说明见 `FINAL_READ01.json`。
- 监督器实际命令使用已安装 Python、`-I` 和新入口，60 s + 5 s 清理，新增 CLI 与计划输入身份；旧结果不会充当新 CLI 实跑证据。名义平衡、未知温度证书及材料/训练 false 边界保留。

最终入口 SHA256：`fdb28b5943bc61da6a7d2fa48d4e29556d921825f8287c1effe375743911cc73`。6 组静态检查完成；完整关联文件 SHA 见 `FINAL_READ01.json`。实际 CLI smoke 尚待 ROOT 独立执行。

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 open / 1 fixed | pass |
| LOW | 0 | pass |

Verdict: APPROVE — 仅通过本次有限入口代码审查，不代表完整 Goal 或材料资格完成。
