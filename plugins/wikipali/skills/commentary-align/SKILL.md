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
- **巴利原文里的黑体（被解释词）用 `**…**` 标出**（服务端存的是 html 的 `<strong>` /
  `<span class="bld">`，工具已经转成 markdown）——切意群全靠它，见下一节。

还要知道这一段是不是本章的第一个正文段、本章的标题句是哪一句（规则 3 要用）：

```bash
wikipali paras <book>:<para>        # 报出「章节 / 范围 / 1 标题 + N 正文」
wikipali get <book>:<标题段>        # 标题句的坐标
```

### 2. 做对应（你自己做，不是调别的模型）

**切块的依据是巴利原文里的黑体**，不是译文，也不是你对句意的判断。注释书把被解释词
标成黑体，所以一段注释天然被黑体切成若干**意群**：一个黑体，加上它后面直到下一个黑体
之前的所有句子。

⚠ **不要用 `ti` / `nti` 去找被解释词。** 黑体后面有没有 `ti` 都不说明什么，而且注释书
大量用「……叫做 X」的定义式，那里 `ti` 在**释义**那一侧、黑体在它后面：

```
Tattha andhassa pabbatārohanaṃ viya niccaṃ na hotīti **acchariyaṃ** .
Abhūtapubbaṃ bhūtanti **abbhutaṃ** .
Esā paṭipadā paramāti **etaparamaṃ** , …
```

靠 `ti` 判断会把释义当成被解释词，整段切反。**黑体是现成的，看黑体。**
某层整段一个黑体都没有（原文确实没标，或工具没转出来）时，如实说明再问用户，
不要拿 `ti` 顶上。

规则只有三条，**逐段照做，不要另行取舍**：

**规则 1——黑体决定锚点。**
把黑体词到上一层的巴利原文里找到（注意连音、格变化、`ṃ`↔`n`），确定它在**哪一句**；
target 就是那一句，`quote_exact` 是那一句**译文**里译这个词 / 短语的那段文字，原样摘出。

**不用去数一个意群里有几个被解释词、同一个词被标了几次**。同一个词前后标了两次、
一句里标了两处，都按它实际在解释哪段译文来挂；语义上是一回事就并成一条，不必为了
对齐标记数量拆开。

**规则 2——黑体后面的非黑体句子与它同属一个意群，挂同一个锚点。**
不管那些句子自己有没有引词、看着像不像过渡句，一律列进**同一条**对应的 `note` 数组，
顺序照原文。注释书是成段的散文：一个意群里通常只有头一句带黑体，后面几句是它的展开，
**这是常态，不是硬挂**。不要因为「这句没引词」就把它丢掉或另开一条。

**规则 3——段落里第一个黑体之前的句子**（还没开始释词的引子）：

- 该段是本章的**第一个正文段**时 → target 取本章的**标题句**，**不给 `quote_exact`**
  （整句挂，`pos` 留空，阅读页插在句尾）；
- 不是第一个正文段时 → **哪里都不挂**，在报告里列出来。

标题句也得在该 channel 有译文才挂得上（`note-push` 会拒收没有译文的 target）——
没有就先把标题那一句翻出来写进去，再挂。

**除规则 3 那几句之外，下一层的每一句都必须出现在某一条对应里，不许遗漏。**
`note-push --dry-run` 会报「下一层未覆盖 N 句」并逐句列出，照着补齐；补完只应剩规则 3
允许留白的那几句。

另外两条老规矩不变：

- **target 永远是上一层的一句**，不能是列表；**note 可以是多句**，逐句列进数组，
  不必相邻、可以跨段，**不要合并成区间**（`101-513-14-42` 这种写法会被拒绝）。
- 一个 lemma 在上一层出现多次时，挂在它**第一次**出现、且语境符合的那一处；若
  `quote_exact` 在该句译文里不唯一，给 `quote_prefix` / `quote_suffix` 消歧。

上一层某句**没有译文**时挂不了——在报告里列出，不要改挂到别的句子上。

写成 **JSONL** 文件：**一行一条对应，一行一个完整的 JSON 对象**，不要外层数组、不要
`{"items": […]}`。条目多时一个大 JSON 很容易在中途截断、收不了尾，整份作废；JSONL 坏一行
只丢一行。每写完一行就是一条完整记录，也方便分批追加（`>>`）。

只写这几个字段；位置由工具数，**不要自己数字符**：

```jsonl
{"target": "89-33-2-23", "note": "101-513-6-13", "quote_exact": "six unsurpassed things"}
{"target": "89-33-27-49", "note": ["101-513-14-18", "101-513-19-23", "101-513-24-42"], "quote_exact": "The unsurpassed sight"}
{"target": "89-33-27-49", "note": "101-513-43-59", "quote_exact": "the unsurpassed hearing", "quote_prefix": "sight,"}
{"target": "101-512-2-4", "note": ["101-513-2-5"]}
```

最后一行是**规则 3** 的样子：target 是章节标题句，不给 `quote_exact` ＝ 整句挂。

- 一条对象不要跨行；空行和 `//` 开头的行会被忽略。
- 句子很多时分批做：每处理完一组就把结果追加到文件，不必一次输出全部。
- `target`：上一层**一个**句子坐标（`note-context` 里的 sid），不能是列表。
- `note`：下一层句子坐标——单个 sid，或 sid 数组（解释同一片段的全部句子）。
  每个都必须是 `note-context` 里真实存在的单句，**不能写区间**。
- `quote_exact`：**逐字摘自 target 句的译文**（`translation` 字段，含标点、含其中的 markdown），
  不要改写、不要补空格、不要用巴利原文。
- 片段尽量短而准——译 lemma 的那几个词，不要整句。
- **只有规则 3 的整句挂可以不给 `quote_exact`**（连 `pos` 一起省掉）；其余每条都要给。

### 3. 预检再写

```bash
wikipali note-push items.jsonl --channel <channel_uid> --dry-run
wikipali note-push items.jsonl --channel <channel_uid> -y
```

`note-push` 做的事：按摘录在译文原始 content 里数出 `pos_start`/`pos_end`，自动补 32 字
前后缀；校验 `target` 与 `note` 各项都是真实单句、`target` 在该 channel 有译文、插入点不落在 `{{…}}`/`[[…]]`
里；**核对下一层的覆盖率并逐句列出没挂上的句子**；同一句已有同一 `note` 的对应就跳过
（`--replace` 则删旧重写）。不给 `quote_exact` 的那条回显成「整句」。

预检里的 `✗` 逐条修（`#N` 是行号）：坏行（输出被截断）→ 把那一行重写完整；摘录不在句中 → 回到译文原样复制；不唯一 → 加前后缀；不是真实句子 →
回 `note-context` 核对 sid，区间拆成数组。**全部修好再去掉 `--dry-run`**。

### 4. 报告

告诉用户：写了几条、跳过几条（已存在 / 无译文），以及每条 `target ← note 「摘录」`
的清单。**「没挂上的句子」只应是规则 3 允许留白的那几句**（不是第一个正文段、又在第一个
黑体之前）；除此之外报「未覆盖」就是还没做完，回去补，别把它当成正常结果。核对用：

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
