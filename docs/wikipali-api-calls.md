# WikiPali API 调用清单

本文汇总 `wikipali-plugins`（`plugins/wikipali`）实际调用的全部 WikiPali HTTP 接口，
用于快速检索「某个能力对应哪个接口、入参是什么、返回什么」。

应用层插件 `plugins/wikipali-workspace` **不直接调用任何接口**，一律经由底层的 `wikipali` 命令，
所以本清单只覆盖底层。`wikipali guide` 只打印插件自带的文档，也不发请求。

基址记为 `{API}`，`lib/sites.py` 只内置两个地址：

| 简称 | 地址 | 版本 | 数据 |
|---|---|---|---|
| `www` | `https://www.wikipali.cc/api` | 稳定版 | 线上共享库 |
| `next` | `https://next.wikipali.cc/api` | 最新版 | 线上共享库 |

其他地址（开发机、预发布等）不写进插件代码：用 `wikipali endpoint add <简称> <url>` 登记，
只保存在本机 `~/.wikipali/credentials.json` 的 `custom_sites` 里，一律按独立库处理。

**响应约定**

- **v2**：统一 `{ "ok": true, "data": <任意>, "message": "" }`。`ok: false` 时 `message`
  是原因；`client.py` 只把 `data` 透出，`ok: false` 会抛 `ApiError`。
- **v3**（`/v3/*`）：成功直接 `{ data: … }`（列表另带 `meta` 分页）；失败是 Problem
  Details `{ type, title, status, detail }`，**成败只看 HTTP 状态码**。
- 读侧（检索/阅读）**全部不需要凭据**；写侧区分三种 token（见文末「三种 token」）。

---

## 接口总表

| 类别 | API（方法 + 路径） | 一句话说明 |
|---|---|---|
| 读 | `GET {API}/v3/pali-word-forms/{词}` | 输入变格形/词根，返回候选词根及全部词形，是一切检索的前置 |
| 读 | `GET {API}/v2/dict` | 查词典释义与形态分析（形→根），用于确认选对了词根 |
| 读 | `GET {API}/v3/tipitaka-word-paragraphs` | 按词形列表检索命中的段落，带页码出处与黑体高亮 |
| 读 | `GET {API}/v3/tipitaka-word-paragraphs/aggregate` | 统计词形在各部书里的分布（段落数与词次分开给） |
| 读 | `GET {API}/v3/search` | 多词检索（OpenSearch）：几个词一起搜，黑体定义优先，不用先展开词形 |
| 读 | `GET {API}/v2/sentence` | 按坐标取原文/译文句子（view=paragraph / chapter） |
| 读 | `GET {API}/v2/sentence/{uid}` | 取单句，拿到它所属的 channel 与 book、原始 content |
| 读 | `GET {API}/v2/palitext` | 目录类查询（view=paragraphs-info 旧段落清单回退） |
| 读 | `GET {API}/v3/tipitaka-titles` | 章节标题：按名字找章节（容错、可用中文译名，`locate`），或列出一本书的全部标题（`toc`） |
| 读 | `GET {API}/v2/para-info` | 取某章辖区的段落清单（每段是标题还是正文、多长） |
| 读 | `GET {API}/v2/palitext/{book}-{para}` | 段落/章节元信息（chapter_len / strlen / pcd_book_id / path） |
| 读 | `GET {API}/v2/chapter-content/{book}-{para}` | 整章内容（嵌套 JSON，逐句带 origin/translation） |
| 读 | `GET {API}/v3/tipitaka-reading/{channel}` | 整章内容（直接读库，`chapter --fetch` 默认；按游标翻页取全） |
| 读 | `GET {API}/v2/tipitaka-content/{book}-{para}` | 整章内容（OpenSearch 预建 HTML，正文夹版本页码；`--via tipitaka-content`） |
| 读 | `GET {API}/v3/tipitaka-paragraph-channels/{book}/{para}` | 某段有内容的 channel（`versions`） |
| 读 | `GET {API}/v3/channels?system=true` | 系统 channel（非线上站点按名字找巴利原文 uid） |
| 读 | `GET {API}/v3/glossaries/{kind}` | 社区权威译名 / 语法术语对照表（整表拉取，本地过滤） |
| 读 | `GET {API}/v2/nav-page/{版本}-{pcd}-{册}-{页}` | 印本页码 → WikiPali 坐标 |
| 读 | `GET {API}/v2/related-paragraph` | 根本/义注/复注段落对应（v2，按 book:para） |
| 读 | `GET {API}/v2/article` | 文章列表 |
| 读 | `GET {API}/v2/article/{uid}` | 文章详情 |
| 读 | `GET {API}/v2/anthology` | 文集列表 |
| 读 | `GET {API}/v2/anthology/{uid}` | 文集详情（含文章列表） |
| 读 | `GET {API}/v2/book-title` | 书目清单（按 tag 找书，含 toc/tags/related_name） |
| 读 | `GET {API}/v3/tipitaka-related-paragraphs` | CST 锚点（书名+段号）→ 各层对照段落（v3） |
| 读 | `GET {API}/v3/tipitaka-related-paragraphs/aggregate` | 列出有 CST 锚点的 book_name（可反查 file/book） |
| 读 | `GET {API}/v3/tipitaka-related-paragraphs/aggregate/{book_name}` | 列出某 book_name 下的全部 CST 段号 |
| 读 | `GET {API}/v3/tipitaka-chapter-channels/{book}/{para}` | 一章有哪些公开 channel 及各自完成度（`versions --chapter`） |
| 认证/模型 | `POST {API}/v2/sign-in` | 用户名+密码登录，返回 JWT 字符串 |
| 认证/模型 | `GET {API}/v2/auth/current` | 取当前登录用户信息（realName 即 studio_name） |
| 认证/模型 | `GET {API}/v2/ai-model` | 查 AI 模型记录列表 |
| 认证/模型 | `POST {API}/v2/ai-model` | 新建 AI 模型记录 |
| 认证/模型 | `PUT {API}/v2/ai-model/{uid}` | 增量修改 AI 模型记录 |
| 认证/模型 | `GET {API}/v2/ai-model-token/{uid}` | 取模型身份 token（写句子的 Authorization） |
| 认证/模型 | `DELETE {API}/v2/ai-model-token/{uid}` | 撤销模型已签出的全部 token |
| 认证/模型 | `GET {API}/v3/channels/editable` | 列出当前账号可写内容的 channel |
| 认证/模型 | `GET {API}/v3/channels/{uid}` | 回显单个 channel 的名字 |
| 认证/模型 | `POST {API}/v2/access-token` | 为 channel 签发 access token（写句子的 body 字段） |
| 写 | `POST {API}/v2/sentence` | 按坐标写/覆盖译文句子 |
| 术语(v3) | `GET {API}/v3/studios/{studio}/terms` | 列某 studio 名下的术语（缺省是当前账号本人） |
| 术语(v3) | `GET {API}/v3/channels/{uid}/terms` | 列某 channel 的术语 |
| 术语(v3) | `GET {API}/v3/me/groups` | `--studio` 给团队名时按名字找团队 uuid |
| 术语(v3) | `GET {API}/v3/terms/{guid}` | 取单条术语（改之前读原值与 `etag`） |
| 术语(v3) | `POST {API}/v3/channels/{uid}/terms` | 新建术语（模型 + `X-Agent-Grant`） |
| 术语(v3) | `PATCH {API}/v3/terms/{guid}` | 增量修改术语（模型 + `X-Agent-Grant` + `If-Match`） |
| 批注(v3) | `POST {API}/v3/agent-grants` | 人类为模型签发「某 channel、某 book」写入授权 |
| 批注(v3) | `GET {API}/v3/discussions` | 列出某句上的话题/批注 |
| 批注(v3) | `GET {API}/v3/discussions/summary` | 某句上的批注统计 |
| 批注(v3) | `GET {API}/v3/discussions/{id}` | 取单条批注/话题 |
| 批注(v3) | `GET {API}/v3/discussions/{id}/replies` | 取某话题下的回复 |
| 批注(v3) | `POST {API}/v3/discussions` | 新建话题/批注 |
| 批注(v3) | `POST {API}/v3/discussions/{id}/replies` | 回复某话题 |
| 批注(v3) | `PATCH {API}/v3/discussions/{id}` | 局部修改批注/话题 |
| 批注(v3) | `DELETE {API}/v3/discussions/{id}` | 软删除批注/话题 |
| 批注(v3) | `GET {API}/v3/tipitaka-discussions/{channel}` | 列出一段经文（章 / 段落区间 / 书 / 整个 channel）里的话题/批注，带句子坐标 |
| 读 | `GET {API}/v3/credit-policy` | AI 对话积分策略（公开：每日赠送、提问价格、读经 / 编辑换积分） |
| 管理(v3) | `GET {API}/v3/admin/reading-stats` | 阅读统计汇总（活跃读者、时长、热门章节；仅管理员） |
| 管理(v3) | `GET {API}/v3/admin/agent-stats` | AI 问答统计汇总（提问、耗时、评价、工具；仅管理员） |
| 管理(v3) | `GET {API}/v3/admin/agent-runs` | AI 提问记录列表（仅管理员） |
| 管理(v3) | `GET {API}/v3/admin/agent-runs/{run}` | 一次提问的研究过程（步骤、证据、回答；仅管理员） |
| 管理(v3) | `GET {API}/v3/admin/agent-runs/digest` | 精简导出：同意用于改进的提问，不含身份，给 agent 分析（仅管理员） |
| 管理(v3) | `GET {API}/v3/admin/agent-feedback` | 用户评价列表（点赞点踩、原因、说明，带对应提问；仅管理员） |

