# N3真实水终态保存结果独立审核

输入SHA256 `2660d33ec0e832e006d5adcccd8ddcf38cc314ac5e65a17830cdf2f73cbdc51d`。主核算265项、原政策/资格补查132项，共397项断言通过，分别0.247575s/0.250040s。只读唯一终态保存对象，无新EOS、生产导入或模型重跑。

32实际callback全部对应原始seed/approach/shifted以及两dry候选实际输入、时刻与输出，逐call固定energy和真实operator身份一致。4显式构造锚点与3个初U记录独立核对，初U关联实际packed库存/固定kg/温度/volume。Darcy几何直接取actual adapter.provenance里的area与widths，液配置与顶层原配置相同，不再借制造fixture推断。

两路径均k1、12库存竞争、完整三项净液clock与全部非选库存在整个括区严格正；各1个实际mixed干态接受步，粗3/细4前缀。原根区间距离1.018643030917017e-14s；实际事件时刻7.291730816556658e-7/7.291730847115948e-7s；共同末端1.0937596265580707e-6s。原全部标量门槛和细化预算保持。

粗terminal真实液输运9.550288013388692e-14mol、gross evaporation9.904497072865123e-12mol；细terminal7.75960904419179e-14和8.047403904807276e-12mol（细之前有真实ordinary段）。液流Darcy、供体n*h及其投影分别核对，recipient U变化−2.7110218070447445e-8/−2.2017047740519047e-8J，与负液体参考焓一致。全部共享面精确积分与投影、内部面成对抵消、全链逐格/全域N/U水/H/O/N/流体质量记录独立一致，原预算未乘N。

仅k液汽写回，所有U与非k库存保持；粗rho=15/19807040628566084398385987584mol，细rho=−15/79228162514264337593543950336mol。两种符号非零汽存储舍入都显式核算并通过原单次/累计storage、元素、质量及correction门槛，不混同transport量。

每个event/common实际格绑定对应dry/wet压力记录；湿格global/bootstrap、干格完整T/V与joint-only十项误差/角点独立核算。两时刻selected各格压力界均[0.0020867669852728784,1.0056927090806915e-5,0.0020864234721800507]Pa；原1e-4门槛为false/true/false。因此wet0/2真实失败阻止整体数值事件接受；event=false/material=false原结论保留。液面方向仍fixed_decoded_temperature且full_inverse=false。

主265项首轮通过。补查首版误假设wet SourceInversePressure与dry记录同样有material_qualified字段而KeyError；真实wet记录仅核source_certified/event_admitted，材料总资格由实际source/transition字段核。原native_scope_budget01.py/NATIVE_SCOPE01.log保留，修正实际schema后132项通过；没有改JSON、模型或重跑EOS。

这证明唯一已保存真实水/声明材料来源、制造几何与输运条件下的N格数值候选及其明确拒绝，不是原污泥材料适用性认证或整段事件准入。

## SHA256

- audit_native_multicell.py: `fa11c7147e366384749c83a87966dd219845842dd64541f27ef79e61cbebec95`
- NATIVE_RESULT.json: `21edbb1e58ca815eec4d96a6174a57afa2732d3d0966fd5f21d9c0947c294b74`
- native_scope_budget.py: `2ac49aca266a0bdfa5622e9bff4b2521a8285a452729be67365601e6ee2fbfa0`
- NATIVE_SCOPE_RESULT.json: `d0453786556b43cdcd0fb26980880518a0c50d5f313f63271a04f3f967afdbd3`
