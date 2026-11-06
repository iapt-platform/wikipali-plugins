---
name: discuss
description: "Use this skill to open, reply to or summarize a discussion thread (discussion type=discussion) on a WikiPali sentence about an open question in translating or understanding the Pali — a rendering choice, an interpretive disagreement, conflicting commentaries or translations — with a structured post laying out the Pali, existing translations, commentary evidence and the options. Trigger whenever the user asks to 发起讨论 / 开个讨论 / 讨论一下这个译名 / 把这个分歧挂出来讨论 / 回复讨论 / 总结这个讨论串 / 看看这一章有哪些讨论. Do not use for clear errors in a translation (review skill: issue), for trial glossary terms (glossary skill), or for side notes (note skill)."
---

# 讨论

在某一句上开讨论（`type=discussion`），把**没有定论**的问题摆出来，让人判断：译名怎么取、
句子怎么理解、义注与别家译本说法不一……也负责回复已有讨论、汇总一个讨论串。

和相邻类型的分界：

| 情况 | 用什么 |
|---|---|
| 有明确的错，依据清楚（漏译、误译、违背义注） | `issue`，走 `review` |
| 一个译名要试用、讨论该不该收进术语表 | `glossary`，走 `glossary` |
| 解释难词、补背景 | `note`，走 `note` |
| **几种理解或译法都说得通，要人来定** | **`discussion`，本 skill** |

**存取全部走底层插件 `wikipali` 的命令**，本 skill 只规定**怎么开、怎么写**。

- `command -v wikipali` 为空：底层插件没装、没启用，或刚装完还没重启会话。请用户
  `/plugin install wikipali@wikipali` 后重启会话。
- 批注命令、挂点、写入授权：底层的 `write` skill「批注」一节。
- 文献层次、译文来源判定：`wikipali guide conventions`。

## 铁律

1. **只摆证据，不替人下结论。** 可以说你倾向哪个方案、为什么，但要把其他方案和它们的依据一并列出。
2. **每条依据都带得回坐标**：巴利原文、义注复注、别家译文都注明坐标与层次；引用机器译文要标明
   「机器译」。没有依据的说法不写。
3. **挂对地方**：问题在译文上就挂译文（`--channel <译文>`），关乎巴利原文本身（读法、异文）就挂
   原文（不给 `--channel`）。一段多句时用 `--words` 指明是哪一句。
4. **不重复开。** 先看这一句（或这一章）已有的讨论；同一个问题已有讨论就在下面回复。
5. **默认不发站内通知**；用户要提醒别人时才加 `--notify`。
6. **先给用户看标题和正文再发**，确认后才发。讨论是追加的，发错要手动删（`discuss-delete`）。
7. **关闭讨论要用户同意**；有结论时先回复结论，再关闭。

## 流程

### 1. 看已有的讨论

```bash
wikipali discuss <坐标> --channel <译文> --words <起-止>                # 这一句的讨论（默认 type=discussion）
wikipali discuss-range <坐标> --chapter --channel <译文> --type discussion --status active
```

### 2. 备材料

```bash
wikipali get <book>:<para> --json                        # 巴利原文
wikipali get <book>:<para> --channel <译文> --json       # 当前译文
wikipali versions <book>:<para>                          # 有哪些别家译本、有没有 nissaya
wikipali related <book>:<para>                           # 义注、复注
wikipali terms <词>                                       # 社区术语表的译名
```

### 3. 写帖子

**标题**：一句话说清问题，如「tajjanīyakamma 译「呵责羯磨」还是「呵责业」」。

**正文**固定五项：

```markdown
1. **原文**：*…*（只摘相关的那段巴利）
2. **当前译文**：「…」
3. **问题**：哪里有分歧、为什么拿不准
4. **依据**：
   - **义注**（坐标）：*…*（汉语意思）
   - 别家译文：某译本（坐标）译作「…」；⚠ 机器译的注明
   - nissaya、术语表、语法上的依据
5. **可选方案**：
   - A.「…」——理由
   - B.「…」——理由
   - （倾向：A，因为……）
```

正文里巴利、缅文、引文用 `*斜体*`。

```bash
wikipali discuss-add 216:35 --channel <译文> --words 2-17 --type discussion \
    --title 'tajjanīyakamma 译「呵责羯磨」还是「呵责业」' --content-file post.md --dry-run
```

确认后去掉 `--dry-run` 再跑；用户没明确同意本次写入前不加 `-y`。

### 4. 回复、汇总、关闭

- **回复**：`wikipali discuss-reply <id> --content '…'`——只能回复话题本身，不能回复一条回复。
- **汇总**：用户要「总结这个讨论」时，读出话题与全部回复，按「各方观点 → 各自依据 → 共识与分歧 →
  待定事项」整理给用户；用户要贴回去时再作为一条回复发。
- **有了结论**：先回复结论（以及要不要改译文、收术语），用户同意后
  `wikipali discuss-edit <id> --status close`。要改译文交给 `revise`，要收术语交给 `glossary`。
