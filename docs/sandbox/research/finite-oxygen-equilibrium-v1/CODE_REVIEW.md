# 有限 O₂/N₂ 薄驱动独审

**APPROVE：最终候选可进入原登记的最多两点受监督执行。** 审查仅限新 PLAN、run_finite_oxygen.py、ROOT launch.py、相关保存基线和有限制造验证；未改生产、构相、EOS、求平衡、安装或重跑旧基线。

最终 SHA：driver `596a8d52b08c415c944018339c44cb38eabe1fc8becab8160a730190fe9f24f4`；PLAN `4fdb331339e201448bb94bf14b5bcf6ea11dd140931ba038ff4b44d2023e109b`；launcher `38962a24c3a36fb96c4cd7e4e71f5e66683b1dadc975dde4c3f334192284db6b`。核心仍 `da382eea…14849c`。

[MEDIUM, 已关闭] 已执行的点可能误标未运行。

原 `main()` 在求解返回后先写 RESULT，再更新 comparison 行。如果第一次 RESULT 写入抛 OSError，最终 global failed/attempts=1，但该 λ 行仍是 not_run。独立 `test_result_write_failure.py` 仅制造这一 I/O 异常，实际 `RESULT_WRITE_RED01` 为 1 failed / 0.04 s；未调用任何模型。最终在调用前持久化 about_to_call，只有结果成功保存后才进入 returned_unchecked；下一点仍保持 not_run。作者运行同一独立探针，`author-tests/RESULT_WRITE_GREEN01` 实际 1 passed / 0.03 s，日志/XML已核读。原候选与失败保留，不以 I/O 异常承诺结果完整。

其它审查结论：

- `case_input` 两次都从原基线 b 出发，`D=bC+bH/4+bS−bO/2`、`ΔO=2λD`、`ΔN=2(79/21)λD` 是精确 Fraction；没有累加前点返回库存。实际 binary64 原子量来自已验收保存源。每点质量为0.704 kg加对应有限气体质量，分别约1.95840314/5.72161257 kg；driver同时与冻结独立算术逐项对应。λ0只读取、核算旧结果，没有 solve 调用。
- 原19种库存、气相摩尔分数和石墨碳份额全部保存，不删小正值。用实际元素组成与同原子量复算 `Mout−Min=ΣA r/1000`，传播原五元素数值门；新质量基准不错误沿用0.704 kg。原 module物性/元素/G/KKT/资源门、请求/来源/策略/实际加载身份均保留；没有新增期望产率、单调或石墨消失门。
- 第一个 λ=1/4 调用仅一次，由同一个 profiler 包裹；enable/disable的开销计入实际 solve_elapsed，完整 driver也计时。RESULT先独占保存，之后才进行profile、时间检查和外部派生；profile错误或未通过本层检查不会标completed，也不启动第二点。第二点不profile，不能把两点耗时差当作纯物理成本差。
- 三行 λ0/1⁄4/1保留基线复用、准备调用、已返回未验收及未运行区别。最终返回值/全局状态与累计attempt计数保留，结果文件不重写。模块10s、driver30s、监督40s+5s清理均未放宽；在途本地调用依靠现有进程组监督，不额外声称跨会话进程可完全回收。
- launcher明确隔离runtime、`-I`并去PYTHONPATH，先拒已有native01/supervised目录，冻结基线四件/原监督、四设计文件、公开源、当前core、安装包/依赖和自身执行文件。driver重读输入固定SHA，runtime实际模块路径/字节和原基线策略一致。新输出无覆盖旧Gibbs或Cedrone结果的路径。

作者原7项不同有限制造用例覆盖精确加料、旧库存拒绝、返回失败/超时、profile写失败和两点独立dispatch；本次只增加上述一个有意义的独立异常反例，未重复整套。最终修复只有调用前行状态保存及对应文字，数学、预算和物理资格不变。

21/79为虚拟有限干混合气，D是所列参考产品的形式计量需求，不是实测燃尽氧耗；N₂可参与候选化学。灰/Cl/Br/打印闭合差仍外置，不另加水。石墨不是实测char、H/G差不是炉热耗或放热、气相不是实际排放；材料/训练资格与完整烧砖模型仍未取得。profiling只能说明所观察到的调用成本，不冒称未细分C++内部已定位。

## Review Summary

| Severity | Unresolved | Status |
|---|---:|---|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | 1 resolved; original RED retained |
| LOW | 0 | pass |

Verdict: APPROVE — 可执行原限定两点计划，不声称实际新增结果已通过。
