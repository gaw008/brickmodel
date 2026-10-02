# F 碳酸化来源数据单位接口候选

该模块为现有 F JSON/CSV 增加带来源的 SI 单位视图，并提供现有 P38 观测记录的单位视图包装入口。原始记录、来源位置、质量分母、实验条件身份和近似关系随结果保留。输出的迁移率准入始终为 `false`，不生成拟合输入或主机参数。

本次补丁只新增：

- `src/sludge_sandbox/carbonation_units.py`
- `docs/research/DIRECT_CARBONATION_UNIT_CLI.md`

现有 F 来源/观测文件、P38 `source_tg.py`、`observations.py`、根参数文件及包初始化文件均不修改。旧 fixture、外部下载快照和历史校验结果不进入该补丁。

## CLI

以下为合入后在项目根目录使用的命令说明，本轮没有执行这些命令。省略 `--output` 时输出到标准输出；指定文件时其父目录须已存在。输入路径相对于当前工作目录，`--project-root` 只指定 P38 模块所在项目。

读取主仓已合入的 F 数据：

```sh
python3 src/sludge_sandbox/carbonation_units.py f-data \
  --evidence data/research/direct-carbonation-workpackage-f/evidence.json \
  --output /tmp/f-carbonation-units.json
```

`f-data` 只读取指定 JSON 及其 `observations_file` 所指的相邻 CSV。源码没有访问 manifest 中的来源缓存路径、历史 `verification.json` 或 fixture。当前 F manifest 声明上限为三来源，源码读取该声明，不另设隐式上限参数。

转换一条调用方提供的带来源标量记录：

```sh
python3 src/sludge_sandbox/carbonation_units.py convert-record \
  --input /absolute/path/to/sourced-record.json \
  --output /tmp/carbonation-unit-record.json
```

`sourced-record.json` 必须显式提供下列字段。本文不附加合成记录或测试 fixture。

| 字段 | 语义 |
| --- | --- |
| `value` | 有限数值，不接受布尔、数字字符串或缺失值 |
| `quantity`, `unit` | 下表列出的物理量与原始单位 |
| `source_id`, `source_locator` | 实际来源身份及表、图、原始记录位置 |
| `basis` | 数值的原始质量、体积或其它归一基准声明 |
| `domain.identity` | 样品或实验条件身份声明 |
| `domain.source_id` | 必须与记录的 `source_id` 一致 |

来源、位置、基准和域身份不能用空串或 `unknown`、`pending`、`template` 代替。该检查核对声明是否完整且一致，不独立证实声明的真实性。

使用现有 P38 记录：

```sh
python3 src/sludge_sandbox/carbonation_units.py p38 \
  --project-root . \
  --config parameters.full_cycle.json \
  --record /absolute/path/to/existing-p38-record.json \
  --output /tmp/p38-carbonation-unit-view.json
```

`p38` 直接读取指定根参数 JSON，不调用 `load_case`。原始记录首先原样交给 `map_saeki2026_tg(config=config, record=record)`，旧接口报错直接传播；接受后才附加单位视图。该分支需要当前项目的 P38 模块和已有项目依赖。运行时无联网或下载步骤。

P38 记录仍使用旧合同：`quantity`、`measurement_kind`、`source_kind`、共同的 `source_id/source_locator`，以及 `sample`、`time`、`denominator`、`phase_separation`、`applicability` 和 `phase_masses.portlandite/calcite`。样品、时间和分母关联字段及身份配对要求由旧映射器检查，参见 [P38 来源 TG 合同](../FULL_CYCLE_P38_SOURCE_TG.md)。不能把整砖 TG、未分离峰或干基 CH 直接塞入此记录接口。

## 可导入 API

在已安装项目包的环境中：

```python
from sludge_sandbox.carbonation_units import (
    convert_record,
    normalize_f_evidence,
    load_f_evidence,
    map_p38_record,
)
```

| 入口 | 输入与输出 |
| --- | --- |
| `convert_record(record)` | 一条显式来源标量；返回原始记录和转换过程 |
| `normalize_f_evidence(evidence, observations)` | 已读取的 F manifest 和 CSV 字符串行字典列表；返回带原始数据的条件/观测单位视图 |
| `load_f_evidence(evidence_path)` | JSON 路径；读取声明的 CSV，返回上述视图及输入文件路径 |
| `map_p38_record(*, config, record)` | 当前根参数字典和旧 P38 记录；返回完整旧映射与附加 SI 视图 |

