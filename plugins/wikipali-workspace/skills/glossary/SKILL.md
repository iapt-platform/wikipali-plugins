---
name: glossary
description: "Use this skill to work with external glossary terms (外挂术语, discussion type=glossary) on WikiPali translations — find Pali terms in a chapter that deserve a term link (not yet in the glossary, or translated inconsistently), attach trial glossary terms to the exact phrases without changing the translation, review the open ones, and when a term is settled promote it into the user's term glossary (term-add) and close the trial. Trigger whenever the user asks to 加外挂术语 / 挂外挂术语 / 试用译名 / 找出该挂术语的词 / 处理外挂术语 / 把外挂术语收进术语表 / external glossary. Do not use for simply listing or editing the user's term glossary entries (wikipali write skill: my-terms / term-add / term-edit) or for inline [[term]] marks written into the translation (translate / revise skill)."
---

# 外挂术语

外挂术语（`type=glossary`）**不改译文**：把某句译文里的一段文字临时显示成术语，挂上去**试用**，
围绕「这个译名值不值得正式收进术语表」讨论。生命周期：

```
发现候选 → 挂外挂术语试用 → 讨论（回复）→ 定了：term-add 收进术语表，关闭外挂术语
                                        → 不收：回复理由，关闭外挂术语
```

三样东西别混：

| 用户说 | 是什么 | 归谁 |
|---|---|---|
| 加外挂术语、试用译名 | `glossary` 批注，临时的 | **本 skill** |
| 新建术语、把 X 收进术语表 | 用户自己的术语表条目（`term-add`） | 底层 `write` skill；本 skill 只在「收录」一步调用它 |
| 译文里写 `[[词根]]` | 术语标记，改了译文本身 | `translate` / `revise`，按风格文件 |

**存取全部走底层插件 `wikipali` 的命令**，本 skill 只规定**挂什么、怎么定**。

- `command -v wikipali` 为空：底层插件没装、没启用，或刚装完还没重启会话。请用户
  `/plugin install wikipali@wikipali` 后重启会话。
- 批注命令、锚点、写入授权：底层的 `write` skill「批注」「术语表」两节。

## 铁律

1. **`--title` 是术语词头，用巴利词典形**，不用变格形；挂之前用 `wikipali forms <词>` 验证——
   展不出词形的不是有效词根。词头不能含 `[ ] { } | #`。
2. **必须给锚点**：`--channel <译文>` ＋ `--quote-exact '<译文里那几个字>'`，逐字摘自那一句译文。
   摘录不能和句中已有的 `[[…]]`、`{{…}}`、粗体重叠，工具会提前报错；完全落在 `**…**` 里面的可以挂
   （加粗的被解释词常就是术语）。
3. **只挂在译文上，只有该句 channel 的编辑者能挂。** 没有编辑权时写入授权签不出来，如实告诉用户。
4. **不重复挂。** 先 `discuss-range --type glossary --status active` 看本章已有的；同一个词头已在试用，
   就在那条下面回复，不另开。
5. **挂之前先查术语表**：`wikipali my-terms <词> --channel <译文>`（用户自己的）、`wikipali terms <词>`
   （社区的）。已正式收录、且译文用的就是那个译名的，不用挂。
6. **收录要用户拍板。** 讨论有结论、用户同意后，才 `term-add` 并关闭外挂术语；不同意的回复理由后关闭。
7. **先给用户看清单再写**，确认后才挂；批注是追加的，挂错要手动删（`discuss-delete`）。

## 流程

### 1. 找候选

```bash
wikipali get <book>:<para> … --channel <译文> --json      # 译文
wikipali get <book>:<para> … --json                       # 巴利原文
wikipali discuss-range <坐标> --chapter --channel <译文> --type glossary --status active
```

候选是这几类教理术语、专名：

- 用户术语表与社区术语表里**都没有**的；
- 同一个巴利词在本章**译法不一致**的（每种译法各出现在哪几句，一并列出）；
- 用户术语表里有，但译文**没用那个译名**的——这种先问用户：是改译文（交给 `revise`），还是挂外挂术语讨论要不要换译名。

普通词不算术语（`asuci` 就是「不净」），拿不准就问用户。

### 2. 写清单，确认后挂上

清单每条：词头（词典形）、句 id、锚点摘录、试用译名、理由（术语表缺 / 本章不一致 / 与社区译名不同）。

```bash
wikipali discuss-add 216:35 --channel <译文> --words 2-17 --type glossary \
    --title tajjanīyakamma --quote-exact '呵责羯磨' \
    --content '试用此译名。社区术语表无此条；本章另有一处译作「呵责业」（216-36-0-9）。' --dry-run
```

确认后去掉 `--dry-run` 再跑；用户没明确同意本次写入前不加 `-y`。

### 3. 处理已挂的

```bash
wikipali discuss-range <坐标> --chapter --channel <译文> --type glossary --status active
wikipali discuss <坐标> --channel <译文> --words <起-止> --type glossary   # 看某条与它的回复
```

把每条的讨论汇总给用户，请他逐条定：

- **收录**：
  ```bash
  wikipali term-add tajjanīyakamma 呵责羯磨 --channel <译文> --note '…' --dry-run
  wikipali discuss-reply <id> --content '已收入术语表。'
  wikipali discuss-edit <id> --status close
  ```
  已有同名条目时 `term-add` 会报「已存在」——去 `my-terms` 找到 guid 用 `term-edit` 改，不要另建。
- **不收**：`discuss-reply <id> --content '不收：……'`，再 `discuss-edit <id> --status close`。
- **再议**：只回复，留着不关。

收录后译文里不一致的地方，交给 `revise` 统一；本 skill 不改译文。
