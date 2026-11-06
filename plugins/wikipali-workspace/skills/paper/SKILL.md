---
name: paper
description: "Use this skill to write a paper, research report or other formal scholarly writing grounded in Pali sources from the WikiPali corpus — with a stated search methodology, every claim traceable to a coordinate, and mūla / aṭṭhakathā / ṭīkā clearly distinguished. Trigger when the user explicitly asks for a 论文 / 研究报告 / 学术文章 / 要发表 / 要引用 / paper / research report on a Pali term or topic. Do not use for quick look-ups or short summaries (that is the wikipali research skill, which this skill uses for retrieval)."
---

# 写论文

把 WikiPali 语料里的材料写成论文或研究报告。**检索与取证照底层插件 `wikipali` 的
`research` skill 走**（`/wikipali:research`），本 skill 只规定论文比一般回答多出的要求。

- `command -v wikipali` 为空：底层插件没装、没启用，或刚装完还没重启会话。请用户
  `/plugin install wikipali@wikipali` 后重启会话。
- 坐标、引用格式、文献层次、译文来源判定：`wikipali guide conventions`，必须遵守。

## 铁律

1. **research 的铁律全部适用**：每条引用带得回坐标，交付时配 citation＋WikiPali 链接；
   检索前展开词形；0 条如实报告；根本、义注、复注不混；判断依据是巴利原文。
2. **必须写方法论。** 方法论不是修辞，是读者判断你的检索是否穷尽的唯一依据。至少交代：
   展开了哪些词形（连同频次）、检索范围、总命中词次与段落数、实读段数、黑体与非黑体分布。
   例：「检索 parivāsa 的 13 个词形，得 281 段（449 词次），分布于 43 部书，其中律藏根本
   159 词次、义注 28、复注 102」。
3. **`dist` 数词次，`search` 数段落**，方法论里两个数不能写混。
4. **二手研究标明作者。** `wikipali articles` 查到的文章，引它的观点要写明是谁说的，
   不能当成经律本身的说法。
5. **频次只报数字，不下判断。** 高频可能只是某部注疏反复提及，重要与否由研究者判断。
6. **各家说法不一致就如实写出不一致**，不要挑一家当「标准」——这往往正是论文值得写的一笔。

## 流程

1. **先看有没有人写过**：`wikipali articles <关键词>`、`wikipali anthology`。
2. **定范围**：`forms` → `dist`，看命中集中在哪一层、哪部书，据此搭论文结构——
   根本命中少而义注多，就是注释书概念，结构要相应调整。
3. **定义部分**取自注疏（`search --lemma … --limit 50`，黑体加权排在前面）；注疏枚举了
   子类的，每个子类单独查，不凭构词法推测含义。
4. **案例部分**回到根本（用 `dist` 给的根本书 `--book` 收窄）。
5. **注释**用 `related` 从根本跳到义注、复注，不在注释书里搜关键词充数。
6. **边取边记**：每批材料归纳出结论并记下坐标，再取下一批；方法论要用的数字同步记下。
7. **成文**：方法论 → 定义 → 分类（若注疏有）→ 案例 → 讨论；每条引用照抄 `search`
   的「出处」行或 `wikipali ref` 的输出。
8. **交付前核对**：正文每条引用都有坐标和出处；用到的译文已判定人译 / 机译并标注。
