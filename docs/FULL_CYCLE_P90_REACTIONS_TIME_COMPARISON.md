# P90 原反应段配对实际结果

P90 唯一原反应段97200→115200s paired60/30完成，wall65.369760125s/CPU64.850636000s，四science3516252B/4194304B，240s窗closed/reaped/0retry/0postwindow科学。原55保持P89新版本(不同旧P88frozen55)、原54/strictloader/758=144literature614assumed0measured/37context保持；2strict50load/ctor/BDF/endpointdecodevalueinterval和302rates302center实际完成，0initial/baseline/reference重求/summary/fitUQ。原RHS18653/Jac104、nfev/njev/nlu分开，低层primitive仍sourceforecast。各151原120s完整cell/surface/center采样峰18.2667389391/18.2669798804K均在新终点115200s，peakrelative1.318999202e-05，不证明continuouspeak；四产品strict<.02=True。两个端点mass/elements/U/S/4gas原.1%=True，最坏relative0.0002120696254/0.0003128577853。严格非负false，char负6/5格、min-2.179584804e-22/-2.496783691e-24mol；输入char12格全正、OH/CaO已负，两个输出OH仍负，signed变化不定位未存时刻/唯一因，不clip/seed修复。P78newreference条件化/历史t0缺失、sharedinput275+两actualsolverfull275t0/delta/sourcecontext共享三config各一次保持。仅当前stage局部time/sampledpeak/endpoint结果，原drying.1358920787402553%>.1%/CaO零nullfalse/P45/resources/高温三源assumed/directsynthetic290–350K及wholefalse保持。独立full80MiB仅覆盖行政额度，旧P89快照不改。下一原heating86400→97200合同静态候选未采用，0后续科学。GitDrive恢复/历史容量另receipt。详见docs/FULL_CYCLE_P90_REACTIONS_TIME_COMPARISON.md/json。

|量|原60s|独立30s|signed refined−coarse|绝对相对差|
|---|---:|---:|---:|---:|
|porosity (1)|0.4900926822031283|0.4900923429770608|-3.392260675e-07|6.921676545e-07|
|residual_carbon_kg (kg)|1.263920714418148e-24|9.952224687582779e-26|-1.164398468e-24|1.164398468e-17|
|shrinkage (1)|-0.008714677163500495|-0.008714676612357586|5.511429091e-10|6.32430707e-08|
|peak_temperature_difference_k (K)|18.26673893907309|18.266979880392|0.0002409413189|1.318999202e-05|

完整原峰值包含cells、原rates的surface和原center，每条151个原120s点。两个峰均在各自新实际终点，不能借旧P88共同起点zeropeak，也不证明连续峰值。内部采样span的signed差及surface/center差是已存数组诊断，无额外验收门槛或模型调用。

两新端点完整账本保留原signed增量、预算与初始归一化，质量/元素/U/S/四气体判定独立于非负库存。能量相变/反应沿用原source一次，不新增热源。P78新声明reference只用于原归一化和条件收缩；原历史t0并未恢复，负收缩仍保留。

原coarse/refined solver证据：{"coarse": {"method": "BDF", "success": true, "message": "The solver successfully reached the end of the integration interval.", "nfev": 965, "njev": 56, "nlu": 157, "solver_wall_seconds": 33.198715624865144, "actual_rhs_calls_including_jacobian": 9701, "actual_jacobian_calls": 56}, "refined": {"method": "BDF", "success": true, "message": "The solver successfully reached the end of the integration interval.", "nfev": 1464, "njev": 48, "nlu": 201, "solver_wall_seconds": 30.54680816596374, "actual_rhs_calls_including_jacobian": 8952, "actual_jacobian_calls": 48}}。公共302rates/302center是实际调用，原BDF内部RHS/Jac及nfev/njev/nlu为各自计数；固定Newton等低层次数仍为源码forecast，不能用publicsample计数替代。原输入和两条actualsolver完整t0/delta直接分别保存，所有差值为原值，不通过input+delta重建。原source55未改、3份完整config和sharedsource/context各一次，输入50明确完整子集。

输入heating char最小1.377360372932039e-10mol，全12格正；OH负4格、CaO负8格。新输出char/OH仍负，refined最小负值绝对幅度较小并不满足strict非负。保存各species原signed输入到端点增量；不定位未保存时刻或唯一成因。旧P88 refined更负、旧各FAIL未撤销。

源域：本轮actualsample/endpoint温度范围在JSON，未存连续域未知；高温三源声明外推仍assumed，direct合成290–350K不扩域，0measured。局部stagePASS不授全前六段、全周期time/grid、三方案、反演、工艺或材料PASS。名义干燥0.1358920787402553%>0.1%、CaO零预算relative=null/passed=false、P45/资源失败保留。

当前只执行一窗。下一未采用静态候选是原heating86400→97200根合同与必要预算；不自动启动下一科学或再次加密。完整下一静态预算另存candidate，由实际当前full对象及独立newGit/admin/archive/freeze分配推导，无新科学额度。

准备到报告实际wall474.612249s，科学wall/CPU见窗口。变更8文件：根参数、spec/report/plan/GOAL、P90 MD/JSON、final acceptance；生产代码0改动。科学四输出不入Git。Git普通继承及原Drive一次2MiB必要增量另receipt，metadata不是恢复，下载/恢复0；历史20GB/GitHub容量未解决。

启动前新root80MiB门槛有正式commandExecution完整未截断输出证据(exec-9e576357-c646-48c2-ab10-42658c2eeae1)，实见67,881,537B/83,886,080B，且先输出gate后才Popen。prepare的first-complete-gate属于旧root，未冒充；启动前fullmanifest未另做不可变copy，当前保留真实正式输出及精确root-at-launch和source/config审查。独立协调已存结果和serialization复核路径列于JSON。P90和P88是各自固定原输入的局部比较，不能拼接为全周期整体加密；元数据、字节相同和原归一化不代替材料实测。下一heating静态候选完整预算以candidate self为准；尚未采用，无额外科学。

补充已存数组资格：149/151个span有变化，cell最大绝对采样差0.01286919751657933K；OH全局signed和coarse/refined=1.736442059204638e-24/-1.347045369799205e-25mol。最小负量级变小不等于各全局符号改善；两case仍strict非负FAIL。这些是既存输出算术，无额外模型/势/RHS调用。
