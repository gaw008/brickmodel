# 动态点储能与自由湿单格证据

基线 d4894a2。实现与事前门槛见 ../../DYNAMIC_SOLID_STORAGE.md；DRY_TEST_PLAN/IMPLEMENTATION/SOURCE_BINDING保留最初候选状态，后续执行以本页和实际XML为准。

代码来源：候选dynamic_solid_storage.py逐字节应用，完整provider/能量/几何身份及误差继承既有源。新增ClosedFreeSolidCell实际逐stage反解温压再求自由率，外压功独立schema经Rates、ledger和checkpoint；不加入第二份耗散热。code-reviewer及独立物理审查均无剩余阻断；审查不冒外部专家认证。

实际失败与修复：

- dry-tests-final.xml保留测试构造器错误的1failed/13passed，正确kwargs后final02为14pass0.42s；未改源或容差。
- free-host-red.xml实际复现功分量schema缺external_traction，新增独立_FREE_WORK_COMPONENTS后通过，并测试拒绝混入dissipation。几何/功率表示错误转换为IntegrationError，实际测试保留接受前缀。
- wet-original-envelope-failed保存原宽固相比容误差试件不满足1e-6J精度的两个失败。原试件仍有必拒回归；成功点验证使用先前已定义的精确有理比容制造试件，不收紧原材料误差，也不改变反解精度。
- wet-trajectory-resource-failed保存15秒每档/45秒外限失败，实际正常回收，总35.32秒；按实测成本改30秒每档/75秒外限，所有物理范围和精度门槛保持不变。

源码163项相关回归3.24s、3项真实湿点3.08s通过。湿轨迹1项58.86s通过，外层59.095s退出0并回收：粗1步8次评价23.642s，细2步15次评价27.254s。细档T299.9998934100734K、P304152.5165397252Pa；n1.0002030679890357/t1.0002030572704022。两档温差约5.5e-12K、伸长差约1.8e-12；外功残差-1.90e-11/5.60e-11J，通过原2e-6J、2e-6K、2e-7门槛。

限定：独立湿点与生产共用水EOS，验证耦合算法而非EOS准确性。短轨迹固定液/气/固库存，未发生蒸发、反应或空间输运，也不是整块砖完整烧制。自由速率误差界仅条件于表示孔压，未建立真实材料预测精度。

安装终态：非editable安装58个实际site-packages模块逐字节匹配，cwd=/private/tmp且无PYTHONPATH。167相关测试实际26.70s全部通过、零失败/错误/跳过；外层26.965s退出0。安装湿轨迹粗/细6.612/12.512s，实际温压/伸长/功残差与源码结果相同。资源耗时会随本机负载变化；不把源码与安装耗时差冒充算法性能提升。installed-status/log/XML保存实际命令和输出。