---

# 一、读侧（无需凭据）

## 1. 词形展开 —— `GET {API}/v3/pali-word-forms/{词}`

输入任意变格形或词根，返回候选词根（取代 v2 `case/{词}`）。

- **入参**：路径参数 `{词}`（可含巴利变音符号，客户端已做百分号编码；不区分大小写；超过 64 字符 404）。
- **返回**：`data: [ { base, forms: [ {word, count, bold}, … ] } ]`，`meta: { total }`
  - `data[0]` 是输入的词本身，其后是推导出的词根；`forms` 是该词根在语料中实际出现过的全部词形，按次数降序。
  - 查无此词返回空数组（v2 会给一个 `case` 为空的候选行）。客户端仍过滤空组，避免空词形串发给检索。

## 2. 词典 —— `GET {API}/v2/dict`

查词典释义与形态分析，用来确认「选对了词根」。

- **入参**：`word`（词典形）、`lang`（释义语言，如 `zh` / `en` / `jp`）。
- **返回**：
  ```
  data.words[].words[] = {
    word, anchor, factors, parents,
    grammar: [ {word, type, grammar, parent, factors, confidence} ],   ← 形 → 根
    dict:    [ {shortname, dictname, lang, note, dict_id} ]            ← 释义在 note
  }
  ```
  - ⚠ 释义在 `note`；`description` 是词典介绍不是词条内容。`note` 里可能夹 `<MdTpl>`
    模板标记，需清掉。

## 3. 检索 —— `GET {API}/v3/tipitaka-word-paragraphs`

按词形列表检索命中的段落（多词形之间是 OR）。取代 v2 `search-pali-wbw`（2026-11-19）。

- **入参**：
  | 参数 | 说明 |
  |---|---|
  | `words` | 逗号分隔的**词形**列表（不是词根），最多 200 个，多个词形之间 OR；空词形 422 |
  | `bold` | `only` 只要黑体命中、`exclude` 只要非黑体；不给则不限 |
  | `book_id` | 限定书，逗号分隔，值用第 4 节返回的 `book_id` |
  | `page` / `per_page` | 分页，`per_page` 上限 100（`search --offset` 必须是 `--limit` 的整数倍） |
- **返回**：`{ data: [ {id, book, para, score, hits, title, level, path, text, refs} ], meta: {total, …} }`（`v3=True, envelope=True`）
  - `refs` 是各印本页码 `[{type, volume, page, title}]`，最后一条恒为 `WP`（`page` 就是段落号）；
  - `path` 是章节路径数组 `[{book, para, title, level}]`；`score = sum(weight)`；
  - `text` 是整段正文，只有 `<b>`（黑体）与 `<mark>`（命中词）两种标签，其余已转义；
  - 不带网页链接，CLI 用坐标拼旧版阅读地址（服务端永久 301）；
  - 没有 `tags` 参数：`search --tags` 先调第 4 节，按书的 tag 筛出 `book_id` 再检索（口径同 v2：组间 OR、组内 AND）；
  - CLI 的 `--json` 输出沿用旧字段名（`paragraph`、`paliTitle`、`rank`、`ref`、`link`、`highlight`）。

## 4. 出处分布 —— `GET {API}/v3/tipitaka-word-paragraphs/aggregate`

统计词形在各部书里的分布。取代 v2 `search-pali-wbw-books`。

- **入参**：`words`、`bold`（同检索），不分页。
- **返回**：`data[] = { book_id, book, para, title, layer, tags: [...], paragraphs, occurrences }`，
  `meta = { total, paragraphs, occurrences }`，按段落数降序。
  - `paragraphs` 是段落数，`occurrences` 是**词次**（v2 只有词次 `count`）；
  - `layer` 取自书的 tag（`mula` / `atthakatha` / `tika` / `anna`）；`dist --tags` 在 CLI 里按 `tags` 筛；
  - CLI 的 `--json` 输出沿用旧字段名（`pcdBookId`、`count`=词次、`paliTitle`、`tags[].name`），另加 `paragraphs`。

## 4b. 多词检索 —— `GET {API}/v3/search`

