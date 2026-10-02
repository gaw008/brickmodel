# 显式湿度入口候选

生产API接受既有read_parameters已读取根配置；CLI复用该读取入口，未另设finite/range/source/status通用校验层。只保留换算所需单位、同温、参考相及气氛合同。当前根未提供RH/Psat；本轮不调用转换或填入未知null，不改入口/温压/阶段边界。

## 根输入合同

`examples/humid_gas_boundary_contract.fragment.json` 是待主集成填写的根字段片段。
所有 `null` 均代表缺项，不能作为已知量或实测输入。填写数值、声明范围、
source 注册项、status 和参考相之后，由主集成合入根参数文件；不要用该片段
替换整个根文件。代码不会替用户执行合入。

合同在 `humid_gas_boundary` 中按参数键显式命名以下输入：

- `relative_humidity_parameter`：RH，单位 `1` 或 `%`，不能缺单位。
- `total_pressure_parameter`：总压，单位 `Pa`，必须正。
- `temperature_parameter`：RH 与饱和蒸气压对应温度，单位 `K`，必须正。
- `saturation_pressure_parameter`：该温度下饱和蒸气压，单位 `Pa`，必须正；
  该参数条目还必须含同一个 `temperature_parameter` 和
  `reference_phase`，后者为 `liquid_water` 或 `ice`。
- `dry_mole_fraction_parameters`：按实际根物种完整覆盖除 H2O 外的干气，
  每项单位 `1`；输入为摩尔分数，不能将质量分数或摩尔份额当作摩尔分数。
- `output_source` 与 `output_status`：显式声明派生入口的来源和身份，
  status 沿用 `literature`、`assumed`、`measured` 约定；转换本身不新增实测。

每个输入参数沿用根格式 `value / unit / range / source / status`。source 必须
在同一根文件的 `sources` 注册。模板共用的输入来源可以拆为不同来源；
不得为了填写模板而将未知量称为 measured。
压力、温度键也可以指向既有根参数，但这表示显式接受其现有声明与身份。

## 公式和边界

`RH_fraction = RH_percent / 100`（百分数输入时），
`p_H2O = RH_fraction × p_sat(T, reference_phase)`，
`x_H2O_wet = p_H2O / P`，
`x_i_wet = (1 − x_H2O_wet) × x_i_dry`。

采用用户指定的理想气体分压口径。NIST 原文说明理想气体混合物中 RH
可表示为水蒸气分压与同温饱和分压之比，见
[The use of dew-point temperature in humidity calculations](https://nvlpubs.nist.gov/nistpubs/jres/74c/jresv74cn3-4p117_a1b.pdf)。
[NIST 湿度不确定度论文](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=901715)
明确区分纯液水/冰的参考相及非理想增强因子；本模块不引入这些未提供的修正。

工具不计算或猜测 p_sat，不联网获取气象、材性或压力。
RH 不得负，水分压不得超出 `[0, P]`。若调用者范围允许 RH > 1，
工具保留该值并记录相对于声明参考相的过饱和，不隐式把它改为 1。
干气组成必须闭合，不自动归一化。RH=0、纯水蒸气或任何零干气分量
转出的入口不满足现有主机严格正条件，会报 ValueError 并解释该限制，
不加 epsilon、不添加未知痕量、不 clip。饱和压来源的温度适用性由显式
声明及来源承担，本工具不验证一个任意 p_sat 数值是否具有实测或物性准确性。

## 集成和调用

补丁仅新增两个生产文件。主集成审阅后，在主工程使用：

```sh
git apply --check /Users/wanggaoying/Documents/Codex/2026-10-01/task-9/humid_gas_boundary.patch
git apply /Users/wanggaoying/Documents/Codex/2026-10-01/task-9/humid_gas_boundary.patch
python scripts/build_humid_gas_boundary.py ROOT_PARAMETERS.json --out HUMID_INLET_CANDIDATE.json
```

CLI 在项目已安装的 Python 环境中调用。所有物理参数只从根 JSON 读取，
没有数值命令行默认值或环境变量注入。输出使用新文件创建模式；已有输出
文件会报告 FileExistsError。`--out` 必须由调用者选择，工具不会写回输入根。

API：

```python
from sludge_vme.models.gas_boundary_inputs import build_humid_gas_boundary
from sludge_vme.models.full_cycle import read_parameters
candidate = build_humid_gas_boundary(read_parameters(ROOT_PARAMETERS))
```

输出 `candidate_root_fragment.parameters` 是完整的目标参数条目，单位仍为 `1`，
range 按目标根原样保留，source/status 来自显式输出声明。
`candidate_root_fragment.humid_gas_boundary_provenance` 保存合同、原始输入条目、
原入口条目、所引用来源注册项、温度、参考相、分压、干/湿基组成和闭合残差。
`integration_context` 同时给出原主机温压、输入温压是否一致、范围冲突以及
独立阶段气氛参数的名字。主集成必须据此决定候选根片段如何采用；
仅修改 inlet 不能自动将全部阶段转换为恒定 RH 边界。


本轮仅静态语法/接口审查；该CLI导入已有VME/NumPy/SciPy依赖，非纯stdlib部署入口。无新增依赖、物性或实测。
