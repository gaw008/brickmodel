# 污泥预制焦的图示氧化进度达时

此接口在原论文固定10 vol.% O2/Ar气氛下，用450/550°C两个作者拟合速率常数，插值计算指定等温标签下的图示进度达时。它适用于该文1000°C制备的污泥焦；响应为`alpha_plot`，不能据此获得质量库存、耗氧或反应热。

安装本项目后，在仓库根目录运行：

```sh
python -m sludge_sandbox char-oxidation-times \
  --source-data data/sandbox/research/nowicki2011-oxygen-interpolation-v1 \
  --temperature-c 500
```

默认输出0.1至0.8的八个预登记水平。也可加`--alpha-plot 0.2 0.5 0.8`选择所需水平。允许的温度域为450–550°C；它是限定的插值域，不能称整个连续温度域都已经实测验证。域外温度、域外进度及未知/非有限输入会被拒绝。

Python调用同一计算函数：

```python
from sludge_sandbox.nowicki_oxidation import calculate_nowicki_oxygen_times

result = calculate_nowicki_oxygen_times(
    "data/sandbox/research/nowicki2011-oxygen-interpolation-v1",
    temperature_c=500,
    conversion_levels=[0.2, 0.5, 0.8],
)
for point in result["predictions"]:
    print(point["alpha_plot"], point["time_s"])
print(result["trace"]["model.rate_s_inv"])
```

计算只读取冻结的`training.json`和`source_metadata.json`。`facts.json`中的500°C图值没有进入速率计算；改变或缺少训练文件会失败，不回填默认材料值。原PDF路径是来源记录，不会被当作程序执行。

`trace`逐项给出达时、图示坐标速率、温度转换及插值速率的实际依赖路径；`training.rows`保两个原值/单位/表格行，`source`保原文DOI、PDF摘要、材料制备、条件、许可和未解决的定义争议。路径中的数字是JSON数组下标，例如`training.rows.0.ks_s_inv`。

原Eq1打印归一化与递增图示conversion矛盾仍未解决。界面没有把`alpha_plot`改成绝对失重或碳摩尔转化；反应热、耗氧和产气计量保持null，也没有解温度反馈、能量守恒或有限氧库存。不要由本项指定等温响应推断整砖全烧成、原湿泥反应或MIA3焦反应性。

原图提取与读取界见[EXTRACTION.md](EXTRACTION.md)，模型和数据角色见[PREREGISTRATION.md](PREREGISTRATION.md)。数值输出的小数是计算精度，实验重复性与参数置信区间未知。
