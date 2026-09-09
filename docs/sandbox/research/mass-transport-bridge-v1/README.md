# 两单元混合质量传输桥接

基线 ebe6455。source d9d532c2、正式test04673c96 与已审冻结逐字一致。实际固体kg/气体mol总U反解，有限O2反应、质量修正扩散、Darcy供体焓和Fourier半格热阻共用同一面；面通量仅记录一次，以相反符号作用两格。反应不另加热源，避免重复计热。失败试算不提交，接受前缀保留。

源码32项7.34s与非editable安装32项7.23s通过，88实际安装模块与源码一致。此前独立8项5.08s通过，含不等半格宽反转及第二中点失败保留前缀。4/8步所有接受时刻与独立DOP853方程比较，并以Fraction逐前缀核质量/元素/局部与全局能量。氧元素能量参考变换同时进入存储与输运后T/P/库存保持在原数值门槛内。

实际命令：`PYTHONPATH=src python -m pytest tests/sandbox/test_mass_transport_bridge.py tests/sandbox/test_mass_storage_bridge.py tests/sandbox/test_reaction_reference.py`。安装测试从/private/tmp运行同三个绝对测试路径，不设置PYTHONPATH；实际解释器路径及88模块身份在归档中。水调用被测试明确禁止。

`evidence.tar.gz` 包含原候选、失败日志、最终XML、独立审查和安装身份，逐成员重读SHA核对通过，见manifest.json。仅排除缓存。不宣称外部专家认证。

这是刚性干态两格制造材料耦合验证，尚未接入湿态、自由收缩、精确事件服务或完整周期。比热、反应率、固体占积和传输系数不是原污泥实测；不冒称空间收敛或公共实验对照。
