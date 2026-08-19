---
name: write
description: "Use this skill to write sentences (translations, commentary) into the WikiPali sentence database over its HTTP API, from any project. Trigger whenever the user asks to upload, push, publish, sync, or save translated Pali sentences to WikiPali / 巴利文 / wikipali.org, or mentions writing to a WikiPali channel, or asks to list / add / edit their own WikiPali 术语表 / term glossary entries, or asks about the wikipali CLI, wikipali-login, or ~/.wikipali/credentials.json. Also covers the user's own term glossary (dhamma terms): listing, creating, and editing entries in a channel. Handles login, AI-model identity tokens, channel selection, access tokens, and batched writes with attribution as the AI model rather than the human operator. Do not use for reading WikiPali data or for unrelated Laravel/API work."
metadata:
  author: mint
---

# WikiPali 写入

把句子和术语写进 WikiPali，**署名为 AI 模型身份**（`editor_uid` = 模型 uid），而不是操作者本人。

只依赖 Python 标准库，直接跑，不要建虚拟环境：

- `wikipali-login` —— 唯一接触密码的程序，**必须由用户本人在真正的终端里执行**
- `wikipali` —— 其余全部操作

命令是 `wikipali <子命令>`，登录是独立的 `wikipali-login`。

⚠ **刚装好或刚更新插件时，这两个命令可能还不在 PATH 上**——PATH 注入在会话启动时完成，装完要重启会话。若 `command -v wikipali` 为空，改用 `${CLAUDE_PLUGIN_ROOT}/bin/wikipali`，并提醒用户重启会话。

**坐标、引用格式、术语链接与注释、译文来源判定、凭据规矩见 `references/conventions.md`——那是所有 skill 共用的，必须遵守。** 端点细节见 `references/api-write.md`。

## 铁律

**全部硬约束都在这一节**，照着做不必先去翻 `references/conventions.md`；那份文件
给的是细节、例子与理由。

### 凭据与写入

1. **永远不要向用户索要密码。** 需要登录时**直接执行 `wikipali-login`**——密码由终端的
   `getpass` 或**操作系统的密码对话框**收取，**不经过你**，你既看不到也无法读取。
   绝不允许的三件事：向用户索要密码、把密码写进命令行参数、让用户把密码打进对话
   （那会进入会话记录）。

   ⚠ **不要以「这个命令要读密码 / 我不能处理凭据 / 本会话没有交互式终端」为由拒绝执行它。**
   这三条都不成立：密码不经过你；无 TTY 时它自动改用系统对话框，那正是为这种环境设计的。
   先跑，让它自己判断环境——只有它明确报错时才转达下面的办法。

   若它报「既没有交互式终端也没有图形界面」，把这几条转达给用户：
   - **Claude Desktop**：按 <kbd>Ctrl</kbd>+<kbd>`</kbd> 打开内置终端，在里面跑 `wikipali-login`（内置终端仅本地会话有）；
   - **SSH / 远程开发机**：凭据存在远端，要在**那台机器**上开终端登录；
   - 自动化环境：`... | wikipali-login --username <名字> --password-stdin`。
2. **写入前必须让用户确认。** `wikipali write` 默认会回显目标并等确认；只有用户已经明确同意本次写入时，才可以加 `-y`。
3. **绝不打印 token 全文**（`~/.wikipali/credentials.json` 里的任何值）。脚本自己会打码，不要 `cat` 那个文件。
4. **`count` 不等于提交条数就是有句子没写进去**，必须如实报告给用户，不要说「已全部写入」。
5. **收到 401 不要自动重试**，按脚本的提示走。
6. **术语只能写进 channel。** 不属于任何 channel 的 studio 级术语，模型一律无权建、
   无权改（access token 是 channel 级的，代持不了 studio 权限）。撞上这种情况就如实
   告诉用户「这条得你自己在网站上改」，不要换着法子重试。
7. **术语冲突时服务端拒绝而不是覆盖**（与句子相反）。报「已存在」就去 `my-terms` 找到
   那条的 guid 用 `term-edit` 改，不要改个 tag 绕过去建重复条目。

### 译文内容

8. **坐标不能编造。** 写之前用 `wikipali get <book>-<para> --json` 取真实句子，
   把要写的 `(book_id, paragraph, word_start, word_end)` 与之做集合比对，确认
   无编造、无遗漏；写完独立读回，不要只信 `write` 自报的条数。
9. **默认现代汉语。** 通顺易读的书面语。不要古汉语，不要半文半白，不要译经腔——
   「尔时」「复次」「者……也」「谓」「如是」这类仿古句式一概不用。用户指定风格时
   才改。
10. **术语标记默认不用。** 用户明确要求时才把巴利术语写成 `[[词根]]`；必须用**词典形**
   而非原文的变格形，且**写前用 `wikipali forms <词>` 验证**——展不出词形的不是有效
   词根，链接会落空。普通名词不算术语（`asuci` 就是「不净」，不加标记）。
11. **注释默认不加。** 用户明确要求时才加，且必须：紧跟被注释词、反引号包裹、
   **不能换行**、**标出来源**（`**义注**：`、`**复注**：`）。注释内容只能取自
   `wikipali related` 找到的义注复注，**不许自己发挥**；注释里的巴利词不再加 `[[ ]]`。
12. **被解释词必须与所注文本逐字同译。** 义注的黑体引自本文、复注的引自义注；
    同一 channel 内译法不一致，读者就看不出这条注在注哪个词。这条可机械核查。
13. **文献层次必须标明**，本文、义注、复注不能混——把义注的解释当成经律本身的
    说法是学术错误，不是措辞问题。**机器生成的译文必须显式标注。**

## 首次准备

```bash
wikipali whoami          # 先看缺什么
```

按缺什么补什么：

```bash
# 1) 登录（用户自己在另一个终端里跑，不要用 ! 前缀，也不要代跑）
wikipali-login

