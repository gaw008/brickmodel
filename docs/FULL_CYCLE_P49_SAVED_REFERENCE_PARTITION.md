# P49 保存参考面生产初始化交付

P49显式保存面初始化接口及一次保存几何转换完成（2026-10-02T15:40:52.764071+00:00）：H原13格/14faces原值接入mode3 saved_faces，新增initial_partition_from_faces与整记录saved_reference_partition_case、纯离线脚本；主机构造未执行，接线仅静态。唯一1job/1primitive/1worker rc0回收，监督0.412691s/CPU0.330740s、case+geometry共420111B<30s/512KiB，窗口关闭不重试。faces/centers/widths原值一致；逐格new A*diff(faces)−saved fine-volume-sum保留−3.388131789e−21/+1.694065895e−21m3。P49 numpy.sum全局差0与H原math.fsum+2.710505431e−20m3并列，不授几何容差或物理PASS。根595=144literature451assumed0measured，旧587所有value保持、586完整条目保持；唯一旧mode range[0,2]→[0,3]+note例外，名义12格/mode0/sampling0/Cacoord0/directoff不变。0构造/RHS/Jac/ODE/fit/UQ/C/G/H-selection/P38，新mode3动态/加密/八阶段/采样/比较/反演/模型CLI未资格。P34/P40/P44/P45失败、CaO零预算relative=null/passfalse、名义余水0.135892078740%>0.1%及wholefalse保留。Git/Drive与历史恢复容量另计。

实现文件为 `initial_finite_volume.py`、`full_cycle.py`、`scripts/materialize_saved_reference_partition.py` 和根参数。原 `initial_partition` 签名及 uniform/exterior_power 算术保持；mode3 只读取明示 faces，不读指数。主机复用原逐格质量、初始物种、site、独立 extent 尺度链，通过 `self.p(...,'m')` 记录所用单位。没有执行主机构造。

参数 case 完整复制 root 声明的 cells/mode 条目；实际13格 `[13,13]` 和mode3 `[3,3]` 快照由既有 `read_parameters` 读回成功，没有偷偷改名义 `[12,12]`。8新记录仅3数值输入及5操作政策，来源 policy/assumed、note精确指向H保存字段；不是新增物性或measured数据。名义所有旧参数值保持。

一次实际作业输出 `case-parameters.json` 409892B、`geometry.json` 10219B，共420111B；监督0.412691125s、CPU0.330740s、脚本转换0.020411250s，rc0/reaped，首30s独立截止未延。仅一次原语调用，所有旧窗口关闭，无模型调用或第二次转换。启动前直接import因旧editable pth指Desktop失败，尚未启动operation/primitive；新CLI沿用既有examples的Research源码定位，未修改venv或全局配置，原失败另留。

faces/centers/widths一致只说明输入保持。new体积用面积乘面差，old为保存fine体积求和，逐格−3.3881317890172014e−21与+1.6940658945086007e−21m3保留。实际新报告numpy.sum全局差为0；原H用math.fsum保存+2.710505431213761e−20m3，原字段原样复制到 `output-readback.json`，不混称为同一全局原值。没有容差、clip、floor、snap、子格状态重建或物理PASS。

当前mode3主机、热力学/守恒/短动态、time/grid/全8阶段、13格C采样、版本匹配三方案/反演/UQ/模型CLI尚未资格。0measured、无目标砖体direct L、CaO零预算undefined/passfalse、P45净U失败、P34/P40/P44及P44direct3.01853436%和名义余水失败保持。下一最小物理候选仅为13格每格尺度与瞬时RHS链；额外构造/RHS/时间/字节资源尚未分配，未执行。

实际材料见 `runs/full-cycle/p49-saved-reference-partition/{declaration,execution,geometry,output-readback}.json`、case/root snapshots与原失败。正常Git/普通push和一个小型增量上传读取独立最终receipt；metadata不是恢复，0下载/解包/字节恢复，原件与历史/独有Git保留，20GB及GitHub容量问题未解决。未新增测试、SHA、护栏、memory、定时任务、文献或独立研究目录。
