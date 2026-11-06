# CLAUDE.md

## 版本号与发版

**不是每个 commit 都要升版本号。** 每次提交前先问用户：这次要不要改版本号、改成多少。
用户说不改就只提交代码，不动版本号，也不写 CHANGELOG。

仓库里有两个插件，**各自独立管版本**：底层 `wikipali` 与应用层 `wikipali-workspace`。
只改了哪个就只升哪个。

用户决定升版本时，按以下步骤做：

1. 版本号遵循语义化版本（`MAJOR.MINOR.PATCH`）。新功能或不兼容的改动升 MINOR，只修 bug 升 PATCH。
   提议一个版本号，由用户确认。
2. 每个要升的插件，两处改成同一个版本号：`plugins/<插件>/.claude-plugin/plugin.json` 和
   `.claude-plugin/marketplace.json` 里该插件那一条。
3. 在 `CHANGELOG.md` 最前面加一节 `## [版本号] - YYYY-MM-DD`，按「新增 / 变更 / 修复」列出
   自上一版以来的主要改动。应用层的版本写成 `## [wikipali-workspace 版本号] - YYYY-MM-DD`；
   两个一起升时可以合成一节，标题里两个版本都写。
4. 跑 `./release-check.sh`，通过后再提交。
5. 推送后，经用户同意，给这个提交打标签并推送标签：底层 `v版本号`，应用层
   `wikipali-workspace-v版本号`。

## 分层：改动放哪个插件

- **底层 `plugins/wikipali`**：存取。CLI（`bin/`、`lib/`）、登录与凭据、读写接口，以及
  「做错了会写错位置、引错出处、误标作者」的规矩（`references/conventions.md`）。
- **应用层 `plugins/wikipali-workspace`**：做法。译文风格、术语标记、随文注释、审稿定级、
  nissaya 读法、论文写法——因人而异、可以不装的东西。它**不直接调接口**，只调 `wikipali` 命令。
- 应用层读不到底层的文件（`${CLAUDE_PLUGIN_ROOT}` 只指向自己），共享文档经 `wikipali guide`
  提供。**底层 CLI 的子命令与参数就是两层之间的契约**：改名、删参数前先查应用层的 skill 有没有用到。
- 个人化的做法（译文风格、nissaya 开关）放在**文件**里，不用 Claude Code 的 `userConfig`：
  项目 `.wikipali/styles/<名字>.md` → 个人 `~/.wikipali/styles/<名字>.md` → 插件默认，
  由应用层的 `bin/wikipali-style` 查找。新增一种风格文件时，在它的 `DEFAULTS` 里登记插件默认。
- 应用层 `plugin.json` 的 `dependencies` 目前不带版本范围。要加范围（如 `>=0.23`），依赖解析
  需要 `wikipali--v<版本>` 格式的 tag，先确认标签格式再加。

## API 调用清单文档

`docs/wikipali-api-calls.md` 是插件实际调用 WikiPali 接口的清单（接口总表 + 每个接口的
入参/返回）。**新增、删除或修改 command 或 API 调用时，必须同步更新这份文档**：

- 改了命令触发的接口（新增/删除/变更 endpoint、方法、参数、返回字段）→ 更新对应条目；
- 接口总表里的「一句话说明」和正文小节的入参/返回要一起核对；
- 只在代码里改、不更新文档，会漏掉接口契约变化，提交前当作遗漏处理。
