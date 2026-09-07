# 石英固相热化学候选

原始依据为 [NIST WebBook石英表](https://webbook.nist.gov/cgi/cbook.cgi?ID=C14808607&Mask=2&Table=on&Type=JANAFS) 与 [JANAF O-037](https://janaf.nist.gov/tables/O-037.html)。完整HTML已实际取得并保存在本地忽略目录，hash/尺寸见 `extraction_audit.json`；Git只保留有限事实和派生验证，不声称完整SRD页面可再分发。

`facts.json`保留2温段的16个原系数、相同生成焓参考和847 K双行。`extract.py`按原始资产hash门控，以Decimal60逐项复算19个打印温点的Cp、焓增量、熵和Gibbs函数，按各自打印小数位的半单位检查；全部76项通过。该门槛只核对页面格式舍入，不是实验误差。初版只核Cp/H/S三列，经独立审核补Gibbs列；原版脚本/输出存 `initial-three-column-check.zip`，没有用当前四列覆盖重写历史声明。

847 K处JANAF双行的焓增量为34.196与34.924 kJ/mol，熵为103.840与104.700 J/(mol K)，明确标记相变。由表差得到728 J/mol，不能直接抹掉。WebBook两段多项式在同温度的焓差为729.127 J/mol、熵差0.857069 J/(mol K)、Gibbs差3.18975 J/mol；拟合并非逐位重现JANAF双行或严格相平衡。保留两种来源表达，不据此修改原系数、虚构精度或自动拼成连续Cp积分。

低温单相可作为后续固体热量provider的来源，但本包没有摩尔体积、热膨胀、压缩性或泥中石英含量。不能将石英热容当整块砖热容，也不能从原料XRF的SiO2量唯一决定石英相。运行时尚不自动载入本候选；跨相变模型和整体湿砖组装仍待实现。

复算（需已核对的本地原始缓存）：`.venv/bin/python data/sandbox/solids/quartz/extract.py`。另一环境需要从 `source.json` 的官方URL取得原文件并重新核查身份与数值；页面若有非数值内容变化使hash不同，脚本也拒绝，不能通过静默替换hash称已复核。
