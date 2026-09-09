# 完整原污泥材料域：三个关键缺口与一个可直接实施增量

只读核查现有仓库，无新文献搜索、EOS、参数安装或源码修改。KNOWN_GAPS/SUPPORTED_DOMAIN含多段明确保留的历史软件状态；本报告不把已完成的自由主机/精确事件/应用工作重新列为材料缺项。当前没有一个真实含原污泥材料包取得全周期资格。

## 1. 同身份原泥的组成—产物—热量闭合

直接位置：`data/sandbox/research/gnest2021/README.md` 第5–11行；`source_facts.json` Table3/4/5、Eq11；`data/sandbox/research/arlabosse2005/source.json:54–97` 的 `caloric_relation` 和 `gaps`；`src/sludge_sandbox/incompressible_solid.py:77` 的 `formation_enthalpy_298_j_mol`、`:161` 的摩尔质量/摩尔体积/参考压力要求。

真正阻碍：GNEST R5/R6每项产物质量少0.050，TG3终点少0.0493，不能以未测伪物种补齐。热值只约束端点差，不能唯一确定演化伪组分Cp(T)/参考能。Arlabosse实测Cp是另一个85%工业/15%市政来水处理样品、kg干物基准，不是该反应材料的摩尔热化学。必须验证的假设是：所使用元素分析、各阶段产率、固相/气相能量参考确属同一可声明材料域，而非把不同研究拼接。

现在可直接实现：Arlabosse Eq2的来源绑定、质量基准显热差 provider/离线核查器（下节具体），不能作为当前 mol-species 固体provider的替换。GNEST已有拒绝结论，不再把同一算术复查列成未做工作。

## 2. 湿料中的水活度与有效热湿输运

直接位置：`data/sandbox/research/arlabosse2005/source.json:89–94`（吸附/解吸图未数字化）；`docs/sandbox/research/SOURCE_COVERAGE.md`“必须保留的来源异常”第2/6项及“湿坯热湿物性”行；`data/sandbox/research/wang_drying_digitized.csv`、`wang_digitization_audit.json`、`wang_midilli_reported_fits.csv`。

真正阻碍：纯水化学势/EOS不提供污泥水活度、吸附热、毛细压或随含水量变化的渗透/扩散。Araújo所印Arrhenius参数与表D数量级矛盾，不能静默修指数。Wang已有12工况186图中实验符号数据，但薄层污泥不是成型污泥—黏土砖；相同曲线的Midilli拟合不能当独立验证。必须验证的假设是：有效系数的材料、制样、含水基准和边界对应拟验证样品，且可迁移到目标湿坯。

现在可直接准入的是“来源条件化观测集/经验式复算”层级，未知吸附/毛细参数继续unknown。若选择Arlabosse同样品的低温干燥域，下一来源工作可只提取其已缓存吸附/解吸图并核定温度、含水基准；这仍不是三维砖传递系数的准入。

## 3. 烧结致密化、孔连通性及冷却力学本构

直接位置：`data/sandbox/research/areias2025/dilatometry_digitization/README.md:5–18`；`areias2025/facts.json` 的 `sludge.pretreatment`、`formulations`、`dilatometry`；`docs/sandbox/research/SOURCE_COVERAGE.md`“动态烧结与几何”“冷却应力”。当前运行case `data/sandbox/cases/reacting-wet-free-paired-events-endpoint-root-v1.json` 的 `mechanics` 下 bulk/shear modulus、viscosity、interface_energy、composition_beta 与输运系数仍为制造定义。

真正阻碍：Areias2025已有26个总轴向长度观测点，单一空气10°C/min历史，不可唯一分离热膨胀、反应产气/失重、自由烧结黏度及相变；没有横向应变、载荷/应力、开闭孔演化和冷却模量/破坏参数。预处理含石灰材料也不等于未经处理原泥。必须验证的假设是：由单轴总长度拟合的律代表本征自由烧结而非实验约束/热膨胀混合响应，且能预测不同热历史和冷却。这目前没有证据。

已有26点可进入来源明确的总轴向长度比较接口，不可直接反推三维n_i/t本构或预测强度。facts.json中`curve_digitized=false`及`prior_reference_read=false`是早期事实快照，后续digitization README和2019引用链研究已补充；不能把这些旧标记误读成尚无数字化/引用链核读，也不能由2019自动证明2025同批材料。

## 最有价值的下一次具体实现

实现一个与mol反应核隔离的 `ARLABOSSE2005_DRY_CP_EQ2` 有界、质量基准显热差组件：

- 明确原样品/source.json资产SHA、kg dry matter，308.15–378.15 K，两端都必须在域内。
- 原式 cp(T_C)=1434+3.29*T_C J/(kg K)。显热差
  Δh=1434*(T_C2−T_C1)+(3.29/2)*(T_C2²−T_C1²) J/kg。
  不必发明绝对参考焓；任意零点只作为显热差坐标，不注册为生成焓。
- 常数原打印十进制作精确有理数来源记录，输出包含测量/拟合误差unknown、无Cp外推、无反应适用性。解析积分、正Cp、端点/单位、能量差可加性、域外拒绝提供直接测试。
- 不补摩尔质量、固体体积、置信区间、伪组分化学式；不宣称cp测量等同当前体积受压路径的cv，也不把它装入已有 SolidShomateCaloric 来满足接口。
- 产物是一个真实来源限定材料热量关系及可审计的显热差能力，material_qualified仍为false、全周期仍未闭合。这是当前证据支持的可实现增量；若目标限定为“完整原泥材料包运行准入”，现有证据没有可直接通过的下一项整包准入。

以上三项是材料模型识别与适用性障碍；精确事件软件通过和全局守恒通过不会自动消除它们。
