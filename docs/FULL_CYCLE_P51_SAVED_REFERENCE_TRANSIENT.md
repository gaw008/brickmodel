# P51 保存13格短时生产前向：实际失败收口

P51 13格10秒生产前向已实际执行，但最终数值序列化失败（2026-10-02T16:55:17.793082+00:00）。1job/1worker/1attempt/1完整实例/1原solve_ivp，2537RHS含Jac内部调用、12Jac、21summary rates；stdout达t=10s，随后在原CLI119行json.dumps(result)发生bool对象TypeError，result.json未生成。实际16:50:12.055734至16:50:22.241066UTC，监督10.185289s/childCPU10.166340s，rc1回收、未超时，唯一900s截止17:05:12.055734UTC未重置、窗口关闭。原必要冻结输入/源/执行前文件及输出1274326B<2MiB；失败和收尾注记另实测。仅补接既有plain(result)序列化，当前源静态核对，0重跑。无法从日志恢复未落盘轨迹/质量元素完整U/四gas/Ca分相/熵/原生面数值，因此所有P51物理数值项未资格，不能由P50代替。根609=144literature465assumed0measured，旧602完整条目及科学核、名义12格mode0Ca0sampling0directoff保持。P50两项初态库存PASS撤销和原raw、P45净U/P34/P40/P44失败、名义余水0.135892078740%>0.1%保留；当前加密/八阶段/三方案反演UQ模型CLI及wholefalse保持。Git/Drive、恢复与历史容量分列，不自动P52。

生产入口 `scripts/run_saved_reference_transient.py` 读取科学启动前冻结的合法case和冻结源码，直接调用既有 `model.integrate()`。case先复制原P46/P44完整物理记录、Ca1及保存13格mode3，再整记录复制baseline max_step/rtol/atol；保持298.15K、10s、最大步0.1s、output0.5s及原BDF，不覆盖y0、不rebin或生成新网格。根7项本轮操作预算全部policy/assumed，旧602完整保持。

实际1个make_cycle实例、3个继承构造入口；1个原solve_ivp入口，2537次真实RHS含12次Jac所调用RHS。原native summary的21次rates/transport/mechanics调用已发生，同次原生gas/水/携能/热通量观察已接线。stdout t=10s支持求解到声明终点；其后最终JSON序列化失败，所有这些数值没有写出。不能声称面有分辨非零输运、守恒通过、Ca相预算通过或严格库存/熵非负，不能从旧P50或P46填充本轮数值。

原始stderr、stdout、调用字典、冻结执行CLI和源输入均留在 `runs/full-cycle/p51-saved-reference-transient`。`failure.json` 是事后按原stderr制作的失败注记，不是伪称原异常分支输出；实际异常发生在原try/except范围外。可能是NumPy布尔类型，traceback没有给出具体对象路径。源只补接既有 `plain(result)` 转换；当前修正版语法核对、未执行、不得冒称修复已动态通过。唯一attempt永久消耗，不修后再跑，不延截止。

质量/元素/完整U/四gas/Ca逐相累计/累计熵/严格signed库存/原生面和终态本轮均未资格；没有新分母或阈值，零预算null/passfalse原政策保持。完整阶段/空间时间加密/三方案/反演/UQ/模型CLI仍未资格。P50两项库存错误PASS撤销、P45净U3.039630570e−9>1e−11、P34 30/81、P40峰温网格7.33335%、P44 CaO3/9及directmesh3.01853436%等历史失败继续保留。名义余水0.135892078740%>0.1%无新尝试，0实测、无目标砖L，whole_project_complete=false。

科学启动16:50:12.055734UTC、回收16:50:22.241066UTC，监督10.185288625s/childCPU10.166340s；行政声明至本记录585.988s，分开记录。必要输出预算包含冻结源/输入/声明/实际计数及失败证据，未保存原始大场；最终实际字节另见交付收据。

本轮源/root/说明/矩阵正常Git和原目录必要Drive小增量状态见 `runs/full-cycle/p51-saved-reference-transient-final-delivery-state.json`。上传元数据不是字节恢复，压缩原件保留；历史/独有Git/20GB与GitHub容量警告仍未通过。不分配或启动P52。
