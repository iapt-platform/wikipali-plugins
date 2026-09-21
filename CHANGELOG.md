# 更新日志 / Changelog

本项目的重要变更都记录在这里。格式参照 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。最新版本在最前面。

## [0.14.0] - 2026-09-21

### 变更
- **注释书对应改用 `type=commentary`**（原来是 `type=note`）：`note-push` 写入的是 commentary，
  `discuss` / `discuss-add` 的 `--type` 也多了这一项。旧数据由 api-v13 的迁移改名
  （content 整体是句子模板的 `note` → `commentary`），其余 note 原样留着。

### 新增
- **`type=note` 是普通边注**：正文就是注解本身（不是句子模板），阅读页在锚点处渲染成一条
  **没有出处**的边注——与 commentary 的区别只在这一点。写法：
  `discuss-add … --type note --pos-end <位置> --quote-exact <摘录> --content <注解>`。

## [0.13.0] - 2026-09-19

### 新增
- **commentary-align skill**：注释书对应。给定 CST 书名 + 段号 + 译文 channel，对照巴利原文与译文，
  把义注（复注）句子锚定到根本（义注）译文的具体片段上，作为带位置的批注（`type=note`）写回 WikiPali。
  - 新命令 `wikipali note-context <book_name> <cs_para> --channel C`：取该 CS 锚点下根本 / 义注 / 复注
    各句的巴利原文与译文。
  - 新命令 `wikipali note-push <文件> --channel C`：读 JSONL（一行一条，坏行只丢一行），按摘录在译文
    原始 content 里数出字符位、补前后缀，校验句子真实存在、去重后写入。一个片段由多句解释时
    `note` 给数组，仍写成一条记录（content 并列 `{{…}}{{…}}`）。
- 批注锚点字段：`discuss-add` / `discuss-reply` 支持 `--pos-start --pos-end --quote-exact
  --quote-prefix --quote-suffix`；`discuss` 列表显示锚点，`--type note` 列注释书对应。
- 新命令 `wikipali discuss-edit <id>`（先取原记录再提交，未改字段原样保留）与 `discuss-delete <id>`。

### 修复
- 巴利原文 channel 不再写死线上 uid：开发机与自定义站点按名字 `_System_Pali_VRI_` 查本站 uid 并按站点缓存。
  之前在本地站点 `get` / `page` / `discuss` 取不到原文。

## [0.12.0] - 2026-09-19

### 新增
- **可追溯出处**：每条引用都带 citation（WikiPali 书名缩写 + 坐标 + 缅 / PTS / VRI / 泰印本页码）
  和 WikiPali 网页链接，两样缺一不可（规则见 `references/conventions.md`）。
  - `wikipali search` 每条结果新增「出处」「链接」两行，数据取自服务端的 `ref` / `link`。
  - 新命令 `wikipali ref <坐标…>`：任意坐标的出处与链接。
  - `wikipali get --ref`：取原文时一并给出每段的出处与链接。
- **citation skill**：把缅甸著作的引用缩写（如 `ဝိသုဒ္ဓိ၊၂၊၂၄၁`、`阿毗达摩义注 2,47`）解析为
  著作与 WikiPali 坐标。
  - 新命令 `wikipali page <册>.<页> --pcd <著作编号>`：印本页码 → 坐标，支持缅 / VRI / PTS / 泰四个版本
    与页码范围；`--text` 连整页巴利原文和章节路径一起取。
  - 参考表 `citation-abbrev.tsv`、`citation-books.tsv`、`citation-book-name.csv`。
- 英文版 README（`README.en.md`）。

### 变更
- mūla 的中文称谓由「本文」统一改为「根本」。
- README 按开源惯例重写。
