<div align="center">

# WikiPali Plugins

**让 Agent 具备访问 [WikiPali](https://www.wikipali.org) 巴利语三藏资料、多版本译文和工具书的能力**

Claude Code 插件市场 · 读语料做研究，也能以 AI 模型身份写回

**中文** · [English](README.en.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Plugin](https://img.shields.io/badge/plugin-wikipali%20v0.11.0-blue.svg)](plugins/wikipali)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-marketplace-orange.svg)](https://docs.claude.com/en/docs/claude-code/plugins)

</div>

---

## 快速开始

```
/plugin marketplace add iapt-platform/wikipali-plugins
/plugin install wikipali@wikipali
```

装完**重启会话**——插件命令进 PATH、skill 被加载，都发生在会话启动时。

> [!NOTE]
> **必须在 Claude Code 里装。** Claude Desktop 的 **Add plugin** 只能搜到官方 marketplace，装不了第三方的。
> 用 Claude Code 装好之后，插件在 Claude Desktop 的 **Plugins** 列表里就能看到、能用——但升级仍然只能回 Claude Code 跑命令。
> 所以只用桌面版的用户，需要**单独装一份 [Claude Code](https://docs.claude.com/en/docs/claude-code/setup)**。

装好后直接用自然语言提问：

```
「dukkha 在长部里出现在哪些段落？义注怎么解释？」
「把这批译文写进 WikiPali 的 xxx channel」
```

## 插件

### [`wikipali`](plugins/wikipali) — WikiPali 客户端

| 能力 | 说明 |
|---|---|
| **Library**（无需登录） | 分类目录、词形展开、词典释义、全文检索、出处分布、章节目录、段落清单与整章阅读、根本 ↔ 义注 ↔ 复注段落对应、多版本对照、词频、术语表、公开文章与文集 |
| **引用缩写**（离线） | 把缅甸著作脚注里的 `ဝိသုဒ္ဓိ၊၂၊၂၄၁` 解析成著作名与坐标 `65-1461`——缅甸版页码经 6.2 万条页码标记索引换算成段落号，全程不联网 |
| **Workspace**（需登录） | 以 **AI 模型身份**写入句子、术语与批注；模型身份 token 的签发与撤销；channel 与 access token 管理 |

两个 skill：`research`（只读研究）与 `write`（写入）。写入的句子 `editor_uid` 记的是 AI 模型的 uid 而不是操作者本人——**谁翻的就是谁翻的**，署名与审计因此准确。

详见[插件 README](plugins/wikipali/README.md)：安全边界、权限模型、CLI 用法、站点切换。

## 更新

**第三方 marketplace 默认不自动更新。** 有新版时手动升，两条命令：

```bash
claude plugin marketplace update wikipali     # 1. 先刷新目录
claude plugin update wikipali@wikipali        # 2. 再升插件
```

然后**重启会话**。

> [!IMPORTANT]
> **两步顺序不能省。** marketplace 目录是克隆到本地的副本，会过期；不先刷新目录，本地拿到的还是旧版插件文件，直接 `plugin update` 什么都不会发生——连「卸载再重装」也会装回旧版。

<details>
<summary><b>Claude Desktop 用户怎么升级</b></summary>

桌面版的 **Manage plugins** 只有 enable / disable / uninstall，**没有更新按钮**，也不会自动升级。升级只能靠 Claude Code 的命令行。

手边没有终端的话，桌面版有内置的：按 <kbd>Ctrl</kbd>+<kbd>`</kbd> 打开（Views 菜单也行，仅本地会话有），在里面跑上面那两条命令。

若 `claude --version` 报找不到命令，说明这台机器还没装 Claude Code（或不在 `PATH` 里）——先[装上](https://docs.claude.com/en/docs/claude-code/setup)，或用绝对路径，例如 `~/.local/bin/claude plugin update wikipali@wikipali`。
</details>

<details>
<summary><b>SSH 会话要在远端升级</b></summary>

SSH 会话读的是**远程主机**的 `~/.claude`，插件也装在那边。要在**那台机器**上跑升级命令，在本地笔记本上升没有用。
</details>

<details>
<summary><b>确认升上去了</b></summary>

```bash
claude plugin details wikipali                   # 看版本号
ls ~/.claude/plugins/cache/wikipali/wikipali/    # 看缓存里有哪些版本
```
</details>

## 安全

插件能在你的机器上执行代码。装之前请读[插件自己的 README](plugins/wikipali/README.md)，那里写明了它会读写哪些文件、会往哪里发数据。

简要说：只用 Python 标准库、不装依赖；凭据存在 `~/.wikipali/credentials.json`（权限 0600）；**密码永远不经过 AI**——登录由独立的 `wikipali-login` 完成，无终端时弹出操作系统密码对话框；每次写入前回显目标并要求确认。

## 仓库结构

```
plugins/wikipali/    插件本体（bin / lib / skills / references）
docs/                设计文档与功能覆盖清单
.claude-plugin/      marketplace 目录文件
release-check.sh     发版前的自检脚本
```

## 参与开发

### 发版流程

插件源码就在本仓库的 `plugins/wikipali/`，marketplace 用相对路径引它、**不钉 sha**。所以发版只有三步：

1. 改 `plugins/wikipali/` 下的代码
2. bump `plugins/wikipali/.claude-plugin/plugin.json` 的 `version`，并把 `.claude-plugin/marketplace.json` 里那条改成同一个版本号
3. PR 合进 `main`

推之前跑 `./release-check.sh`：

| 检查 | 挡住什么 |
|---|---|
| `claude plugin validate` | 结构性错误 |
| 两处 `version` 一致 | 漏 bump——**装的时候以 `plugin.json` 为准**，两处不一致时 marketplace 标了新版也没用 |
| `source` 目录存在且带 `.claude-plugin/plugin.json` | 路径写错 |
| `bin/` 下程序有可执行位 | 丢了 x 位，命令进了 PATH 也跑不起来 |
| `lib/` 与 `bin/` 的 Python 能编译 | 语法错误被推上去 |

合并方式**不限**，squash 也可以。（以前必须用 merge commit，是因为 marketplace 钉着 mint 仓库的 commit sha，squash 会让那个 sha 失效；现在没有 sha 了。）


## 相关链接

- [WikiPali 网站](https://www.wikipali.org)
- [iapt-platform/mint](https://github.com/iapt-platform/mint) —— 后端 Laravel API
- [Claude Code 插件文档](https://docs.claude.com/en/docs/claude-code/plugins)

## License

[MIT](LICENSE) © iapt-platform