`phrase` 命令用。OpenSearch 索引，同义词词典的一行就是一个词的全部变格变位，所以给词根或
任一词形都能召回全部词形——**不用先跑 `forms`**。多个词之间不是 OR 词形列表，而是「几个不同的词」。

- **入参**（插件固定 `resource_type=tipitaka`、`granularity=paragraph`）：
  | 参数 | 说明 |
  |---|---|
  | `q` | 空格分隔的巴利词 |
  | `search_mode` | `definition`（默认）：每个词命中单独黑体 +100、多词黑体 +30，命中的单独黑体字越多越前，正文只作次级排序；`fuzzy`：整句原样 +20、相邻两词原样 +5、拼写相同 +10、同义词 +2，逐项累加 |
  | `page` / `per_page` | 分页，`per_page` 上限 100；`page × per_page` 超过 10000 → 422 |
- **返回**（2026-11-19 起为 v3 原生信封，不再是 OpenSearch 原始结果）：
  `{ data: [hit…], meta: {current_page, per_page, total, total_relation, last_page} }`
  - 每条 hit：`id`、`related_id`（`{book}-{paragraph}`）、`title`（段落标题）、`content`（正文）、
    `highlight`（命中片段，命中词包在 `<mark>`，没有则 null）、`bold`（该段的单独黑体字，数组）、`score`、
    `path`、`category`、`resource_type`、`granularity`、`language`；
  - `meta.total_relation=gte` 表示只统计到 10000，实际更多；
  - 插件读 `meta` 要用 `client.call(..., v3=True, envelope=True)`；
  - 参数非法（未知 `search_mode`、缺 `q`、`per_page` > 100）→ 422；搜索服务不可用 → 503。
  - ⚠ **不带 `ref` / `link` / `path`**：`phrase --ref` 逐条用 `lookup_ref` 补（见第 3 节）。
  - ⚠ 停用词（`na no ca va vā hi pana iva eva`）只参与词序打分，单独不召回。

### `find`：组合 3 与 4b，不新增接口

`find 词…` 对每个非停用词跑一次 `v3/pali-word-forms` + `v3/tipitaka-word-paragraphs`（`per_page=8`，命中超过 1000 再补一次
`bold=only`），再跑一次 `v3/search`（`search_mode=fuzzy`，取 `max(--limit, 30)`，上限 100），按名次做 Reciprocal Rank Fusion
（每个列表给 `1/(60+名次)` 相加）。排序的前 3 段沿用逐词结果轮流取的顺序，其余按 RRF。
`v3/search` 失败时只用逐词结果。请求数 ≈ 2×词数 + 1（命中过多的词再 +1）。

不放 `definition` 一路：在问藏真实问题的留出集（148 题）上，加了它窗口内命中反而少，定义类问题
也没有额外收益。

## 5. 取文 —— `GET {API}/v2/sentence`

按坐标取原文/译文句子。

- **入参**：
  - `view=paragraph`：`book`、`para`（逗号分隔多个段号）、`channels`（逗号分隔多个 uid）、`limit`。
  - `view=chapter`：`book`、`para`（章节段号）、`channels`。
  - ⚠ **`channels` 必填**，不带会 500。巴利原文 channel uid 默认
    `00b577c0-13b9-11ee-a05a-b7307efd9ee6`（`_System_Pali_VRI_`）。
- **返回**：每行是一句：`{id, content, content_type, html, book, paragraph, word_start, word_end, editor, channel, updated_at}`。
  - ⚠ 字段名是 `book`（不是 `book_id`）；按 `word_start` 排序拼接才是整段。
  - `id` 即 `sentences.uid`（挂批注用）。

## 6. 单句 —— `GET {API}/v2/sentence/{uid}`

取单句，拿到它所属的 channel 与 book，以及原始 content。

- **入参**：路径参数 `{uid}`（`v2/sentence` 返回的 `id`）。
- **返回**：`data: { …, content, content_type, channel: { id, … }, book }`——写批注前用
  `data.channel.id`、`data.book` 申请授权；`discuss-add` / `discuss-edit` 用 `data.content`
  按 `--quote-exact` 算锚点位置。

## 7. 目录 —— `GET {API}/v2/palitext`

只剩 `paras` 的旧段落清单回退在用（`view=paragraphs-info`，字段含 `lenght`/`length`）：行
`{book, paragraph, toc, level, length, chapter_len, book_name, cs_para}`，见 §8 的字段说明。
`toc` 原来走的 `view=book-toc` 已改用 §7b。

## 7b. 章节标题 —— `GET {API}/v3/tipitaka-titles`

取代 `v2/search-title-index`（只回标题文字、不带坐标）与 `toc` 原来用的 `v2/palitext?view=book-toc`。
mint 2026-11 起；旧站点 404，命令提示切 `next`。

- **入参**（都在查询串，`q` 与 `book` 至少给一个）：
  - `q`：章节名。巴利名不分大小写与变音符号、去序号与丛书缩写，可只写一部分，拼错一两个字母也能命中；
    也可用公开译本里的章节译名（如「大般涅槃经」）。
  - `book`：只在这本书里；不给 `q` 时 = 按经文顺序列出整本书的标题。`para`：只列 book 里这一章下面的（含它自己）。
  - `layer`：`mula` / `atthakatha` / `tika` / `anna`，逗号多选。`max_level`：层级不深于它（1 是书名）。
  - `page`、`per_page`（最大 1000）。
- **返回**：`{data: [...], meta}`，行 `{book, para, level, title, translations: [{lang, title}], layer,
  paragraphs, chars, parent, prev, next, path: [{book, para, title, level}], score?}`。
  `score` 只在给了 `q` 时有：相等 1、开头相同 0.95、包含 0.9、拼错的按相似度最高 0.85（≥0.86 = 拼对）。
  同一档里根本典在前。
- **谁在用**：
  - `locate <名称>`：`q` + 可选 `layer` / `book`，取前 `--limit` 条（1 次请求）。
  - `toc <书号>` / `toc <book:para>`：`book`（+`para`）+ `max_level=--depth`，按 1000 一页翻完（通常 1 次）；
    `para` 不是章节起始段时服务端返回空，命令再请求一次整本书。
- **TODO**：服务端的按名匹配目前写在 PHP 里，只用来验证效果；正式实现走 OpenSearch 后，`locate` 改调
  `GET {API}/v3/search`（`granularity=chapter`），输出不变（mint `api-v13/documents/search-recall.md` 4.6）。
  `toc` 继续用本端点按书列标题。

## 8. 段落清单 —— `GET {API}/v2/para-info`

取某章辖区的段落清单（哪些是标题、每段多长），一次调用不取正文。

- **入参**：`book`、`para`（章节起始段）。
- **返回**：`data.rows[] = { book, paragraph, toc, level, length, chapter_len, book_name, cs_para }`
  - `level < 8` 是标题（正文段一律 100）；`length` 是该段巴利原文字符数；
  - `chapter_len` 是该行辖区的段数（正文段为 1，判断「是不是章节」看 **> 1**）；
  - `book_name` / `cs_para` 只有新路由才有。旧站点回退到 `palitext?view=paragraphs-info`。

