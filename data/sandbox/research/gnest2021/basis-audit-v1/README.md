# GNEST 原打印基准的有限重建

沿前阶段固定Table4/5事实，重建10个元素/温区行的产率×组成，解释干基、差值液相和灰分扣除的边界。没有覆盖或修正旧表。详见[报告](../../../../../docs/sandbox/research/gnest2021-basis-audit-v1/REPORT.md)及[source-location.json](source-location.json)。

关键限制：原feed O是扣灰分后的difference，不是完整矿物含氧库存。固定打印数下，新增非负遗漏产品不能消除H/O正残差；这不等于证明物理违守恒，也不量化其来源。矿物/输入侧记账、测量与差值推算误差仍未知。

示例25°C LHV代入采用明示水分解释，得2.249853252MJ/kg，未复现论文2.18；保留为未复现示例，不反推参数、不改原值。原2.18仍属LHV推算而非实测反应热。倒算液相组成是28位Decimal诊断值，不能充当严格区间。

可从仓库根用标准库复现，无EOS或原文下载：

```sh
python3 data/sandbox/research/gnest2021/basis-audit-v1/reconstruct.py --output-directory /private/tmp/gnest-basis-reproduction
python3 data/sandbox/research/gnest2021/basis-audit-v1/check_basis.py
```

首命令在指定目录写结果，第二命令以独立Fraction检查已存行和、原料链接、正残差反例及未复现热量，未执行原重建器。若自行合法取得原PDF，可为首命令提供`--source-pdf`以核固定SHA；源文件不会被复制。公开脚本结果已与首次私有结果逐字节一致；路径适配没有改算术。

原PDF/全文/页图许可未独立确定，不随本包分发。本包只有有限事实、方法定位与复算；实验协方差、完整元素/热化学及材料资格仍未建立。
