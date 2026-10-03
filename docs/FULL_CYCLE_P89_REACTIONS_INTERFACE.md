# P89 原反应段显式合同接口：静态实现

当前只完成已有producer55的最小泛化及静态出处、输入兼容性和资源预算。没有生产导入或数值执行，科学wall/CPU为null；全模型仍未完成。

新调用必填根合同：Python `compare_sintering_time(parameters, out, contract_key="reactions_time_comparison")`，CLI必填 `--contract reactions_time_comparison`。原烧结合同仍可显式选择 `--contract sintering_time_comparison`；旧55无此参数的调用方式需更新。函数和模块原名称保留，所选阶段与出处在输出显式记录。原54物理代码、严格loader和其CLI逐字保持。第55份代码与旧P88 frozen55不同，不借旧55身份；旧P88四科学文件及闭窗收据已与完整普通字节副本相等核对，未SHA/恢复。

P68实际heating97200s、275原生量、12格、37上下文；它的50份源码子集与当前原54匹配，P71的51份亦同，两输入均排除producer55。758项完整参数及原60s/rtol/atol/所有旧条件合同相同，144 literature、614 assumed、0 measured。未来只用P68 heating输入到reactions115200s两条原BDF60/30短轨迹；P71仅存端点，所以旧端点不能作为原120s采样峰基线。所有动态接口行为目前未验证。

P89输入heating的char12格全正，最小1.377360372932039e-10mol；OH已有负0/6/7/11，最小−1.913174096650212e-18mol；CaO已有负1/2/3/4/5/8/9/10，最小−1.8012087255484632e-18mol。已存reactions输出char负0/2/4/8/9/11，最小−2.179584804450866e-22mol；OH负0/5/6/11，最小−9.349021574400408e-24mol；CaO此端点全正。两个端点原生向量与P78对应向量相同，原field3/5/9标签明确；纯JSON只取已存切片/库存和signed差，未计算exp、pool、解码或库存重建，不能定位未保存时刻/唯一成因/宣称正性保证。零初始CaO预算relative=null/passed=false保留。

未来各151个原120s绝对采样，逐点完整cell、原rates.surface_T和原center_temperature取max−min后取采样峰，1K原floor和strict<0.02不变，不证明连续峰。未来公共调用为2严格50加载/构造/BDF/新端点decode/value/interval及302rates和302center，0initial/baseline/reference重求/summary/fit/UQ。67节点完整源码方法/分支图及61实际选中rates方法已重新静态生成；机械Newton8×302=2416、surfaceNewton6×302=1812、完整elastic_response10×302=3020，其中解码8×302=2416，热力学逻辑604/MRO entry1812、externalcaloricintegrals1812。完整原反应/水/气体/孔力学/热传递路线见JSON，不以解码次数替代完整rate调用。内部solverRHS/Jac/nfev/njev/nlu/低层primitive当前未知，不作测量声明。

共享exact supplied275起点、每个solver的完整actual275t0及signed275delta分别保存；actualsolver t0不能用input+delta重建替代。采样0恢复原输入的同时保留实际solver t0。P78新声明initialreference只用于原归一化/条件收缩，不恢复历史P68t0。source55和context共享一次，原P68 config和两completeeffective configs各一次，完整input50字典作为完整55显式子集保留；输出schema不是原strictloader checkpoint。

四科学文件静态估算 **4,082,629B/4,194,304B**，余量 **111,675B**。精确共享case layout **2,463,197B**；未知数值、ledger/solver元数据和logs均另分配，实际输出未测。独立240s从firstlaunch到finalreap：旧P71仅一次60s端点launch/reap35.968494625296444s、solver35.34001291682944s、RHS9701/Jac56，仅用于政策推导；1份coarse+3份refined+2份import/302采样/写出分配，6×旧耗时215.81096775177866s向上定240s，assumed上限，不是保证。未机械继承旧P88 300s。

完整未来64MiB枚举见候选full_allocation：现有输入/运行时/源码/规则/所有实际使用copy/self/old新Git表示、future source+root冻结、四输出、未来新Git/admin/一份增量archive均计，原8项27,262,976B及extra2,097,152B不减不退款。未来新Git4MiB/admin2MiB/archive2MiB是独立政策cap，其值/单位/range/source/status在根合同。未来增量只打包必要新内容，原输入/旧输出证据沿用本P89来源记录，不删证据。实际未来预算必须fresh完整gate，唯一失败close/reap/0retry，不搜索参数容差步长seedclip，不额外求值或加guardrail。

未通过事项保持：名义干燥0.1358920787402553%>0.1%；非负库存失败，旧P88 refined更负与共用起点zeropeak保持；CaO零预算nullfalse；P45与资源失败；高温portlandite/calcite/H2Oviscosity解析外推assumed，directsynthetic仅290–350K；旧24UQ固定渗透率3.75e-14m²不资格化全部新机制。全前六/全周期时间网格/三方案/反演/材料实测仍未完成，不以本接口或元数据备份授PASS。

本轮静态行政读取有checkpoints名称、points列表索引及cooling_refinement名称错误，未涉及科学调用；完整失败开发脚本保留，一次名称修复后成功，实际错误和限制在JSON。static/admin实际wall另记录，sciencewall/CPU=null。变更9文件：producer55、根参数、spec/report/plan/GOAL、P89 MD/JSON、final acceptance。证据 runs/full-cycle/p89-reactions-interface-static。Git与Drive一次增量/名称大小父目录读回另receipt，0下载0恢复；metadata不等于实际恢复，不删唯一压缩原件。历史20GB及GitHub容量仍未解决。

最终静态复核：原54/758/全部旧根项和旧条件相等，fresh AST的61方法每次及302总数、center和external counts与协调独立出处相等，已存库存数组亦相等。最终独立未来full必要bytes、余量和真实静态行政wall以JSON/candidate实际self枚举为准；未来另做freshgate，此快照不授数值执行。sciencewall/CPU=null。
