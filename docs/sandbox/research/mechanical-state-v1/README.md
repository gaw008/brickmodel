# 机械动态状态证据

基线 f7bfa7a。事前范围与轨迹门槛见 ../../MECHANICAL_STATE.md。

源码测试分两组：122 passed in3.16s（状态、轨迹、检查点、旧积分/回写），162 passed in31.70s（服务、实验/敏感性/搜索、旧耗尽事件路径）。非editable安装后两组联合284 passed in44.62s；XML实际解析为零失败/错误/跳过。installed-identity.json 保存56个实际site-packages模块与源码的逐字节匹配证据，cwd=/private/tmp、无PYTHONPATH。此处为相关回归而非全部系统套件。

core-red.xml 保留新状态接口尚不存在时的失败；source-tests-failed-import.xml 保留Root改恢复策略规范化时漏导入encode的3失败/117通过，已修复后重跑。Checkpoint worker先发现新增None策略字段令旧原始字典比较失败，现两侧均通过IntegrationPolicy验证后比较。独立审查又发现非机械状态提供未使用伸长尺度在integrator合法、checkpoint过严，已统一单向要求并验证实际integrate→encode→audit路径。

baseline.json 是修改前安装包的非机械非线性轨迹：16接受、1拒。与新源码相同算子和策略比较，剔除确认均None的新字段后全部旧状态/时间/账本/次数逐字一致，结果见baseline-comparison.txt。首次采样脚本误用不存在jsonable导入，未运行轨迹；改为实际encode后采样成功。

自由机械轨迹测试实际调用solve_free_rates和integrate，以独立梯度DOP853对照；另检查恒外压能量变化等于负外压乘体积变化。实际机械取消、续算、拼接测试保留一个已接受前缀并审核原预算。制造参数限定不变，无真实污泥或湿态自由烧结验证主张。

下一必需实现是当前状态驱动的点储能/温压反解及自由形变主机，随后耗尽事件和多格相容。旧主机明确拒绝动态机械状态只是避免错误使用，不能当作这些必需实现已经完成。

独立 code-reviewer mechanical_code_review 已实际复核恢复导入、单向策略修复以及两项实际积分恢复回归，限定 checkpoint/service 审查 APPROVE；未把代理审查当作外部专家认证。program_knot_review 对旧host防护/回写及独立自由轨迹公式静态审查无阻断。

program_knot_review 随后实际读取冻结积分器完整机械修改与测试，确认所有RK阶段/误差/接受态复验及逐步/累计账本均包含机械量，累计状态只在最后guard通过后提交；未发现阻断问题。该审查未运行测试或EOS，执行证据由Root核验。
