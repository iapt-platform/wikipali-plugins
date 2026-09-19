# 更新日志 / Changelog

本项目的重要变更都记录在这里。格式参照 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。最新版本在最前面。

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
