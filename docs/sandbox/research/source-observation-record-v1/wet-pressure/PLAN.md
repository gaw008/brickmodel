# 事前保存端点预算核算

固定输入 /private/tmp/brick-source-multicell-transition-v1/root/native-result.json，SHA2660d33ec0e832e006d5adcccd8ddcf38cc314ac5e65a17830cdf2f73cbdc51d。仅湿格0/2，event/common两时间行，每行实际粗/细两端，共8端。固定原runner摘要并记录其SHA；零EOS/模型构造/生产导入。

先重算nominal压力下界：down(NgRT/Pmax²)，up(sum(volume residual/resolution/Nl*v_error))除以前项up。重算原global/extra/local体积压力上界及与actual记录的surplus，保留total投影。重算global L与bootstrap L，核radius=eP+L*eT，实际成对ΔP+两radius。

能量：液体Nl*u_error、各气ni*u_error均原directed product；保存fluid rounding作为观测项（不伪造缺失逐物性ULP）；液体Nl*B*actualfluidP项；source总U与exactsolid+fluid U之投影；额外Nl*B*exactextraV项；up总界与逆解(|RU|+error)/Cmin。比较所有保存字段，缺失就保留unknown，不补EOS。分离每次directed rounding与实际超额。

输出原eT、L*eT、全部分项exactFraction和便于阅读float，原阈值保持1e-4Pa。检查两端L*eT之和是否已>=阈值；仅判断仍保留这些项的非负联合界形式有无通过空间，不称真实误差下界、不称所有方法不可能。旧event与湿格P失败保持。任何脚本失败保留原版/log再修实际schema假设。
