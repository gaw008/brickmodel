# 数据语义审计：DTU 材料设计 v2

状态：只读公共数据重分析，待独立审核；源文件未改写。

## 总量与完整覆盖

{{COUNT_TABLE}}

四本工作簿全部 {{SHEET_COUNT}} 个sheet、{{AUDIT_ROWS}} 个非空行均有逐行处置记录；row_audit.csv 给出每行选取/排除地址及理由。sheet_audit.json 记录真实维度、可见状态、合并范围、显式空单元格、公式缓存和错误；它不是仅根据Excel最大行号估样本数。

“选取单元格”包含导出的源值和使用的条件地址，不等于样本；未选单元格也可能是已读取的标签/实验说明。“排除”仅指不作为独立分析观测导入，不表示删除、数据无效或材料物理不可行。

{{SHEET_TABLE}}

每个sheet的非空单元格数 = 选取数 + 排除数。Excel仅有格式的空单元格计入 explicit_blank_cells，不计非空行；XRF预期属性的缺项在materials.csv留空，未用零替代。

## 样本与派生层级

- XRF：7个原始标签的组成向量；另外12列“Calculated in clay brick discs”为0/30%混配计算，不是12次独立XRF测量。后续转置表/元素换算图表不重复计样本。[1]
- TGA：7条独立标签曲线；每条曲线的温度点和DTG通道不是独立材料样本，也不能随机拆为train/test。单一10 K/min N2曲线不唯一识别可靠动力学。[2]
- PSD：6列分布，4列身份可配对；每条100个粒级，累计量和粒径阈值画线不是新分布。O/Q两列的#0179身份冲突不参与组成—物性配对。[4]
- 圆片：36个“基料×灰/处理×温度”系列、每系列7片，共252片；每片尺寸三次读数，饱水只测试其中A/B/C三片，共108片。A2P的6个系列/42片不参与定量方向图。[3]
- 有效图示：30系列，直径共210片、饱水共90片。两张图重复展示同一系列，不再增加样本数；组均值的CSV含全部成员ID，第二图横轴n=7、纵轴n=3，明确不是逐片回归。
- 不独立：同系列重复件、同片三次卡尺读数、同质量g/kg转换、P&D列M与R重复孔隙率、所有Figures与P&D 2表，以及XRF元素转换表。

特别发现：High and Diameter!AR139:AT139（R-P2-ED / 1030°C / G）的三个烧后高度值是同列133:138行其他六片的AVERAGE，而不是G片实测。按source_derived保留并独立复算这三个填充值；其烧后高度均值、烧后几何体积、高度/体积收缩不计独立统计。该组体积收缩n=6、其余组n=7，group_summary.csv有n_volume及volume_specimens；直径读数未填补，故两图直径n=7与饱水n=3不受影响。详情见source_imputations.json。此前“全部高度都可按七片统计”的假设不成立。

## 身份映射与未解决冲突

| 原标签/线索 | 采用的解释 | 证据/处置 |
|---|---|---|
| #0250 / Ys / Y | Y，高碳酸盐黄砖基料 | Overview!B6、XRF!B1/B26与组标签、TGA!B16、共用README |
| #0252 / Rs / R | R，低碳酸盐红砖基料 | Overview!B7、XRF!C1、TGA!B16、README |
| #0262 / SSA-Av-Raw | SSA-P1-Raw，未后续处理的焚烧灰 | Overview!E6、TGA!B16、PSD!F4:F5、README |
| Pilot-8 / SSA-Av-ED | SSA-P1-ED | Overview!E7、TGA!B16、PSD!H4:H5 |
| #0263 / SSA-Ly-Raw | SSA-P2-Raw | Overview!E8、TGA!B16、PSD!J4:J5 |
| Pilot-10 / SSA-Ly-ED | SSA-P2-ED | Overview!E9、TGA!B16、PSD!L4:L5 |
| #0179 / A2P | identity_ambiguous | README/Overview称P2-A2P；P&D原表C120称SSA-Av-A2P；H&D A158称SSA-Ly-A2P，A176又称Av-A2P；PSD O4/Q4同为#0179但O5为Silica Sand uncrushed、Q5为P1-A2P (unmilled) |

A2P/#0179 原标签完整保存在材料行、conditions.json、源单元格和逐行审计中；不猜测改成P1或P2。按保守策略将原料 #0179 material_class 标unknown，将其所有原料向量/曲线与A2P圆片隔离。数字仍保留用于审计与源算式重算，数值重算正确不等于身份正确。

P&D表M4/M5还留有“E21-F21-G21-H21”与“#0010 Avedøre-krüger-1”说明，这与本实验Overview记录不一致。采用的是逐系列标签、三原始表的矩阵/灰标识和精确质量引用链，而不是该全局旧模板说明；这能证明表内配对一致，不能证明真实实验室chain-of-custody。故已保留这条全局不确定性，不将resolved解读为独立材料鉴证。

已实际查原论文：ScienceDirect返回摘要/highlights，DTU Orbit返回开放PDF线索；PDF下载HTTP403，web_extract失败，Wayback HTTP429。全文未读，不能据未读方法解决A2P冲突。另读到原污泥研究的具体方法，以说明气氛/反应层边界，不用来改写DTU标签。[5][6]

## 单位、干基、几何与热历史

