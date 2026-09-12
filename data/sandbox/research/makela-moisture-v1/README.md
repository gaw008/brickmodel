# 条件内部湿迁移参数

来源为 Mäkelä 等 2016，Water Research 91，11–18，[DOI](https://doi.org/10.1016/j.watres.2015.12.043)。[作者稿](https://orbi.uliege.be/bitstream/2268/192978/1/Mikko_2016_preprint.pdf)的摘要及Table1脚注给出未处理纸厂混合泥平均表观D=8.56×10⁻⁹ m²/s，正文打印8.57×10⁻⁹，差异保留且不当作误差条。

[source.json](source.json)记录原始样品、105°C空气工况、公式位置、收缩修正、排除区间和缺失信息；[model.json](model.json)记录选值及跨材料、温度、压力与输水路径假设。D由总失水反推，不能声称是独立液相扩散测量。应用域为35–95°C、干基W=.30–.80、90–110kPa，推广误差unknown。材料和训练资格为false。

原PDF只保留本地缓存，不随证据包再分发。复现前从作者稿链接取得原件，存为`runs/sandbox/source-cache/makela2016/makela2016-accepted.pdf`；测试亦可用`MAKELA_SOURCE_PDF`指定。必须为4,442,717字节，SHA256=`f4200d99c4fa8f3f6585fde9ec2e15455bfa78644a953e52b7311c1df25cba91`。来源读取会校验原件及事实/模型文件，缺件或变化直接拒绝。

`sorption_moisture_face.py`是声明输入叶子；`source_sorption_moisture.py`绑定实际吸附储能、化学势和水库存。首个实际列分支保留本地凝聚/蒸发与来源导热，关闭所有额外的格间气体扩散和Darcy输运。瞬时面熵、共享守恒和来源可查不等于整步熵证明、时间空间收敛或实验验证。