## 9. 段落与章节元信息 —— `GET {API}/v2/palitext/{book}-{para}`

⚠ 是 **path 参数**（`/palitext/216-481`），`data` 是**单个对象**。

- **入参**：路径 `{book}-{paragraph}`。
- **返回**：`data: { class, chapter_len, chapter_strlen, next_chapter, prev_chapter, parent, path, pcd_book_id, … }`
  - `class`：`chapter` / `subhead` / `bodytext` …；
  - `chapter_len` 章节段数、`chapter_strlen` 章节字符数（取整章前报体量）；
  - `path` 是面包屑，⚠ 这个端点返回的是 **JSON 字符串**（search 返回的是数组）；
  - `pcd_book_id` 等于 `tipitaka-word-paragraphs` 的 `book_id` 参数值。

## 10. 整章内容（JSON）—— `GET {API}/v2/chapter-content/{book}-{para}`

一次返回整章，带 `channels` 时把译文一并返回，服务端已按 wordStart/wordEnd 对齐。

- **入参**：路径 `{book}-{para}`；`channels`（逗号分隔多个 uid，可选）。
- **返回**：`data.content` 是**双重编码的 JSON 字符串**（`content_type: "json"`），二次解析后：
  ```
  [ {book, para, channels, sentences:[[…]], mode, children: [
      { id: "book-para-start-end", book, para, wordStart, wordEnd,
        origin:[…], translation:[…], commentaries:[…], tranNum, nissayaNum, commNum, originNum, simNum } ] } ]
  ```
  - 取值规则「**优先 content，为空回退 html**」：original 的 content 空（正文在 html），
    nissaya 的 content 是 markdown（巴利词=缅文释义）。
  - 请求的 channel 在本句无内容时，仍返回等量空占位条目，客户端须滤掉。

## 11. 整章内容（默认）—— `GET {API}/v3/tipitaka-reading/{channel}`

`chapter --fetch` 的默认取文路径，直接读库（不依赖 OpenSearch 预建文档）。

- **入参**：路径 `{channel}`（缺省巴利原文，按站点查 `_System_Pali_VRI_` 的 uid）；查询串 `book`、
  `chapter`（章节起始段，服务端按 chapter_len 展开）、`unit=para`、`page_size=200`、
  `format=text|html`（`--text` 用 text）、`include=sentences`、`after`（游标，取 `meta.next_cursor` 原样回传）。
- **返回**：`{data: [{book, para, sentences: [{sid, html}]}], meta: {next_cursor, total, remaining}}`；
  sid 即引用坐标。`next_cursor` 为 null 表示取完。
- **请求次数**：每个 channel `ceil(段数 / 200)` 次（一般 1 次）；`--channel` 可给多个，逐个取。
- **权限**（2026-11-16 起）：私有 channel 只有拥有者、团队成员、被共享的人能读，其余 403；公开与「公开不列出」
  不用登录。客户端登录了就带 Bearer = userToken，403 时提示先 `wikipali-login`。
- 指定的 channel 在本章没有句子时返回空列表，命令报「该版本在本章没有任何内容」，不拿别的版本顶替。
- 正文里**不夹版本页码**；要页码用 `--ref` / `wikipali ref`，或改用 §11b。

## 11b. 整章内容（预建 HTML）—— `GET {API}/v2/tipitaka-content/{book}-{para}`

`chapter --fetch --via tipitaka-content`。走 OpenSearch 预建文档，返回一整串渲染好的 HTML。

- **入参**：路径 `{book}-{para}`；`channel`（**单数**，一次一个；缺省巴利原文）。
- **返回**：一整串 HTML。每句包在 `data-sid='93-6-31-46'` 中，sid 即引用坐标
  `book-para-wordStart-wordEnd`。
  - 三种响应分开处理：正常（200 且含 `data-sid`）；有文档但没句子（200 但 sid 数为 0）；
    **无预建文档返回 400，message 里带 OpenSearch `found:false`**（不是服务故障，是这一章没建索引
    或该版本无文本）。
  - 正文夹 `<code>M1.1</code>` 是版本页码（M/V/P/T），须留在原位。

## 12. channel 列表（读侧）—— v3（2026-11-16 起，取代 v2 `channel?view=paragraphs|system`）

- **某段有哪些 channel** `GET {API}/v3/tipitaka-paragraph-channels/{book}/{para}`（`versions`）：
  query `per_page`（最大 200）；登录了就带 Bearer = userToken，能看到自己有权限的私有 channel，
  没登录只看公开的与系统 channel。
- **系统 channel** `GET {API}/v3/channels?system=true`（非线上站点按名字找巴利原文 uid）：
  query `search`、`per_page`。系统 channel 不论 status 都列（巴利原文是 status 10）。
- **返回**：v3 信封 `{ data: [ { id, name, type, lang, status, is_system, owner{kind,id,…}, abilities, … } ], meta }`。
  客户端把 `id` 映射成内部一直用的 `uid`。

## 13. 术语表（权威译名）—— `GET {API}/v3/glossaries/{kind}`

权威译名对照，只读、公开（取代 v2 `term-vocabulary`）。

- **入参**：路径 `{kind}` = `community`（社区译名，`terms` 默认）/ `grammar`（语法术语），对应命令的 `--view`；
  查询 `lang`（如 `zh-Hans`，缺省按 `Accept-Language`）。
- **返回**：`{ data: [ { id?, word, tag, meaning, other_meaning } ], meta: { kind, lang, total } }`，按词排序、整表不分页。
  - `id`（术语 guid）只有 `grammar` 表给，`community` 表不给（2026-11-20 起，省流量）。
  - `meta.lang` 是实际用到的语言：该语言没有这张表时回退到 `en`，命令会提示。
  - ⚠ 不支持按词查询，只能拉全表（zh-Hans 上万条），客户端缓存后本地过滤。
  - 与批注的 `glossary` 类型（外挂术语）不是一回事。

## 14. 版本页码 → 坐标 —— `GET {API}/v2/nav-page/{版本}-{pcd_book_id}-{册}-{页}`

按印本页码定位坐标，如 `nav-page/M-71-2-241`。

- **入参**：路径 `{版本}-{pcd}-{册}-{页}`；版本 `M`=缅甸版 / `V`=VRI / `P`=PTS / `T`=泰版。
  - 书用 **`pcd_book_id`**（不是 `book`），多个 pcd 用 `_` 分隔。
- **返回**：
  ```json
  {"curr":{"type":"M","volume":2,"page":241,"book":65,"paragraph":1461,"wid":6,"pcd_book_id":71},
   "prev":{"page":240,"paragraph":1450,…},"next":{"page":242,…}}
  ```
  - `curr` + `next` 即这一页的段落区间；`wid` 是页在段内的起始词；查无此页返回 404。

## 15. 关联段落（v2）—— `GET {API}/v2/related-paragraph`

