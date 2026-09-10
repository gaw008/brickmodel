# 终态制造结果独立审核

输入 SHA256 ab3212f82333ae2d84219d15a676617f302397e46c21d095e604761ea89dad62。直接解析同次 pytest 返回对象的 closed/programmed 两例；144 项标准库 Fraction 断言通过，0.066503 s。本次审核无失败/重试，无生产模块导入、EOS、模型求值或测试重跑。

核对：旧时钟从 [0,H] 独立重建全部二分，液三项与源共享 phase 投影一致，写回液→汽实际量及 U 不变，原 correction/gross fraction、storage/element/mass 单项及累计门槛；全链原始初态的 represented/full-terminal N/U，实际水、H/O/N元素及流体质量余额与每个保存行逐项相同。四次写回 rho 均为0，因此这些实际例不覆盖非零汽存储误差（先前制造算术反例另有覆盖）。

此前提出的同面板细化链绑定缺口已修复并核实：prior_clock等于原 refinement clock，四库存多项式相同；reused 深度=order+choice追加+prior比较追加，最终 depth=reused+terminal追加且不超原cap。最终closed两路径深度25/26，programmed25/28。

closed粗/细各1个实际dry接受步，共3/4个审核前缀；programmed粗/细各2个dry接受步，共4/5个前缀。programmed两路径真实接受时刻都包含精确F(0.0002)炉程节点，dry事件→共同末端U与T均有非零变化。

闭域根时间保守距离5.240119742399723e-12 s；programmed为5.851467045675877e-12 s。两例各event/common的N/U/T/报告P门槛全部通过。独立按原气体库存、R、T±eT及V±eV角点重建dry完整压力箱，与保留名义P±(eP+L eT)取包络；同时核对全箱T/P域。closed两端比较压力界均6.2742532133401276e-6 Pa；programmed事件6.316107793519926e-6、共同端点7.062228831110973e-6 Pa，均通过原P门槛。

结果可称原声明模型条件下的数值湿→干事件通过；仍是人工水/明确制造体积与系数，不是native EOS新验证或真实污泥材料认证。source_certified/material_qualified保持false。普通段full字段对应已保存普通步账本，terminal才额外核对精确仿射积分；不宣称整条ODE连续真误差界。事件元素/质量专属门槛与普通段IntegrationPolicy余额区分保留。

## 文件哈希

- audit_manufactured.py: `3dda60d3d042f26bc341ab5b967fde002fe72c4700d09fbca91c3d348299712d`
- audit_cases.py: `22296e8e43154174d516727948fbe3997cabaf93c22daf7627dac0e5b0f1240b`
- MANUFACTURED_AUDIT_RESULT.json: `7d4593c50270f04490794630740ab43e222e2dd9e3227eae1bbb3fa23981efc1`
- 审查时源码 source_terminal.py: `007754efd6a1da47fa8dbb5cdbaff059b8f682d9a4be8b03b0335d71ccce925f`
- 审查时源码 source_dry_transition.py: `e56331a6b9dcc89df4319d9534dea992484f81f29bc188aea09d6b2d090a6abe`
- 审查时源码 source_dry_pressure.py: `1404797b0f9e4d7f8154d8d5937d745f9754b3e512b57833185f581152be33d8`
