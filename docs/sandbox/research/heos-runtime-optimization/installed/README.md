# 锁定依赖安装复验

应用独立审查的 stage8 两个源码文件及新清单摘要后，在既有且已核查 CoolProp8.0.0 构建的隔离环境安装项目。普通 uv pip offline 无法解析缓存中的 numpy2.5.2，失败时没有安装；改用 uv sync --frozen --no-editable --inexact --extra dev --extra water --offline --reinstall-package sludge-vme 成功，从项目锁恢复 numpy2.5.2（此前2.5.3），其余版本见 identity.json。--inexact 保留已单独固定清单的 CoolProp，不声称默认 water extra 已包含 CoolProp。

41个实际 site-packages 模块与当前源逐字节一致，相关测试后再次核对。测试 helper 的 PYTHONPATH 只包含 tests/sandbox，child 所在目录没有候选包，并断言所有 sludge_sandbox 导入来自 site-packages。child 与隔离 stage8 的物理输入及科学门槛相同，只改安装路径记录、安装版本与导入路径断言。

实际 wet-attempt01 exit0，外部18.5954143秒；积分14.40582975秒，29评估/4接受/0拒绝，原25秒积分与30秒外限均满足。原端点温差8.60638e-9K、压差1.19981e-5Pa、孔压功误差7.35992551e-7J，各组件与独立账本门槛通过。全部是制造固定相库存短时变形验证，不是活动蒸发或完整砖烧成。

从 /private/tmp 无 PYTHONPATH 运行 test_water_properties、test_water_response、test_water_cache、test_ideal_water_vapor、test_joined_water_vapor、test_water_chemical_potential，实际212通过/0失败错误跳过，XML1.486秒。此为本版本定向回归，不冒称重新跑过全1112 suite。