根本 ↔ 义注 ↔ 复注的段落对应（按 book:para）。

- **入参**：`book`、`para`。
- **返回**：`data.rows[] = { book, book_title_pali, para: [段号…], tags: [{name}] }`。
  - 约 2% 的段落没有 CST 锚点（稳定版此时可能 500），如实报告「无」。

## 16. 文章列表 / 详情 —— `GET {API}/v2/article`、`GET {API}/v2/article/{uid}`

- **入参（列表）**：`view`、`limit`、`offset`、`search`（关键词）、`lang`。
- **返回（列表）**：`data: { rows: [ { uid, lang, title, subtitle, editor, updated_at } ], count }`。
- **返回（详情）**：`data: { uid, lang, title, subtitle, content, editor, studio, updated_at }`。

## 17. 文集列表 / 详情 —— `GET {API}/v2/anthology`、`GET {API}/v2/anthology/{uid}`

- **入参（列表）**：`view`、`limit`、`offset`。
- **返回（列表）**：`data.rows[] = { uid, lang, title, childrenNumber }`（含 `count`）。
- **返回（详情）**：`data: { title, lang, summary, article_list: [{uid, title}] }`。

## 18. 书目清单 —— `GET {API}/v2/book-title`

整表拉一次（约 281 条），本地缓存后按 tag 筛选。

- **入参**：无。
- **返回**：`data.rows[] = { book, paragraph, toc, tags: [tag…], related_name }`。
  - 旧站点无 `tags`/`toc` 字段，分类目录功能需切最新版。

## 19. CST 锚点关联段落（v3）—— `GET {API}/v3/tipitaka-related-paragraphs`

给 CST 书名 + 段号，一次回各层（根本/义注/复注）对照段落。

- **入参**：`book_name`（CST 书名）、`cs_para`（CST 段号）。
- **返回**：`data: [ { book, book_id, para: [段号…], tags: ["aṭṭhakathā"…], title } ]`。
  - v3 的 `tags` 是字符串数组（v2 是对象数组）。

## 20. CST 锚点索引（v3 aggregate）—— `GET {API}/v3/tipitaka-related-paragraphs/aggregate`、`…/aggregate/{book_name}`

- **入参**：`file`（可选，反查）、`book`（可选，反查）；分页 `page`、`per_page`（上限 200）。
- **返回**：
  - `aggregate`：`data: [ { book_name } ]`（另带 `meta.total`）；
  - `aggregate/{book_name}`：`data: [ { cs_para } ]`。

---

# 二、认证与模型管理

## 三种 token（职责不能混）

| Token | 来源 | 代表谁 | 用在哪 | 有效期 |
|---|---|---|---|---|
| userToken | `POST /v2/sign-in` | 人类操作者 | 查/建 ai-model、签 access token、列 channel | 365 天 |
| modelToken | `GET /v2/ai-model-token/{uid}` | AI 模型身份 | 写句子/术语/批注的 `Authorization` | 30 天 |
| accessToken | `POST /v2/access-token` | 被委托的 channel 编辑权 | 写句子时的 body 字段（术语、批注改用 v3 的 agent grant） | 7 天 |

## 21. 登录 —— `POST {API}/v2/sign-in`

- **入参**：body `{ "username": "<用户名或邮箱>", "password": "<明文>" }`。
- **返回**：`data` 是 **JWT 字符串本身**（不是对象）。
  - 失败 **HTTP 400**，`message` 是 `invalid token`（实际含义是用户名或密码不对）。

## 22. 当前用户 —— `GET {API}/v2/auth/current`

- **入参**：`Authorization: Bearer <userToken>`。
- **返回**：`data: { id, nickName, realName, avatar, token, roles }`。
  - ⚠ `realName` 就是后面 `studio_name` 参数要用的值。

## 23. 模型列表 —— `GET {API}/v2/ai-model`

- **入参**：`Authorization: Bearer <userToken>`；query `view`（`all`/`studio`/`usable`/`chat`，
  ⚠ 传别的值会 500）、`name`（studio 名）、`keyword`（模型名，`like %kw%` 模糊匹配）。
- **返回**：`data: { rows: [ … ], count }`；客户端自己做 `name` 精确比对。
  - `key` / `system_prompt` 只有 owner 本人可见。

## 24. 新建模型 —— `POST {API}/v2/ai-model`

- **入参**：`Authorization: Bearer <userToken>`；body
  `{ name, studio_name, model?, url?, key?, privacy?, description?, system_prompt? }`。
- **返回**：`data: { uid, name, … }`。
  - 同 studio 内重名 → **409**；`name`/`studio_name` 缺失 → 422；
    鉴权要求 `studio_name` 是操作者本人的 studio（group studio 一律 403）。

## 25. 修改模型 —— `PUT {API}/v2/ai-model/{uid}`

- **入参**：`Authorization: Bearer <userToken>`；body 只提交要改的字段（**增量更新**，
  未提交保持原值，显式传 `null` 才清空）。
- **返回**：`data: { uid, … }`；改名撞名 → 409。

## 26. 取模型身份 token —— `GET {API}/v2/ai-model-token/{uid}`

- **入参**：`Authorization: Bearer <userToken>`；路径 `{uid}`（模型 uid）。
- **返回**：`data: { uid, name, token }`；有效期 30 天，payload 带 `typ: "ai-model"`。
  - 仅 owner 可调：未登录 401、非 owner 403、不存在 404；较新端点，旧站点可能 404。

## 27. 撤销模型 token —— `DELETE {API}/v2/ai-model-token/{uid}`

- **入参**：`Authorization: Bearer <userToken>`；路径 `{uid}`。
- **返回**：`data: { uid, name, token_version }`；作废该模型已签出的**全部** token。

## 28. 可写 channel —— `GET {API}/v3/channels/editable`

取代 v2 `channel?view=user-edit`（v2 那条的搜索一直不生效：前端传 `key`、后端读 `search`）。

- **入参**：`Authorization: Bearer <userToken>`；query `order`/`dir`/`per_page`（最大 200）/`search`。
- **语义**：本人名下的 ∪ 本人是团队 editor 及以上的团队名下的 ∪ 共享权限 ≥20 的。
- **返回**：`{ data: [ { id, name, summary, type, lang, status, owner{kind,id,nickName,…}, abilities{read,write,update,delete}, … } ], meta }`。
  客户端把 `id` 映射成 `uid`，`role` 由 abilities 推出（能删 owner / 能改信息 manager / 能写 editor）。

## 29. 单 channel 回显 —— `GET {API}/v3/channels/{uid}`

- **入参**：`Authorization: Bearer <userToken>`；路径 `{uid}`。
- **返回**：`{ data: { id, name, … } }`（主要用于显示 channel 名字）；看不见的私有 channel 403。

## 30. 签发 channel access token —— `POST {API}/v2/access-token`

