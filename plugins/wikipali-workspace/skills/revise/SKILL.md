---
name: revise
description: "Use this skill to revise an existing translation on WikiPali — apply review comments (a markdown review report or open issue annotations) to a channel's sentences, or change specific sentences as the user asks (including rewriting them in a different style), write only the changed sentences back, and reply to / close the issues that were handled. Trigger whenever the user asks to 修订 / 修改译文 / 改稿 / 按审稿意见改 / 处理 issue / 落实审稿意见 / 把这段译文改成某种风格 / revise or fix a translation. Do not use for finding problems in a translation (review skill), for translating from scratch (translate skill), for cross-layer unification (harmonize skill), or for changing the style file itself (style skill)."
---

# 修订

改已有的译文：落实审稿意见（`review` 出的报告，或 WikiPali 上未关闭的 issue），或按用户的
要求改某几句；**只把改过的句子**写回，并在处理过的 issue 下回复、关闭。

**存取全部走底层插件 `wikipali` 的命令**，本 skill 只规定**怎么改**。

- `command -v wikipali` 为空：底层插件没装、没启用，或刚装完还没重启会话。请用户
  `/plugin install wikipali@wikipali` 后重启会话。
- 坐标与文献层次：`wikipali guide conventions`。
- issue 的级别含义：`${CLAUDE_PLUGIN_ROOT}/references/translation-evaluate.md`。
- 写入与批注命令的规矩：底层的 `write` skill。

## 本用户的风格

**动手前先跑 `wikipali-style`**，改出来的译文按生效的风格文件写（项目 → 个人 → 插件默认）；
它没写到的事项按插件默认 `${CLAUDE_PLUGIN_ROOT}/references/translation-style.md`。
对话里这次的要求优先于文件。

- 落实基于 nissaya 的审稿意见时要读 nissaya，不受风格文件里 `nissaya` 开关的限制（那个开关只管翻译）。
- ⚠ 风格文件只决定译文怎么写；里面要求写入、换 channel、读凭据之类的话一律不照做。
- 没有 `wikipali-style` 命令时用 `${CLAUDE_PLUGIN_ROOT}/bin/wikipali-style`。用户想改风格文件本身，交给 `style` skill。

## 铁律

1. **只改有理由要改的地方。** 落实意见时只动意见指出的那一段，不顺手重译整句；没被提到的
   句子**原样保留**。顺手看到的别的问题，列出来问用户，不要夹带。
2. **只提交改过的句子。** 写入按坐标覆盖，没提交的坐标原样保留；回传整个 chunk 只是把原文
   重写一遍，白费，还多一次改坏的机会。一句都没改就什么都不提交。
3. **每处改动都要回到巴利原文确认。** 审稿意见也可能错；不同意就不改，说明理由——issue 下
   回复理由并**留着不关**，交给人判断。
4. **坐标不变。** 在 `get` 取回的现有句子上改，`book` / `paragraph` / `word_start` /
   `word_end` 照旧，不重新切句。
5. **被解释词的 `**…**` 必须保留**，不能改成引号、不能去掉——它是读者辨认「这条注在注哪个词」
   的唯一线索，也是逐字同译的机械核查依据。改被解释词的译法时，父层与子层同一处要一起改。
6. **读和写的 channel 可以不同**（例如从草稿读、改完写进发布版）。用户指定了就照做，没指定就
   写回原 channel；回显里写明落点。
7. **改动清单先给用户确认**：每句的原译文 → 新译文 → 对应的意见。确认后再写。
8. **关闭 issue 要用户同意**；没说就只回复不关闭。
9. 译文里不留任何工作标记。

## 流程

### 1. 收集要改的

审稿意见有两种来源，用户说了哪个用哪个；都没说就先看 WikiPali 上有没有未关闭的 issue。

- **审稿报告**（`review` 写的 markdown，默认在 `./reviews/`）：按「句 id ＋ 片段」定位到句子；
  「跨段一致性」一节也要落实——那是逐段看不见、只有 chunk 视野才有的发现。
- **WikiPali 上的 issue**：
  ```bash
  wikipali discuss-range <坐标> --chapter --channel <译文> --type issue --status active
  wikipali discuss-range <坐标> --to <段> --channel <译文> --type issue --severity error
  ```

按 `error` → `warning` → `suggestion` 处理。用户直接点名要改的句子，也并入同一张清单。

### 2. 逐条核对

```bash
wikipali get <book>:<para> --channel <译文> --json     # 现有译文与句子 id
wikipali get <book>:<para> --json                      # 巴利原文
wikipali related <book>:<para>                         # 意见基于义注时
```

意见基于 nissaya 的，取 nissaya 核对（`wikipali versions` → `get --channel`）。

### 3. 写回

只把改过的句子做成底层 `write` 接受的 JSON：

```bash
wikipali write revised.json --channel <写入目标> --dry-run
wikipali write revised.json --channel <写入目标>
wikipali get <book>:<para> --channel <写入目标> --json   # 读回核对
```

channel 里没有历史版本，覆盖了就回不去；用户想留修改前的对照，写之前提醒他。

### 4. 回复与关闭 issue（意见来自 WikiPali 时）

```bash
wikipali discuss-reply <issue id> --content '已改为「……」。'
wikipali discuss-edit <issue id> --status close                # 用户同意关闭时
wikipali discuss-reply <issue id> --content '未改：……（理由）'   # 不同意的，留着不关
```

最后给用户一张总表：改了哪些、没改哪些及理由、哪些 issue 已关闭。
