# 自由速率闭合验证

基线 4a9d9e9。仅制造的固定固相单格瞬时双自由度速率，没有 EOS 或时间推进。

物理审查 program_knot_review 确认取向界面能要求法向/横向独立，两个横向功贡献均须保留，Piola 平衡相乘求和得到文档中的功率身份。Python 审查 liu_audit_review 未发现阻断问题，确认求解误差对最终表示速率平衡残差的线性界成立；它不是任意速率扰动的全状态功率误差界。按建议补充 eta=3、单位伸长的独立 Fraction 证书测试。

实际源码相关测试 39 passed in 0.14s，非 editable 安装后同组 39 passed in 0.12s；原始 XML 在本目录。安装测试 cwd=/private/tmp、无 PYTHONPATH；实际导入 56 个 site-packages 模块逐字节与源码一致，见 installed-identity.json。这是相关测试，不是完整系统套件重跑。

测试包含 160 位 Decimal 独立能量梯度、不可精确表示速率的 Fraction 残差与误差界、方向性、外压功、黏度/孔压响应及适用域拒绝。数值误差界不代表材料可信区间。公开来源只支持其限定关系，未提供污泥参数准入。

源码复现：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /private/tmp/brick-water-backend-probe/venv/bin/python -m pytest tests/sandbox/test_free_skeleton_rates.py tests/sandbox/test_skeleton_energy.py -q`。

下一必需实现：机械伸长与库存、总能量共同进入积分阶段、拒步回滚及持久化，再闭合当前温压/孔体积。多格机械相容、真实材料准入、公开对照及完整周期仍未完成。