- **入参**：`Authorization: Bearer <userToken>`；body
  `{ "payload": [ { "res_type": "channel", "res_id": "<uid>", "power": "edit", "book": 0 } ] }`。
  - ⚠ `book` **必须是整数**（`0` 表示不限 book）；写成字符串会让服务端严格比较恒真而鉴权失败。
- **返回**：`data: { rows: [ { payload, token } ], count }`。
  - ⚠ 无权时该条被**静默跳过**，返回 `count: 0` 和空 rows（HTTP 仍 200）——等同 403，不可继续写。

---

# 三、写入（句子、术语）

## 31. 写句子 —— `POST {API}/v2/sentence`

- **入参**：`Authorization: Bearer <modelToken>`；body
  ```json
  { "sentences": [ {
      "book_id": 1, "paragraph": 10, "word_start": 0, "word_end": 12,
      "channel_uid": "<uid>", "content": "译文", "content_type": "markdown",
      "access_token": "<第 30 步签出的 JWT>" } ] }
  ```
- **返回**：`data: { rows: [ … ], count }`。
  - 语义：按 `(book_id, paragraph, word_start, word_end, channel_uid)` `firstOrNew`，
    **存在即覆盖、不存在则新建**（幂等但会静默覆盖，写前须确认）。
  - 返回 rows 用另一套字段名：`book`（不是 `book_id`）、`paragraph`、`word_start`、
    `word_end`、`channel.uid`、`editor`。
  - ⚠ 逐句鉴权失败会被**静默跳过**：提交 N 条、HTTP 200、`count` < N 即有句子没写进去，
    须逐条比对报差集。缺 `sentences` 字段时 HTTP 200 且 `message: "no date"`（客户端 bug）。

## 32. 列术语 —— `GET {API}/v3/studios/{studio}/terms`、`GET {API}/v3/channels/{uid}/terms`

- **入参**：`Authorization: Bearer <userToken>`（人类身份）。
  | 命令参数 | 接口 | 说明 |
  |---|---|---|
  | （缺省） | `GET /v3/studios/{当前账号 id}/terms` | 当前账号名下全部（它的 channel 里的 + studio 级的）；id 取自 `GET /v3/me` |
  | `--studio` | `GET /v3/studios/{uuid}/terms` | 给 uuid 直接用；给自己的用户名 → 本人；给团队名 → 经 `GET /v3/me/groups?search=` 找 uuid |
  | `--channel` | `GET /v3/channels/{uid}/terms` | 某 channel 的 |
  查询参数：`search`（词 / 释义包含匹配，不分大小写）、`order`（`updated_at`/`created_at`/`word`）、
  `dir`、`page`、`per_page`（≤200；命令行的 `--offset`/`--limit` 换算成它们）。
- **返回**：v3 列表 `{ data: [ … ], meta: { total, … } }`；行含 `id`（guid）/`word`/`tag`/`meaning`/
  `other_meaning`/`quality`/`categories`/`channel{id,name}`（studio 级为空）/`editor`/`co_editor`/`etag`。

## 33. 单条术语 —— `GET {API}/v3/terms/{guid}`

- **入参**：`Authorization: Bearer <userToken>`；路径 `{guid}`（uuid，不是雪花 id）。
- **返回**：`data: { id, word, tag, meaning, …, channel_id, channel, etag, body }`。改术语前用它读
  原值与 **`etag`**（乐观锁版本）。不存在 / 已删 404，所在 channel 看不见 403。

## 34. 新建术语 —— `POST {API}/v3/channels/{uid}/terms`

- **入参**：`Authorization: Bearer <modelToken>` + 请求头 `X-Agent-Grant: <授权>`（第 36 步，
  `book` 签 0——**按 book 限定的授权不覆盖术语**）；body
  ```json
  { "word": "satipaṭṭhāna", "meaning": "念处", "tag": "abhidhamma",
    "other_meaning": "念住", "note": "正文 {{category|分类}}", "summary": "摘要",
    "quality": "draft", "content_type": "markdown-e2", "redirect": "word@tag" }
  ```
  - `word` + `meaning` 必填；**`language` 不能给**（跟随 channel）；`content_type` 缺省 `markdown-e2`；
    `quality` 取 `featured`/`standard`/`draft`/`pending`；分类不是字段，服务端从 `note` 的
    `{{category|…}}` 抽出。AI 写术语**必须落在 channel 里**（studio 级术语模型 403）。
- **返回**：**201** `data: { id, word, …, editor（授权人）, co_editor（模型）, categories, etag }`。
  - 同 channel 下 `word + tag` 唯一，冲突 **409**（与句子「覆盖」相反）。
  - **`word` + `tag` 建立后不能改**，拼错只能新建一条再把旧的 `redirect` 过去。

## 35. 修改术语 —— `PATCH {API}/v3/terms/{guid}`

- **入参**：`Authorization: Bearer <modelToken>` + `X-Agent-Grant` + **`If-Match: <etag>`**（第 33 步读到的）；
  body 只提交要改的字段（`meaning`/`other_meaning`/`note`/`summary`/`quality`/`content_type`/`redirect`，
  给 `null` 清掉）。**`word`、`tag` 给了就 422**；channel 里的术语不能改 `language`。
- **返回**：`data: { …, editor, co_editor, etag }`（新的 etag）。
  - 不带 `If-Match` **428**；读取之后被别人改过 **412**——CLI 提示重新运行、不自动重试（会覆盖别人的修改）。

---

# 四、批注（discussion，v3）与授权

v3 约定：成功 `{data:…}`（列表带 `meta` 分页），失败 Problem Details，**成败只看状态码**；
请求带 `Accept-Language: zh-Hans` 时 `detail` 是中文。读（列表/单条/回复）只要模型 token，
**写要人类授权**（`Authorization: Bearer <modelToken>` + 请求头 `X-Agent-Grant: <授权 token>`）。

## 36. 签发写入授权 —— `POST {API}/v3/agent-grants`

- **入参**：`Authorization: Bearer <userToken>`（人类）；body
  `{ "ai_model": "<模型 uid>", "target_type": "channel", "target_id": "<channel uid>", "book": 1935 }`。
  - `book` 给 0 或不给表示不限 book；7 天有效。
- **返回**：201 `data: { token, grantor, ai_model, target_type, target_id, book, expires_at }`。
  - 服务端记 editor=授权人、co_editor=模型；模型不带授权写一律 403。

## 37. 列批注 —— `GET {API}/v3/discussions`

- **入参**：query `target_type`、`target_id`（必填，句子 uid）、`type`、`status`、
  `per_page`（≤200）、`page`。不带 `type` 只列话题（含 issue / glossary），批注与评估要显式
  `type=note`/`commentary`/`assessment`。
- **返回**：`data: [ { id, target_type, target_id, type, title, content, severity, score, status, editor, co_editor, reply_count, abilities, pos_start/pos_end/quote_exact/quote_prefix/quote_suffix, created_at, updated_at, … } ]` + `meta` 分页。
  `score` 只有 assessment 有值（0–100 的整数），其余为 null。

