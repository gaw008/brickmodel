# 移动主机programmed边界构造失败：独立精确定位

只读审计，未修改仓库或generic canonical。父任务证据`/private/tmp/brick-sphere-surface-review/prior-deforming-check.log`已证明旧HEAD wrapper同样失败；因此不是本轮sphere新增行为，但确实阻断原Goal移动主机表面换热测试，不能用sphere测试通过替代它。

## 实际对象路径

本次执行`inspect_identity.py`，按现有`_canonical`的字段顺序遍历真实`host(load_water_properties(DATA),isotropic=True)`。执行正常退出，无新EOS数值求解；结果保存在identity-paths.log。

**首个不支持对象为：**

`base_model.point_storages[0].motion._reference_state.widths_m`

具体类型链：`DeformingSolidHeat → point_storages[0] → DeformingSolidStorage.motion → PrescribedSlabMotion._reference_state → CurrentSlab.widths_m → numpy.ndarray`。

不是ReferenceSlab自身：`geometry.py:58`的ReferenceSlab仅含half_thickness、area、cells三个标量。`deformation_program.py:118`定义的`_reference_state`为init=False、compare=False缓存，152–156行由reference.deform在单位伸长下生成并快照。它是CurrentSlab，下面7个字段都是真实只读float64数组：

| 字段 | 本例shape | 本例值 |
|---|---|---|
| widths_m | (1,) | [0.01] |
| faces_m | (2,) | [0,0.01] |
| centers_m | (1,) | [0.005] |
| face_areas_m2 | (2,) | [0.014,0.014] |
| reference_volumes_m3 | (1,) | [0.00014] |
| volumes_m3 | (1,) | [0.00014] |
| volume_ratios | (1,) | [1] |

遍历发现7个unsupported对象，均为上述字段，没有其他未知类型。`deforming_solid_storage.py:59`遍历所有dataclass字段，不跳过init=False/compare=False，遇首个数组即在60行拒绝。wrapper的`_current_content_digest`直接传入完整base_model，因此构造时失败。

## 最小修复建议

限定在`programmed_solid_fluid_heat.py`的身份计算或一个仅该wrapper使用的身份适配器。增加**精确CurrentSlab类型**的递归序列化分支，位置在通用dataclass分支之前；其余序列化规则与既有canonical保持一致，未包含CurrentSlab的旧可工作输入得到同样canonical树/摘要。不要修改generic `_canonical`让任意ndarray、np.generic或任意对象进入身份。

CurrentSlab适配器应：

1. 绑定完整模块/类型标签和全部7个字段名；保留字段顺序，新增未处理字段时拒绝而不是漏掉。
2. 对各数组要求type(value)为明确支持的np.ndarray、dtype为实际float64、ndim=1、全部有限；cell数组长度N，face数组长度N+1，N>0。拒绝object/complex/整数/bool或数组子类；不通过宽泛tolist转换掩盖类型。
3. 序列化dtype/shape及逐项binary64的float.hex值（包含signed zero），从而任意实际几何改变都会改变身份；读取数组时保留稳定快照并按需要检查读取期间一致性。不能仅序列化类名、缓存名或数组shape。
4. 当前入口以readonly快照为约定，可拒绝writeable数组；这不是认为readonly即可保证不被替换，运行前后仍须重算内容身份。现有`_check_content`的构造/运行变更拒绝继续保留。
5. 对CurrentSlab之外任何ndarray仍报unsupported；不要加repr、str、hash(object)或遇未知类型跳过的兜底。

不建议只改为hash(base_model.energy_model_identity)：嵌套身份只绑定选定配置，并不天然证明全部当前缓存值未被修改。也不能跳过`compare=False`或下划线字段；`validate_reference_geometry`实际读取_reference_state.widths_m与volumes_m3，该缓存属于运行物理内容。即使准备改为每次从ReferenceSlab重建缓存，也必须显式校验现有缓存一致、拒绝不一致，不能悄悄覆盖；这不是本次最小修复。

## 应做的最小回归

- 首先原失败测试`test_deforming_wet_admission::test_actual_current_halfcell_surface_single_inverse_and_original_errors`实际通过：只做一次总能量逆解，使用当前halfcell/area及原逆解误差对象，保留mechanical功率分项和入流焓检查。这个测试证明移动主机路径恢复，不由sphere测试替代。
- 相邻的`test_explicit_type_tag_sources_and_duplicate_boundary_guards`、`test_program_motion_knot_union_validates_both_domains`覆盖显式类型、双边界和运动/边界时间域。
- 对7个CurrentSlab数组逐字段改变一个值、shape或dtype；对_motion.reference标量和表面系数改变；必须在评估前报内容改变/无效，不能调用EOS或第二次温度逆解。mutation测试只需构造和内容检查，不需昂贵积分。
- 非有限数组、object数组、未知自定义对象以及放在其他字段的任意ndarray继续拒绝。旧可工作的SolidFluidHeat无数组身份应与修复前同树/同摘要。
- 序列化合法新构造器即可，本修复不授予新codec/resume或材料准入。无需为了这个身份修复重跑完整长时形变积分或native水证明。

结论：这是一个范围明确的内容身份适配缺失。保留严格未知类型拒绝的同时，绑定真实CurrentSlab的全部数组即可解除移动主机构造阻塞；没有理由编造参数、关闭身份检查或扩大generic接受范围。
