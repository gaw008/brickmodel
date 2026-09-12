# 纯方解石热化学接口

当前接口计算指定温度下的纯物质标准反应焓、热容差，以及指定反应进度对应的产气质量。三种物质都采用同一USGS评估，输入温度为 **298.15–1200 K**。1200 K为926.85°C，不能覆盖MIA3的1150–1180°C峰值。

在已安装本项目的Python环境、仓库根目录运行：

```sh
python -m sludge_sandbox calcite-thermochemistry \
  --source-data data/sandbox/research/calcite-thermochemistry-v1 \
  --temperature-k 800 --extent-mol 0.1
```

Python调用同一个函数：

```python
from sludge_sandbox.calcite_thermochemistry import calculate_calcite_thermochemistry

result = calculate_calcite_thermochemistry(
    "data/sandbox/research/calcite-thermochemistry-v1",
    temperature_k="800",
    extent_mol="0.1",
)
print(result["reaction"]["enthalpy_j_mol_extent"])
print(result["reaction"]["mass_changes_kg"]["carbon_dioxide"])
print(result["trace"]["reaction.enthalpy_j_mol_extent"])
```

例中0.1 mol是明确指定的CaCO3消耗量，其名义CO2增量为0.004401 kg。程序没有初始砖坯库存，因此不判断该进度是否可由某块砖实现；它也不预测反应速度、达到该进度的时间或平衡方向。正反应焓表示该指定同温转化的标准焓差，不是实际窑炉耗能。

`species`保留每一相的原始形成焓/不确定度、原Cp系数、名义省略项解释及计算值。`trace`中每项依赖均为结果JSON内的实际路径，可从反应焓追到三相储能坐标、显热积分和原书打印/PDF页码。`source`提供完整书目、原PDF URL/SHA、两份提取文件SHA及实际阅读范围。来源的上游论文未全部核读，不能由编译表核读升级为全部实验认证。

运行只需要本目录的`facts.json`和`source.json`，不下载资料、不调用水EOS、不执行元数据中的文件路径。变更任一已核读提取文件、非普通文件、非有限输入、负进度及域外温度会被拒绝。数值运算使用固定80位十进制上下文；这些计算小数位不是实测精度，也没有被当作高温物性误差。

已核读原PDF另保存在本地忽略目录`runs/sandbox/source-cache/usgs2131-20260912/usgs-b2131.pdf`，SHA256为`ca89fc07fd110a0441f3bc01d5fe67d749a944da2e7f2537520dbaf367f49dd8`；它与来源记录中的原下载件字节相同。该缓存不随Git分发，原来源记录保留获取时路径。

`uncertainty.reaction_enthalpy_uncertainty_j_mol`保持null，因为跨物种协方差与高温拟合误差未获依据。298.15 K的固相体积保留为原始信息，不作为高温体积定律。动力学、平衡、MIA3矿物库存和全周期资格分别保留未完成。