## 38. 批注统计 —— `GET {API}/v3/discussions/summary`

- **入参**：query `target_type`、`target_id`、`type`。
- **返回**：`data: { status_counts: { active, close }, creatable_types }`。

## 39. 单条批注 —— `GET {API}/v3/discussions/{id}`

- **入参**：路径 `{id}`。
- **返回**：`data: { … }` 单条完整记录。

## 40. 回复列表 —— `GET {API}/v3/discussions/{id}/replies`

- **入参**：路径 `{话题id}`；query `per_page`、`page`。
- **返回**：`data: [ … ]` 按时间正序。

## 41. 新建话题/批注 —— `POST {API}/v3/discussions`

- **入参**：body
  ```json
  { "target_type": "sentence", "target_id": "<句子 uid>", "type": "discussion",
    "title": "标题（话题必填，批注可省）", "content": "markdown 正文", "notify": false }
  ```
  - `type` 八类：`note`/`commentary`（批注，收锚点，注入阅读页）、`discussion`/`qa`/`help`
    （话题，**title 必填**，不收锚点）、`issue`（话题，title 必填，收锚点，注入阅读页高亮）、
    `glossary`（外挂术语：话题，**title 必填且为术语词头**，锚点服务端可省但没有就不显示（CLI 要求必须给，完全落在 `**…**` 内的摘录也放行），只能挂句子，
    注入阅读页显示成术语）、`assessment`（译文评估：**`score`（0–100 的整数）与 `severity`=评估方法必填**，
    title 可省、`content` 写理由，不收锚点，只能挂句子，只有该句 channel 的编辑者能建，
    注入阅读页在句尾显示按分数着色的对勾）。
  - 锚点字段（W3C Web Annotation，`note`/`commentary`/`issue`/`glossary` 收，其余 422）：
    `pos_start`/`pos_end`（`mb_strlen` 口径）、`quote_exact`、`quote_prefix`/`quote_suffix`。
    CLI 只要 `--quote-exact`，位置与前后缀在本地按句子原文算（`lib/anchors.py`），
    算之前先 `GET {API}/v2/sentence/{uid}` 取原文（§6）。
  - `commentary` 的 `content` 是下一层句子模板 `{{book-para-start-end}}`（可并列多个）。
  - `severity` 随 type：`issue`→`error/warning/suggestion`，`help`→`urgent/normal`，
    `assessment`→评估方法（1–16 位字母数字 `. _ -`，如 `mqm`、`llm-judge`），其它类型传了 422。
  - `score` 只有 `assessment` 收（且必填），其它类型传了 422。CLI：`discuss-add --type assessment --score 85 --method mqm`。
  - `notify` 缺省 true；AI 批量写显式给 `false`（批注与评估本来就不发）。
- **返回**：201 `data: { id, …, editor, co_editor }`。`assessment` **一句只留一条**：该句已有评估时
  就地覆盖（分数、方法、标题、理由、署名换成这次的，回复保留），返回 **200**、id 不变。

## 42. 回复 —— `POST {API}/v3/discussions/{话题id}/replies`

- **入参**：body 只有 `{ content, notify }`（类型、挂靠对象由服务端继承）。
- **返回**：201 `data: { … }`；话题已关闭 409，对回复再回复 422。

## 43. 修改 —— `PATCH {API}/v3/discussions/{id}`

- **入参**：body 只提交要改的字段（**局部更新，无 PUT**）。`title`/`status`/`type`/`severity`/`score`
  只对话题有效；批注 `type` 只能在 `note`/`commentary` 之间改。改 type 时锚点保留。
  `assessment` 可改 `score`、`severity`（评估方法，不能清空）、标题、正文；没有 `status`，不能与其它类型互转。
  CLI：`discuss-edit <id> --score 90 --method mqm`。
  CLI 给了新的 `--quote-exact` 时先取句子原文重新定位（同 §41）。
- **返回**：200 `data: { … }`。

## 44. 删除 —— `DELETE {API}/v3/discussions/{id}`

- **入参**：路径 `{id}`。
- **返回**：200 + 删除后的记录（**软删除**；有回复的话题以「已删除」占位保留）。

---

## 45. 按经文范围列批注 —— `GET {API}/v3/tipitaka-discussions/{channel}`

`discuss-range` 用。与 §37（一句）不同：一次列出一段经文里挂在句子上的批注，按经文顺序
（书、段、句起始词）排列，每条带所在句子坐标。只读，用模型 token。

- **入参**：路径 `{channel}`（句子所在 channel 的 uuid，必填）；query 全部可选——
  `book`（与 `chapter`/`para`/`to` 同用时必填，不给就是整个 channel）、`chapter`（章节起始段，
  服务端按章节长度展开；不能与 `para`/`to` 同用）、`para`、`to`（段落区间，含两端）、
  `type`（**逗号多选**，如 `issue,glossary`；不给只列话题，批注与评估要显式 `note`/`commentary`/`assessment`）、
  `status`、`severity`（逗号多选；assessment 时是评估方法）、`per_page`（≤200）、`page`。
- **返回**：`data: [ { …同 §37 的每条…, sentence: { book, paragraph, word_start, word_end } } ]` +
  `meta` 分页。channel 不存在或范围内没有批注返回空列表；`chapter` 不存在 404；参数非法 422。
- 可见性同 §37：未登录看不到 discussion，basic 角色在不能编辑的 channel 上只看得到自己发的。

# 五、管理统计（只读，仅 root / administrator）

`wikipali admin …` 用。全部用**用户 token**（`Authorization: Bearer`），v3 原生信封，
非管理员 403（CLI 译成「当前账号不是管理员」）。日期一律 UTC 日 `YYYY-MM-DD`，`to` 含当天；
统计与 digest 不给 `from`/`to` 时服务端取最近 30 天，跨度上限 366 天（超了 422）；
评价列表不给就不限日期。

## 46. 阅读统计 —— `GET {API}/v3/admin/reading-stats`

`admin stats reading` 用。

- **入参**：`from`、`to`、`client`（`all`/`web`/`mobile`）。
- **返回**：`data: { range, summary{active_readers, chapters_opened, reading_seconds, reading_users,
  page_views, dict_lookups}, previous{同 summary，上一个等长区间}, sticky{dau, mau}, daily[],
  top_chapters[{article_id, book, paragraph, title, readers, records}], pitaka_share[], layer_share[],
  duration_buckets[], reading_credits }`。`reading_seconds` 等只有 App 上报，网页为 null。

## 47. AI 问答统计 —— `GET {API}/v3/admin/agent-stats`

`admin stats agent` 用。

- **入参**：`from`、`to`、`account_type`（`all`/`user`/`guest`）。
- **返回**：`data: { range, summary{runs, deep, passage, denied, errors, cancelled, improve, askers,
  askers_user, askers_guest, latency_p50_ms, latency_p95_ms, tokens_in, tokens_out, feedback_up,
  feedback_down, feedback_asked},
  previous, daily[], clients[], tools[{name, calls, errors, avg_ms}], feedback_reasons[{reason, count}],
  credits{…} }`。

