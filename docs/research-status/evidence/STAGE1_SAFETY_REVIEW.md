# PASS — approved_for_research_stage1

任务：t_c6aa7e5f。独立审核对象：research/material-design-v2，commit `2620afe40faaf592fbb42b39e3a6a6a351009ad8`；基线 `eef479cdf41e1ccfb7cabc1b63b7d8a92c57b910`。

结论：满足 DIRECTION_BRIEF 的首阶段研究验收。未发现需要阻止本研究阶段通过的缺陷；required_changes 为空。仅批准固定公开输入下的 Stage 1 材料方向研究，不批准生产配方、强度认证、排放合规、部署或设备控制，也不继承旧核心 solver/verifier 的审批。

## 1. 审批与范围

- 实时读取父卡 t_e36c9d82 和 t_dce3aa2b：均 done；后者最新结论明确 PASS / approved=true / subscription_included。没有把 done 单独当作通过，没有重试 OAuth 或读取凭证。
- 规范来源：`/home/ubuntu/.hermes/reports/sludge-material-design-v2/DIRECTION_BRIEF.md`，逐条映射首阶段交付与验收。
- Git diff 仅含 `experiments/material_design_v2/` 下35个新增文件；无项目依赖、核心 solver/verifier、主仓库、Hermes 配置或生产服务改动。
- 审核员未修改实现或输入。将16个非artifact文件逐字节复制到本卡临时目录运行；不运行会覆盖原提交artifact的默认 `verify.py`。

## 2. 实际执行证据

详细 argv、退出码、输出和计时保存在 evidence 包内 `execution.json`、`focused_tests.log`、`full_pipeline.log`。

主要命令：

    /usr/bin/python3 -B -m unittest discover -s /tmp/t_c6aa7e5f-review/copy/experiments/material_design_v2 -p test_pipeline.py -v
    /usr/bin/python3 -B /tmp/t_c6aa7e5f-review/copy/experiments/material_design_v2/pipeline.py --output-dir /tmp/t_c6aa7e5f-review/copy/experiments/material_design_v2/replay
    python3 -B /tmp/t_c6aa7e5f-review/independent_audit.py
    python3 -B /tmp/t_c6aa7e5f-review/safety_checks.py
    python3 -B /tmp/t_c6aa7e5f-review/literature_checks.py
    git diff --check eef479cdf41e1ccfb7cabc1b63b7d8a92c57b910 HEAD

实际结果：

- 10项 focused unittest 全部通过，测试框架报告10.263秒；包括错误退出码保留、身份反例、Ref配比反例、源派生重算、填补排除和两次完整导入。
- 另一次独立CLI完整pipeline退出0，计算耗时2.370751秒，峰值RSS 133184 KiB；串行、标准库，无新增依赖。
- 17个确定性产物（CSV/JSON/三份报告/两张SVG）与提交版逐字节一致。`pipeline_run.json`的时间/内存信息不要求字节一致；没有伪造重跑的 `verification.json`。
- 7个Python文件AST语法检查通过；没有运行旧项目full suite。
- 提交证据中18个输出hash、4个代码hash、15个输入hash全部匹配；原研究archive内35个普通文件逐字节匹配当前提交，archive SHA256匹配Engineer handoff。
- 审核结束前35个tracked文件及15个授权输入hash均未变，worktree仍clean。

## 3. 来源、全量对账与独立计算

实际请求四个公开Figshare API，当前工作簿发布MD5/大小与冻结元数据一致；本地四本Excel及共用README的MD5/SHA256/字节数亦匹配。XRF、TGA许可均为CC BY 4.0。[4][5]

圆片与PSD数据的许可亦为CC BY 4.0。[6][7] 注册表保留作者、DOI、许可和覆盖边界；两张SVG保留作者、数据DOI、关联论文和衍生制图归属。详见 `safety-checks.json` 与 `public-*.json`。

审核员另写OOXML解析器，不导入Engineer代码，直接核对：

