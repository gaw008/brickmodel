# Hermes → GitHub 持续同步

2026-09-06 用户授权此模型后续更新持续提交并上传至 `gaw008/brickmodel`。

## 已启用

Codex 自动任务：**同步 Hermes 砖模型到 GitHub**，ID `hermes-github`，每 15 分钟检查一次，状态 ACTIVE。

执行依赖：这台 Mac 开机、联网，Codex 自动任务可运行，SSH 别名 `hermes` 及当前 GitHub 登录有效。这不是 Hermes 服务器常驻同步服务；关机、离线或 Codex 不可运行时不能保证同步。调度检查保存当时可见的状态，不保证记录两次检查之间被撤销的每一次编辑。

| 内容 | GitHub 位置 |
| --- | --- |
| 当前 B2 主线的已提交更新 | `main` 常规合并，保留仓库文档与输入 |
| 所有模型研究分支的提交 | `hermes/<源分支名>` |
| 各工作树未提交源码/文档/输入变化 | `hermes-wip/<源分支名>`，存在变化时创建，明确未审核 |
| 新增研究报告、审核和失败证据 | `docs/research-status/evidence/auto-sync/` |
| 后续发生变化时的同步状态 | `docs/research-status/SYNC_STATUS.md` |

首次初始化已发布 `hermes/master`、`hermes/research/material-design-v2`、`hermes/research/material-dynamics-v2b1`、`hermes/research/material-dynamics-v2b2`。初始化时两处源工作树均无未提交修改，所以尚无 WIP 分支。新分支自动发布到 hermes/；main 的后继来源只有在关系明确后才调整。

## 同步规则

- 获取源码仓库全部分支，定期发现新 worktree。通过 SSH bundle/scp 和本地 GitHub 身份同步，服务器不持有新增 GitHub 凭据。
- 不更改 Hermes 工作树、index、源分支或运行服务；WIP 在隔离副本生成。
- 常规非强制 push；源历史重写另存时间分支。main 合并冲突时保留分支更新并报告，不自动覆盖。
- 同步模型相关研究数据；不上传凭据、环境、Hermes 配置、会话或无关项目。发现可疑内容则暂缓该部分并报告。
- 失败和 pending 是应保留的研究状态；同步不表示测试或独立审核通过。
- 无变化不提交、不制造更新时间；普通成功静默，重要阶段变化、失败或需用户处理时提醒。

## 管理

在 Codex 自动任务中打开“同步 Hermes 砖模型到 GitHub”，可暂停、修改频率或删除。自动任务的完整执行规则保存在应用中。GitHub 上此文件只记录配置，不会自行触发任务。

目前配置已启用，并已通过首次真实分支 push 验证连接。后续定时 WIP/证据同步将在出现对应变化时执行，尚未用真实后续更新验证。
