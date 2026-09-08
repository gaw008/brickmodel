# 两水平因子实验与结果对比

此入口确定性生成1至3个因子的全部高/低端点组合，再调用已有实验服务。它分析限定输入区间内的变化，不能替代全局敏感性分析、不确定性传播或多代搜索。当前材料入口仍是manufactured_verification；科学模型范围不因新增实验工具而扩大。

每个因子记录路径、单位、低/高值及来源类别。初始温度是虚拟设计选择；制造材料的导热、扩散、反应系数只能保持制造参数类别，不得改标为公开实测。不接受网格、时间步、容差、物理常数、材料资格或测试开关作为工艺因子。各候选只改允许的数值输入，其余案例和数值策略一致。明确拒绝当前分支不使用的因子，避免把未接入的输入误报为零影响。

对响应Y和因子j，输出等权高水平响应均值减低水平均值，以及该差值除以指定高低输入间距。多因子时这是在其余因子端点上的平均对比，不是处处成立的导数。交互或非线性可能使不同条件下的影响不同。缺少任一必要结果时，不从成功子集估计对比值，也不填零。

统计方法定位：[NIST两水平主效应及交互效应说明](https://www.itl.nist.gov/div898/handbook/pri/section6/pri615.htm)。本实现不拟合概率分布、不进行显著性检验、不输出置信区间或Sobol指数；数值确定性不等于现实材料确定性。

在仓库根目录安装当前包后：

```sh
sludge-sandbox sensitivity-prepare data/sandbox/sensitivity/initial-temperature-contrast-v1.json --water-data data/sandbox/water --evidence-data data/sandbox --output /tmp/brick-sensitivity-new
sludge-sandbox experiment-run /tmp/brick-sensitivity-new/experiment
sludge-sandbox sensitivity-analyze /tmp/brick-sensitivity-new
```

取消、状态、继续执行仍使用experiment-cancel/experiment-status/experiment-run，目标为experiment子目录。来源设计文件及生成案例冻结并校验；分析使用每个经过核查的保存结果，记录结果与案例SHA。修改设计或升级求解器应建立新实验，不能混合旧评分。

示例只改变制造湿态模型的一格初始温度300至300.5K，用于检验通路。该区间为明确的虚拟选择，未声称对应本厂波动、材料统计分布或完整烧成热历史。与真实污泥相关的参数闭合、自由烧结冷却、完整周期及公开机制验证继续按Goal执行。

实际验证与已知范围见[验证记录](research/sensitivity-v1/README.md)。报告分别保存敏感性模块和指标计算模块的当前SHA，模拟器仍以每个原始运行的冻结身份为准。
