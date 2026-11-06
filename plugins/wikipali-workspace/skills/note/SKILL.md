---
name: note
description: "Use this skill to add external notes (外挂注释, discussion type=note) to translated sentences on WikiPali without changing the translation — explain hard words, supply background, point out what the commentary says — with content drawn from the aṭṭhakathā / ṭīkā or nissaya and its source labelled, anchored to the exact phrase. Trigger whenever the user asks to 加外挂注释 / 外挂注释 / 给译文加注但不改译文 / 给难词加边注 / 把义注的解释挂成注释 / annotate a translation with side notes, for one sentence or a whole chapter. Do not use for inline notes written into the translation text itself (translate / revise skill, per the style file), for commentary alignment with {{…}} templates (commentary-align skill), or for reporting errors (review skill: issue)."
---

# 外挂注释

给 channel 里的译文挂边注（`type=note`）：**不改译文一个字**，在锚点处显示一条注释，解释难词、
补出背景、交代义注怎么说。

三种「注」别混：

| 用户要的 | 归谁 | 结果 |
|---|---|---|
| 外挂注释：译文不动，旁边挂一条注 | **本 skill** | `note` 批注，阅读页在锚点末尾显示边注，无出处 |
| 随文注释：注释写进译文里（反引号包裹） | `translate` / `revise`，按风格文件 | 改了译文本身 |
| 义注对照：把义注那几句的译文挂上去，带出处 | `commentary-align` | `commentary` 批注，内容是 `{{…}}` 模板 |

**存取全部走底层插件 `wikipali` 的命令**，本 skill 只规定**注什么、怎么写**。

- `command -v wikipali` 为空：底层插件没装、没启用，或刚装完还没重启会话。请用户
  `/plugin install wikipali@wikipali` 后重启会话。
- 批注命令、挂点、锚点、写入授权：底层的 `write` skill「批注」一节。
- 文献层次：`wikipali guide conventions`「文献层次必须标明」。
- 读 nissaya 前看 `${CLAUDE_PLUGIN_ROOT}/references/nissaya-reading.md`。

## 铁律

1. **注释内容只能有出处**：取自 `wikipali related` 找到的义注、复注，或该段的 nissaya，或用户
   自己给的内容。**不许自己发挥**；查不到依据就不注，告诉用户。
2. **来源必须标明**，开头写 `**义注**：`、`**复注**：`、`**Nissaya**：`——义注的说法不是本文的说法，
   混为一谈是学术错误。用户自己写的注不加来源标签。
3. **体现义注的主要意思，不是只摘一句。** 先把该段的义注读完，再决定注什么；用通俗的现代汉语
   把意思说出来，不必逐字直译义注。
4. **挂在译文上，锚点逐字摘自那一句译文**：`--channel <译文>` ＋ `--quote-exact '<被注释的词>'`，
   摘录含标点、原样照抄，位置由工具算。不确定就先 `wikipali get <坐标> --channel <译文> --json`。
5. **不重复挂。** 写前 `wikipali discuss <坐标> --channel <译文> --type note` 看已有的；同一处已有
   意思相同的注就跳过。
6. **该句没有可注的就不注**，不为了均匀硬凑。
7. **先给用户看清单再写**：每条的句 id、锚点摘录、注释全文。确认后才写；批注是追加的，写错要
   手动删（`discuss-delete`）。

## 流程

### 1. 定范围、取材料

```bash
wikipali paras <坐标> --body                              # 体量；一批不超过 12 段
wikipali get <book>:<para> … --channel <译文> --json      # 译文与句子 id
wikipali get <book>:<para> … --json                       # 巴利原文
wikipali related <book>:<para>                            # 义注、复注对应段 → 再 get
```

用户要参考 nissaya 时再取（`wikipali versions` → `get --channel <nissaya uid>`）。

### 2. 选注点

读完原文、译文和义注，挑出值得注的地方：

- 义注对某词有解释、分类、辨异，而译文读者看不出来；
- 义注补出的背景：谁对谁说、指涉何事、为什么这么说；
- 一词多义、译文取了某一义，需要交代依据；
- nissaya 补出的隐含成分、指代对象，译文没写出来又容易误解。

### 3. 写清单，确认后挂上

```bash
wikipali discuss-add 216:35 --channel <译文> --words 2-17 --type note \
    --quote-exact '呵责羯磨' \
    --content '**义注**：tajjanīya 指对屡犯争执的比丘所作的呵责，**并非**驱出僧团。' --dry-run
```

`--dry-run` 看回显，确认后去掉它再跑；用户没明确同意本次写入前不加 `-y`。一段多句时用 `--words`
指明是哪一句。最后报告挂了几条、跳过了哪些（已有 / 无可注）。
