# Ghodke、Sharma、Chen：原污泥热解数据集 V1

原始来源：[Mendeley Data, DOI 10.17632/r4tb4nbsbc.1](https://data.mendeley.com/datasets/r4tb4nbsbc/1)，2022-05-27发布。许可为 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。作者、版本、原文件名、URL、实际读取位置、原始SHA256和许可保存在source-manifest.json；dataset-snapshot.json及files-api.json是官方只读API原始响应。原工作簿与PDF未修改；CSV、审计JSON和本说明是本项目派生，不表示原作者认可本模型。

实际下载并核读两份文件。tga-record.xlsx仅含一次仪器运行：Praveen_UPES!A28:E11602共11575行，A–E依次为时间min、温度°C、DTA µV、TG µg、DTG µg/min。B6记录初始样重10.54 mg，B16为原文“Gas2: Nitorgen (200 ml/min)”。C10:F10是35→900°C、10°C/min、保温10 min的程序记录，不能当作实测温度；实测温度约31.23–895.65°C，时间约0.0083–96.4583 min。

运行 `.venv/bin/python data/sandbox/research/ghodke2022/extract_tga.py` 可从已锁定原文件重建CSV和审计。CSV保存原始XML数值字符串与每行位置，仅另作min→s、°C→K、µg→kg十进制单位换算。930步质量回升、180步温度下降均保留，没有平滑、截断、排序或强制单调。源G列等附加公式不用于重新定义DTG。DTA信号是µV，没有热流标定，不能转成反应热；TG也没有擅自变为干基转化率。

kinetic-parameters.pdf完整单页列13种Coats–Redfern模型的E、A及R²，明确E单位kJ/mol、A单位min⁻¹。它是论文拟合汇总，不能当成13次原始试验；单页没有足够的转化率定义、拟合温区或模型函数信息，不把其参数装入任意温程反应器。

该数据集提供了可直接读取的单次原污泥仪器曲线。它没有第二个升温速率或独立批次；随机拆分11575行不能称为独立外部验证。相关论文10.1016/j.jenvman.2021.113450本轮只读出版商元数据/节选，未获取全文；完整原料组成/基准、热解产物计量、反应热及与现有砖材身份匹配均未闭合。该源尚未作为全周期材料参数包，也没有完成公开实验预测对照。

获取记录：最初试探的public-api版本URL返回404，随后读取公开页面脚本确认snapshot/1与files?folder_id=root&version=1实际端点。两份原文件的字节数和SHA256分别与官方文件清单一致；未接触私有API、登录凭据或付费正文。

首次暂存格式检查因派生CSV默认CRLF返回退出码2，未继续提交。旧提取脚本、CSV和审计已原样保存在initial-crlf-extraction.zip；显式改用LF后重新提取，逐字节核实仅行结束符改变，全部11575行字段一致。原始工作簿/PDF始终未改动。
