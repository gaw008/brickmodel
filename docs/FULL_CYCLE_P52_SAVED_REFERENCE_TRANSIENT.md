# P52 保存13格短时生产前向：JSON输出修复完成

P52 JSON类型转换已完成一次真实13格10秒生产前向并保存结果。实际2026-10-02 17:03:21.432530至17:03:32.613455UTC（洛杉矶10:03），11.181062291s/childCPU10.998613s，rc0回收；1job/worker/attempt/constructor/原solve_ivp，2537RHS含12Jac，另21native summary rates。唯一900s截止17:18:21.432530UTC未重置，窗口关闭。必要冻结源/输入/实际输出初测1682007B<2097152B。质量/元素/完整U相对残差6.822906222e-10/7.562083972e-9/1.578059999e-8，四gas最坏9.353029983e-6，native累计熵3.208755776e-9，均低于原0.001门槛。Cc/OH逐相预算通过；CaO初末/源/残差/预算均0，relative=null、passed=false、undefined_zero_budget，逐相整体不PASS。21保存时刻库存和各原生熵项非负，仅授保存时刻资格。原生带符号gas、水、携能和热面值已保存，有非浮点量级输运，仍不授空间精度。native累计熵最大残差已保存，但单独完整signed Sstorage/Sproduction/Sexchange累计序列未序列化，独立重放未资格。根616=144literature472assumed0measured，旧609完整记录、liveP51失败合同及科学核不改；当前名义12格mode0/Ca0/sampling0/directoff保持。P51首次序列化失败、P50两项初态错误PASS撤销、P45/P34/P40/P44失败和历史名义余水0.135892078740%>0.1%保留，0新名义尝试。当前时空加密/八阶段/三方案反演UQ/完整模型CLI仍未资格、whole_project_complete=false。Git/Drive另读实际收据，metadata不是恢复；历史20GB和GitHub容量未解决，不分配P53。

入口 `scripts/run_saved_reference_transient.py` 只调整既有 `plain(result)` 的使用位置：在文件输出和stdout摘要之前统一转换NumPy标量。P52真实执行已同时写出JSON和stdout；P51原失败source、stderr、stdout、计数和未写出result的事实不改，不冒称恢复P51内存轨迹。

科学启动前冻结完整root/case及47个既有Python源文件586189B；本轮live独立合同为 `saved_reference_transient_json_recovery`，snapshot内行政alias供既有CLI selector读取，原live P51合同保持。合法case沿既有P46/P44物理合同、保存13格mode3和baseline整记录数值设置，保持298.15K、10s、max_step0.1s、output0.5s、BDF/rtol/atol，不覆盖y0、不rebin或生成新网格。新增7条全部行政policy/assumed，旧609完整记录保存。

| 原判据 | 实际结果 | 有效范围 |
|---|---|---|
| 质量/元素/完整U | 6.822906222e-10 / 7.562083972e-9 / 1.578059999e-8 <0.001 | 单一0..10s |
| O2/N2/H2O/CO2预算归一残差 | 1.387731355e-9 / 1.069588711e-9 / 8.185547502e-6 / 9.353029983e-6 <0.001 | 原带符号源/边界/增量及初始库存归一值都保留 |
| calcite/portlandite逐相 | 2.389758472e-17 / 2.775339840e-18 | 原逐cell残差先算再全域，非库存代理 |
| lime(CaO)逐相 | budget=0、relative=null、passed=false | undefined_zero_budget；组合相验收不PASS |
| native累计熵 | 3.208755776e-9 <0.001；最大原残差1.229072575e-6 J/K | 原Escale/Tr归一；独立全序列重放未资格 |
| 严格库存/熵符号 | condensed min0，gas min5.953054548e-15 mol；各熵项min>=0 | 21真实保存时刻，仅t=0,0.5,…,10s |
| 反应/相变热与量纲 | native count-once声明与dimension_check通过 | 原模型定义，不构成新独立热力学势微分验收 |

原生产summary的同次返回值提供带符号内面/边界事实。gas内面约[-2.37650e-5,+2.57425e-5]mol/s，gas携能内面[-0.30736,+3.40040]W；水内面[-4.17470e-10,+3.78681e-9]mol/s，热内面[-6.07481e-6,+1.17324]W。gas/water边界向外为正；heat into-left/into-brick为正，方向不能混用。实际存在非浮点量级输运，不能由此授网格准确性或新阈值。

必要原始结果 `runs/full-cycle/p52-saved-reference-transient-json-recovery/result.json` 保存端点账本、逐cell相残差/源、21时刻严格项与原生signed面数组；`saved-readback.json` 仅已有保存数据归纳，无新增模型或算子。native累计熵最大残差与相对指标已落盘，但单独完整signed Sstorage/Sproduction/Sexchange累计序列没有序列化，不能声称可独立逐项重放，未重新积分或恢复。机械熵rate identity采用同缓存导数，不能冒称独立势微分。

原raw schema带P51是复用格式名；身份、路径和execution是独立P52。冻结root中的declared_not_started是启动前元数据，有效关闭状态见实际execution和收据。原report.scope描述完整模型，但本轮declared_process_window只有direct_transient0..10s；whole和onlystage是同一窗口，不是八阶段、两次重复或加密。

终态孔隙率0.19102385845253245、残碳0.0029250461599359245kg、带符号收缩-6.160045240566348e-7、峰温差0.28494580263088665K只作描述，没有本轮时间/网格加密配对。P45净U原门槛FAIL、P34 30/81、P40峰温mesh7.33335%、P44 CaO3/9/directmesh3.01853436%、P50两项错误初态PASS撤销和P51输出失败都保留；不以P52短窗成功覆盖。历史名义余水0.135892078740%>0.1%无新尝试，0实测、无目标砖L，全部模型与物理数值验收仍未完成。

科学监督11.181062291s、childCPU10.998613s，唯一截止17:18:21.432530UTC，无超时/重试；行政声明至本记录801.199s，分开记录。2MiB初测包含冻结输入/源/声明及实际结果；行政收尾字节另读最终收据。变更12个精确路径、正常Git后继/push和原Drive父目录小增量实际结果见 `runs/full-cycle/p52-saved-reference-transient-json-recovery-final-delivery-state.json`。元数据不是实际字节恢复，压缩原件保留；历史/独有Git/20GB/GitHub容量未通过。当前窗口永久关闭，不分配或启动P53。
