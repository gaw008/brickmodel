# 首例验收驱动与监督器静态审查

**APPROVE（最终已安装包入口已静态核对）。** 驱动 SHA `1a4f6bc0ba8abd8d54917cee62e9ce960d7891da2ae401695d3139a9760eb5e5`；监督 SHA `cd5f2633402e6daddd0cb58c95f694740ab9e9ac38fb35c704b13aeb87ce5860`。

原静态发现保存在 `HARNESS_FINDINGS01.json` 和 `HARNESS_DRIVER01.py.txt`。驱动已修：物性阶段完成对象先写再检查全局预算；源哈希检查之后共用 finished；两格/两端点/一步 shape 和初始化→run 连续性显式门，消除 zip 截短的通过风险；从 old+faces 独立重算逐格 Nt*/U*/J，绑定真实 mechanical 库存与 inverse U 残差；逐项重算面/状态费用并核一次继承。原始能量闭合使用外面实际总 energy，分开展示 Q/H 时减 decomposition。

actual_vapor 字段与作者最终 API 对应，核 T/actual pv 并从保存的 μliq、μex、μvap 用原 fsum 重算 full μ；同时检查 peq−pv、给定组成 U/T/P 门及不升级平衡证书。无额外 EOS。非完成初始化和完整 run 均先保存；只有所有原门合格才正常退出。输出目录/文件采用 exclusive 创建，不覆盖旧失败；不承诺磁盘故障可原子保存。

监督仍以 argv、已安装 Python、-I 和独立进程组执行，100 s+5 s 清理；冻结当前来源资产、源树/安装包、IAPWS/NumPy/SciPy 及其元数据、scratch 实现/计划/驱动。仅约束原进程组，不新增逃逸会话隔离保证。最终驱动仅移除 implementation 的 sys.path 并切换主机 import 至 installed package；反向恢复这两处可逐字重建已审草稿。186 包文件与原冻结及安装相同；新 native 尚未运行，不以草稿测试或旧 native 代替。

设计旧 .05 s 建议现已保留并澄清为未执行历史；首个已登记例为 1 s/1 步，init/run 各40 s、驱动80 s；阈值/物性域未放宽。实际成功、耗时或微小蒸气池限制改善尚无本例证据。

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 open / 1 fixed | pass |
| MEDIUM | 0 open / 3 fixed | pass |
| LOW | 0 | pass |

Verdict: APPROVE — 有限静态方案；无 EOS/native 执行，无材料、收敛或完整 Goal 通过声明。
