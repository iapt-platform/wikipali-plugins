# 更新日志 / Changelog

本项目的重要变更都记录在这里。格式参照 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。最新版本在最前面。

## [0.19.0] - 2026-10-21

### 新增
- **`--type glossary`（外挂术语）**：不改译文，给一段译文临时挂上术语，供讨论该词值不值得正式收进
  术语表；阅读页把那段文字显示成术语，关闭后不再显示。`--title` 必填且就是术语词头，必须给
  `--quote-exact`；只能挂在句子上，只有该句所在 channel 的编辑者能建。与术语表（`term-add`）是两回事：
  用户说「新建术语」仍走 `term-add`，说「给译文添加外挂术语」才用它。
- **issue 可带锚点**：给 `--quote-exact` 后阅读页把那段文字标成波浪下划线（颜色随 `--severity`），
  不给则在句尾显示三角图标。
- **锚点只给摘录即可**：`discuss-add` / `discuss-edit` 只要 `--quote-exact`，工具先取句子原文，
  算出 `pos_start` / `pos_end` 与前后缀，不必再自己数字符位；摘录不在句中、出现多次又没给前后缀、
  位置与摘录不符时报错。外挂术语的摘录与句中已有的术语 / 模板 / 格式重叠、或含 `[ ] { } | #` 时
  提前报错（服务端遇到这些会静默不显示）。

### 变更
- 锚点不再只限 note / commentary：note / commentary / issue / glossary 都收，discussion / qa / help 仍不收。
- `discuss-edit` 给了新的 `--quote-exact` 时按句子原文重新定位；确认回显显示合并后的完整锚点。
- 摘录定位函数从 `cmd_notes.py` 移到 `lib/anchors.py`，`note-push` 与 `discuss-*` 共用。
- 文档：write skill 的说法映射表加入 issue（带 / 不带位置）、外挂术语，并区分「外挂术语」与「术语」；
  `references/api-write.md` 与 `docs/wikipali-api-calls.md` 同步七类 type、锚点、阅读页注入与可见性
  （issue / glossary 对所有人可见，只有 discussion 不公开）。**需要服务端已部署 glossary 与 issue 锚点**，
  否则 `--type glossary` 与带锚点的 issue 会被 422。

## [0.18.0] - 2026-10-15

### 变更
- **批注（discuss / discuss-add / discuss-reply / discuss-edit / discuss-delete / note-push）改走 v3
  `/v3/discussions`**。写入要人类授权：工具用你的登录身份为模型签一张「channel + book」的写入授权
  （`POST /v3/agent-grants`，7 天，缓存在凭据文件的 `agent_grants` 里自动复用、被撤销时自动重签一次），
  写入带请求头 `X-Agent-Grant`。署名改为**你**（授权人），模型记为协作者，显示成「你（与 模型）」。
  读不需要授权。**需要服务端已部署 v3 discussions 与 agent-grants**，否则这些命令 404。
- discussion / qa / help / issue 类话题**必须给 `--title`**，且不收锚点；锚点只有 note / commentary 收。
- `discuss-edit` 只提交改了的字段（v3 局部更新），不再先取回整条再全量覆盖。
- `discuss-delete`：作者或该句所在 channel 的编辑者可删，软删除。
- client：`http_json` / `Client.call` 增加 `headers`（额外请求头）与 `envelope`（返回含 `meta` 的完整响应）；
  默认发 `Accept-Language: zh-Hans`，v3 的错误说明为中文。

### 新增
- `--type issue`（问题报告）。
- `--severity`：`issue` 可选 `error` / `warning` / `suggestion`，`help` 可选 `urgent` / `normal`，
  本地先校验与类型是否匹配；`discuss-edit` 也可改。

### 移除
- `discuss` 的 `--offset`（改用 `--page`，`--limit` 最多 200）。
- `discuss-add` / `discuss-reply` 的 `--content-type`（v3 只收 markdown）；`discuss-reply` 的锚点参数。

## [0.17.0] - 2026-09-28

### 新增
- **`related-books` 命令**：列出有 CST 锚点的书名（`book_name`），走 v3 的
  `tipitaka-related-paragraphs/aggregate`；可用 `--file`（文件号）或 `--book`（书号）
  反查某一本，两者互斥。端点每页只给 15 条、上限 200，命令内部自动翻页拉全。
