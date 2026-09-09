# 冻结计算脚本独立代码审查

Tesla 核对 `calculate.py` SHA-256 `73e8e6841847b87eb0dd8e67fce606eab284e46c9d5425f6625b59526b9104e6` 与 `build_registry.py` SHA-256 `0dd61e73534a1c423fc59b3c82874c7f52fffb6d46e998188faa9b107b0e1885`，结论 APPROVE。

Decimal乘积、50位比值和差值定义正确。四节点链保留MJ/kg→J/kg转换及干进料产率乘积，冻结节点与source_facts逐项一致；不声称反应热、误差传播或材料准入。构建脚本含该冻结实例的明确节点数值，是可复算证据实例组装器，不是接受任意新facts的通用变换程序。本次独立审查未重跑求解器或EOS。
