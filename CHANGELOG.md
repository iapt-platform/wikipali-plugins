# 更新日志 / Changelog

本项目的重要变更都记录在这里。格式参照 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。最新版本在最前面。

## [0.29.0] - 2026-11-23

### 变更
- **检索改走 v3**，CLI 输出字段名不变：`forms` / `count` / `search --lemma` / `find` 的词形展开改走
  `GET /v3/pali-word-forms/{word}`；`search` / `find` / `dist` / `ref` 改走 `GET /v3/tipitaka-word-paragraphs`
  （及 `/aggregate`），`--tags` 先经 `/aggregate` 按书的 tag 筛 book_id，出处链接按坐标自己拼；`phrase` 与
  `find` 的多词一路适配 `/v3/search` 新响应 `{data, meta}`（`page_size` → `per_page`，≤100）；`locate` / `toc`
  改走 `/v3/tipitaka-titles`。
- **`get` 的 `--limit` 改名 `--page-size`**（默认 200）：它只是每页行数，不限制总量。旧名留作隐藏别名，
  用了会提示改名。
- API 调用清单补上 `v2/sentence` 的 `offset` 参数、`{count, rows}` 返回与翻页说明；`/v3/glossaries/community`
  不再返回 `id`（`terms` 本就不读）；research skill 同步。

### 修复
- **按段取句子不再静默截断**：`get` / `discuss` / `notes` / `page` 统一经 `fetch_sentences` 按服务端 `count`
  用 `offset` 翻页取全。以前只发一次请求（`get` 200 行、`page` 500、`notes` 1000、`discuss` 200），超出部分
  被丢掉、退出码仍是 0；长段落后半截的句子 `discuss` 找不到。中途某页失败或取到的行数少于 `count` 时整次报错，
  不给半截。

## [0.28.0] - 2026-11-18

### 新增
- **`term-add` / `term-edit`** 新增 `--summary`（摘要）、`--quality`（featured / standard / draft / pending）、
  `--content-type`（markdown-e2 / markdown）、`--redirect`（重定向到 `word` 或 `word@tag`）；`term-edit`
  给空串即清掉该字段。分类写在 `--note` 里的 `{{category|名}}`，由服务端抽取。
- `my-terms --studio` 可给 uuid、自己的用户名或所在团队的名字（经 `GET /v3/me/groups` 按名找团队）。

### 变更
- **用户术语表改走 v3**：`my-terms` → `GET /v3/studios/{studio}/terms`、`GET /v3/channels/{uid}/terms`；
  `term-add` → `POST /v3/channels/{uid}/terms`；`term-edit` → `PATCH /v3/terms/{guid}`。写入改用模型 token +
  人类签的 `X-Agent-Grant`（与批注同一条链路），记录上 editor 是授权人、co_editor 是模型；修改带 `If-Match`
  乐观锁，被别人改过时回 412 并提示重跑。
- **word + tag 建立后不能改**：`term-edit --word/--tag` 报错并提示新建 + `--redirect`；`--language` 不再提交，
  channel 里的术语语言跟随 channel。
- `terms` 改走 `GET /v3/glossaries/{community|grammar}`（取代 v2 `term-vocabulary`），`--view` 限定两种取值；
  服务端没有所要语言时提示实际返回的语言。
- `versions` 改走 `GET /v3/tipitaka-paragraph-channels/{book}/{para}`，登录后能看到有权限的私有 channel。
- 可写 channel 列表改走 `GET /v3/channels/editable`，channel 回显改走 `GET /v3/channels/{uid}`；
  非线上站点找巴利原文 channel 改走 `GET /v3/channels?system=true`。
- `chapter --fetch`（`v3/tipitaka-reading`）登录后带上用户 token，读私有 channel 被拒时给出登录提示。
- API 调用清单、API 参考、功能覆盖表、write skill 同步。

### 修复
- 去掉稳定版 `channel?view=paragraphs` 已知缺陷的切站提示（`versions` 已不再用它）。

## [0.27.0] - 2026-11-11