- 4本工作簿、19个sheet（均visible）、7694非空行、16922公式格。每行的选取/排除地址无交集且并集精确等于原始非空地址；排除不代表删除或物理不可行。
- materials 26102行、observations 7656行，共33758个导出值/空值与原始单元格相符；measured观察没有伪装原始公式格。
- 108片饱水试件的吸水率、开放孔隙率、干密度：324项由无公式的原始干重/饱水重/水下重独立计算，同时匹配源缓存与导出；其中90片进入有效比较。
- 252片的直径收缩由每片6个无公式原始卡尺读数独立计算，匹配源缓存与导出；其中210片进入有效比较。
- 30组的上述物性均值/样本SD、直径收缩均值/SD及成员集合全部独立匹配；60条图表数据行匹配组统计。
- 示例：`Water and Burning!F9=2.8395 g`，`Porosity and Density!F14=3.364 g`、`G14=1.803 g`、水密度998.2 kg/m³。重算吸水率0.18471561894699762 kg/kg、开放孔隙0.3360025624599614 m³/m³、干密度1815.75201793722 kg/m³，与源缓存一致。

不把这些数值一致性说成独立实验验证；Engineer的4270项源重算也不是4270个独立样本。

## 4. 单位、身份、重复与证据边界

- XRF保留源含LOI的报告基础、Total和8个缺项，不静默转换成oxide-only归一化或矿物相分数。公开方法明确包含1050°C LOI。[4]
- `Mixing!D15/E15`明确dry，参照25/0 g、含灰17.5/7.5 g；加水不进入灰替代分母。mm、mm³、g、kg/m³、质量吸水率与体积孔隙率分开。
- README、Overview和逐系列原标签支持Y/R、P1/P2、Raw/ED的表内映射。#0179/A2P/Silica Sand冲突真实存在，原标签保留；42片身份不明圆片及相关材料数据没有混入定量图。P&D全局#0010旧说明仍列为chain-of-custody未知，resolved仅表示表内配对。
- `High and Diameter!AR139:AT139`确为其他六片高度的均值填补。原始AT139是共享公式从属格，AS139为anchor；已独立核对XML与数值。该组体积收缩n=6，直径n=7，不伪增高度样本。
- 两图都是30个离散系列；卡尺重复读数、组均值、Figures/P&D 2辅助表、XRF计算混配、PSD粒级、TGA温度点均不新增独立样本。无train/test拆分、无模型校准、无外部实验验证。
- TGA四表D百分比列Table27实际属#0262。独立本地C/B17诊断3455点，其中2591不匹配；Pilot-8!D896为孤立缓存。全部相关D公式已隔离，未静默修正。
- DTU TGA的N2/单升温速率不是原污泥空气氧化证据。[5] 本轮另外通过MDPI公开PDF核读方法，确认空气TG与多速率N2动力学分开；未将流化床操作映射成砖窑时长或工厂排放结论。[3]
- 公开物性方法每系列只取3片饱水试件，不是独立批次；PSD使用乙醇分散，粒径分布不能唯一决定砖坯孔喉/渗透。[6][7]

## 5. 科学方向是否成立

四条假说均区分支持、反例、未知、适用范围与可证伪条件，超出“至少三条”的要求；未将假说冒充已识别机理。

H1的主要数值结论独立复现：1050°C下ED相对Raw的吸水率差（百分点）为Y/P1 −2.284157、Y/P2 −2.496660、R/P1 +2.868759、R/P2 +0.840623。它支持“该实验内排序依赖基料”，不支持通用ED优越性、单元素因果系数或工厂预测概率。

H2的吸水—尺寸折衷是描述性离散比较；没有将较低温观测说成强度合格、最佳灰掺量或连续可行域。H3保留化学与PSD共变的不可识别性，不把处理收益等同于磨细。H4仅提出原污泥供氧/排气与致密化时序假说，没有假造阈值或校准结果。

报告所谓“中等置信”只可理解为这批记录内的描述性排序，不能升级成跨批次/工厂统计置信。液相/黏度、有限供氧、渗透和能量闭合的优先级有排序翻转逻辑；文中明确没有定量灵敏度结果。强度/缺陷/环境试验仍是独立合格门槛，不因排在表后而可省略。

