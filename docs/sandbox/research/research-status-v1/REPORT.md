# 离线研究状态查询

入口从根目录 `parameters.research_status.json` 声明的原始结果路径逐项取值，覆盖来源吸附、CO₂/N₂输运、方解石温程、显式低温表面，以及高温碳/钙封闭、开放、表面三条研究线。返回每项路径、原始布尔值或详细预算；不计算全项目完成百分比。

从项目根目录执行：

```sh
.venv/bin/python -c 'import sys; sys.path.insert(0,"src"); from sludge_sandbox.cli import main; raise SystemExit(main())' research-status --parameters parameters.research_status.json
```

成功读文件与通过预算分别表示。声明为待产出的文件尚不存在时，输出 `awaiting_result_file`；这不是进程运行状态。文件已经存在时，原有失败仍为 false。源码不会用另一条模型的结果替代，也不会把存档上传当作物理验证。已要求存在的结果或字段缺失时，读取错误直接暴露。

初次从未安装本包的环境执行 `python -m sludge_sandbox` 失败，stderr 保留在 `snapshot-initial.stderr.txt`；随后显式使用本地源码执行成功。`snapshot-source-v1.json` 保留初版读取结果。最终索引已将高温三条研究线的待产出路径对齐为各自实际使用的两档合并审计文件，最终实际输出保存为 `snapshot-source-v2.json`。

人工逐项核对确认旧吸附失败、方解石空间失败、高温三条空间失败与待完成审计均可分别追查。当前读数不授予真实砖材料资格。此轮只执行实际命令、JSON读取和Python语法检查，没有新增或运行软件测试，没有生成或比对SHA。
