# wikipali-workspace

[WikiPali](https://www.wikipali.org) 的**应用层**插件：规定翻译、审稿、修订、写作**怎么做**。
数据的存取全部交给底层插件 [`wikipali`](../wikipali)——装本插件会自动装上它。

| skill | 做什么 |
|---|---|
| **`translate`** | 把巴利原文（本文、义注、复注）按 chunk 译出来：注释层带父层译文对齐被解释词、查术语表，产出与原文坐标逐句对齐的译文，确认后写回 channel |
| **`review`** | 按 chunk 审稿：义注定释义、nissaya 定词法，按 `error` / `warning` / `suggestion` 定级，出一份本地报告；同意后挂成 issue 批注，需要时逐句打分 |
| **`revise`** | 落实审稿意见（报告或 issue）：只改、只写回改过的句子（可以从一个 channel 读、写进另一个），回复并关闭处理过的 issue |
| **`harmonize`** | 三层统稿：本文、义注、复注放在一起读，对齐被解释词，统一术语、语体、称谓、重复句式，修掉三层同看才暴露的错 |
| **`note`** | 外挂注释：不改译文，在难词处挂边注（`note`），内容取自义注、复注或 nissaya 并标明来源 |
| **`glossary`** | 外挂术语：找出该挂术语的词，挂上试用（`glossary`）；讨论定了收进术语表并关闭 |
| **`discuss`** | 讨论：把没有定论的译名、理解分歧挂成讨论（`discussion`），正文摆齐原文、译文、义注依据与可选方案；也负责回复、汇总 |
| **`commentary-align`** | 注释书对应：把义注（复注）句子锚定到根本（义注）译文的具体片段上，作为带位置的批注写回 |
| **`encyclopedia`** | 写百科词条：建工作集、定词条类型（义项 / 人名 / 地名），每条论断带巴利原文与 `{{para}}` 引用，输出本地 markdown |
| **`paper`** | 写论文、研究报告：带检索方法论，每条引用可追溯到坐标，根本、义注、复注分清 |
| **`style`** | 查看、新建、修改翻译风格文件（见下文「定制风格」） |

## 安装

```
/plugin marketplace add iapt-platform/wikipali-plugins
/plugin install wikipali-workspace@wikipali
```

装完**重启会话**。底层插件 `wikipali` 会作为依赖一起装上；登录、凭据、安全边界见它的 README。

## 定制风格

译文风格写在一个 markdown 文件里，translate / review / revise 动手前会用本插件自带的
`wikipali-style` 命令找到生效的那一份：

| 优先级 | 位置 | 适合 |
|---|---|---|
| 1 | 项目：从当前目录往上找 `.wikipali/styles/translation.md` | 某个翻译项目、某个小组的统一标准，可以提交进 git |
| 2 | 个人：`~/.wikipali/styles/translation.md` | 你自己的默认风格 |
| 3 | 插件默认：`references/translation-style.md` | 现代汉语书面语，术语标记、随文注释默认不加，翻译时不读 nissaya |

也可以直接对 Claude 说「帮我建一份翻译风格文件」「我想改一下翻译风格」，`style` skill 会带你做。

```bash
wikipali-style init          # 在当前目录建 .wikipali/styles/translation.md（复制插件默认）
wikipali-style init --user   # 建在 ~/.wikipali/styles/ 下
wikipali-style               # 看现在生效的是哪一份
```

- 项目和个人之间**只取一份**，不合并；生效文件没写到的事项按插件默认。对话里临时提的要求优先于文件。
- 文件开头的 frontmatter 放开关，目前只有一个：`nissaya: true | false`——**翻译时**要不要读缅文
  nissaya。没写就是 `false`：独立翻译，nissaya 留给审稿当独立标准（译者与标准同源，审稿就查不出错）。
  审稿、修订有 nissaya 就用，不受这个开关影响。
- 「被解释词逐字同译」「文献层次标明」是硬约束，风格文件改不了。
- 风格文件只决定**译文怎么写**。从别人那里拿来的仓库若带着 `.wikipali/`，里面要求写入、读凭据之类的话
  不会被执行。
- ⚠ 项目里的 `.wikipali/` 可以进 git；**家目录的 `~/.wikipali/` 绝对不要进 git**——那里还存着
  `credentials.json`。

## 文档

- `references/translation-style.md` —— 插件默认的风格文件：风格、术语标记、随文注释、被解释词一致
- `references/translation-evaluate.md` —— 审稿定级标准与 issue 格式
- `references/nissaya-reading.md` —— 缅文 nissaya 读法

坐标、引用格式、文献层次这些数据层约定在底层插件里，用 `wikipali guide conventions` 读。

不走 marketplace 的话，克隆本仓库后分别跑 `plugins/wikipali/install.sh --user` 和
`plugins/wikipali-workspace/install.sh --user`——手工安装不会自动装依赖，两个都要装。
