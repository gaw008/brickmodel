# 本阶段已执行命令

基线 ac04d8b。源码 session 8183、安装测试 session 88788、保存观测运行
session 57716 均已 exit 0；不重复旧 EOS 或上阶段数值实验。

源码四组（仓库根目录）：

```sh
PYTHONPATH=src /private/tmp/brick-water-backend-probe/venv/bin/python -m pytest tests/sandbox/test_source_observation_record.py tests/sandbox/test_source_observation_cli.py tests/sandbox/test_exact_record.py tests/sandbox/test_run_service.py -q --junitxml=/private/tmp/brick-source-record-v1/root/source-final.xml > /private/tmp/brick-source-record-v1/root/source-final.log 2>&1
```

离线非 editable 安装（仓库根目录，Python 3.12.13）：

```sh
UV_CACHE_DIR=/private/tmp/brick-sandbox-uv-cache uv pip install --python /private/tmp/brick-water-backend-probe/venv/bin/python --no-deps --offline --reinstall .
```

安装同四组及身份核对（cwd=/private/tmp）：

```sh
env -u PYTHONPATH /private/tmp/brick-water-backend-probe/venv/bin/python -m pytest /Users/wanggaoying/Desktop/brickmodel-github/tests/sandbox/test_source_observation_record.py /Users/wanggaoying/Desktop/brickmodel-github/tests/sandbox/test_source_observation_cli.py /Users/wanggaoying/Desktop/brickmodel-github/tests/sandbox/test_exact_record.py /Users/wanggaoying/Desktop/brickmodel-github/tests/sandbox/test_run_service.py -q --junitxml=/private/tmp/brick-source-record-v1/root/installed-final.xml > /private/tmp/brick-source-record-v1/root/installed-final.log 2>&1
env -u PYTHONPATH /private/tmp/brick-water-backend-probe/venv/bin/python /Users/wanggaoying/Desktop/brickmodel-github/docs/sandbox/research/source-endpoint-comparison-v1/check_install.py /Users/wanggaoying/Desktop/brickmodel-github /private/tmp/brick-source-record-v1/root/installed-identity.json /private/tmp/brick-source-record-v1/root/installed-final.xml 93
```

一次被动 111 观测运行（cwd=/private/tmp；事前固定 60/90 s 和三原始 SHA）：

```sh
env -u PYTHONPATH /private/tmp/brick-water-backend-probe/venv/bin/python /private/tmp/brick-source-record-v1/root/exercise_saved.py --n3 /private/tmp/brick-source-multicell-transition-v1/root/native-result.json --n1 /private/tmp/brick-source-dry-shared-pressure-v1/root/native-result.json --programmed /Users/wanggaoying/Desktop/brickmodel-github/docs/sandbox/research/exact-source-column-v1/native-result.json --output /private/tmp/brick-source-record-v1/root/saved-exercise > /private/tmp/brick-source-record-v1/root/saved-exercise.log 2>&1
```

安装 CLI（cwd=/private/tmp）：

```sh
env -u PYTHONPATH /private/tmp/brick-water-backend-probe/venv/bin/sludge-sandbox source-observation-import /private/tmp/brick-source-multicell-transition-v1/root/native-result.json --capture-index 16 --output /private/tmp/brick-source-record-v1/root/cli-observation.json > /private/tmp/brick-source-record-v1/root/cli-import.json
env -u PYTHONPATH /private/tmp/brick-water-backend-probe/venv/bin/sludge-sandbox source-observation-inspect /private/tmp/brick-source-record-v1/root/cli-observation.json --cell 1 > /private/tmp/brick-source-record-v1/root/cli-inspect.json
```

两条 stdout 分别与 Python `inspect_source_observation` 的全格/原格 1 结果
实际完全一致，另核索引、ordinal 和四项 false 标志，共 7 项；见
`raw-evidence.zip` 内 `source-record/root/cli-parity.json`。

复现运行器可更换三个输入文件的路径，其原 SHA 必须相同。N3/N1 完整
输入分别已保存在前两阶段 `raw-evidence.zip` 的 `root/native-result.json`；
程序边界原 JSON 在 `research/exact-source-column-v1/native-result.json`。
本阶段归档包含 111 个规范观测、完整原始失败、源码冻结和所有本阶段审核。
