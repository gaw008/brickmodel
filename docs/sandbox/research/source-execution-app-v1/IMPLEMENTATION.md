# 来源运行、暂停和恢复的应用入口

本增量把已有隔离来源执行器接入现有进程监督器。代码审查及196项相关安装测试已通过；实际三进程验收以REPORT.md及Goal当前入口为准。软件测试不替代真实运行验收。

## 使用路径

来源计算需要完整的已登记运行环境及原始来源资产。当前登记配置使用Python3.12、NumPy2.5.2、SciPy1.18.1、iapws1.5.5和CoolProp8.0.0；除了版本，还检查登记的源码/二进制文件身份。不能仅安装模型基础包就假定这些可选科学依赖齐全，也不能把另一平台的同版本二进制当作当前已审身份。只读记录查询不等于重新构造物性。

准备一个闭合JSON请求后运行：

```sh
python -m sludge_sandbox source-execute /absolute/request.json --job-directory /absolute/jobs/new --wall-seconds 180 --grace-seconds 5
python -m sludge_sandbox source-execution-inspect /absolute/jobs/new
python -m sludge_sandbox cancel-job /absolute/jobs/new
python -m sludge_sandbox source-checkpoint-inspect /absolute/jobs/new/execution/resume-point
```

请求共同字段为schema=`source_execution_request_v1`、operation、source、output、cancel_file、shared_budget。所有路径必须显式绝对路径；output必须为新任务目录下的`execution`，cancel_file必须为同目录下的`source-cancel`，shared_budget在这一入口必须为null。请求最多65,536字节，原字节保存并参与校验；不能指定任意模块、命令或脚本。

三种operation沿用原worker含义：

| 操作 | source | 额外字段 | 成功产物 |
|---|---|---|---|
| source-run | 既有受支持来源案例JSON | assets_root | execution/run |
| source-advance | 完成且数值事件接受的父run目录 | 精确end分子/分母、step_sizes、pause_after_steps | trajectory；若暂停则另有resume-point |
| source-resume | 尚未使用恢复权限的resume-point | pause_after_steps | 新trajectory；若再次暂停则另有新resume-point |

pause_after_steps=0表示不请求暂停；正数表示本次操作新增的接受步数。source-resume不接受新终点、步长、材料、资产或数值政策。恢复沿用存储的工作扣账S与新工作A；离线时间D仅作诊断。旧版本记录不能通过改写runtime身份变成当前版本可恢复材料。

Python使用`job_supervisor.supervise('source-execute', request, new_job, SupervisionPolicy(...))`，与CLI共用同一监督路径。`source_execution_service.inspect_source_execution`和`inspect_source_checkpoint`只读取证据，不执行恢复。完整结果、资格、数值失败、原始异常与结果是否已核验分开返回。

## 进程与记录的含义

监督器只启动固定的`python -I -m sludge_sandbox.source_execution_worker`，保留现有锁、进程归属、取消、超时、强杀和回收机制。用户取消先核任务ID，再发布worker专属哨兵；无效旧请求不能启动取消。直接worker不输出包装器CPU/RSS指标时，指标保持unknown。

任务外壳保存job.json、原始request.json、INPUT_BINDING.json、stdout/stderr与RESULT_VERIFICATION.json，worker产物仍独占execution目录。准备和被动核验耗时分别记录。监督状态是进程观察；之后读取保存的job记录不能凭旧PID证明当前存活。

父run使用已有来源包验证；暂停包使用已有完整检查点验证，再核对请求、累计计数和原事件。完成的普通轨迹没有伪装成暂停检查点：使用有限类型的事件读取器核对精确时间、状态/观察/账本关联、累计计数和恢复前缀。它不宣称重做积分器控制算术或独立认证原来源。

检查点内容有效和剩余恢复权限是两项结果。任何现存`.restore-attempt`均消耗该本地恢复入口，包括失败、进程中断或不完整claim；不清除它、不复制它取得免费重试。内容有效但已经使用过的包可以被动查看，无法再启动恢复。

这一工作不会授予原污泥材料、实验预测、完整烧制或训练数据资格。现有制造几何/输运与来源水/干物热容边界保留；完整物理和材料Goal仍有必需未完成项。
