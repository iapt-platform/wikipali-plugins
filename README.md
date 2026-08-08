# WikiPali 插件目录

[WikiPali](https://www.wikipali.org) 的 Claude Code 插件 marketplace。

```
/plugin marketplace add iapt-platform/wikipali-plugins
/plugin install wikipali@wikipali
```

桌面版在 **Code** 标签页点 `+` → **Plugins** → **Add plugin** 也能装。

装完**重启会话**——插件的命令进 PATH、skill 被加载，都发生在会话启动时。

## 插件

| 插件 | 说明 |
|---|---|
| [`wikipali`](https://github.com/iapt-platform/mint/tree/development/plugins/wikipali) | 巴利三藏的检索与阅读：词形展开、按词形检索、出处分布（分本文/义注/复注）、章节目录与整章阅读、多版本对读、词频统计、术语表；以及以 AI 模型身份写入句子。 |

## 更新

**本 marketplace 默认不会自动更新**——Claude Code 只对官方 marketplace 默认开启自动更新，第三方的（包括本仓库）默认关闭。所以有新版时要手动升，两条命令：

```bash
claude plugin marketplace update wikipali     # 先刷新目录
claude plugin update wikipali@wikipali        # 再升插件
```

然后**重启会话**（PATH 注入和 skill 加载都在启动时完成）。

**两步顺序不能省。** marketplace 目录是克隆到本地的副本，会过期；不先刷新目录，本地记的还是旧版本的 commit sha，直接 `plugin update` 什么都不会发生——连"卸载再重装"也会装回旧版。

### 在 Claude Desktop 里

桌面版的 **Manage plugins** 只有 enable / disable / uninstall，**没有更新按钮**。用内置终端：按 <kbd>Ctrl</kbd>+<kbd>`</kbd> 打开（Views 菜单也行，仅本地会话有），在里面跑上面那两条命令。

若终端里 `claude --version` 报找不到命令，用绝对路径，例如 `~/.local/bin/claude plugin update wikipali@wikipali`。

### SSH 会话要在远端升

SSH 会话读的是**远程主机**的 `~/.claude`，插件也装在那边。要在**那台机器**上跑升级命令，在本地笔记本上升没有用。

### 确认升上去了

```bash
claude plugin details wikipali          # 看版本号
ls ~/.claude/plugins/cache/wikipali/wikipali/   # 看缓存里有哪些版本
```

## 发版（维护者）

改插件的流程：改 `iapt-platform/mint` 的 `plugins/wikipali/` → bump 那边的 `plugin.json` 的 `version` → PR 合并 → 回到本仓库更新 `marketplace.json` 的 `version` 与 `source.sha`（**完整 40 位**）→ 推。

推之前跑：

```bash
./release-check.sh
```

五项检查，任一不过就退出码 1：

| 检查 | 挡住什么 |
|---|---|
| `claude plugin validate` | 结构性错误，含短 sha |
| `source.sha` 是 40 位十六进制 | 写短 sha |
| **sha 是上游分支的祖先** | 只推到 fork、还没合并就钉过去——用户会装不上 |
| 该 sha 上的 `plugin.json` 版本与目录一致 | 漏 bump 版本号——`plugin.json` 的 version 决定用户能否收到更新，不一致时 marketplace 标了新版也没用 |
| `source.path` 在该 sha 上存在 | 路径写错或目录还没进上游 |

第三项要用**祖先关系**判断，不能用「GitHub API 能按 sha 查到」：fork 与上游共享对象存储，只推到 fork 的提交在上游 API 上照样查得到。

## 这个仓库里为什么只有一个 json

插件本体住在 [iapt-platform/mint](https://github.com/iapt-platform/mint) 里，跟它调用的 Laravel API 同仓演进——API 契约一改，插件在同一个提交里跟上，不会漂移。

本仓库只放目录文件，是因为 `/plugin marketplace add` 会**完整克隆** marketplace 仓库，而 mint 是个几百 MB 的 monorepo。插件本身用 `git-subdir` 源，Claude Code 会**稀疏克隆**，只取 `plugins/wikipali/` 那一个目录。所以你装插件时下载的是几十 KB，不是几百 MB。

## 安全

插件能在你的机器上执行代码。装之前请读插件自己的 README，那里写明了它会读写哪些文件、会往哪里发数据。