- **`related-paras` 命令**：给定 `book_name` 列出其中全部 CST 段号（`cs_para`），走
  `…/aggregate/{book_name}`，同样自动翻页拉全；人读输出把连续段号压缩成区间，
  `--json` 输出扁平字符串数组。

## [0.16.0] - 2026-09-28

### 新增
- **`related-cs` 命令**：按 CST 书名 + 段号（`wikipali related-cs mn1 1`）直接查注释层
  段落列表，走 v3 的 `tipitaka-related-paragraphs`。与 `related`（`book:para`，走 v2）
  并存；输出按 根本 → 义注 → 复注 分层，每部书列出对应的 `book:para` 段落。

### 变更
- **client 支持 v3 响应信封**：`http_json` / `Client.call` 增加 `v3` 开关。v3 返回
  Laravel 原生 `{data, meta}`（没有 `ok` 字段），成败只看 HTTP 状态码；错误路径顺带
  兼容 v3 的 Problem 响应（取 `detail`），422 能直接显示具体原因。v2 行为不变。

## [0.15.0] - 2026-09-22

### 修复
- **巴利原文的黑体不再被丢掉**：`strip_markup` 原先只认 `<span class="bld">`，而语料里
  大量用 `<strong>`（中部义注、复注都是），黑体被静默吞掉——输出照样通顺，只是看不出
  少了东西。现在两种写法都转成 `**…**`，`note-context` / `get` / `chapter --text` /
  `page --text` 一起受益。黑体是注释书标出被解释词的唯一线索，丢了就只能靠 `ti` 猜，
  而那是错的（见下）。

### 变更
- **按 `content_type` 决定要不要转换正文**，不再按 channel 身份猜：新增
  `cmd_read.row_text(row)`，`markdown` 的 content（译文、批注）原样取，只有 `html` 的
  （巴利原文）才过 `strip_markup`。原来的写法等于假定「巴利一定是 html、译文一定是
  markdown」，而服务端每条记录都已经在 `content_type` 里明说了。
- **commentary-align 的切块规则改为只看黑体**，并**明确禁止用 `ti` / `nti` 找被解释词**：
  注释书大量用「……叫做 X」的定义式（`Abhūtapubbaṃ bhūtanti **abbhutaṃ** .`），那里
  `ti` 在释义那一侧、黑体在它后面，照 `ti` 判断会把释义当成被解释词、整段切反。
  规则简化成三条：一个黑体定一个锚点；黑体后面的非黑体句子与它同属一个意群、挂同一个
  锚点（不因为「这句没引词」就丢掉）；段落第一个黑体之前的引子，是本章第一个正文段就
  挂章节标题句（整句挂），否则不挂。除此之外下一层不许有遗漏。

### 新增
- **`note-push` 支持整句挂**：不给 `quote_exact` 就是挂在整句上（不发锚点字段，与
  `discuss-add` 一致），回显成「整句」。给上面规则 3 的段落引子用。
- **`note-push --dry-run` 核对覆盖率**：逐句列出下一层没有进任何一条对应的句子，并在
  汇总行报「下一层未覆盖 N 句」。只有段落引子允许留白，其余报未覆盖就是还没做完。

## [0.14.0] - 2026-09-21

### 变更
- **注释书对应改用 `type=commentary`**（原来是 `type=note`）：`note-push` 写入的是 commentary，
  `discuss` / `discuss-add` 的 `--type` 也多了这一项。旧数据由 api-v13 的迁移改名
  （content 整体是句子模板的 `note` → `commentary`），其余 note 原样留着。
- **`--title` 改为可选**（服务端也不再必填）：批注 / 脚注、注释对照这类正文即全部的不必给
  标题；`note-push` 不再拿句子模板顶一个标题，列表里没有标题就不显示这一行。

### 新增
- **`type=note` 是普通边注**：正文就是注解本身（不是句子模板），阅读页在锚点处渲染成一条
  **没有出处**的边注——与 commentary 的区别只在这一点。写法：
  `discuss-add … --type note --pos-end <位置> --quote-exact <摘录> --content <注解>`。
- **批注按用户的说法分五类**，`discuss` / `discuss-add` 的 `--type` 收全五个，`write` skill
  里给出对照表：批注 / 脚注→`note`，注释对照 / 义注对照 / 复注对照→`commentary`，
  审稿意见 / 讨论→`discussion`，问答→`qa`，求助→`help`。五类的**锚点都可以不给**
  （不给就是整句的批注）；只有 `note` 与 `commentary` 会被注入阅读页。

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