### 新增
- **`wikipali locate <章节名>`**：按章节名找坐标——经名、品名、偈名、律的章节名，或公开译本里的中文译名。
  不分变音符号，拼错一两个字母也能找到（标「≈拼写不同」）；同名的根本典、义注、复注一起列出，带段数、
  字符数与路径。走 `GET /v3/tipitaka-chapters`（mint 2026-11 起）。
- research skill「2b. 先判断问题类型，选第一条路」：回答具体问题有三条路——检索（`find`）、定位
  （`locate` → `toc` → `chapter`）、选章（`books` → `toc` → `chapter`），按问题类型决定先走哪条，没有答案
  再换下一条。依据：148 道真实问题，只用检索 40 题能作答，三条路依次走到有答案为止 90 题。

### 变更
- **`toc`** 改走 `GET /v3/tipitaka-chapters`：参数是书号或 `book:para`，每个标题带中文译名与字符数，
  可直接当选章清单；去掉 `--all`（整套丛书用 `books`）。
- **`chapter --fetch`** 默认改走 `GET /v3/tipitaka-reading/{channel}`：直接读库、翻页取全，`--channel`
  可给多个；原来的 OpenSearch 预建 HTML 改为 `--via tipitaka-content`（正文夹版本页码）。
- API 调用清单、API 参考、功能覆盖表同步。

### 修复
- 没有预建整章文档的章节（多见于小节）`chapter --fetch` 报「该版本在本章无文本」，现在默认路径不再依赖预建文档。

## [0.26.0] - 2026-11-11

### 新增
- **`wikipali find 词1 词2 …`**：回答具体问题的第一轮检索。逐词（`search-pali-wbw`，各词全部词形，
  命中过多时补一轮只看黑体）与多词合并（`/v3/search` fuzzy）两路一起搜，按名次融合（RRF，k=60）；
  前 3 段沿用逐词轮流排序，其余名额按融合结果补。每行标出命中来源。`--per` 每词取几段，`--ref` 补出处。
  合并检索失败时退回只用逐词结果。在 148 道问藏真实问题上，同样阅读量下命中的引用段落多约 10%，
  89% 的题更好或持平，前 3 段不变。

### 变更
- research skill 加「回答具体问题：先选词，再用 `find`」：选答案段落里会出现的词、引文用原文词形、
  列举类带成员、不用泛用词、没找到就换词再搜。
- `docs/wikipali-api-calls.md`、`api-read.md`、`wikipali-feature-coverage.md` 补 `find`。

## [0.25.0] - 2026-11-11

### 新增
- **`wikipali phrase 词1 词2 …`**：多词检索，走 `GET /v3/search`（OpenSearch）。给词根或任一词形即可，
  不用先跑 `forms`。默认 `definition` 模式黑体定义优先——每个词命中单独黑体字的段落排前，命中越多越前；
  `--mode fuzzy` 按词序与拼写一致程度排序，用来找某句话出现在哪。`--ref` 逐条补出处。
  需要服务端支持 `search_mode=definition`（mint 2026-11 起）；旧服务端会静默按模糊检索处理。

### 变更
- `docs/wikipali-api-calls.md` 加第 4b 节；`api-read.md` 加第 3b 节，删去「短语检索拆词绕行」的说明；
  research skill 加 `phrase` 用法，单词查全仍以 `search --lemma` 为准。

## [0.24.0] - 2026-11-09

### 新增
- **`wikipali versions <book>:<para> --chapter`**：按章查版本，列出这一章有哪些公开 channel 及各自的完成度
  （按完成度降序、按类型分组）。补上了 `versions` 只能按段落查、只能用章节起始段近似整章的缺口。
  走 `GET /v3/tipitaka-chapter-channels/{book}/{para}`；站点还没有这条路由时提示退回段落粒度。

### 变更
- `docs/wikipali-api-calls.md` 加第 51 节；功能覆盖清单、research skill、`api-read.md` 同步说明 `--chapter`。

## [0.23.1 / wikipali-workspace 0.2.0] - 2026-11-06

