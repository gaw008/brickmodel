# 实际验证报告：G0/G1 基础模块

日期：2026-09-07 UTC；平台 macOS arm64，Python 3.12.13。本报告只有已实际运行的验证，不代表完整 Goal 验收。

## B2 历史修复

源提交：`0634e80b1fa4d69c195022f1c7ecd79a16110fe2`。

| 实际运行 | 结果 |
|---|---|
| `run_tests.py` 指定新输出目录 | 14单元测试；全部8类NUM门槛passed；绑定bound |
| focused实际积分数 | B2 30 + B1 4 = 34；没有漏掉单元测试内2次调用 |
| `run.py --suite frozen --verification ...` | 22情景integrated，全部passed_frozen_suite |
| 独立 `audit.py` | 322204 checks通过，固定门槛1e-6未变 |
| 最大反应暴露误差 | 6.917104489190251e-8 |
| focused资源 | 77.61s，peak RSS 41.52MiB |
| 22情景资源 | 15.92s，peak RSS 94.63MiB |

命令、实际源码/输入/结果和校验包见 `research/b2-bound-0634e80/summary.json` 与 `reproduction.tar.gz`。原失败根因与未绑定隔离复跑保留在 `B2_ROOT_CAUSE.md` 和原始目录；未冒充当前绑定运行。打包成功不等于整个离线包已做全部重新积分。

该结果只验证原B2固定孔隙、给定温度、synthetic域。不提供真实材料参数或完整湿砖能量验证。外部`time -l`曾受sandbox kern.clockrate限制，未把其非零退出隐藏成成功；上述耗时/RSS来自实际内部计量。

## 新内核模块

源码模块位于 `src/sludge_sandbox/`；相应测试位于 `tests/sandbox/`。

| 模块 | 实际覆盖与边界 |
|---|---|
| evidence / units / geometry | 56项：分类、未知、适用域、方程依据根、布尔/非有限输入、单位、共享面积/孔容；不是材料外部验证 |
| materials | 25项：干湿料账目、额外加水、原泥/SSA分组、独立分析类型、矿相身份声明与非法值 |
| thermochemistry | 41项：真实NIST原值、分段范围、cp/h/u关系、反解、多解/间隙/精度不足/溢出；原拟合未平滑改写 |
| gas_transport | 79项：全气体库存/EOS、压差反馈、质量平均修正/上风Darcy、零库存方向、一阶修正离散收敛、归一化诊断 |
| exchanges | 10项：半格导热、气温/辐射环境分离、实际物种焓耦合、R一致性、净流与分项一致、相反溢出拒绝 |

独立审查报告分别在 `research/CODE_REVIEW_*` 与 `PHYSICS_REVIEW_GAS_TRANSPORT.md`。首审问题和修复前失败均保留。气体中心修正曾破坏零库存不变域；改为修正漂移的上风组成后，另150场景/450分项方向检查通过，最大全扩散质量相对舍入6.34e-15。这个离散是一阶数值处理，尚无完整PDE时空误差声明。

NIST 的原文表值核对是移录/拟合函数验证，不能称独立现实实验验证。热化学审查还使用独立求积、Decimal能量及反例；全部范围见其报告。作者/代理审查不等于外部专家认证。

## 干净安装的实际检查

从空目录创建 `/private/tmp/brick-sandbox-g1-install-20260907`，以冻结锁文件、非editable、离线方式安装。未设置 `PYTHONPATH`，从 `/private/tmp` 运行仓库的sandbox测试，实际导入位置为该环境的 `site-packages/sludge_sandbox`。

```sh
UV_CACHE_DIR=/private/tmp/brick-sandbox-uv-cache \
UV_PROJECT_ENVIRONMENT=/private/tmp/brick-sandbox-g1-install-20260907 \
uv sync --frozen --no-editable --extra dev --extra research --offline

env -u PYTHONPATH /private/tmp/brick-sandbox-g1-install-20260907/bin/python \
  -m pytest /Users/wanggaoying/Desktop/brickmodel-github/tests/sandbox -q \
  --junitxml=/Users/wanggaoying/Desktop/brickmodel-github/docs/sandbox/research/g1-installed-final-tests.xml
```

最终结果：**211 passed，0 failed，0 skipped**。首次非editable测试与最后类型注解同步后的测试分别保留，不覆盖首份证据。最终XML为 `g1-installed-final-tests.xml`；依赖/实际导入位置/首次pip离线解析失败说明在 `g1-installation.json`。冻结 `uv sync` 复用了已缓存锁定轮子；这不表示没有缓存的任意新机器可以不下载依赖。

这个检查只证明包安装、导入与上述模块测试。新CLI/UI、数据准备命令、全周期求解、搜索和恢复还没有通过安装流程，不把它计作完整 V12/U01–U04。

## 对现实的验证状态

已提取 Wang 2021 的12干燥条件/186图中实验符号读数；40/60°C拟合、50°C留出的计划已登记，但尚未执行内核预测对照。Nowicki和Mohajerani的参数/条件/语义问题仍隔离。三个机制组的独立预测对照、完整原污泥材料域与整砖耦合验证均未完成。

`software_status=implementation_in_progress`；`scientific_status=partial_sources_no_complete_raw_sludge_domain`；`deployment_status=offline_research_only`。本 Goal 保持 active。
