# 显式保存参考面初始化

`initial_partition.profile_by_mode` 的3映射 `saved_faces`，仅该分支读取 `faces_parameter`，以米为单位。明示faces必须有cells+1个位置、严格递增，从0到给定half_thickness；体积为area×面间距，中心为相邻面中点。原 uniform/exterior_power 入口和名义mode0不变。

离线源码 API：

```python
from sludge_vme.models.full_cycle import read_parameters, saved_reference_partition_case
from sludge_vme.models.initial_finite_volume import initial_partition_from_faces
root = read_parameters('parameters.full_cycle.json')
case = saved_reference_partition_case(root)
```

case从 `public_reference_cases.saved_reference_partition.parameter_records` 完整复制数值、单位、范围、来源、身份和note；root保持名义12格，case为声明的13格与mode3，不用环境变量或代码硬编码faces/13。原语要求faces/cells/half_thickness/area全显式提供。源码API按项目既有源码导入方式使用；新脚本自行沿用examples源码定位，不依赖旧Desktop editable路径。

生产脚本形式如下，输出父目录由调用者准备；参数值与来源均读统一root：

```text
.venv/bin/python -B scripts/materialize_saved_reference_partition.py parameters.full_cycle.json --case-output CASE.json --geometry-output GEOMETRY.json
```

P49唯一实际转换已完成，30秒／512KiB／1job／1primitive窗口已关闭；上式是接口说明，不授权再次运行。实际输出位于 `runs/full-cycle/p49-saved-reference-partition/case-parameters.json` 与 `geometry.json`。既有reader已实际读回生成case；保存faces/中心/宽度一致，两个体积basis与signed差原样报告。P49global使用NumPy sum，原Hglobal使用math.fsum，原H诊断另留output-readback。

生产主机按mode3静态接线，复用既有逐格库存及尺度，尚未构造或积分。当前13格模型、C采样、守恒/热力学/加密/八阶段与比较/反演/模型CLI未资格。运行期无外网、下载、CDN或新依赖。
