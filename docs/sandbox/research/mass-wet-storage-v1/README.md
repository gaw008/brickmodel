# 同质量基准湿储能层

source60f6ec5d/test481e2378。固体kg、液水mol、气体mol与总U分别保存；流体先从实际固体占积后的孔容求液体/气体共同压力。保留原流体误差，固体体积误差经全局压力域证明、局部压力界收紧，再以液量和液体du/dp传播进总U误差。液气同实际水来源/后端/参考/M，水化学反应系数必须零。相变不额外加潜热，化学不重复加反应热。

原负/正极小Fraction库存被float转成零的HIGH已修复；原始非负性及非零转零拒绝在三类库存均实际测试。来源聚合补齐数值包络与常数。原6失败和聚合1失败、旧源码/冻结均保留，独立最终23项0.50s通过。源码与非editable安装各46项通过（7.43s/7.49s），89实际模块与源码一致。

命令：`PYTHONPATH=src python -m pytest tests/sandbox/test_mass_wet_storage.py tests/sandbox/test_mass_storage_bridge.py tests/sandbox/test_mass_transport_bridge.py tests/sandbox/test_reaction_reference.py`。安装测试从/private/tmp以四个绝对测试路径执行，不设PYTHONPATH。纯测试使用明确制造液体响应并禁止native EOS，非零du/dp独立负控验证压力/能量包络，不能冒充真实水实验。

实际水一点验证见相邻mass-wet-native-v1证据。当前仍是制造固体、常Cp/比容与有来源水的湿储能，不含时间积分、湿→干耗尽、自由收缩或真实污泥材料准入。后续必须将同一kg状态接到传输/相变和完整事件账本。

归档及逐成员SHA见manifest.json，实际重读核对通过。HANDOFF保留作者原7项阶段结果，最终修复与23/46项以CODE_REVIEW和root XML为准。审查为代理审查，不是外部认证。
