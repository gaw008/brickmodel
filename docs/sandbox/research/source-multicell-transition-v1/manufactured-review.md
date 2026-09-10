# N3/k1终态制造保存审核

输入SHA `db8cc74ec8e6c119d10054e28a00794ec08526a2d54f7e25ba148f7bff98f211`；最终221项Fraction断言通过，0.229196s，无EOS、生产导入或模型check。第一轮195项通过后补全混合湿/干与shared压力独立公式；01版本/结果/stdout全部保留，无失败。

两条真实路径选k=1，完整12库存竞争、原三项净液clock及prior共用预算通过。以保存decoded/mobility重建exact Darcy q、n=q/vdonor、Q=n*hdonor及各次float投影，活动face2向右输水但h<0。粗终端transport6.238130484569159e-12mol、gross evaporation3.761869491064921e-12mol；细终端分别5.068481050289391e-12、3.0565189441608563e-12mol（细路径之前另有真实ordinary段）。运输未冒充gross，原phase小校正预算保留。

每条完整源面/phase/U的仿射精确积分及积分投影独立重建，全共享面左右反号在全域严格抵消。粗3/细4前缀每格及全域N/U、水/H/O/N/流体质量数组逐项一致，原预算没有乘N。仅k液汽写回，全U及其他槽不变；粗rho=0，细rho=1/2475880078570760549798248448mol，作为汽储存舍入显式保留。这次实际保存例覆盖非零rho。

每路径1个实际mixed dry接受步，只有中格dry，接收格仍wet；原active面进入预声明zero_mobility分支。粗/细recipient终端U变化分别−1.71925057657063e-6、−1.3968892744742334e-6J，与带符号液体参考焓一致，不要求U随液体流入而上升。

两时刻全格原N/U/T/P差异及top max独立重建；wet0/2 global/bootstrap公式、dry1全T/V箱、shared1全部十项误差与联合四角独立相等。selected压力两时刻均约[0.0021062340736656892,2.7561808623166004e-6,0.0021283986254641892]Pa，门槛[false,true,false]；wet邻格失败正确阻止总体数值事件接受，材料资格不授予。

原retained_failures含late wet2 assessment失败及positive-zero-mobility真实DomainExit（active_face_requires_existing_liquid_both_sides），此前候选未被覆盖为成功。首轮root“recipient U应增”的断言错误属作者历史验证，当前独立核算使用原Q符号，不变更方程或门槛。

几何不是JSON字段：A=.01、face2半宽(.15625,.1875)来自实际fixture setup/prepare_multicell，读取并哈希绑定下列代码；未执行fixture。独立算术仅验证保存源观测与声明构成的数值链，非真实材料验证或独立EOS物性验证。

## SHA256

- audit_multicell.py: `9eeb7a1ce310fe0d2bdbac02797f17c08233907f02d5441f0a9ad41913306e23`
- RESULT.json: `7970bab4dcfbe24ecbc21447567d811a022b080ad74d4c69e94e7b49dfa08d93`
- geometry fixture test_source_wet_column.py: `72b31274da6620a388d64b83ae864ced164131e76e7ec3bcf506c13f344b1638`
- geometry fixture test_source_multicell_terminal.py: `a3ff2e22317dbaad5f2a6052bf5b2e78ff3e822675e954c3ad5fa012e4874f30`
