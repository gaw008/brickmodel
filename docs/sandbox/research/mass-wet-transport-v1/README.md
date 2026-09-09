# 两格正液量反应、相变与传输耦合

source7b56d8f5/testb825af0c，依赖已准入湿储能60f6ec5d。每阶段重建当前T/P、液/气占积与分压；有限O2反应、WaterChemicalPotential相变、三气体修正扩散/Darcy供体焓、Fourier传热共同更新kg固体/Nl/Ng/U。相变液/气源相反，面账本仅一次，潜热和反应热不另外加入总U。失败不提交试算状态；保存实际接受前缀及回调尝试/完成数。

源码37项14.10s、非editable安装37项13.98s通过，90实际模块与源码一致；独立11项10.23s通过。两档4/8步每接受点对照独立DOP853代数，全水/元素/质量/U和本格账本分别核验；不等半格宽反转、同时间步分段一致、第二中点失败、回调后来源变化均独立测试。极小非零系数的RED与修前来源保留。

正式命令：`PYTHONPATH=src python -m pytest tests/sandbox/test_mass_wet_transport.py tests/sandbox/test_mass_wet_storage.py tests/sandbox/test_mass_transport_bridge.py tests/sandbox/test_mass_storage_bridge.py`。安装测试从/private/tmp运行这些绝对路径，无PYTHONPATH。纯测试液体响应是明确制造替身，真实水热化学框架调用不意味着真实液体EOS验证；禁止native water求解。

仅严格正液量短轨迹，没有耗尽、干态模式、精确事件或续算许可。原生真实水轨迹另行保存，完整湿→干及真实材料仍未完成。外部监督负责打断阻塞EOS；内部墙钟检查不具备该能力。

归档逐成员SHA重读核对通过，见manifest.json。原初始水蒸气过饱和导致预期相变方向不符的失败保留，测试明确修改左初始蒸气量而未改生产方程/门槛；不把制造测试调试当原生成功。
