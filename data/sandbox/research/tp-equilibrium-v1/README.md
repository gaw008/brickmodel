# 受限 CHONS TP 平衡来源包

固定 Cantera **v3.2.0** 的 18 种 NASA7 气体和纯 `C(gr)`，用于 800–1200 K、100000 Pa 的理想气体/石墨组成计算。候选物种和元素池是显式设计；未包含焦油、矿物、其他固碳和全部硫产物，不能据此报告真实污泥产气率、反应时间或升温热耗。NASA7 常数已包含形成焓，禁止再次叠加。

`original/` 是官方发布原件，SHA 和公开 URL 见 `source.json`；原许可原文保存在 `LICENSE.txt`（BSD 式三条条件）。`derived.json` 只选择固定记录并显式添加每个物种的参考压力 100000 Pa，原 NASA7 系数、组成和温度区间不改。JSON 也是可供 Cantera 读取的 YAML 子集，没有动态扩展、外部物种导入或反应机构。

此参考压力选择有意区别于原分发文件的缺省 101325 Pa。NASA TM4513 第 1–2 页说明原数据采用 1 bar；来源代理已目视第 33 页 H2S、第 39 页 N2、第 55 页石墨的代表系数，并未声称逐原页重新核过全部物种。派生分支名为 `NASA1993_1BAR_EXPLICIT_REFERENCE_V1`，属于从证据推导的元数据纠正，不是把输入 P 偷换为标准态或修改熵常数。1000 K 等号归 NASA7 低温段，沿用 Cantera v3.2.0 的实际分支规则。

公共库存为 mol，Cantera 的绝对库存与摩尔物性分别为 kmol 和 J/kmol 系，入口/输出显式换算并保留投影差。实际 R 和原子量随结果记录，不宣称逐末位重现 1993 年的维度表值。模型小包的 SHA、分类、未知项和资格见 `model.json`；运行成功仅表示该限定模型的名义数值检查通过。

安装项目的 `equilibrium` extra 后，从仓库目录运行例如：

```sh
python examples/sandbox/run_tp_equilibrium.py --source-root . --output tp-example.json --temperature-k 1000 --carbon-mol 1 --hydrogen-mol 1.6 --oxygen-mol .6 --nitrogen-mol .1 --sulfur-mol .01 --basis-id virtual_CHONS_C1_mol
```

此命令显式使用虚拟元素池，并非 1 kg 原污泥配方。已有输出文件会被拒绝覆盖。模块墙钟限只在调用边界检查；需要强制终止失去响应的原生调用时，应另用外部进程监督。