### 新增
- **wikipali-workspace：三个批注 skill**——`note`（外挂注释：不改译文，挂 `note` 边注，内容取自义注、复注、
  nissaya 并标明来源）、`glossary`（外挂术语：找出该挂术语的词并试用，讨论定了 `term-add` 收进术语表、关闭
  外挂术语）、`discuss`（讨论：把没有定论的译名、理解分歧挂成 `discussion`，正文摆齐原文、译文、依据与
  可选方案，也负责回复与汇总）。workspace 现在用到 note / commentary / discussion / issue / glossary /
  assessment 六种类型。
- **wikipali：批注类型说明**——插件 README 新增「批注类型」一节（8 种类型、怎么说、阅读页上的样子）；
  `references/api-write.md` §8 新增八种 type 的属性总表，注明对应 api-v13 `Discussion.php` 的常量。

### 变更
- **wikipali：外挂术语可以挂在粗体里面**。摘录完全落在 `**…**` 之内（不碰两头的 `**`）时不再拒绝，
  渲染成 `**[[词头#原文]]**`；跨出粗体边界或把 `**` 包进去的仍然拒绝。注释书里加粗的被解释词常就是术语。
  服务端排版目前仍可能把整个粗体当受保护区间，能否显示以阅读页为准。

## [0.23.0 / wikipali-workspace 0.1.0] - 2026-11-06

插件拆成两层：底层 `wikipali` 只管存取；新增应用层插件 `wikipali-workspace`，规定翻译、审稿、
修订、写作**怎么做**。

### ⚠ 迁移
- 翻译风格、术语标记、随文注释、审稿定级、nissaya 读法、`commentary-align` 都从 `wikipali` 移到了
  `wikipali-workspace`。**只装底层的用户不再有这些默认规则**，译文怎么写完全按对话里的要求。
  要原来的行为，再装一个：`/plugin install wikipali-workspace@wikipali`（会自动装上底层），然后重启会话。
- 调用名变了：`/wikipali:commentary-align` → `/wikipali-workspace:commentary-align`。

### 新增
- **`wikipali-workspace` 0.1.0**，八个 skill：`translate`（按 chunk 翻译，注释层带父层译文对齐被解释词）、
  `review`（义注定释义、nissaya 定词法，出本地报告，同意后挂 issue、打分）、`revise`（按报告或 issue
  修订，只写回改过的句子）、`harmonize`（本文 / 义注 / 复注三层统稿）、`encyclopedia`（百科词条）、
  `paper`（写论文）、`commentary-align`（迁入）、`style`（风格文件的查看、新建、修改）。
  translate / review / revise / harmonize / encyclopedia 的做法吸收自 pali-translab。
- **风格文件**：译文风格写在 markdown 文件里，按「项目 `.wikipali/styles/translation.md` → 个人
  `~/.wikipali/styles/translation.md` → 插件默认」查找，项目与个人只取一份，没写到的事项按插件默认。
  frontmatter 的 `nissaya` 开关只管翻译，默认 `false`（独立翻译，nissaya 留给审稿当独立标准）。
  应用层自带命令 `wikipali-style` 查找与 `wikipali-style init [--user]` 新建。
- **`wikipali guide [conventions|api-read|api-write]`**：打印底层的共享约定与端点参考，供上层插件读取
  （上层插件读不到底层的文件）。

### 变更
- `conventions.md` 只留数据层约定（坐标、引用、文献层次、译文来源、站点、凭据）；译文写法拆到应用层的
  `translation-style.md`，并补入文言禁例对照表。
- write skill 删去风格类铁律（原 10–13）；research skill 删去审稿定级与论文方法论，新增「整章、整本的
  跨层对应用 `cs_para`，不用 `related`」。
- `nissaya-reading.md` 补核心格助词速查表、`ဝါ=` 异释说明。
- 底层文档里原来叫「Workspace（需登录）」的部分改称 **Account**，Workspace 一名留给应用层插件。

## [0.22.0] - 2026-11-06

### 新增
- **管理统计（只读）**：`wikipali admin stats agent|reading`、`admin feedback`、`admin runs` / `admin run <run_id>`、
  `admin digest`，走 `/v3/admin/*`，仅 root / administrator 账号可用。
- **本机登记 endpoint**：`wikipali endpoint add <简称> <url> [--label 说明]` / `endpoint remove <简称>`。
  登记的地址只存在本机 `~/.wikipali/credentials.json` 的 `custom_sites` 里，不进插件代码，一律按独立库处理
  （凭据与缓存单独一桶）。