## 6. 软件/安全清单

- Secrets/PII：对35个变更文本做凭证形状、敏感赋值和email扫描，无命中；不读取.env、OAuth或其他凭证。公开作者署名仅用于学术归属，审核证据不附通讯邮箱。
- 身份/权限：离线研究CLI，无新HTTP服务、鉴权接口或权限扩展。批准仅适用于已校验固定公共输入和受控本地输出目录，不是任意不可信文件上传服务的安全认证。
- 注入/命令：OOXML只读，不执行Excel公式/宏或外部链接；无eval/exec、shell=True。verify的subprocess使用argv列表、超时与真实退出码；实际测试了失败码保留。
- 文件/回退：默认生成器会覆盖指定研究输出，因此本次在逐字节副本中运行。未删除原始数据、回滚提交或覆盖已提交产物。未来回退仅限经批准的该研究目录revert/定点恢复；不reset主仓库、不改写历史。
- 网络/依赖：pipeline无网络调用，7个Python文件仅标准库/本目录导入。审核只做公共资料GET；无webhook、远程SVG资源或脚本，无包安装、新收费服务、OCI资源或按量API。
- 外部状态：无push/merge/发布、对外消息、金融交易、PLC/机器人/窑炉、训练控制或生产部署；未更改Hermes、Cloudflare、WhatsApp。此结论不是整机服务审计。

## 7. 未覆盖项与执行中的真实失败

1. 无实验室chain-of-custody鉴证、独立批次验证、强度/排放认证或工厂外推；A2P身份未解决。
2. 未进行CJK客户端逐像素渲染；已检查SVG XML、全部系列、坐标生成、字节重现和无活动/远程内容。
3. Stage1“DTU全文未取得”是其生成时的访问状态。后续2A附件声称补齐方法，Manager已另行记录；本次DTU PDF重取失败，不冒称独立核读这份全文，也不把后续资料静默写回冻结Stage1。后续热模型须使用并复核2A的明确来源，气氛仍不能猜测。
4. 本次MDPI HTML只返回部分内容，/htm失败；改用该页面提供的公开PDF成功获取方法段。只附与审核有关且无作者邮箱的摘录。
5. 审核脚本首轮把共享公式从属格误当完整公式字符串，退出1；随后查原始XML确认AS139→AT139共享关系，仅修正审核脚本并全量重跑成功，未改Engineer代码。这不是产品缺陷或被隐藏的失败。
6. 运行时拒绝了最初用于创建临时目录的inline Python命令；未放宽审批或修改配置，之后用标准write_file工具建立审核脚本/目录。
7. 引用工具三份报告均通过--evidence，但它不证明每句科学结论；本结论另依赖上述原表/数值/方法审查。原ledger未引用的检索源编号7（Orbit检索页面，并非本报告的引用编号）仅信息级提示。

## 8. 下游交接

已读取现有子卡t_c787a990；本卡通过只释放其Stage1前提，B1仍须独立审核，不自动批准B1。没有创建重复review或返工卡。任何费用、删除、外部发送/发布、部署、金融或工业控制仍须独立人工批准。

详细机器证据与审核脚本见同目录 `stage1-safety-evidence.tar.gz`；本报告和bundle为审核员产物，不改动研究结论文件。

## Sources

[3] https://www.mdpi.com/1996-1073/16/18/6634/pdf?version=1694767720
    > "Next, the kinetic analysis of the sewage sludge was carried out using three different heating rates and in nitrogen environment."
[4] https://api.figshare.com/v2/articles/30156127
    > "Oxide content was reported as a percentage of the total sum of measured oxides, including loss on ignition at 1050°C"
[5] https://api.figshare.com/v2/articles/30157066
    > "the cell was purged with 50 ml/min nitrogen gas."
[6] https://api.figshare.com/v2/articles/30157108
    > "Open porosity, water absorption, and dry density were determined on 3 discs for each test series."
[7] https://api.figshare.com/v2/articles/30156970
    > "with ethanol as the dispersion medium."
