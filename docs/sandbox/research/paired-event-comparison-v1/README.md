# 显式事件压力比较证据

`implementation-evidence.zip`：110 个成员，含调用守卫、helper、事件连接、案例及记录审核、失败/通过测试、安装 140 项测试 XML、65 模块身份、最终全部模块和相关测试。`implementation-manifest.json` 记录归档和成员 SHA-256。

`native-evidence.zip`：39 个成员，含事前计划、独立审查、真实短探针与完整事件实验、监督进程终态、完整 v2 记录、独立前缀账本脚本/旧版/审查/实际输出、最终身份复核以及带原许可和来源文件的水数据。`native-manifest.json` 记录归档和成员 SHA-256。两个包均检查无重复成员且 CRC 通过。

真实事件实验到达原 0.50032s 终点，两格分别耗尽，30 个接受步骤；独立前缀审计通过原门槛。报告见 [PAIRED_EVENT_COMPARISON.md](../../PAIRED_EVENT_COMPARISON.md)。这是制造材料和明确共享常数假设的结果，不是旧独立误差族通过或真实砖料实验验证。

独立账本可离线重放：解压 native 包，在 Python 中运行 `native/audit_prefix.py`，参数为解压后的 `native/event-attempt01` 目录。只使用标准库，不导入生产代码或 EOS。实际换目录解压执行已通过，见 `archive-replay-check.json`。

`native/probe.py` 保留当时用于原生实验的绝对临时路径；它不是任意机器可直接运行的安装脚本。新的原生运行应使用仓库案例 `data/sandbox/cases/reacting-wet-free-paired-events-v1.json` 和声明的依赖/来源环境。实际水运行的平台依赖仍受原批准清单约束。

原始 case/result 中的来源哈希和实际运行版本原样保留。保存数据审计验证算术、状态关联和内容身份，不重新建立热化学适用性或材料参数证据。
