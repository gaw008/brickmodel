# 真实水终态保存结果独立审核

输入 SHA256 `0a242ef8c239226b68ee085abe51641e1b95165c464f7edb175454555543fa49`。174项显式主审核断言通过，0.085850s；仅标准库读取唯一终态JSON，无新EOS、模型导入或求值。32实际source callbacks逐项对应初始探针1+seed2+approach11+shifted2+两条dry各8；32预估字段单列，未作为实际计数推断。4显式provider构造锚点及初U1次核对；不宣称所有底层内部操作数。

两条真实路径均从正湿态经完整source终端前缀与有界写回至Nl=0，并各有1个实际dry接受步。两事件时刻分别7.370438425601268e-7、7.370438456490419e-7s；共同终点1.1055657679587435e-6s；干态推进分别3.685219253986168e-7、3.685219223097017e-7s。两路径prior共用9轮，再追加18轮，总27轮不超32；原四库存多项式/实际prior绑定通过。保守绝对根区间距离1.0296383572155336e-14s，通过原时间门槛。

从原始初态检查粗3/细4个前缀，完整N/U、终端精确affine积分、实际writeback、水/H/O/N/流体质量记录逐项一致；两次rho=0，不冒称该实际例覆盖非零汽存储舍入。原普通IntegrationPolicy与事件专属roundoff预算分别核对；固定kg不纳入mol动态，写回U不变，材料资格false。

event/common两组N/U/T原门槛通过，报告压力均0.0020266532580509866Pa，完整dry箱条件压力均0.002035256129739854Pa，超过原1e-4Pa，因此两组P/条件P均false，numerical_event_accepted=false，原candidate_comparison_not_certified保留。

压力主导项：名义ΔP=0；两端可用体积误差贡献0.0020266506579743617Pa，占报告界99.9998717059%；原fluid半径和2.6000766247855945e-9Pa；总半径相加的binary64投影+1.3799730082130278e-19Pa；完整T箱传播/保留包络另增8.602871688867286e-6Pa。原eV=1e-12m³保留。独立重建NgRT/V角点、原名义P±(eP+L eT)包络及完整T/P域，未抵消共享体积误差或放宽门槛。

附加压力分解脚本首轮错误地要求 binary64 总半径精确等于两个未投影Fraction分项之和，触发AssertionError；原脚本native_pressure_breakdown01.py和NATIVE_PRESSURE01.log已保留。修正为验证实际一次float投影，并显式保存投影差；NATIVE_PRESSURE02.log和NATIVE_PRESSURE_BREAKDOWN.json保留精确Fraction。这是审核器假设修正，没有修改任何模型/原结果或重跑EOS。主174项审核首轮通过。

结论：实际条件来源湿→干执行及原始失败门槛证据完整；尚未通过数值事件比较，也不是材料验证。closed原生不证明程序加热行为，后者已有单独制造例证据。

## 文件SHA256

- audit_native.py: `eb4f0aad94cf239247d61571f6ce0ef31735b9cad2b7168e4273ce7e923a426e`
- audit_manufactured.py: `3dda60d3d042f26bc341ab5b967fde002fe72c4700d09fbca91c3d348299712d`
- NATIVE_AUDIT_RESULT.json: `8058f74e30850414ce197fcc7f77c35fae0237bddcf261346d9c1e4172e1c99a`
- native_pressure_breakdown.py: `add51893754dcebfdacafc3c8db342675b715dea3557a98eb4f774379221d9dc`
- NATIVE_PRESSURE_BREAKDOWN.json: `4ff4d72f13c181047dbb566f8171473c47ace444ca715e54c8bd4c074a0f099f`
