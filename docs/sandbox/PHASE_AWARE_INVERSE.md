# 按实际液库存选择反解括号

事前合同：SolidFluidHeat 的 optional dry_temperature_brackets_k 仅是 numerical_policy，须带 id/version/reason。每次真实 decode 按完整库存的液列严格等于0选择该格干态括号，正液库存保持原 transport 括号；不从温度、界面标签或小量阈值推断干态。原储能/物性域/误差预算、反应与边界不变。默认 None 保留旧路径，显式每格元组不能自动扩容。

事前验证：单一真实 Joined 水汽/制造固相主机的 wet300K 与 dry502K 完整 evaluate/储能反解；前者295–310K、后者295–510K，温度绝对误差2e-5K，输入U逐位不改。缺少新政策时高温库存反解失败。正微量液库存不能选dry；域外干括号仍失败。非法括号/身份/不可变检查。此轮不宣称已完成实际耗尽跨模式积分，长程由事件器独立验证。

接口：新增三个身份字段 `inverse_bracket_policy_id/version/reason`，启用 dry 括号时均须非空；未启用时不允许残留政策身份。`temperature_brackets_for(state)` 返回各格本次括号，`SolidFluidHeatEvaluation` 在原位置字段之后追加所选括号和完整政策身份，classification 为 numerical_policy，未把数值选择冒称材料来源。显式括号冻结成嵌套元组。`decode_inverse` 仍调用每格原 SolidFluidStorage.temperature_from_energy，使用原 inverse_policy 与真实 N/U；没有用纯气反解替换整体固液气储能，也没有 constructor 探测高温液相。

验证历史：首轮8项失败，主要因新API未实现；其中旧默认高干态失败的异常预期最初错写IntegrationError，核对原有分类后改为DomainExit，未改原异常处理。实现后8项1.57s通过；补双格 mixed 与默认 None replace 后共9项。双格选择检查使用显式状态（不称已验证双格物理解码），单格 wet/dry 两条为真实完整 evaluate。正液量即使1e-100 mol仍选wet，无 epsilon；干态括号超过原误差/物性域仍DomainExit。未改变任何来源适用域或数值预算。
