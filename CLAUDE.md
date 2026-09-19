# CLAUDE.md

## 版本号与发版

**不是每个 commit 都要升版本号。** 每次提交前先问用户：这次要不要改版本号、改成多少。
用户说不改就只提交代码，不动版本号，也不写 CHANGELOG。

用户决定升版本时，按以下步骤做：

1. 版本号遵循语义化版本（`MAJOR.MINOR.PATCH`）。新功能或不兼容的改动升 MINOR，只修 bug 升 PATCH。
   提议一个版本号，由用户确认。
2. 两处改成同一个版本号：`plugins/wikipali/.claude-plugin/plugin.json` 和
   `.claude-plugin/marketplace.json` 里 wikipali 那一条。
3. 在 `CHANGELOG.md` 最前面加一节 `## [版本号] - YYYY-MM-DD`，按「新增 / 变更 / 修复」列出
   自上一版以来的主要改动。
4. 跑 `./release-check.sh`，通过后再提交。
5. 推送后，经用户同意，给这个提交打 `v版本号` 标签并推送标签。
