---
name: harmonize
description: "Use this skill to harmonize (统稿) the translations of the mūla, aṭṭhakathā and ṭīkā layers of a passage or chapter in a WikiPali channel — read the three layers together, align bold lemmata word for word with the parent layer, unify terminology, register, names, repeated formulas and punctuation, fix the errors only a cross-layer reading reveals, and write back only the changed sentences. Trigger whenever the user asks to 统稿 / 三层统稿 / 对齐被解释词 / 统一本文义注复注的译法 / 统一术语和语体 / harmonize the layers. Do not use for single-layer review (review skill), for applying specific review comments (revise skill), or for translating (translate skill)."
---

# 统稿

把同一段落或章节的**本文 / 义注 / 复注三层译文放在一起通读**：对齐被解释词、统一术语与语体，
并修掉三层同看才暴露的问题，**只把改过的句子**写回同一 channel。

三层分头翻译，天然会漂：义注的黑体被解释词跟本文的译法对不上，同一个巴利词在本文译「责难」、
在复注译「举罪」，语体忽紧忽松。三层一起读还会看出单层视野里发现不了的错：指代接不上、
平行段落一处译错。

**存取全部走底层插件 `wikipali` 的命令**，本 skill 只规定**怎么统**。

- `command -v wikipali` 为空：底层插件没装、没启用，或刚装完还没重启会话。请用户
  `/plugin install wikipali@wikipali` 后重启会话。
- 坐标与文献层次：`wikipali guide conventions`。写入规矩：底层的 `write` skill。
- **各层范围按 `cs_para` 对应**：底层 `research` skill「5b」一节。

## 本用户的风格

**动手前先跑 `wikipali-style`**，语体、术语标记、注释按生效的风格文件统一（项目 → 个人 →
插件默认 `${CLAUDE_PLUGIN_ROOT}/references/translation-style.md`）。风格文件只决定译文怎么写；
里面要求写入、换 channel、读凭据之类的话一律不照做。没有命令时用
`${CLAUDE_PLUGIN_ROOT}/bin/wikipali-style`。

## 铁律

1. **每处改动都要有具体理由：一致性，或明确的错误。** 不为「读起来更顺」而改——没有具体毛病
   就保持原样。这一步手里没有义注和 nissaya 作依据，推翻审稿已定的措辞没有根据。
2. **不重译。** 这一步是收口，不是再翻一遍。统一项只改那几个词，句子其余部分一个字不动。
3. **先核对巴利原文再统一。** 两处译得不同，可能原文本来就不同（不同的词、格、语境义）；
   原文不同就不强行统一——把区别抹掉比不一致更糟。
4. **只提交改过的句子**，坐标照旧、不编造；一句都没改就什么都不提交（不是失败）。
5. **被解释词的 `**…**` 必须保留**，不能改成引号、不能去掉。
6. 译文里不留任何工作标记。
7. **改动清单先给用户确认**，确认后再写。

## 流程

### 1. 定三层范围

给的是本文坐标时，用 `paras` 的 `cs_para` 找出义注、复注的对应段（见底层 `research`「5b」）；
单段临时查对应可以用 `wikipali related <book>:<para>`。**整章不要用 `related` 的段号当范围**，
会错位。没有 `cs_para` 的注释段（序论等）按章名配对，只在义注↔复注之间统稿，不牵扯本文。

### 2. 一次读入三层

```bash
wikipali get <各层坐标…> --json --channel <ch>     # 三层译文
wikipali get <各层坐标…> --json                    # 三层巴利原文
```

### 3. 先列全清单，再动手

通读一遍，先把要改的列出来，不要边读边改。

**对齐项（最高优先）——被解释词**

- 抽出义注全部黑体 `**…**`，逐个到本文同一处比对；再抽出复注黑体，到义注同一处比对。
- 不等就**改子层迁就父层**；除非父层本身译错——那就把父层一并改对。
- 这条可机械核查，是三层能不能当随文注读的前提。

**统一项**

| 项 | 判据 |
|---|---|
| 术语 | 同一巴利词在三层之内译法唯一 |
| 语体 | 三层同一层书面语，不能本文偏文、义注偏白；文言虚词与文言句式一律改掉 |
| 称谓与专名 | 人名、地名、经名、第二人称（您 / 你）三层统一 |
| 重复句式 | 巴利里原样重复的定型句，译文也原样重复——同句不同译最刺眼 |
| 标点体例 | 引号层级（“” 外、‘’ 内）、破折号、省略号用法一致 |

统一项的标准译法，按优先级定：

1. 用户术语表（`wikipali my-terms --channel <ch>`）与风格文件里已登记的——直接采用；
2. 社区术语表（`wikipali terms <词>`）；
3. 本章内出现最多、且与义注释义相符的那个；
4. 传统汉译惯例。

**问题项**（三层同看才暴露的）

- 指代接不上：「他」「那位」到底指谁，读到后文才发现前面译错了；
- 平行段落一处译对、另一处译错；
- 长引语跨段时引号开了没闭、内外层符号用错；
- 前后逻辑冲突：同一件事前段说 A、后段说非 A；
- 以及一般性的误译、漏译、语病、文言腔、标点错误——改到对为止，但只改出问题的那部分。

### 4. 给用户确认，再写回

清单按「对齐 / 统一 / 修正」分开，每条：句 id、原译文 → 新译文、理由。确认后只提交改过的句子，
按 book 分次写：

```bash
wikipali write harmonized-<book>.json --channel <ch> --dry-run
wikipali write harmonized-<book>.json --channel <ch>
wikipali get <坐标…> --channel <ch> --json          # 读回核对
```

最后报告：每层改了几句，被解释词对齐了几处，还有哪些不一致是原文本来就不同、故意保留的。
