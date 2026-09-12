# 来源普通段的本地保存与恢复

这是现有来源试算的运行功能：水物性和干物质热容有来源，但当前砖坯几何、输运设定仍属制造验证案例。它尚未构成有完整材料证据的污泥烧成模型。旧`SourceStudyRecord`的历史controller不支持恢复；新的ordinary trajectory恢复点单独保存完整来源、数值checkpoint和累计计费。

安装当前版本后，用独立隔离进程调用同一服务：

```sh
python -I -m sludge_sandbox.source_execution_worker /absolute/path/request.json
```

请求是闭合JSON，只接受以下三个操作。全部路径用绝对路径；output必须不存在。`cancel_file`为`disabled`或取消文件的绝对路径；创建该文件提出合作取消，实际结果以保存的状态为准。需要监督整个进程时参考同目录execution/run_supervised_native01.py中的进程监督调用；合作取消不承诺能中断任意阻塞的本机调用。

新父研究请求：

```json
{
  "schema": "source_execution_request_v1",
  "operation": "source-run",
  "source": "/absolute/path/source-nonstationary-heos-resume-v5.json",
  "assets_root": "/absolute/path/private-source-assets",
  "output": "/absolute/path/new-parent",
  "cancel_file": "disabled",
  "shared_budget": null
}
```

来源资产必须按case中完整17项准备，禁止缺项替代；原文来源缓存是私有本地副本，不随公开证据包再分发。source-run实际父运行保存在output/run。先确认OUTCOME和原run/result.json中数值事件检查通过，然后以该run目录作为`source-advance`的source。

`source-advance`沿用同一组基础字段，去掉assets_root，增加：

```json
{
  "end": {"numerator": 875870864055254099391, "denominator": 18684848959032849465344},
  "step_sizes": {
    "initial_step_s": 0.015625,
    "maximum_step_s": 0.015625,
    "rationale": "原三步导热数值检查，初始与最大步为1/64秒。"
  },
  "pause_after_steps": 1
}
```

以上end是本次预登记案例对应的原末时加3/64秒，不适用于任意父案例。实际程序从父记录选用candidate 1的精确末时计算目标；调用者必须提供约分后的精确分数，不能把浮点显示时间当作原始时钟。数值步长是实验策略，不能改变材料参数或原容差。`pause_after_steps: 0`表示不主动暂停；正整数表示本次接受指定数量的新步后暂停。

干净暂停后，worker实际调用save-and-suspend，关闭旧live会话，输出output/resume-point。新进程恢复请求：

```json
{
  "schema": "source_execution_request_v1",
  "operation": "source-resume",
  "source": "/absolute/path/paused-output/resume-point",
  "output": "/absolute/path/new-restored-output",
  "cancel_file": "disabled",
  "shared_budget": null,
  "pause_after_steps": 0
}
```

恢复不能传入新终点、容差、物理模式或预算。它继承保存点的原问题、原观察与全部已耗成本；只计算剩余部分，同时明确记录新构造物性对象的成本。离线等待仅作诊断，原在线暂停和所有实际工作仍计费。每个保存点只有一次本地恢复attempt；失败或中断后不能从这个旧点免费重试。复制目录不能被理解为全局唯一身份或防伪保证。

Python接口位于`sludge_sandbox.source_trajectory`与`sludge_sandbox.source_trajectory_record`，公开函数分别为`open_source_trajectory`、`save_source_trajectory`、`read_source_trajectory_checkpoint`、`restore_source_trajectory`。read只做被动数据核查；save/restore使用原控制器与真实来源对象。`managed_execution=True`只允许专用隔离worker使用，普通导入不会获得native scope权限。

OUTCOME分别列出raw_case_sha256和canonical_config_sha256。FAILURE保留原异常、原求解状态/原因与已观测计数；计数无法取得时为unknown，不写成0。FINALIZING、未完成claim、来源不符、完整观察不对应和原预算耗尽都不能被当作有效完成。

shared_budget只用于有明确外部分支成本的实验；默认null保留本来源链自身预算。预登记比较驱动会填写其他分支的实际差额并从事件重新核对，普通调用者不应为扩大额度伪造此字段。
