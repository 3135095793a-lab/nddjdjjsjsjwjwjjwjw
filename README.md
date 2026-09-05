# AgentFusion (workspace placeholder)

本仓库用于按用户要求在 GitHub Actions 上验证 AAswordman/Operit 指定提交的原版构建，并作为后续将 Operit 与 AutoJs6 融合（AgentFusion）工程的托管起点。

注意事项：
- 本仓库仅包含初始占位文件和一个手动触发的 CI workflow（位于 feat/ci/operit-build-check 分支的 PR）。
- 不包含任何私钥、签名或敏感信息，也不会使用上游发布签名。
- 所有上游源码按指定提交从原仓库克隆（不做镜像或上传）。

后续计划（分阶段）：
1. 在 Actions 上验证 Operit 指定提交能否在 Ubuntu x86_64 runner 上按上游官方流程编译通过。若原版编译通过，则分阶段提交融合修改（将 AutoJs6 源码以源码级方式集成到 Operit，形成独立应用 AgentFusion）。
2. 每个阶段通过 PR 提交，并保留审查与 CI 校验。不会自动合并或发布。

上游参考提交（按你提供）：
- Operit: f323d6c50fa661837fad06d4618462861779b562
- AutoJs6: ed3eb10e88db5a8425fd94bdddefa4176e5e1c94
- Operit terminal 子模块: e4442bc6a047b6165bf59103721ad143149c620d

如果你同意，我将在 feat/ci/operit-build-check 分支中提交一个手动触发的构建 workflow，并创建 PR。