### 变更
- **内置 endpoint 只留两个**：`www`（`https://www.wikipali.cc/api`，默认）与 `next`（`https://next.wikipali.cc/api`）。
  `www.wikipali.org`、`next.wikipali.org`、`staging`、`local` 从代码中删除。旧凭据自动迁移：记着 `.org` 的改成
  对应的 `.cc`，原 `local` / `staging` 桶转成同名的本机登记站点，已登录的 token 照旧可用；旧简称
  `www.cc` / `next.cc` 仍可用。
- **不再自动切换站点**：所有请求只发往当前设定的 endpoint，网络不通即报错退出（退出码 1）。
- **报错一律带 HTTP 状态码**：服务端错误统一显示为 `HTTP <码>：<服务端说明>`，包括 HTTP 200 + `ok:false`。

## [0.21.0] - 2026-10-23

### 新增
- **译文评估**：`discuss-add --type assessment --score <0–100 的整数> --method <评估方法>`，用某种方法给
  一句译文打分，理由写 `--content`（可省）。只有该句 channel 的编辑者（及其授权的模型）能写；
  **一句只留一条，再评估就覆盖**旧的分数、方法、标题与理由，工具会提示「已覆盖」。阅读页句尾显示对勾，
  按分数着色（≥80 绿、≥60 橙、其余红），同段未评估的句子显示灰色对勾。需要服务端支持
  `/v3/discussions` 的 `assessment` 类型。
- `discuss-edit <id> --score / --method` 改分数与方法；`discuss` / `discuss-range` 列表显示分数，
  `discuss-range --type assessment --severity <方法>` 按方法筛选。

## [0.20.0] - 2026-10-22

### 新增
- **译文评价标准**（`references/translation-evaluate.md`）：问题分三级，对应 issue 的 `--severity`——
  `error`（严重错误：严重失真、教理违背；一般错误：漏译、多译、词义误译、修饰错误、误解表达、
  义理不符、用词不符、指代错误）、`warning`（待提升）、`suggestion`（可提升）。审稿 issue 的格式固定：
  标题 `[类别] 简要描述`，正文四项「原文 / 译文 / 理由 / 建议修改为」，正文不用反引号、引文用斜体。
- **用 nissaya 审稿**：按 nissaya 对照结果定级——词义用法不符为 `error`，明显歧义为 `warning`，
  nissaya 补词、指代、解释性内容为 `suggestion`（可建议加脚注）；漏译一律以巴利原文为准。
- **缅文 nissaya 读法**（`references/nissaya-reading.md`）：语序重排、语尾即语法分析（格位 / 时态 /
  敬语对照表）、`iti` 的讲法交代说话人、补出的巴利与缅文、`ပ` 等省略记号与末音节缩写、
  夹注的义注 / 复注层次、巴利拼写不可靠、权威排序。依《优波离经》前 200 句抽样核对。

### 变更
- research skill：校对、审稿、评估时按评价标准定级；交叉验证一步读 nissaya 前先看读法文档。
  前后风格不一致由「就是错」改为 `suggestion`「风格统一」，被解释词不一致仍为 `error`「用词不符」。
- write skill：`--severity` 说明指向评价标准与 issue 格式。

## [0.19.1] - 2026-10-22

### 新增
- **站点 `staging.cc`**（`https://staging.wikipali.cc/api`）：与 `staging` 是同一个库，共用一桶凭据与缓存，
  可用 `wikipali endpoint staging.cc` 切换。`local` 的序号随之由 6 变为 7（简称 `local` 不变）。

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
- **`discuss-range`**：一次列出一章（`--chapter`）、一段段落区间（`--to`）、一本书（`--book`）或整个
  channel 里挂在句子上的讨论，按经文顺序、每条带句子坐标与 id；`--type` / `--severity` 可逗号多选，
  `--status` 过滤，`--all` 自动翻页，`--json` 输出原始数据。走 `GET /v3/tipitaka-discussions/{channel}`，
  **需要服务端已部署该端点**，否则 404。

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
