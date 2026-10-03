# P84 最终 cooling_hold 比较接口：仅静态实施

新增独立 producer54 `src/sludge_vme/models/full_cycle_cooling_hold_comparison.py`，原53源码、strictloader、CLI及758完整参数逐字节/逐记录保持。接口已完成源/AST/不执行的source-compile核对，本轮 production import/load/ctor/initial/decode/values/RHS/Jac/ODE/rates/helper/gradient/dynamics/projection/summary/predict/fit/UQ全部0，未来数值窗口未采用。静态实现、Git和Drive交付不等于动态或物理数值验收。

## 数据可用性及三项原产品定义

原定义见 full_cycle_gas.py:1225,1246,1287–1291（thermoelastic沿用该summarize），full_cycle.py:633–636给原时间/网格验收公式。

| 项 | 原定义与单位/权重 | 当前输入能提供什么 |
| --- | --- | --- |
| porosity | 每格 native_pore/bulk；用终态bulk作np.average权重，单位1，数学上等于sum(pore)/sum(bulk) | P78 coarse162000s、P80 refined154800s有每格pore/bulk；未来新final inventory也给它们。代码用原weighted表达，不改成等格平均或含液水的total_pore_volume_fraction。 |
| residual_carbon_kg | sum_i[(organic_i+char_i)*atomic.C]，单位kg，全域元素碳质量；不除干质量、不用char分数代替 | 已存两点都含organic/char mol，根atomic.C为0.0120107kg/mol/literature。未来仅已存数组与新inventory直接归约。负号保持，不能把原残碳很小/负值经floor裁零。 |
| shrinkage | 原summary为1-total_bulk_final/total_bulk_first，单位1；不是局部收缩等格均值 | P78新declared初始参考有每格bulk，本接口共用该参考算条件化收缩。P68旧t0的原native y未保存，原历史t0收缩值不可恢复；输出available=false/null的独立历史t0项，并标注新参考条件。不能用geometry.b0代替actual unpack初始bulk或声称旧t0已恢复。 |

已存点没有直接名为这三个summary产品的字段，但前两项所需实际基础库存/体积齐全；第三项仅条件化共同新参考可用。coarse/reference不重新decode、potential或summarize。P80 refined cooling库存只作未来本段起点的已存U/S与累计账本，不能当refined162000s终态。本轮不计算/伪造尚未存在的refined final产品。

连续peak_temperature_difference_k不可从这些保存端点得到：原span还使用surface_T、center及中途样本，两个输入没有完整路径/这些中途量。峰overpressure/连续熵或源域也不授PASS，网格未加密。接口不回拼未保存轨迹、不调用summary暗增所有rates/unpack。

## 原比较分母与严格失败边界

三个终态保存 coarse_raw/refined_raw/signed_refined_minus_coarse，不改变原库存。相对差为abs(refined-coarse)/max(abs(refined),原root floor)，严格小于原root acceptance.convergence_relative=0.02。原floors：porosity0.01[1]、residual_carbon_kg1e-7[kg]、shrinkage0.001[1]，全部assumed/policy完整记录保留；它们只作比较分母，不是库存floor、零点修复或新阈值。本地两冷却段终态差门槛即使满足，也不等于原全周期run_acceptance通过。

两输入已存strict_nonnegative_inventories均false。未来两端raw/minimum/strict布尔独立输出，本接口不clip/seed/abs库存，不改linearchar/gaslog/Ca/OH或热源。CaO零预算null/false/undefined、P45float、全部旧science与资源FAIL保持；原干燥0.1358920787402553%>.1%仍FAIL，没有新工艺尝试。P83暂停jointBE和同态Fleft/Ru障碍/fullU_S未证明保持，没有新理论扩展或坐标修复。

## 明确的独立条件及 source53→54

在根 `conditional_numerical_conditions.cooling_hold_half_step` 单独声明30s，[30,30]、assumed/policy，只适用于原最后cooling_hold。原758 parameter records的60s、rtol1e-5、atol1e-7及所有物理/工艺保留；旧cooling_half_step条件和cooling_time_refinement整个合同原样，不能以旧cooling-only授权扩到hold。

