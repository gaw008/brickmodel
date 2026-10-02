# P61 有效case条件与来源接口

P61 有效case条件与真实来源接口已实现，实际JSON功能完成（2026-10-02T22:37:27.274912+00:00）。单阶段合法case输出24项有效条件、65项legacy完整记录/48项非当前stage旧键；真正既有83行synthetic输入原样保留，八stage配置使用66项有效条件。v2 bundle保存完整records/sources/原source及显式变换；compare/save/measuredfixed共用同一投影，数值网格/步长/容差不混入实验物理条件。CLI传实际args.parameters，Python调用须显式case_reference/case_transformations，派生窗口只记真实内存变换且savedfile=null。已准备v2保留原source_dataset_schema；fit结果保存整个bundle、三个新synthetic生成合同v2，相关fit/reference/measured/重prepare分支本轮仅静态接线，未执行。实际一次direct JSON及一次prepare用时1.382284s，0模型构造/RHS/Jac/ODE/fit/UQ；包导入的旧dataclass类体/代码生成4事件另保raw profile及来源分类，不称物理forward。一次源语法错误在AST前停止、修正后执行，失败留证。

根690=144literature/546assumed/0measured，旧689完整records及名义物理参数保持；新增仅独立64MiB行政额度。原32MiB预检33618433>33554432，超64001B并0实施/功能，原FAIL保留。新完整事前估算34633649≤67108864（所有六reserve保持），最终actual连同Gitblob/增量档案/末收据读 `runs/full-cycle/p61-effective-case-conditions-64mib-final-delivery-state.json`；一次正常提交和一次Drive增量以后，末local收据不递归commit/打包。P60原完整预检补齐17600341>16777216超823125B，协议FAIL；actual16701789B及已真实两段熵/预算证据不追认预检。名义余水0.1358920787402553%>0.1%仍失败，P34/P40/P44/P45/P50撤回/P51、CaO零预算nullfalse保持。当前8stage、独立势/分支、组合加密、最新三方案/反演/UQ及材料仍未完成；本次接口功能不授整体模型或工艺PASS，0新物理验收/测量/恢复/历史删除。

实现及执行证据 `docs/FULL_CYCLE_P61_CASE_CONDITIONS.json/md`。下一代码缺口为inverse/UQ Ca与native entropy证据保留；当前无下一科学窗口。Git、Drive元数据、实际恢复和20GB/GitHub容量分别判断。

实际验证输入是此前保存的合法case及同模型synthetic观测，既不是测试fixture也不是材料实测。reference/measured配置比较、measured固定条件排除、fit结果保存、三个demo和v2二次prepare已审阅调用链，没有动态资格声明。原candidate72输出和旧bundle未覆盖。

Python API现在要求显式来源和变换列表：`prepare_dataset(config, dataset, case_reference=str(parameter_path.resolve()), case_transformations=[], for_calibration=False)`；`fit`及三个synthetic helper同样要求两个关键词。窗口调用传真实变换记录；未知来源不由库猜测。完整数值CLI以及`map_observations`会构造模型，本轮没有执行。