## 48. 提问记录 —— `GET {API}/v3/admin/agent-runs`、`GET {API}/v3/admin/agent-runs/{run}`

`admin runs` / `admin run` 用。

- **列表入参**：`filter[status]`（`ok`/`error`/`cancelled`/`denied`/`unchecked`）、`filter[route]`、
  `filter[account_type]`、`filter[client]`、`filter[improve]`、`filter[q]`（问题文字）、`page`、`per_page`（≤100）。
- **列表返回**：`data: [{run_id, thread_id, account_type, client, question, route, deep, improve, status,
  latency_ms, tokens_in, tokens_out, started_at, …}]` + `meta` 分页。
- **详情**另含 `answer`、`evidence`、`plan`、`passage`、`citations`、`error`、`model`、`prompt_version`、
  `steps[{seq, kind, name, args, result, result_chars, tokens_in, tokens_out, ms, error}]`。
  详情带账号信息（`user`、`device_id`、`client_ip`），CLI 文本输出不显示，`--json` 会原样输出。

## 49. 精简导出 —— `GET {API}/v3/admin/agent-runs/digest`

`admin digest` 用，输出 JSONL（一行一次提问），给 agent 做问题聚类与改进分析。
**只含用户同意「用于改进」（improve=true）的提问，不含任何身份字段。**

- **入参**：`from`、`to`、`full`（`1`/`0`，默认 0）、`limit`（≤2000，默认 500；`full` 时 ≤200，默认 100）。
- **返回**：`data: [{run_id, started_at, question, route, route_raw, confidence, deep, from_reader, client,
  status, latency_ms, lemmas[], keywords["lemma|tags"], retries, llm_calls, tokens, tools[{name, ms, chars, error}],
  feedback[{rating, tags, comment, asked}], events{kind: n}, next_question_after_s}]`，
  `meta: {from, to, count, has_more}`。`has_more` 为真时缩小日期范围或加大 `limit`。
- `full=1`（`admin digest --full`）时每条再带 `answer`、`evidence`（给作答模型的证据全文）、`citations[]`。
  **服务端不做回答质量评估**，由 agent 拉这些自己评（引用是否都在证据里、是不是证据里有却说没找到等）。
  单条也可以 `admin run <run_id> --evidence`（走 §48 详情接口）。

## 50. 用户评价 —— `GET {API}/v3/admin/agent-feedback`

`admin feedback` 用。

- **入参**：`filter[rating]`（`1`/`-1`）、`filter[tag]`（点赞标签 `accurate`/`useful_citations`/`clear`/`inspiring`，
  点踩原因 `citation_wrong`/`missed`/`off_topic`/`incorrect`/`too_long`/`too_academic`/`slow`/`other`）、
  `filter[has_comment]`、`from`、`to`、`page`、`per_page`（≤100）。
- **返回**：`data: [{id, message_id, rating, tags[], comment, asked, client, created_at, updated_at,
  account_type, run_id, question, route, status, deep, latency_ms}]` + `meta` 分页。
  `run_id` 为 null 表示那次提问还没入库（评价先到）。不含账号身份。

# 附录

## 51. 一章有哪些 channel —— `GET {API}/v3/tipitaka-chapter-channels/{book}/{para}`

`versions --chapter` 用。取代 v2 `progress?view=chapter_channels`；段落粒度的 `versions`
走 `v3/tipitaka-paragraph-channels`（见 §12）。

- **入参**：路径 `book`、`para`（章节起始段，不是章内任意段——非起始段返回空列表）；
  查询 `per_page`（最大 200，客户端传 200 一次取全，单章最多几十个）、`page`。
- **返回**：`data[] = { id, book, para, progress, progress_line, views, updated_at,
  channel{id, name, type, lang}, studio{id, nickName, realName, avatar?}|null }`，
  按 `progress`（0–1）降序；`meta` 是 Laravel 分页。
  - 不带凭据调用，只列**公开** channel（服务端按登录身份过滤可见性）。
  - 旧站点没有这条路由时 404，客户端提示退回段落粒度的 `versions`。

## 52. 积分策略 —— `GET {API}/v3/credit-policy`

`credit-policy` 用。公开，不需要登录，不带 token。

- **入参**：无。
- **返回**：`data: {version, day_timezone, daily_free{guest, user}, cost{normal, deep}, guest_ip_daily_cap,
  earn{reading{credits_per_minute, daily_cap}, editing{credits_per_minute, daily_cap}}}`。
  `version` 是策略生效日（YYYYMMDD），也是积分流水里记的版本号；`daily_cap` / `guest_ip_daily_cap` 为 null 表示不限。
  服务端只有当前生效的一版，没有历史接口。

## 常见错误约定

客户端的报错**一律带 HTTP 状态码**：`ApiError` 的文本固定为 `HTTP <码>：<服务端 message>`
（v2 取 `message`，v3 取 `detail` / `title`；服务端没给说明时只有 `HTTP <码>`）。
HTTP 200 但 `ok: false` 也按 `HTTP 200：<message>` 报。网络层失败没有状态码，报「连不上 …」。

| 现象 | 含义 | 处置 |
|---|---|---|
| 401 | token 失效/过期/被撤销 | 提示重新登录/重取 token，不自动重试 |
| 403 | 无 channel 编辑权，或不是模型 owner | 指出缺哪项权限 |
| 404（较新端点） | 站点跑旧版代码 | 提示切最新版，别当成「资源不存在」 |
| 409 | 同 studio 模型重名 | 当作「已存在」，回查列表取 uid |
| 422 | 参数校验失败 | 看 message |
| `access-token` 返回 `count: 0` | 对该 channel 无编辑权（静默跳过） | 当作 403，中止写入 |
| `sentence` 的 `count` < 提交条数 | 部分句子鉴权失败被跳过 | 逐条比对并报告 |
| `message: "word existed"` + 200 | 同 channel 下 `word + tag` 已存在 | 不是成功，改 PUT |
| `message: "no date"` + 200 | 缺 `sentences` 字段 | 客户端 bug |

## 不自动切换站点

所有请求**只发往当前设定的 `{API}`**（`--api` > `WIKIPALI_API_URL` > 凭据文件 > 内置默认）。
网络层不可达（连接失败、超时、传输中断）时直接报错退出，**不会自动换到别的站点**——
即使 `www` 与 `next` 同库，代码版本也不同。要换站点由用户执行 `wikipali endpoint` 或给 `--api`。

## 未调用 / 已知故障

- `GET {API}/v2/search?view=pali`、`GET {API}/v2/search-book-list`：**500**（gRPC 不可达），
  本插件不使用；短语检索靠拆词分别展开词形再检索。
- `GET {API}/v2/chapter/{book}-{para}` 与 `palitext/{book}-{para}` 返回一致，本插件用 `palitext`。
