# 实际验证命令

项目根目录 `/Users/wanggaoying/Desktop/brickmodel-github`，
Python `/private/tmp/brick-water-backend-probe/venv/bin/python`（3.12.13）。
证据工作目录 `/private/tmp/brick-source-wet-shared-pressure-v1`。
命令输出和原失败保存在本阶段原始证据归档中。

## 合并回归和修复后针对性验证

从项目根目录运行，合并回归的八个测试文件为：

```text
tests/sandbox/test_paired_pressure.py
tests/sandbox/test_paired_pressure_host.py
tests/sandbox/test_paired_pressure_arithmetic.py
tests/sandbox/test_source_dry_shared_pressure.py
tests/sandbox/test_source_dry_transition.py
tests/sandbox/test_source_multicell_transition.py
tests/sandbox/test_source_wet_shared_pressure.py
tests/sandbox/test_source_wet_transition_pressure.py
```

使用 `PYTHONPATH=src <python> -m pytest -q <上述八文件> --junitxml=<输出>`。
`root/source-final01.xml/log` 和 `root/installed-final01.xml/log` 各 151 项，
属于修复临时物性配置绑定缺陷前的版本。原回归证据保留，不声称这两批已包含后加的回归。

修复不改变数学和旧接口，最终重验受影响的两文件：

```sh
PYTHONPATH=src /private/tmp/brick-water-backend-probe/venv/bin/python -m pytest -q tests/sandbox/test_source_wet_shared_pressure.py tests/sandbox/test_source_wet_transition_pressure.py --junitxml=/private/tmp/brick-source-wet-shared-pressure-v1/root/source-fixed02.xml
UV_CACHE_DIR=/private/tmp/brick-sandbox-uv-cache uv pip install --python /private/tmp/brick-water-backend-probe/venv/bin/python --no-deps --offline --reinstall .
```

安装验证在 `/private/tmp` 运行，清除 `PYTHONPATH`，两测试文件使用项目绝对路径。
最终输出 `root/installed-fixed02.xml/log`，同 44 项。实际安装包和源码文件逐一比较：

```sh
env -u PYTHONPATH /private/tmp/brick-water-backend-probe/venv/bin/python /Users/wanggaoying/Desktop/brickmodel-github/docs/sandbox/research/source-endpoint-comparison-v1/check_install.py /Users/wanggaoying/Desktop/brickmodel-github /private/tmp/brick-source-wet-shared-pressure-v1/root/installed-file-check.json /private/tmp/brick-source-wet-shared-pressure-v1/root/installed-fixed02.xml 44
```

## 唯一新原生运行

先核查 `EXECUTION_FREEZE.json` 的源码、测试、合同、审查和安装记录。
在 `/private/tmp`、无 `PYTHONPATH` 下执行冻结包装器一次：

```sh
env -u PYTHONPATH /private/tmp/brick-water-backend-probe/venv/bin/python /private/tmp/brick-source-wet-shared-pressure-v1/root/run_native.py /Users/wanggaoying/Desktop/brickmodel-github /private/tmp/brick-source-wet-shared-pressure-v1/root/native01
```

输出目录必须不存在；不覆盖、不把旧对象关联当 live resume。
包装器复用冻结父执行器和原物理输入，原 510 s 时间限、97 source 回调限不变；
额外湿态查询上限 16，每次请求/返回/失败单独保存。
父原始输出和 stdout 原样保留；最终文件只加新策略和执行证据。

完整新运行 JSON 位于归档 `root/native01/native-result.json`；
`parent-native-result.json` 为父执行器原输出，`pressure-observations.json` 保存额外查询。
原生输出的独立复算只读保存值，不重新调用物性或执行模型。

子代理审查、制造解、源码和安装一致性各有明确范围，均不代替公开实测材料验证。
