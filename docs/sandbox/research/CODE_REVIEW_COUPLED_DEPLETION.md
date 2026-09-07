# Coupled depletion attempt02 独立只读审核

结论：APPROVE，限定为本次两格制造材料/输运/动力学、真实水物性耦合的已保存轨迹及数值账本。没有重跑EOS、温度反解或积分。本审核不将事件细化指标当真实ODE事件时间证书，也不将4毫秒范围的制造算例当真实污泥湿砖完整周期。

绑定快照：

- 结果 `coupled-depletion-attempt-02.json` SHA256 `15574aa2e2811182b64759aa1fd733f47924d2ce5c3ee7a151fe523577465497`。
- `tests/sandbox/test_depletion_coupled_host.py` SHA256 `fb29fdd1b37ca5b8939f186eab93da0d727740d494fde823454d63196f94efed`。
- `coupled_depletion_run.py` SHA256 `25692c1c309e04d689ec44f15d917d9b4cab8ad20c20cfe61ae0ab0e4ab3d647`。
- `src/sludge_sandbox/depletion_integration.py` SHA256 `afff823dd48ca2bc4eeb650bf2e7ab4bf12a70d60f45a32ce6bc35091d0b3355`。

运行原记录：completed，444.5252291669967 s墙钟，494次evaluate、58试探panel、3拒步；42个已提交step、43个状态/时刻，终时刻1/256 s并包含程序节点1/512 s。试探panel包含未提交路径，因此58不应称为58个物理轨迹步。JSON中前后82个源码/test/runner哈希完全相同；本审核逐项重读当前对应文件并重新SHA256，82项全部匹配。

## 独立重算方法与实际结果

直接读取JSON数值，对每个已表示float使用Fraction(float)，对JSON保存的有理数字符串使用Fraction(string)。未调用root审计函数；独立脚本在/private/tmp/audit_coupled_json.py执行，只读取文件，没有EOS依赖。步骤如下：

1. 验证states/times/steps长度、时刻严格递增和每step的start/end严格等于相邻保存时刻。
2. 每cell、每库存列，独立累计 `face_left − face_right + reaction`；只在event对应的唯一terminal_panel添加液列 `−δ`、水汽列 `+δ+actual_storage_residual`。JSON已失去Python对象identity，以完整terminal字典与唯一对应step内容相等及事件end时间绑定。
3. 独立核对δ等于修正前Nl，理想增量等反，实际水汽写回差等于record.actual增量，residual等于实际减理想；独立sum核对signed/absolute/correction/eventcount totals。
4. 每步与从初态累计两个层级核对全部14个库存和两个U；U只由相同面能量差与cell_work累加，不加潜热/反应热。最后独立有理数累计数组与JSON cumulative_amounts_mol/cumulative_energy_j逐项精确一致。
5. 两格系统账本扣除数值修正及外边界物种通量后，按显式C/H/O/惰性载气向量与制造摩尔质量核对守恒；另以两格总U对最外两面能量/功独立核验内部面抵消。
6. 各cell在其自身事件时刻及之后的每个保存状态Nl严格0，不仅终态0。

| 实际最大残差 | 独立复算值 | 原审计上限 |
|---|---:|---:|
| 单列单步/前缀库存 | 8.275681604024994e-18 mol | 1e-10 mol |
| 单格单步/前缀U | 6.612767160236819e-13 J | 1e-7 J |
| 系统元素 | 1.123259811279456e-17 mol | 1e-10 mol |
| 系统质量 | 1.534083555950382e-19 kg | 1e-12 kg |
| 系统U与外热/功 | 3.179949805510366e-13 J | 额外独立核验，亦低于1e-7 J |

独立重算与原runner给出的前四项逐值一致。库存与能量实际残差也低于更严格的原普通积分绝对容差1e-12mol/1e-8J，不需要借宽松审计阈值解释通过。两次paired修正合计8.257945042676029e-22mol，signed与absolute水汽storage残差均2.329966798002725e-22mol；所有原有理数记录精确匹配，未把paired库存修正误称水的真实物理生成。

## 两事件与共同物理时刻

cell0事件0.00028837917551549386s，公共比较时刻0.0006820793569047581s；cell1事件0.0010885050887795723s，公共时刻0.001953125s。先后次序清楚，均早于最终1/256s。第一轮公共视窗曾记录 `common_time_horizon_reduced`；没有隐去该操作或假定任意公共时刻均可跨越另一事件。

两个事件均保存连续两次comparison_pass。最终比较记录分别为：

| cell | 时间差s | 库存差mol | U差J | T差K（含所声明反解界） | P差Pa（原资格） |
|---|---:|---:|---:|---:|---:|
| 0 | 1.1661234558118952e-12 | 1.3779476505274913e-14 | 1.9051640265388414e-9 | 6.266238378804663e-8 | 0.005977635107230723 |
| 1 | 1.5643360103780088e-12 | 1.5590827240341554e-16 | 1.864464138634503e-11 | 1.0906771488782884e-7 | 7.414591888262506e-7 |

逐项低于事前1e-7s、1e-10mol、1e-6J、1e-5K、1Pa门槛。此处独立检查记录数值与门槛，没有重建未保存的粗/细试探轨迹，所以不声称独立重新算出了这些T/P差，也不声称P界已含完整δT传播。

## 原test/runner覆盖及可追溯性限度

原test实际运行审计明确检查初态两格均wet、两个有序事件、最终dry模式、原K=(1e-6,1e-6)全程对象一致、safe_inventory_fraction=.4、实际液共享面累计非零、反应产物/反应物变化、最终热边界与反应仍活跃以及最终液流0。JSON audit_status=passed及绑定源码证明这些assert实际经过；但JSON刻意不序列化operator，因此本次纯JSON审核不能独立读出K/provider对象或最终全mechanism diagnostics，只能区分“原运行已检查”与“本次独立重算”。

原审计未直接断言最终cumulative数组精确一致，也仅断言最终Nl0；本次补充的只读核算覆盖这两点。原修正绑定按step.end_s检索，而非Python terminal_panel identity；本次进一步核对完整terminal内容唯一对应。未发现这些覆盖差异在本结果中造成错误，无需为此重跑昂贵EOS。

runner保存前后源码/test/runner哈希、完整已提交轨迹/事件/细化摘要和所有失败，拒绝覆盖旧证据；它的82项哈希集合不包括全部原始物性源资产，不能把sources_unchanged标签解释成对每个外部PDF/JSON资产前后均逐字节核验。物性来源身份仍依赖已有source-gated加载器合同。后续增强可独立序列化K/provider语义identity及输入资产哈希、完整对比路径；这不是本次数值账本通过的阻断项。

没有修改源码/tests/runner、没有扩大已有数值/物性资格、没有重新执行积分。
