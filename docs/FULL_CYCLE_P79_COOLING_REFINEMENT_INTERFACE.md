# P79 冷却时间步加密接口

仅完成静态实现与源码、AST、现存 JSON 审查；未导入或运行生产模块，所有科学调用实际为 0。完整模型仍未完成。

独立新增生产入口，原 52 源码逐字节不变，原 758 参数不变。根文件另列 conditional `cooling_half_step`：max_step=30 s、范围[30,30]、policy/assumed。原基准60 s、rtol=1e-5、atol=1e-7及材料、边界、八阶段绝对时间与气体程序保留。

未来先通过原 strictloader 恢复 P75 实际 hold 133200 s 的完整 y275、37项 numeric、initial_partition、phase0、liquid_reference，再复制保存案例并应用条件记录。`model.config=effective` 后由原 `model.p(target,"s")` 取得求解器 max_step；case-parameters 与 native bundle 均保存相同完整有效配置，原保存案例另有完整配置、来源和数值差异元数据。历史 source50/51 不弱化，新输出身份明确列原51、ledger52、新producer53完整文本。

未来只求原 cooling 至154800 s，一次 BDF 后一次新解码、完整势值与区间账本。P78 保存的 hold、coarsecooling、declaredinitial 行直接作为数据使用，势值不重求。JSON hold.native_y 转为 ndarray 供原熵账本 slot 相减；输出数组沿用既有 serializer。原U/globalS/逐格F和相变反应热一次计入、signedwork、原分母及 undefinedzero 保持；initial归一化仍依赖P78新声明初始参考，并非P68历史初态恢复。端点ptp不代表轨迹极值。

已存负库存只按原字段分类：char/OH线性库存、calcite/Ca_pool分数坐标、lime池差重建。报告保留各阶段数量和最小原值，逐cell原存条目仅保存在本次run。分类不能证明单一成因，也没有修复非负、裁剪、加seed或改变容差/门槛。

静态调用图支持未来1load/constructor、0initial、1solve、1decode/value/interval。constructor继承3入口、postsolve解码8次原Newton等仅source forecast，未来solver RHS/Jac/rates及其内部工作量未知；本次实际全部0。语法审查不等于运行、序列化或物理数值验收通过。

下一最小候选见同名JSON与runs/full-cycle/p79-static-cooling-refinement/future-cooling-time-refinement-proposal.json：现存离线venv CLI、两完整原输入、source53、120s首次launch到最终reap含JSON、四science合计4MiB、新完整64MiB gate及原八reserve27262976+extra2097152。candidate保持proposal_not_adopted，当前科学窗口0。降低、不变、更坏都照实报告；不以局部残差比较授全周期/最终cooling_hold产品/峰温/网格/材料PASS。

名义干燥历史0.1358920787402553%>0.1%、CaO零预算null/false、高温三源assumed延拓、directsynthetic290–350K、P34/P40/P44/P45/P50撤回/P51/P58/P60/P61/P63及全部旧FAIL继续保留。原24 UQ固定渗透率3.75e-14 m²不能验证新机制。待实测、最新全时间/网格及三方案反演验收未完成。

本次八变更路径：新增producer、根参数、spec/report/plan/goal、P79 JSON/md。Git普通后继、Drive增量元数据与actualrestore及历史存储独立记账，最终实际收据另存本次run，不循环提交或归档收据本身。