# 2) 建立模型身份并取 token；--name 必须是你自己的模型标识
wikipali ensure-model --name claude-opus-5

# 3) 看有哪些可写的 channel
wikipali channels
```

`--name` 决定句子的作者署名，**不要冒用别的模型的名字**。同名记录已存在时会直接复用（幂等）。

## 写入

输入是一个 JSON 文件，两种形状都接受：

```json
{
  "channel_uid": "可选，整批共用的 channel",
  "sentences": [
    { "book_id": 1, "paragraph": 10, "word_start": 0, "word_end": 12,
      "content": "译文", "content_type": "markdown" }
  ]
}
```

或直接是句子数组（此时用 `--channel` 指定目标）。`content_type` 可省略，默认 `markdown`；`channel_uid` 可以逐句给，用于跨 channel 批量写。

译文**默认用现代汉语**（通顺易读的书面语，不要古汉语、不要半文半白、不要译经腔），
**默认正常翻译、不加注释**。用户明确要求时才用这两种标记，格式见 conventions.md：

- **术语标记**：巴利术语写成 `[[词根]]`（`[[seyyasaka]]`），用词典形而非变格形
- **注释**：紧跟被注释词、反引号包裹、不能换行，来源要标出——
  ``不乐于`**义注**：被欲贪的热恼所烧，但**并非希求还俗**`修习 [[brahmacariya]]``

**硬约束**：译义注、复注时，其中的**被解释词**（义注的黑体引自本文，复注的引自义注）
必须与所注文本在同一 channel 里逐字同译，否则读者看不出这条注在注哪个词。

```bash
wikipali write sentences.json --channel <uid或名字片段> --dry-run   # 先看回显
wikipali write sentences.json --channel <uid或名字片段>            # 再真写
```

`write` 会自动完成：解析校验 → 确定 channel → 回显确认 → 按需签发/复用 access token → 每 50 条一批提交 → 核对 `count` 并报告漏写的句子。

**写入是覆盖式的**：相同 `(book_id, paragraph, word_start, word_end, channel_uid)` 的已有句子会被替换。回显里那行警告要转达给用户。

## 术语表

用户自己的术语表（`v2/terms`），与只读的社区权威译名表（`wikipali terms`）**不是一回事**——
后者是全网通用的译名对照，这里是用户自己 channel 名下、可增可改的条目。

```bash
wikipali my-terms                      # 当前账号名下全部
wikipali my-terms --channel <名字片段>  # 只看某个 channel
wikipali my-terms satipa               # 按词/释义过滤
```

列出走人类身份（只读）；建和改走模型身份 + access token，和写句子同一条链路：

```bash
wikipali term-add satipaṭṭhāna 念处 --channel <名字片段> \
    --other-meaning 念住 --note '注解（markdown）' --tag abhidhamma --dry-run
wikipali term-edit <guid> --meaning 念住          # 只改给出的字段，其余保持原值
```

- `term-add` / `term-edit` **必须有 channel**，见铁律第 6 条。`term-edit` 的 channel
  从术语本身读出，不用给。
- guid 用 `my-terms` 查（输出行首是 guid 前 8 位，`--json` 拿完整值）。
- `--dry-run` 先看回显，确认无误再真跑；用户没明确同意本次写入之前不要加 `-y`。
- 改动是**增量**的：没给的字段保持原值，不会被清空。
- 译名应与社区术语表（`wikipali terms`）一致；不一致时要在 `--note` 里说明理由。

## 站点

四个线上地址共享同一个数据库和密钥，凭据通用；`www` 是稳定版、`next` 是最新版代码，**不是**不同的数据环境。

```bash
wikipali endpoint            # 列出并标出当前
wikipali endpoint next       # 改默认（唯一会写回凭据的方式）

⚠ 用户要切换站点却**没指定目标**时，把站点列表**作为选择题呈现给他**再执行——不要
替他挑，也不要指望命令行弹选单（agent 没有 tty，永远等不到）。见 conventions.md。
wikipali --api next write …  # 只影响这一次调用
```

新端点在稳定版上返回 404 是「代码版本还没到」，不是「资源不存在」。

## 出问题时

| 现象 | 处置 |
|---|---|
| 401 | 用户 token 失效 → 重跑 `wikipali-login`；模型 token 失效或被撤销 → 重跑 `ensure-model` |
| 403 | 不是 channel 的 owner/协作者，或不是模型 owner。指出缺哪项权限，别换个姿势重试 |
| `count: 0`（签 access token） | 对该 channel 无编辑权。**中止写入**，不要继续 |
| `count` 小于提交条数 | 逐条差集已由脚本列出，如实转达 |
| 404（`ai-model-token` 等新端点） | 提示切到 `next` 或稍后再试 |

凭据泄漏时撤销模型的全部 token：

```bash
wikipali revoke
```

## 更多

端点字段、返回形状与各处陷阱见 `references/api-write.md`。若脚本行为与该文件对不上，多半是这份副本过期了——插件用户跑 `/plugin update`，手工安装的用户重新装一遍。
