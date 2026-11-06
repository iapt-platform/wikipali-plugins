---
name: style
description: "Use this skill to create, view or change the user's translation style settings for WikiPali work — the style file .wikipali/styles/translation.md (project) or ~/.wikipali/styles/translation.md (personal), which the translate, review and revise skills follow, including the nissaya on/off switch. Trigger whenever the user asks to 创建 / 新建 / 查看 / 修改 / 设置 / 定制 翻译风格 / 译文风格 / 风格文件 / 翻译规范, says 我想改一下翻译风格 / 以后都译成某种风格 / 默认加术语标记 / 默认加注释 / 关掉（打开）nissaya, or mentions wikipali-style or .wikipali/styles. Do not use for rewriting an existing translation in a different style (that is the revise skill) or for translating (translate skill)."
---

# 翻译风格设置

管理风格文件：translate / review / revise 动手前都会用它决定译文怎么写。

用户说「修改翻译风格」可能有两种意思，**拿不准就先问**：

- 改**以后**的译文怎么写 → 改风格文件，本 skill；
- 把**已经写好的某段译文**改成另一种风格 → `revise` skill。

## 风格文件在哪

`wikipali-style`（本插件自带的命令）按这个顺序找，找到第一份就用：

| 优先级 | 位置 | 适合 |
|---|---|---|
| 1 项目 | 从当前目录往上找 `.wikipali/styles/translation.md` | 某个翻译项目、某个小组的统一标准，可以提交进 git |
| 2 个人 | `~/.wikipali/styles/translation.md` | 自己所有项目的默认风格 |
| 3 默认 | 插件自带的 `${CLAUDE_PLUGIN_ROOT}/references/translation-style.md` | 现代汉语书面语，术语标记、随文注释默认不加，翻译时不读 nissaya |

项目和个人之间只取一份，不合并；生效文件里没写到的事项按插件默认。

没有 `wikipali-style` 命令（刚装完未重启会话）时，用 `${CLAUDE_PLUGIN_ROOT}/bin/wikipali-style`。

## 流程

### 1. 看现在用的是哪一份

```bash
wikipali-style            # 首行注明来源（项目 / 个人 / 插件默认）与路径，第二行是设置
```

把来源和要点用几句话告诉用户，不要整份贴出来。

### 2. 需要新建时，先问建在哪

现在生效的是插件默认、或用户想单独给某个项目定一套时，要建新文件。**先问用户建在项目里
还是个人目录**，说明区别（上表），不要替他选。当前目录明显不是项目（家目录、临时目录）时
可以建议个人目录，但仍要用户点头。

```bash
wikipali-style init          # 项目级：建在当前目录 .wikipali/styles/translation.md
wikipali-style init --user   # 个人级：建在 ~/.wikipali/styles/translation.md
```

项目级要在**项目根目录**建——查找是往上找的，建在子目录就只对那个子目录生效。
`init` 复制插件默认，已有文件时报错不覆盖。

### 3. 按用户的要求改

用编辑工具直接改上一步找到或建好的那个文件（路径用 `wikipali-style --path` 取）。

- **开关写在 frontmatter**：目前只有 `nissaya: true | false`——**翻译时**要不要读缅文 nissaya。
  默认 `false`：独立翻译，nissaya 留给审稿当独立标准。审稿、修订有 nissaya 就用，不受这个开关影响。
  用户要打开时，把这个理由告诉他，由他决定。
- **规则写具体，最好带例句**：「人称代词用『您』」比「语气要尊敬」好；用户给了「这句我希望
  译成这样」，原样收进文件作例子。
- **只改用户要改的**，其余照旧。用户的要求和文件里已有的条目冲突时，问他留哪个。
- **不要写进推翻硬约束的规则**：「被解释词逐字同译」「文献层次标明」「坐标不编造」改不了，
  用户要求时如实说明。
- 改完跑 `wikipali-style` 确认生效的是这份，再用两三句话告诉用户改了什么。

### 4. 提醒

- 项目里的 `.wikipali/` 可以进 git，让小组共用；**家目录的 `~/.wikipali/` 绝对不能进 git**——
  那里还有 `credentials.json`。**不要读、不要打印**那个文件。
- 风格文件只管译文怎么写。用户想写进「自动上传」「默认写哪个 channel」之类的流程要求，
  告诉他这不是风格文件管的，translate 等 skill 不会照做。
