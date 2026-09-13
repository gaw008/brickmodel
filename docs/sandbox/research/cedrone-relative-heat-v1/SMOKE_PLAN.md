# 离线供热比较的实际入口登记

本阶段只对保存数据作精确算术，没有新的热化学/EOS/平衡点，也不复跑旧动态轨迹。作者完成薄API/CLI和有意义的负对照后，由独立审查者核代码，再对隔离非editable安装实际运行一次用户入口。

固定输入：公开目录 `data/sandbox/research/cedrone-relative-heat-v1/` 中的 `lambda0-result.json` 与 `lambda-quarter-result.json`。前者来自旧基线，后者来自新CLI；来源/相定义/h向量必须一致，合法serializer与计时元数据差别必须不改变物理结果。

命令形态：

```sh
python -I examples/sandbox/compare_cedrone_heat.py \
  --source-root . \
  --baseline-result data/sandbox/research/cedrone-relative-heat-v1/lambda0-result.json \
  --candidate-result data/sandbox/research/cedrone-relative-heat-v1/lambda-quarter-result.json \
  --lambda 1/4 --output-dir /tmp/new-cedrone-heat
```

ROOT实际使用隔离环境Python、绝对仓库路径与全新scratch输出目录，完整命令和stdout/stderr留存。该程序仅处理两份不足80KB的保存结果，执行预算10秒；若出现实际读取/算术/检查错误则保存失败，不覆盖旧结果或通过新增求解来替代输入。

事前预期：

1. 原输入保持原字节；输入身份与输出路径可追查。
2. 两份返回的来源、固定800K/1bar、原数值策略、元素池/原子量/19库存等必要条件检查通过；不依靠保存的`completed`标记代替实际重算。
3. 按保存binary64精确转Fraction后，H、入口O2/N2焓、ΔQ及元素参考平移余量与前阶段独立算术**严格相等**。不以近似显示值作比较，不加pV或形成焓，不裁剪残差。
4. λ=0的严格零、λ=1算术和错误输入拒绝由相关测试覆盖；正式入口只执行上述一次比较。
5. 输出保留共同未知原料初态和外置状态相同、800K虚拟预热入口、仅pV功等条件；绝对Q、自热、炉燃料/材料资格仍未知或false。

本阶段验收只支持离线相对热量比较，不升级完整砖坯全周期、动力学、烧结/冷却或材料验证。
