# P38 来源特定 TG 双 DoC 适配

UTC 2026-10-01T20:41:25.704315+00:00。新 `inverse/source_tg.py` 已实现并完成四次单行纯数据核查；本项完成，完整模型未完成。原43周期主机、P37局部模块、原9观测与fit保持。460=144literature/316assumed/0measured；原448完整条目保持，仅新增3来源观测摩尔质量、6运行预算及3synthetic数组，不新增主机物性或宏观率。

## 来源与接口

使用已知[Saeki2026原文](https://pmc.ncbi.nlm.nih.gov/articles/PMC12980848/) Carbonation Experiment Eq5/Eq6完整MathML：DoC_CH=1−(mCaO/mCH)M_CH；DoC_Cc=(mCaO/mCc)M_Cc。独立来源舍入m为56.08/74.09/100.09g/mol，不替换主机atomic质量。M是同一灼烧CH(CaO参考)的相质量比；g/g与kg/kg比值数值等价，但分母语义不可互换。Eq6不扣初始Cc，Eq5不再除剩余或初始CH；两定义独立，不强制等值。完整来源记录在p38-source-tg/source-equations.md，未扩扫、数字化曲线或读取新补充材料。

`map_saeki2026_tg(*, config, record)` 两输入必填。record明示quantity、measurement_kind/source_kind、source_id/locator、sample、time、denominator、phase_separation、applicability、两phase_masses。每相关联共同source/sample/time/denominatorID；相质量必须已分峰所得且以声明CaO基准归一，不接收整砖总TG/initialdry替代。当前仅来源语义准入，使用已有_known/_number/convert；一致声明不是来源真实性证明。根source_observation_contracts及3m条目缺失直接暴露，不给默认值。

输出两个DoC、DoC_CH−DoC_Cc、原始输入深拷贝、来源常数/公式、原来源时间及适用标记。保持signed量与差值，不裁剪、平均或基线扣除。synthetic仍synthetic；其他输入输出source-derived，不由公式自动升为targetmeasured。canonical_fit_observation/material_validation固定false；原UNITS九类及拟合准入未改，也未将该来源DoC自动映为整砖观测。没有自动TG分峰或RH/时间动力学识别。输入measured/reference路径只经代码审阅，本轮未数值执行。 负相质量和越界DoC保留也仅经源码审阅，本轮未数值覆盖；初始Cc例微小负差值不等于这类覆盖。

## 实际单行结果

| 显式synthetic记录 | DoC_CH | DoC_Cc | 独立差值 | 实际结果 |
|---|---:|---:|---:|---|
| 纯CH未碳化 | 0 | 0 | 0 | mapped |
| t0含初始Cc贡献，kg/kg | 0.09999999999999998 | 0.09999999999999999 | −1.3877787807814457e−17 | mapped，初始Cc未扣 |
| 定义不一致 | 0.35 | 0.19999999999999998 | 0.15 | mapped，分别保留 |
| 整砖/总TG/initialdry/unknown分母来源 | null | null | null | ValueError，原拒绝保存 |

第四条是一个复合负例：错误中列四个原因，不宣称四项独立拒绝覆盖。拒绝是本条预期语义结果，不改称主机物理失败。所有4调用各1记录，child退出0并回收，0重试/未知失败；没有重复P11的58项或P37四本构。没有主机/RHS/Jac/本构/积分/fit/UQ/恢复。

执行UTC20:36:14.964565至20:36:18.098492，总3.13389362487942s；单例60s/总120s唯一硬截止20:38:14.964565未延长，单并发、2MiB。当次目录658487B含根快照/脚本，不是净四结果大小；未触发timeout，停止路径未动态演练。监督schema沿用scalar字样，这里只指单record求值，不是模型本构节点。登记至本报告513.739s为含阅读/实现/文档/审阅墙钟，非积分耗时。

## 当前仍未通过与下一项

P38只授来源转换/声明语义资格：无真实TG峰分离、原论文测量点误差、实砖适用性、宏观率、动态非负性或完整能量资格。原P34普通81/气体108/规定加密保持历史当前主机证据，本轮未重跑或升级。额外逐相30/81失败、strictOH未资格及负值/近零原分母保留；名义0.1358920787402553%>0.1%工艺失败，原两次处理不重启。0measured、当前主机UQ/fit未获资格，wholefalse。

确未实现的下一候选P39：将P37明确L/来源/域的direct算子条件化接入周期RHS、独立累计extent及共享U/S/体积账本。依据是P36局部路径差距及现源码缺通道，P38公式本身不能识别L。先候选4单态RHS求值、60/120s/2MiB/单并发、0积分/fit/UQ/恢复，仅可授局部真实接线；若进入周期，加密与受影响完整账本另事前登记，原失败不改判。本项未登记P39参数、改主机或启动该候选。

正常Git/push与明确小增量metadata以随后实际收据为准。恢复下载/解包继续停止，原压缩件/独有历史保留；完整备份、20GB及容量告警另未通过，不以元数据称恢复。

## 实际交付

P38实际交付（2026-10-01T20:47:43.095242+00:00）：sourceTG适配提交aa2221de已普通推送且远端一致；明确27文件小增量589,522B/28成员已上传，名称、大小、父目录读回通过，收据FULL_CYCLE_P38_DELIVERY.json。首次打包继承错目录在创建前失败，修正后一次成功，失败保留且0新科学调用。新source_tg离线4记录3.133894s/3mapped+1compoundreject/全退出回收，旧43主机/P37/9canonical/fit保持，460=144literature/316assumed/0measured、旧448完整保持。所有输入synthetic，未测真实peak/负相质量/越界DoC/实砖/宏观率/fit；旧30/81、strictOH、名义0.135892078740%工艺失败与wholefalse保持。0主机/RHS/Jac/本构/积分/fit/UQ/恢复；未下载/解包，原件保留，历史/独有Git/20GB/容量告警未解决。P39条件化主机通道仅候选未启动。