独立文件 CLI 的 `f-data`/`convert-record` 及 F API 模块只使用标准库。当前 `sludge_sandbox.__init__` 只声明版本，常规导入该模块不会经 `sludge_vme` 初始化导入模型。P38 函数在调用时才导入 `sludge_vme.inverse.source_tg`；其包初始化仍会加载当前项目的模型/逆向搜索定义和 NumPy/SciPy。该函数没有调用主机科学计算、优化或拟合。

## 单位与原始基准

转换表中的数值是单位定义，不是材料参数。P38 的摩尔质量数值始终来自调用方根参数文件，不在此模块硬编码。

| `quantity` | 接受的原始 `unit` | 目标单位 |
| --- | --- | --- |
| `time` | `s`, `min`, `h`, `d` | `s` |
| `temperature` | `degC`, `K` | `K` |
| `fraction` | `1`, `percent`, `vol_percent`, `ppmv` | `1` |
| `specific_area` | `m2/g`, `m2/kg` | `m2/kg` |
| `density` | `g/cm3`, `kg/m3` | `kg/m3` |
| `specific_pore_volume` | `cm3/g`, `m3/kg` | `m3/kg` |
| `length` | `um`, `mm`, `m` | `m` |
| `pressure` | `Pa`, `kPa` | `Pa` |
| `mass` | `mg`, `g`, `kg` | `kg` |
| `molar_mass` | `g/mol`, `kg/mol` | `kg/mol` |
| `mass_ratio` | `g/g`, `kg/kg` | `kg/kg` |
| `CH_per_dry_reference` | `g_CH/100g_dry_reference` | `kg_CH/kg_dry_reference` |

基础标量单位视图记录原始数值/单位、量纲类别、倍率、偏移、公式、来源位置、基准和域；派生分压及 P38 已转换秒值使用各自的来源/公式结构。数值与转换结果必须有限，符号保留，不做裁剪。`temperature` 只声明绝对温度，摄氏温度使用绝对温标偏移；温差与温度误差没有受支持的量纲类别，调用方不得把它们标为 `temperature`。接口不依据自由文本 `basis` 自动辨认这些语义。

F 条件视图转换温度点、外部 CO₂ 体积分数、比表面积、RH 点/界限/历史及历史时长。CO₂ 分压只在显式总压和 CO₂ 数值同时存在时按乘积派生；当前来源总压缺失时保持 `null`，不假设常压，也不把外部边界当孔内分压。条件中的温度范围、关系和报告误差等其它字段完整留在 `original`，没有被这个最小接口自动转换为新端点或不确定度。

F 观测视图转换时间值/界限和数值值/界限/读图误差。CSV 的每一原始字符串行完整留在 `original`；`time_relation`、`observed_relation`、提取方法及 `history_or_basis` 保留。读图精度与作者报告的不确定度只缩放单位，不做传播或同化；定性记录不生成数值分数。

比表面积的质量基准与观测分母分别声明：`condition_material_basis_id` 只标识实验材料，`observation_basis` 和原始 `history_or_basis` 描述观测基准。BET 的 `m2/g` 换为 `m2/kg` 不把含杂粉末换成活性 CH，也不换成砖体积。残余 CH 的干基质量比不变成初始 CH 转化率。当前 Arias 高温脱水后 CaO 碳酸化排除说明随原始来源/条件保留。

P38 附加视图保留 CaO 点火参考分母；`g/g` 与 `kg/kg` 数值相同不等于可换成整砖分母。旧 `DoC_CH`、`DoC_Cc` 和 `DoC_CH_minus_DoC_Cc` 原样放在 `P38_mapping`，不改初始碳酸盐处理、不强制一致、不裁剪。摩尔质量视图引用根参数的公式来源、公式位置及独立常量域，原始参数字典完整保留。

F 支持天单位不扩大 P38 时间合同；P38 仍首先由旧单位转换器处理输入，拒绝的时间单位不会被本模块预转换成秒。P38 拒绝的相质量百分比也不会被预转换成 `g/g`。`admission` 保留旧映射内容，外层另明确 `mobility_admitted: false`。

## 交付审查状态

只读核对时主仓为 `f9a3abdf3fbdec790874025ba44d0ac4fae492d2`，F 数据为三来源、十二条件、二十三观测记录。此次只做源码和数据字段的静态人工审查；没有执行候选 CLI/API、`--help`、语法编译、换算、测试、模型、SHA 校验和生成/比对或 patch 应用检查。不能把该候选称作运行验证通过。

本轮静态审查收敛了常量/观测来源混接、单位结果有限性及包导入依赖问题，并移除未接接口的旧速率助手。旧验证或 fixture 不作为此生产候选的验收证据。主工程集成后实际部署可用性仍未验证；本轮没有新增材料实测，也没有改变已有失败、零实测或迁移率未知结论。
