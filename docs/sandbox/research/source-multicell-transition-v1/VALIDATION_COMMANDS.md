# 本阶段实际验证命令

以下记录已经执行的命令，不是待跑清单。临时路径对应原始证据归档中的
同名 root/ 文件。源码、安装测试和唯一原生进程均已正常终态，不因恢复
上下文而重跑。独立审核脚本读取保存 JSON，不重新执行 EOS。

源码四组（仓库根目录，session 73037）：

```sh
PYTHONPATH=src:/private/tmp/brick-source-multicell-transition-v1/root /private/tmp/brick-water-backend-probe/venv/bin/python -m pytest -p save_manufactured tests/sandbox/test_source_dry_transition.py tests/sandbox/test_source_multicell_terminal.py tests/sandbox/test_source_multicell_transition.py tests/sandbox/test_source_liquid_column.py -q --junitxml=/private/tmp/brick-source-multicell-transition-v1/root/source-final.xml > /private/tmp/brick-source-multicell-transition-v1/root/source-final.log 2>&1
```

非 editable 安装（仓库根目录，exit 0）：

```sh
UV_CACHE_DIR=/private/tmp/brick-sandbox-uv-cache uv pip install --python /private/tmp/brick-water-backend-probe/venv/bin/python --no-deps --offline --reinstall .
```

安装同四组（工作目录 `/private/tmp`，session 32272）：

```sh
env -u PYTHONPATH /private/tmp/brick-water-backend-probe/venv/bin/python -m pytest /Users/wanggaoying/Desktop/brickmodel-github/tests/sandbox/test_source_dry_transition.py /Users/wanggaoying/Desktop/brickmodel-github/tests/sandbox/test_source_multicell_terminal.py /Users/wanggaoying/Desktop/brickmodel-github/tests/sandbox/test_source_multicell_transition.py /Users/wanggaoying/Desktop/brickmodel-github/tests/sandbox/test_source_liquid_column.py -q --junitxml=/private/tmp/brick-source-multicell-transition-v1/root/installed-final.xml > /private/tmp/brick-source-multicell-transition-v1/root/installed-final.log 2>&1
```

实际安装身份和 XML 核查（工作目录 `/private/tmp`，exit 0）：

```sh
env -u PYTHONPATH /private/tmp/brick-water-backend-probe/venv/bin/python /Users/wanggaoying/Desktop/brickmodel-github/docs/sandbox/research/source-endpoint-comparison-v1/check_install.py /Users/wanggaoying/Desktop/brickmodel-github /private/tmp/brick-source-multicell-transition-v1/root/installed-identity.json /private/tmp/brick-source-multicell-transition-v1/root/installed-final.xml 52
```

唯一原生 N3 运行（工作目录 `/private/tmp`，session 8377，exit 0）：

```sh
env -u PYTHONPATH /private/tmp/brick-water-backend-probe/venv/bin/python /Users/wanggaoying/Desktop/brickmodel-github/docs/sandbox/research/source-multicell-transition-v1/run_native.py /Users/wanggaoying/Desktop/brickmodel-github /private/tmp/brick-source-multicell-transition-v1/root/native-result.json > /private/tmp/brick-source-multicell-transition-v1/root/native.log 2>&1
```

前置六份代码/测试及运行器、预登记 SHA 检查完成后才启动原生运行。
原先无 N3 native 结果；无外部自动重试、结果断言或预算增加。
完整原政策、成本登记及原运行器见 [PREREGISTRATION.md](PREREGISTRATION.md)。
