---
name: commentary-align
description: "Use this skill to align a Pali commentary with the text it comments on and upload the alignment to WikiPali — given a CST book name (an6, dn1, mn1 …), a cs_para number and a translation channel, work out which aṭṭhakathā sentences explain which phrase of the mūla translation (and ṭīkā → aṭṭhakathā), then write them as position-anchored notes (discussion type=commentary). Trigger when the user asks for 义注复注对应 / 注释书对应 / 注释对齐 / 把义注挂到根本上 / commentary alignment / anchor commentary notes, or gives a book_name + cs_para + channel for that purpose. Do not use for plain per-sentence discussions (that is the write skill) or for reading commentaries for research (research skill)."
metadata:
  author: mint
---

# 注释书对应（义注 / 复注 → 上一层译文）

输入：`book_name`（CST 书名，如 `an6`）、`cs_para`（CST 段号）、`channel_uid`（译文所在版本）。

输出：若干条 `type='commentary'` 的 discussion，每条把**下一层的一句或几句**挂在
**上一层某句译文的某个片段**上：

| 字段 | 值 |
|---|---|
| `res_id` | 上一层句子在该 channel 的**译文**句子 uid |
| `content` | 下一层句子模板 `{{book-para-start-end}}`（**不是**译文）；多句时并列 `{{…}}{{…}}` |
| `pos_start`/`pos_end` | 片段在译文原始 content 里的字符位 |
| `quote_exact`/`prefix`/`suffix` | 片段摘录与上下文 |

阅读页渲染根本句时，在 `pos_end` 处插入该义注句在同一 channel 的译文作边注。

命令与登录的通用规矩见 `write` skill（模型身份、`ensure-model`、不索要密码），
坐标约定见 `references/conventions.md`。

## 流程

### 1. 取素材

```bash
wikipali note-context <book_name> <cs_para> --channel <channel_uid> --json > ctx.json
wikipali note-context <book_name> <cs_para> --channel <channel_uid>          # 人读版
```

给出三层（根本 / 义注 / 复注）在该锚点下的全部正文句，**每句同时有巴利原文和该 channel
的译文**，句子坐标形如 `{{89-33-2-23}}`。某层没有就不出现；某句没有译文标「无」。

- 只要根本↔义注：`--layers mula,att`；义注↔复注：`--layers att,tika`。
- 各层都查不到 → 如实报告，**不要**拿相邻段落凑。

### 2. 做对应（你自己做，不是调别的模型）

**对照必须看巴利原文**。义注的行文是「先引根本词句（lemma，一般是标记黑体，有时不是，常在 `ti` / `nti` 前），
再释义」——判断「这句义注在解释根本的哪个词」，靠的是巴利 lemma 与根本巴利词形的对应，
译文只用来找**在译文里对应的那段文字**。只看译文会被译者的措辞差异带偏。

对每一对相邻层（根本→义注、义注→复注）：

1. 逐句读下一层的巴利原文，找出它引用的 lemma（`Dassanānuttariyan ti …` 的 lemma 是
   `dassanānuttariyaṃ`）。
2. 在上一层巴利原文里找到这个词（注意连音、格变化、`ṃ`↔`n`），确定它在**哪一句**。
3. 在那一句的**译文**里找出译这个词 / 短语的那段文字，原样摘出来作 `quote_exact`。
4. **target 永远是上一层的一句**；**note 可以是下一层的多句**——根本里的一个词常由义注
   好几句来解释（引出 lemma 的句子 + 后面展开的句子）。把这些句子**逐句**列进 `note`
   （数组），不必相邻、可以跨段。这仍是**一条**对应，content 写成按顺序并列的句子模板
   `{{…}}{{…}}`。**不要把几句合并成区间**（`101-513-14-42` 这种写法会被拒绝）。
5. 跳过：总起 / 过渡句、段号行（`8-9.`）、只有 `Esa nayo …`（「余同此理」）这类不对应
   具体片段的句子；对应不上的**宁缺毋滥**，不要硬挂。
6. 一个 lemma 在上一层出现多次时，挂在它**第一次**出现、且语境符合的那一处；若 `quote_exact`
   在该句译文里不唯一，给 `quote_prefix` / `quote_suffix` 消歧。

上一层某句**没有译文**时挂不了——在报告里列出，不要改挂到别的句子上。

写成 **JSONL** 文件：**一行一条对应，一行一个完整的 JSON 对象**，不要外层数组、不要
`{"items": […]}`。条目多时一个大 JSON 很容易在中途截断、收不了尾，整份作废；JSONL 坏一行
只丢一行。每写完一行就是一条完整记录，也方便分批追加（`>>`）。

只写这几个字段；位置由工具数，**不要自己数字符**：

```jsonl
{"target": "89-33-2-23", "note": "101-513-6-13", "quote_exact": "six unsurpassed things"}
{"target": "89-33-27-49", "note": ["101-513-14-18", "101-513-19-23", "101-513-24-42"], "quote_exact": "The unsurpassed sight"}
{"target": "89-33-27-49", "note": "101-513-43-59", "quote_exact": "the unsurpassed hearing", "quote_prefix": "sight,"}
```

- 一条对象不要跨行；空行和 `//` 开头的行会被忽略。
- 句子很多时分批做：每处理完一组就把结果追加到文件，不必一次输出全部。
- `target`：上一层**一个**句子坐标（`note-context` 里的 sid），不能是列表。
- `note`：下一层句子坐标——单个 sid，或 sid 数组（解释同一片段的全部句子）。
  每个都必须是 `note-context` 里真实存在的单句，**不能写区间**。
- `quote_exact`：**逐字摘自 target 句的译文**（`translation` 字段，含标点、含其中的 markdown），
  不要改写、不要补空格、不要用巴利原文。
- 片段尽量短而准——译 lemma 的那几个词，不要整句。

### 3. 预检再写

```bash
wikipali note-push items.jsonl --channel <channel_uid> --dry-run
wikipali note-push items.jsonl --channel <channel_uid> -y
```

`note-push` 做的事：按摘录在译文原始 content 里数出 `pos_start`/`pos_end`，自动补 32 字
前后缀；校验 `target` 与 `note` 各项都是真实单句、`target` 在该 channel 有译文、插入点不落在 `{{…}}`/`[[…]]`
里；同一句已有同一 `note` 的对应就跳过（`--replace` 则删旧重写）。

预检里的 `✗` 逐条修（`#N` 是行号）：坏行（输出被截断）→ 把那一行重写完整；摘录不在句中 → 回到译文原样复制；不唯一 → 加前后缀；不是真实句子 →
回 `note-context` 核对 sid，区间拆成数组。**全部修好再去掉 `--dry-run`**。

### 4. 报告

告诉用户：写了几条、跳过几条（已存在 / 无译文 / 对应不上），以及每条 `target ← note 「摘录」`
的清单。核对用：

```bash
wikipali discuss <book>:<para> --channel <channel_uid> --words <起-止> --type commentary
```

改错一条用 `discuss-edit <id> --quote-exact … --pos-start … --pos-end …`，删用 `discuss-delete <id>`。

## 要点

- 字符位的口径是**译文原始 content**（服务端 `mb_strlen`），渲染后的 HTML、去掉 markdown 的
  纯文本都不对——所以只让工具数。
- 译文被改动后位置可能失效；服务端对越界位置会挂到句尾，`quote_exact` 留着供日后重定位。
- 阅读页按 (book, para, channel) 缓存，新写的对应可能要等缓存过期才显示。
- 对应是**逐 channel** 的：挂在 A 版本译文句上的，只在读 A 版本时出现。