未来strictloader先读取真实P80 saved/effective cooling30s完整config和原37context、partition/phase0/liquid_reference、branch、y275；不传当前root config替代原保存config。之后才复制saved config并将完整独立finalstage30s记录应用到同一target；从P80数值value看30→30，但记录来源/note明确变为最后阶段条件；从其保存的原60s case看是60→30。分别保留原root scientific identity（完整758记录及原species/reaction/stage/source物性合同）、完整P80 saved/原60s/effective三config与原引用路径/大小、明确数值差和独立条件出处。

实际P80完整source53路径在根新合同逐条列明，output_source_paths是这些原路径加唯一newproducer完整路径54条。原root.native_checkpoint.source_paths50和strictloader不改。输出config与source_version都宣告54条完整ordinary源文本；输入53文本由原strictloader逐字比对，保存其显式53路径与输出source_version相同53键的完整文本引用，不重复大块文字，也不只按数量凑54。原P80物理源53完全保持，新代码是独立54身份；parent revision仅祖先，不能称某旧blob执行。

## 未来最小执行图和未采用完整计划

固定读两个完整输入：P80 `runs/full-cycle/p80-cooling-time-refinement/refined-cooling.json`，2230086B、实际154800s/y275/source53/context37；P78 `runs/full-cycle/p78-endpoint-ledger-acquisition/endpoint-ledgers.json`，483536B、已存coarse162000s及新declared初始参考。未来仅从真实154800s继续同一原cooling_hold到162000s，原绝对times/温度/气体program和累计原点不重置。

正常源cwd入口（此处只是命令文本，本轮没有--help/import/入口调用）：

```sh
cd /Users/wanggaoying/Research/brickmodel-github/src
../.venv/bin/python -m sludge_vme.models.full_cycle_cooling_hold_comparison ../parameters.full_cycle.json --out ../runs/full-cycle/p85-final-cooling-hold-comparison
```

未来公用调用预测：1 strictload/逻辑ctor、0 initial、1原solve_ivp BDF、新端点1、native decode1、complete value1、原interval_ledger1；baseline/reference decoder/value/summarize重求0，extra publicrates/dynamics/grad/projection/summary/predict/fit/UQ0。stored-inventory三产品归约两次只是保存数组纯算术；内部RHS/Jac报告existing counters和solve nfev/njev/nlu，内部rates/各thermo/Newton次数未独立测量，不假报为1或0。继承constructor三class entries及postdecode8Newton等仅静态源图预测，不是本轮实际计数。

原interval_ledger复用P80已保存start inventory和P78 reference，只将start native_y普通JSON列表恢复为numpy数组供原Sslot差，其他baseline/reference已存U/S原样。一次新endpoint_inventory同时取得native pore/bulk、全部库存和完整U/S，不暗加unpack/value。原有符号反应/边界/外压功/熵槽和zeroBudget规则保持；energy ptp只是提供的两端，不是路径最大值。

未来仍须正式独立采用后才launch：唯一worker/job/attempt，120s从首次launch至最终reap含读取/导入/JSON；四science文件case-parameters.json、refined-cooling-hold.json、stdout.log、stderr.log合计<=4194304B。fresh complete67108864B独立完整gate计入54source/runtime、两个fullinputs、root、实际cases/freeze、old/stagedGitblob、results/reports/adminformal/archive/self，原八reserve27262976B加extra2097152B不减。任何错误/timeout/输出或budget超额关闭并reap，0retry、0步长/容差搜索。输出大小预测只根据必要已存serialization组件，不是实际输出保证；未来gate与live/reap计量必须新做，不能借本轮PASS或旧headroom。完整可执行计划/源图/单位元数据在JSON和future-execution-proposal.json。

这只比较原hold133200s之后两个冷却阶段60→30s对三个终态量的影响；前六段未加密，完整time/grid/continuouspeak/三方案反演/独立离散U_S/实材qualification未完成。0measured、assumed/synthetic及高温portlandite/calcite/H2O黏度解析外推、旧24UQ固定3.75e-14m2范围和wholefalse保持。

Git原分支普通后继、Drive原folder一次必要静态增量、元数据与实际恢复0及历史20GB/GitHub容量分列finalreceipt；原唯一压缩源与历史均保留。一次行政Git读取cwd错误保存并纠正，不是科学尝试/权限reviewer拒绝。实际静态开发/admin耗时另记录，sciencewall/CPU=null；本轮静态实现不分配下一数值窗口。