- Mixing!D15:E17明写dry，参照25 g基料+0 g灰，含灰17.5 g基料+7.5 g灰；逐系列实际记录质量亦验证这一比例。`additive_fraction_dry=ash_dry/(clay_dry+ash_dry)`；加水不进入分母。单位/干基未知返回unknown，不按湿基推测干基。
- XRF wt%为源“总测得氧化物+1050°C LOI”的报告基础；保留xrf_LoI与xrf_Total以及缺项。没有重新归一化到100%，没有把氧化物总量误当全部矿物相。源XRF混配计算采用0.7/0.3，不是烧后实际测量的混合物组成。[1]
- XRF原表R的LoI为8.2%，不能用它当原污泥挥发分或碳酸盐分数；TGA与XRF的终温/样品制备不同，不能强制两者失重相等。
- 卡尺mm；源几何体积mm3；正收缩=100×(干燥尺寸−烧后尺寸)/干燥尺寸，负值按实保留。体积收缩不是直径收缩，二者字段分开。
- 饱水质量源g；计算体积m3使用1e−3换kg，水密度按源L10=998.2 kg/m3；开放孔隙m3/m3，吸水率kg/kg，图中转换为质量百分数，绝不混当体积孔隙百分数。[3]
- 表中“m105”实际通过源公式指向烧后的干试件质量（例如P&D!E14→Water and Burning!F9）；并非成型后105°C的烧前质量。这一引用已逐片验证。
- N2-TGA保留仪器B17实际初始质量和带符号的C列mg变化，不将其自动变成正的失重率。元数据称35–40 mg，而#0250为30.1207 mg、#0179为33.5031 mg；采用逐曲线仪器记录并标明元数据范围差异。[2]
- DTG是仪器给出的导数通道，标source_derived；其内部平滑/求导窗口未知，material_evidence.json明确unknown_instrument_algorithm，未把它算作独立实测通道或声称已重建其算法。
- TGA元数据：黏土50°C干燥7天、SSA105°C 24h；制样Overview写黏土50°C 6天，与TGA不是相同处理记录，不合并。这一小差别也不能用经验静默修正。
- 砖圆片的烧成气氛/升温速率/保温时间尚未核实，留空/unknown；“Water and Burning”标题950-1000-1050为模板，实际区块标题和Overview均为1020/1030/1050。Mixing的with sand字样按原厂供料标签保留，未获得额外砂配比，不发明砂加入量。

## 公式与缓存：外部源值重算，不是自证

全部 {{FORMULA_COUNT}} 个公式（包括共享公式的从属单元格）已清点并导出formula_audit.csv。没有调用Excel、执行公式、刷新外部链接或重存原工作簿。只有有明确原始输入和已知算式的子集独立计算，其余明确not_recomputed。

{{RECOMPUTATION_TABLE}}

例：P&D!M14的开放孔隙由原始g数值独立计算 `(3.364−2.8395)/(3.364−1.803)`，得到 {{POROSITY_RECALC}}，与源缓存 {{POROSITY_CACHE}} 比较；dry_density用 `(2.8395×998.2)/(3.364−1.803)`，而不是从自己的CSV互相推算。H&D!W9从六个原始直径读数独立计算，而非拿F9/Q9的源均值互证。

导出的每个source_derived观察都有derivations.json中的输入地址、Python算式描述、源公式与缓存值、重算值、差值和容差；materials中不允许新增evidence列，所以材料证据状态放material_evidence.json。组均值/标准差有group_summary.csv与chart_data.csv中的成员ID/方法。派生值不伪装measured。

### 发现并隔离：TGA百分比列不是本地质量列的可靠归一化

Pilot-10、Pilot-8、#0262、#0263 的 D 列公式均引用 `Table27[[#This Row],[Mass loss/mg]]/B$17*100`。OOXML的sheet6关系指向table12.xml，其Table27属于#0262，不是各sheet自己的C列。故跨材料D列不能直接用于温度—失重配对。

独立检查本地 `100*C(row)/B17` 的 {{TGA_DIAGNOSTICS}} 个有温度点，与D源缓存有 {{TGA_MISMATCHES}} 处不一致；这只证伪“D就是本地C归一化”的假设，并非执行了完整Excel结构引用语义。#0262本地的864点匹配，其他三表不匹配。Pilot-8!D896是没有A/B/C/E原数据的孤立公式缓存，不生成曲线点。全4张的3456个D公式均排除，未作动力学输入或源“修正”。原C质量信号仍保留。

## 缺失、排除和不能做的事

materials.csv有 {{MISSING_MATERIALS}} 个缺失值（XRF的CuO/ZnO/SrO/BaO在两种黏土中留空）；其余数值为源数据，不做零填补。导入观察值没有缺失不意味着试验所有属性齐全：A2P身份、热历史、强度、黏度、液相、闭孔/连通孔、实际排气/供氧全部是不同层次的unknown。

公式缓存没有空/错误不等于公式科学正确；TGA例子已经说明这一点。材料身份、热历史和样本层级是更高优先级的约束。所有非空行的未用地址都在row_audit.csv中给出理由，读者可定位原表复核。

没有把孔隙率转换成认证强度；没有把单速率N2-TGA解释为空气氧化；没有校准/交叉验证或工厂适用声明；未使用其他工业污泥冒充市政原污泥。开放数据许可证及作者、DOI保留于source_registry.json与SVG图注。[1][2][3][4]
