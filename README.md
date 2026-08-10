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
| [`wikipali`](plugins/wikipali) | **Library（无需登录）**：分类目录、词形展开、检索、出处分布、章节目录与整章阅读、本文↔义注↔复注段落对应、多版本、词频、术语表、公开文章与文集。**Workspace（需登录）**：以 AI 模型身份写入句子、模型身份 token 与撤销、channel 与 access token。 |

## 更新

**本 marketplace 默认不会自动更新**——Claude Code 只对官方 marketplace 默认开启自动更新，第三方的（包括本仓库）默认关闭。所以有新版时要手动升，两条命令：

```bash
claude plugin marketplace update wikipali     # 先刷新目录
claude plugin update wikipali@wikipali        # 再升插件
```

然后**重启会话**（PATH 注入和 skill 加载都在启动时完成）。

**两步顺序不能省。** marketplace 目录是克隆到本地的副本，会过期；不先刷新目录，本地拿到的还是旧版本的插件文件，直接 `plugin update` 什么都不会发生——连"卸载再重装"也会装回旧版。

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

插件源码就在本仓库的 `plugins/wikipali/`，marketplace 用相对路径引它，**不钉 sha**。所以发版只有三步：

1. 改 `plugins/wikipali/` 下的代码
2. bump `plugins/wikipali/.claude-plugin/plugin.json` 的 `version`，并把 `.claude-plugin/marketplace.json` 里那条改成同一个版本号
3. PR 合进 `iapt-platform/wikipali-plugins` 的 `main`

推之前跑：

```bash
./release-check.sh
```

| 检查 | 挡住什么 |
|---|---|
| `claude plugin validate` | 结构性错误 |
| `marketplace.json` 与 `plugin.json` 版本一致 | 漏 bump——**装的时候以 `plugin.json` 为准**，两处不一致时 marketplace 标了新版也没用 |
| `source` 指向的目录存在，且带 `.claude-plugin/plugin.json` | 路径写错 |
| `bin/` 下的程序有可执行位 | 丢了 x 位，插件命令进了 PATH 也跑不起来 |
| `lib/` 与 `bin/` 的 Python 能编译 | 语法错误被推上去 |

合并方式**不限**——squash 也可以。以前必须用 merge commit，是因为 marketplace 钉着 mint 的 commit sha，squash 会让那个 sha 失效；现在没有 sha 了。

## 这个仓库里有什么

```
plugins/wikipali/   插件本体（bin / lib / skills / references）
docs/               设计文档与功能覆盖清单
.claude-plugin/     marketplace 目录文件
```

插件曾经住在 [iapt-platform/mint](https://github.com/iapt-platform/mint) 里，用 `git-subdir` 稀疏克隆取出来——那是为了不让用户为几十 KB 的插件下载一个几百 MB 的 monorepo。现在插件自己就在这个小仓库里，`/plugin marketplace add` 完整克隆也只有几百 KB，稀疏克隆和 sha 钉桩都不再需要。

代价是插件的 `references/api-*.md` 记的是 [mint](https://github.com/iapt-platform/mint) 那边 Laravel API 的行为，两者不再同仓——**改 API 时要记得回这里更新文档**。

## 安全

插件能在你的机器上执行代码。装之前请读插件自己的 README，那里写明了它会读写哪些文件、会往哪里发数据。
