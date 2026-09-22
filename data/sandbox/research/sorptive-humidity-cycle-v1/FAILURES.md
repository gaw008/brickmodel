# 保留失败

`four-stopped-inside-hold.jsonl`第一次检查点运行在50个接受步后的进度输出失败：新增SciPy阶数统计为NumPy int64，Python JSON不能直接编码。原前缀及`four-stopped-inside-hold.stderr.txt`保留；尚未到指定50s停止点，不作为完整或检查点成功轨迹。

修正只在进度输出边界将阶数/计数显式转为Python int，物理关系、积分设置和误差预算未改。新文件`four-stopped-inside-hold-v2.jsonl`实际停于50s并保存检查点，后续恢复另存文件，不覆盖失败证据。
