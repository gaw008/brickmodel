# native01 原始执行证据

ACCEPTANCE.json、case.json、request.json、ordinary-checkpoint.json 为原字节副本。
evidence.tar.gz 包含全部396个本次输出文件（原日志、父记录、普通段事件、运行时源码等），
每个成员的原路径、字节数、SHA-256见MANIFEST.json。
17份第三方来源assets未再分发，其身份与排除原因逐项列出，原文件仍在本机private scratch。
缺少assets时不能宣称完整源服务读档已经通过；原本机包已用于实际运行及独立核查。

可在一个新的空目录解压本项目产生的归档查看数值记录；跨进程恢复尚未获准。
本归档不是可执行对象或live lease。不要覆盖已有实验目录。

字段注意：原ACCEPTANCE.case_sha256值是规范化配置SHA ead8e8db…；
原case.json字节SHA是e57c51e4…，父result.json及监督metadata.json已正确保存二者。
独立派生报告分别命名raw_case_sha256与canonical_config_sha256，原文件不覆盖。
