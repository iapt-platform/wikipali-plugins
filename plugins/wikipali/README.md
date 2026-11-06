# wikipali

[WikiPali](https://www.wikipali.org) 巴利三藏平台的 Claude Code 插件。

这是**底层插件**：只管存取 WikiPali 数据。三个 skill：

- **`research`** —— 检索与阅读语料做研究：词形展开、按词形检索、出处分布（分根本/义注/复注）、按坐标取原文与各家译本，每条引用可追溯到 WikiPali 坐标与缅/PTS/VRI/泰印本页码。只读，不需要登录。
- **`citation`** —— 解析缅甸著作的引用缩写：`ဝိသုဒ္ဓိ၊၂၊၂၄၁` → 清净道论第二册，坐标 `65-1461`；加 `--text` 连整页巴利原文与章节路径一起取。查的是插件自带的缩写表与页码索引，不加 `--text` 全程离线。
- **`write`** —— 以 **AI 模型身份**把句子、术语、批注写入 WikiPali。

**怎么翻译、怎么审稿**（译文风格、术语标记、随文注释、问题定级、nissaya 读法）不在这里，在应用层插件
[`wikipali-workspace`](../wikipali-workspace)：translate / review / revise / commentary-align / paper。
不装它也能用本插件存取数据，此时译文怎么写完全按你在对话里的要求。

上层插件读共享约定用 `wikipali guide [conventions|api-read|api-write]`——CLI 是两层之间的契约。

写入的句子 `editor_uid` 记为 AI 模型的 uid 而不是操作者本人，署名与审计因此是准确的——谁翻的就是谁翻的。

## 安装

```
/plugin marketplace add iapt-platform/wikipali-plugins
/plugin install wikipali@wikipali
```

**必须在 Claude Code 里装**——Claude Desktop 的 **Add plugin** 只能搜到官方 marketplace。用 Claude Code 装好后，插件在 Claude Desktop 的 **Plugins** 列表里能看到、能用，但升级仍要回 Claude Code 跑命令，所以只用桌面版的用户需要单独装一份 [Claude Code](https://docs.claude.com/en/docs/claude-code/setup)。

不走 marketplace 的话，克隆本仓库后跑 `plugins/wikipali/install.sh --user`。

## 装之前请知道它会做什么

插件能在你的机器上执行代码，装之前你应当知道这一个具体会干什么：

- **读写 `~/.wikipali/credentials.json`**（权限 0600），里面存你的 WikiPali 登录 token、AI 模型身份 token、channel access token 和批注写入授权；
- **往 wikipali.org 写数据**。写入是覆盖式的：相同位置（book / paragraph / word_start / word_end / channel）的已有句子会被替换。插件在每次写入前会回显目标并要求确认；
- **只用 Python 标准库**，不装任何依赖，不建虚拟环境。

它**不会**接触你的密码：登录由 `wikipali-login` 完成，密码只读入内存，不落盘、不进日志、不进对话。

- 有终端时用 `getpass` 读；
- **没有终端时（Claude Desktop、IDE、AI 代跑）自动弹出操作系统的密码对话框**——你把密码输给系统，AI 全程看不到；
- 两者都不可用时它会明确报错并给出办法（Claude Desktop 按 <kbd>Ctrl</kbd>+<kbd>`</kbd> 有内置终端，仅本地会话；SSH 场景凭据在远端，要在那台机器上登录）。

登录是一次性的：token 有效期 365 天，同一台机器上所有副本共用 `~/.wikipali/credentials.json`。

## 用法

装好后直接对 Claude 说「把这些译文写进 WikiPali 的某某 channel」即可，它会自己走完流程。手工调用：

```bash
wikipali whoami        # 看当前凭据状态
wikipali-login         # 登录（自己跑）
wikipali ensure-model --name <模型标识>
wikipali channels
wikipali write sents.json --channel <uid> --dry-run
```

管理员（root / administrator 账号）还可以只读地看运营统计，给 agent 做分析：

```bash
wikipali admin stats agent --since 2026-10-01      # AI 问答汇总（评价、质量检查、工具）
wikipali admin stats reading                       # 阅读汇总
wikipali admin feedback --rating down              # 用户点踩与原因
wikipali admin runs --status error                 # 提问记录；admin run <run_id> 看研究过程
wikipali admin digest --out digest.jsonl           # 精简导出（只含同意用于改进的提问，不含身份）
```

句子文件的形状：

```json
{
  "channel_uid": "<channel uid>",
  "sentences": [
    { "book_id": 1, "paragraph": 10, "word_start": 0, "word_end": 12,
      "content": "译文", "content_type": "markdown" }
  ]
}
```

## 站点

内置两个线上地址：`www`（`https://www.wikipali.cc/api`，稳定版）与 `next`
（`https://next.wikipali.cc/api`，最新版）。两者共享同一个数据库和密钥，凭据通用，可随时切换：

```bash
wikipali endpoint          # 列出并标出当前
wikipali endpoint next     # 改默认
wikipali --api next ...    # 只影响这一次调用
```

其他地址（如本地测试机）不进插件代码，在本机手工登记，只保存在 `~/.wikipali/credentials.json`：

```bash
wikipali endpoint add local http://127.0.0.1:8000/api --label 开发机
wikipali endpoint local            # 切过去（独立库，凭据与缓存单独一桶）
wikipali endpoint remove local     # 删除登记
```

`www` 是稳定版、`next` 是最新版**代码**，不是不同的数据环境。较新的端点在稳定版上返回 404，意思是「该站点代码版本还没到」。

## 权限模型

三种 token，职责不混：

| Token | 代表谁 | 有效期 |
|---|---|---|
| 用户 token | 人类操作者 | 365 天 |
| 模型 token | AI 模型身份，写句子时的 `Authorization` | 30 天，可撤销 |
| access token | 被委托的 channel 编辑权，写句子时的 body 字段 | 7 天 |
| 写入授权（agent grant） | 写批注时的 `X-Agent-Grant` 请求头：你授权模型代写某 channel / book 的批注，署名是你、模型记为协作者 | 7 天 |

模型自身不是任何 channel 的 owner，它的全部写权限来自你签发的 access token，且受 book 范围约束——**你没有编辑权的 channel，签发阶段就会失败**。凭据泄漏时用 `wikipali revoke` 作废该模型已签出的全部 token（批注的写入授权一并失效）。

## 开发

本插件在 [iapt-platform/mint](https://github.com/iapt-platform/mint) 的 `plugins/wikipali/` 下开发，与被调用的 Laravel API（`api-v13/`）同仓演进——API 契约一改，插件在同一个提交里跟上。设计文档在 `docs/wikipali-write-skill-design.md`。

端点细节见 `references/api-read.md` 与 `references/api-write.md`；跨 skill 的通用约定（坐标、引用格式、文献层次、译文来源判定）见 `references/conventions.md`。

## License

MIT
