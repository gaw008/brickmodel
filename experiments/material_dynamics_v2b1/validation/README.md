# 真实执行证据索引

本目录为本次实现的持久验证日志，不依赖2A scratch或Hermes会话继续存在。

- `focused_tests.log`、`test_results.json`：`python3 experiments/material_dynamics_v2b1/run_tests.py` 实际返回exit 0；14 tests，0 failure/error/skip；日志记录完整测试名称、执行时间与Python版本。
- `demo_run.log`：`python3 experiments/material_dynamics_v2b1/run.py --out experiments/material_dynamics_v2b1/artifacts` 的真实stdout/stderr；12情景全部integrated，整体passed。
- `demo_resource.log`：`/usr/bin/time -v -o experiments/material_dynamics_v2b1/validation/demo_resource.log python3 experiments/material_dynamics_v2b1/run.py --out experiments/material_dynamics_v2b1/artifacts > experiments/material_dynamics_v2b1/validation/demo_run.log 2>&1` 实测，exit 0；外层wall 34.29s，峰值RSS 42056 KiB。内部计时34.225562s、41.0703125 MiB，1线程/1worker。
- `deliverable_checks.json`：`python3 experiments/material_dynamics_v2b1/inspect_results.py > experiments/material_dynamics_v2b1/validation/deliverable_checks.json` 实际返回exit 0；再次独立审计库存/flux，并核对两张SVG与原始导出：16条轨迹、3216对坐标、24个柱形。
- `../artifacts/verification.json`：不是预期值文件；包含本次7/15/31格与CFL倍率1/0.5/0.25的实际误差、事件缺失状态、两种解析扩散及密闭反应参照结果。
- `../artifacts/audit.json` 与独立命令 `python3 experiments/material_dynamics_v2b1/audit.py experiments/material_dynamics_v2b1/artifacts`：exit 0，固定1e-6容差，107116项标量比较，最大归一化误差1.0658141036401503e-14。
- `python3 -m compileall -q experiments/material_dynamics_v2b1`：exit 0。写文件工具的语法检查通过；没有可用的独立ruff/pyright CLI，因此不声称跑过它们。

未运行旧full suite。未安装依赖、修改共享venv、接入设备、部署、使用外部收费API或发布。图表做了XML解析和数值映射检查；本轮没有GUI截图/字体像素级渲染验收。

Git入库检查发现标准库CSV的CRLF行尾被视为行尾空白；本目录 `.gitattributes` 指定CSV的text/eol=lf，并执行限于这3份CSV的 `git add --renormalize`。`git ls-files --eol` 确认index为LF、工作副本仍为原始CRLF；数据字段未改。`git diff --cached --check` 之后返回exit 0（git_diff_check.log为空表示无错误），没有关闭或放宽空白检查。复现包使用Git规范化后的LF，CSV解析语义相同。

开发中先观察缺失功能的RED测试，再实现并跑GREEN。补充篡改测试曾揭示派生max_local_meets_95/99布尔标志未重算的问题；审计现已独立检查两阈值，回归测试通过。非有限库存、缺失事件伪装成0、假物理未建模值、单条库存/通量篡改、删除flux区间和artifact容差注入均明确拒绝。

数值验证只支持研究诊断范围，不是材料规律、工厂迁移或生产安全的验证。Safety独立子卡为t_c787a990，同时保留Stage1前提依赖；本实现不自我批准。
