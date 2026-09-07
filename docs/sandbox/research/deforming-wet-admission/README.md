# 规定变形主机的边界/相变组合与当前孔隙修复

`original-evidence.zip`保存隔离候选、基线、原失败、计划、测试、单次真实回调及独立审核。归档逐项读取验证原字节，成员大小和哈希见 `archive-manifest.json`。临时缓存排除；测试所需历史源码在 `baseline/` 另存原字节副本。三份审查和设计可直接阅读。

原7项无EOS接入测试通过。callback01在相变化学前被体积一致性门禁拒绝，未算作相变通过。修复将当前点storage的流体模板孔体积设为当前bulk减固定固体占积；保留原热储能计算与体积不确定性。先失败回归及最终9项无EOS测试和独立复核均保存，没有绕过门禁。

callback02保持原材料fixture、原K与比较门槛，仅修复当前几何并改善运行记录。使用独占目录和已审查的外部监督器，实际1.387秒/exit0，声明113项输入绑定保持。原生化学势操作数、独立peq/速率、液汽成对源、五类功、当前几何和单次反解均检查通过。其原1e-5J/1e-4K反解与另一个未通过的湿态轨迹病例不同；此处不替代后者的1e-6J/K及孔压功门槛。

应用4个源码文件后，测试只重定位历史路径及使用真实安装模块的 `__file__` 做AST比较；全部原断言保留。资格文本只删除过时的not_wrapper_admitted，仍明确规定固定固体总能量且非自由烧结。

实际应用验证命令：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_deforming_wet_admission.py tests/sandbox/test_deforming_solid_storage.py tests/sandbox/test_deforming_solid_heat.py -q -k 'not convergence' --junitxml=docs/sandbox/research/deforming-wet-admission/applied-tests.xml
```

实际34项通过、73.00秒。该筛选词没有排除名为`test_dry_compression_analytic_and_actual_accepted_components`的细网格测试，因此这次确实验证了最终代码的完整干态压缩案例；没有将其误写成34项轻测。XML保留，未另保存该命令stdout日志。

当前通过范围是有限软件组合、当前孔隙上下文及单次来源匹配相变回调。变形湿态时间收敛、耗尽事件、真实原污泥烧结本构和全周期外部实验仍未完成。
