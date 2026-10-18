# WikiPali API 调用清单

本文汇总 `wikipali-plugins`（`plugins/wikipali`）实际调用的全部 WikiPali HTTP 接口，
用于快速检索「某个能力对应哪个接口、入参是什么、返回什么」。

基址记为 `{API}`，由 `lib/sites.py` 定义，六个地址：

| 地址 | 版本 | 数据 |
|---|---|---|
| `https://www.wikipali.org/api` | 稳定版 | 线上共享库 |
| `https://www.wikipali.cc/api` | 稳定版 | 线上共享库 |
| `https://next.wikipali.org/api` | 最新版 | 线上共享库 |
| `https://next.wikipali.cc/api` | 最新版 | 线上共享库 |
| `https://staging.wikipali.org/api` | 预发布 | 独立库 |
| `http://127.0.0.1:8000/api` | 开发机 | 独立库 |

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
| 读 | `GET {API}/v2/case/{词}` | 输入变格形/词根，返回候选词典原型及全部词形，是一切检索的前置 |
| 读 | `GET {API}/v2/dict` | 查词典释义与形态分析（形→根），用于确认选对了词根 |
| 读 | `GET {API}/v2/search-pali-wbw` | 按词形列表检索命中的段落，带页码出处与黑体高亮 |
| 读 | `GET {API}/v2/search-pali-wbw-books` | 统计词形在各部书里的词次分布（数词次，不是段落数） |
| 读 | `GET {API}/v2/sentence` | 按坐标取原文/译文句子（view=paragraph / chapter） |
| 读 | `GET {API}/v2/sentence/{uid}` | 取单句，拿到它所属的 channel 与 book |
| 读 | `GET {API}/v2/palitext` | 目录类查询（view=book-toc / paragraphs-info 等） |
| 读 | `GET {API}/v2/para-info` | 取某章辖区的段落清单（每段是标题还是正文、多长） |
| 读 | `GET {API}/v2/palitext/{book}-{para}` | 段落/章节元信息（chapter_len / strlen / pcd_book_id / path） |
| 读 | `GET {API}/v2/chapter-content/{book}-{para}` | 整章内容（嵌套 JSON，逐句带 origin/translation） |
| 读 | `GET {API}/v2/tipitaka-content/{book}-{para}` | 整章内容（预建 HTML，首选，一次一个 channel） |
| 读 | `GET {API}/v2/channel` | channel 列表（view=paragraphs 查译本、view=system 查巴利原文 uid） |
| 读 | `GET {API}/v2/term-vocabulary` | 社区权威译名对照表（整表拉取，本地过滤） |
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
| 认证/模型 | `POST {API}/v2/sign-in` | 用户名+密码登录，返回 JWT 字符串 |
| 认证/模型 | `GET {API}/v2/auth/current` | 取当前登录用户信息（realName 即 studio_name） |
| 认证/模型 | `GET {API}/v2/ai-model` | 查 AI 模型记录列表 |
| 认证/模型 | `POST {API}/v2/ai-model` | 新建 AI 模型记录 |
| 认证/模型 | `PUT {API}/v2/ai-model/{uid}` | 增量修改 AI 模型记录 |
| 认证/模型 | `GET {API}/v2/ai-model-token/{uid}` | 取模型身份 token（写句子的 Authorization） |
| 认证/模型 | `DELETE {API}/v2/ai-model-token/{uid}` | 撤销模型已签出的全部 token |
| 认证/模型 | `GET {API}/v2/channel?view=user-edit` | 列出当前账号可编辑的 channel |
| 认证/模型 | `GET {API}/v2/channel/{uid}` | 回显单个 channel 的名字 |
| 认证/模型 | `POST {API}/v2/access-token` | 为 channel 签发 access token（写句子的 body 字段） |
| 写 | `POST {API}/v2/sentence` | 按坐标写/覆盖译文句子 |
| 写 | `GET {API}/v2/terms` | 列用户自己的术语（view=user/studio/channel） |
| 写 | `GET {API}/v2/terms/{guid}` | 取单条术语 |
| 写 | `POST {API}/v2/terms` | 新建术语（落在 channel 名下） |
| 写 | `PUT {API}/v2/terms/{guid}` | 增量修改术语 |
| 批注(v3) | `POST {API}/v3/agent-grants` | 人类为模型签发「某 channel、某 book」写入授权 |
| 批注(v3) | `GET {API}/v3/discussions` | 列出某句上的话题/批注 |
| 批注(v3) | `GET {API}/v3/discussions/summary` | 某句上的批注统计 |
| 批注(v3) | `GET {API}/v3/discussions/{id}` | 取单条批注/话题 |
| 批注(v3) | `GET {API}/v3/discussions/{id}/replies` | 取某话题下的回复 |
| 批注(v3) | `POST {API}/v3/discussions` | 新建话题/批注 |
| 批注(v3) | `POST {API}/v3/discussions/{id}/replies` | 回复某话题 |
| 批注(v3) | `PATCH {API}/v3/discussions/{id}` | 局部修改批注/话题 |
| 批注(v3) | `DELETE {API}/v3/discussions/{id}` | 软删除批注/话题 |

---

# 一、读侧（无需凭据）

## 1. 词形展开 —— `GET {API}/v2/case/{词}`

输入任意变格形或词根，返回候选词典原型，按可能性排序。

- **入参**：路径参数 `{词}`（可含巴利变音符号，客户端已做百分号编码）。
- **返回**：`data: { rows: [ { word, count, case: [ {word, count, bold}, … ] } ], count }`
  - `rows[0]` 是可能性最高的候选；`case` 是该词根在语料中实际出现过的全部词形。
  - ⚠ 查无此词会返回一个 `case` 为空的候选行，客户端据此判定「没找到」。

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

## 3. 检索 —— `GET {API}/v2/search-pali-wbw`

按词形列表检索命中的段落（多词形之间是 OR）。

- **入参**：
  | 参数 | 说明 |
  |---|---|
  | `key` | 逗号分隔的**词形**列表（不是词根），多个词形之间 OR |
  | `bold` | `on` 只要黑体命中、`off` 只要非黑体 |
  | `book` | 限定书，值用 `search-pali-wbw-books` 返回的 `pcdBookId` |
  | `tags` | 范围限定，`tag1,tag2;tag3`（组间 OR、组内 AND） |
  | `limit` / `offset` | 分页，`limit=200` 实测正常 |
- **返回**：`data: { count: 命中段落数, rows: [ { book, paragraph, rank, path, paliTitle, highlight, link, ref } ] }`
  - `link` 是网页阅读地址；`ref` 是各印本页码 `[{type, page, title}]`（`WP` 的 `page` 就是段落号）；
  - `path` 是章节路径数组 `[{book, paragraph, title, level}]`；`rank = sum(weight)`；
  - `highlight` 里命中词包在 `<span class='hl'>`，并保留原文的 `<span class="bld">`（黑体）。

## 4. 出处分布 —— `GET {API}/v2/search-pali-wbw-books`

统计词形在各部书里的词次分布。

- **入参**：`key`（词形列表，同检索）、`tags`（可选）。
- **返回**：`data.rows[] = { pcdBookId, count, book, paragraph, paliTitle, tags: [{name}] }`
  - ⚠ `count` 数的是**词次**，不是段落数；段落数看 `search-pali-wbw` 的 `count`。
  - `tags` 含 `mūla` / `aṭṭhakathā` / `ṭīkā`，区分根本、义注、复注。

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

取单句，拿到它所属的 channel 与 book。

- **入参**：路径参数 `{uid}`（`v2/sentence` 返回的 `id`）。
- **返回**：`data: { …, channel: { id, … }, book }`——写批注前用 `data.channel.id`、`data.book` 申请授权。

## 7. 目录 —— `GET {API}/v2/palitext`

目录类查询，按 `view` 区分。

- **入参**：`view`（`book-toc` / `chapter` / `chapter_children` / `children` / `paragraph` /
  `paragraphs-info`），参数 `book` / `para` / `series` 随 view 而定。
- **返回**：
  - `view=book-toc`：整套丛书目录，行 `{book, paragraph, toc, level}`（`para` 给该书任意段号即可，
    返回常含多本书，需按 `book` 过滤）。
  - `view=paragraphs-info`（旧段落清单，字段含 `lenght`/`length`）：行
    `{book, paragraph, toc, level, length, chapter_len, book_name, cs_para}`，见 §8 的字段说明。

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
  - `pcd_book_id` 等于 `search-pali-wbw` 的 `book` 参数值。

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

## 11. 整章内容（HTML，首选）—— `GET {API}/v2/tipitaka-content/{book}-{para}`

走 OpenSearch 预建文档，返回一整串渲染好的 HTML。

- **入参**：路径 `{book}-{para}`；`channel`（**单数**，一次一个；缺省巴利原文）。
- **返回**：一整串 HTML。每句包在 `data-sid='93-6-31-46'` 中，sid 即引用坐标
  `book-para-wordStart-wordEnd`。
  - 三种响应分开处理：正常（200 且含 `data-sid`）；有文档但没句子（200 但 sid 数为 0）；
    **无预建文档返回 400，message 里带 OpenSearch `found:false`**（不是服务故障）。
  - 正文夹 `<code>M1.1</code>` 是版本页码（M/V/P/T），须留在原位。

## 12. channel 列表 —— `GET {API}/v2/channel`

按 `view` 区分用途；读侧用 `view=paragraphs` 和 `view=system`。

- **入参**：
  - `view=paragraphs`：`book_id`、`para` —— 查某坐标有哪些译本。
  - `view=system`：`limit`（如 500）—— 查系统 channel，非线上站点据此找巴利原文 uid。
- **返回**：`data.rows[] = { uid, name, type, lang, status, … }`。
  - ⚠ 稳定版站点 `view=paragraphs` 会 500（修复只在最新版），客户端提示切 `next`。

## 13. 术语表（权威译名）—— `GET {API}/v2/term-vocabulary`

权威译名对照，只读。

- **入参**：`view`（默认 `community`）、`lang`（如 `zh-Hans`）。
- **返回**：`data.rows[] = { guid, word, tag, meaning, other_meaning }`。
  - ⚠ 不支持按词查询，只能拉全表（zh-Hans 约 17074 条），客户端缓存后本地过滤。

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
| accessToken | `POST /v2/access-token` | 被委托的 channel 编辑权 | 写句子/术语时的 body 字段 | 7 天 |

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

## 28. 可编辑 channel —— `GET {API}/v2/channel?view=user-edit`

- **入参**：`Authorization: Bearer <userToken>`；query `order`/`dir`/`limit`（默认 200）/
  `offset`/`search`。
- **返回**：`data: { rows: [ { uid, name, summary, type, owner_uid, lang, status, updated_at, created_at, role, studio } ], count }`。

## 29. 单 channel 回显 —— `GET {API}/v2/channel/{uid}`

- **入参**：`Authorization: Bearer <userToken>`；路径 `{uid}`。
- **返回**：`data: { uid, name, … }`（主要用于显示 channel 名字）。

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

## 32. 列术语 —— `GET {API}/v2/terms`

- **入参**：`Authorization: Bearer <userToken>`（人类身份）。
  | view | 额外参数 | 含义 |
  |---|---|---|
  | `user` | 无 | 当前账号名下全部 |
  | `studio` | `name`=studio 名 | 某 studio 的 |
  | `channel` | `id`=channel uid | 某 channel 的 |
  通用：`search`、`order`、`dir`、`offset`、`limit`。
- **返回**：`data: { rows: [ … ], count }`；行含 `guid`/`word`/`meaning`/`other_meaning`/
  `note`/`tag`/`channel`/`editor` 等。

## 33. 单条术语 —— `GET {API}/v2/terms/{guid}`

- **入参**：`Authorization: Bearer <userToken>`；路径 `{guid}`（uuid，不是雪花 id）。
- **返回**：`data: { guid, word, meaning, …, channel_id, channel }`（改术语前读原值用）。

## 34. 新建术语 —— `POST {API}/v2/terms`

- **入参**：`Authorization: Bearer <modelToken>`；body
  ```json
  { "word": "satipaṭṭhāna", "meaning": "念处", "other_meaning": "念住",
    "note": "markdown", "tag": "abhidhamma",
    "channel": "<uid>", "access_token": "<JWT>" }
  ```
  - 参数名是 **`channel`**（不是 `channel_uid`）；`word_en` 由服务端生成；
    AI 写术语**必须落在 channel 里**（studio 级术语模型 403）。
- **返回**：`data: { guid, word, meaning, …, editor }`。
  - 同 channel 下 `word + tag` 唯一，冲突时**拒绝**（HTTP 200 且 `message: "word existed"`），
    与句子「覆盖」相反。

## 35. 修改术语 —— `PUT {API}/v2/terms/{guid}`

- **入参**：`Authorization: Bearer <modelToken>`；路径 `{guid}`；body 只提交要改字段
  （增量更新），另带 `access_token`。
- **返回**：`data: { guid, word, meaning, …, editor }`；`editor_uid` 判断是否模型所写
  （模型没有 `editor_id`，记 -1）。

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
  `per_page`（≤200）、`page`。不带 `type` 只列话题，批注要显式 `type=note`/`commentary`。
- **返回**：`data: [ { id, target_type, target_id, type, title, content, status, editor, co_editor, reply_count, abilities, pos_start/pos_end/quote_exact/quote_prefix/quote_suffix, created_at, … } ]` + `meta` 分页。

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
  - `type` 六类：`note`/`commentary`（批注，收锚点，注入阅读页）、`discussion`/`qa`/`help`/
    `issue`（话题，**title 必填**，不收锚点）。
  - 锚点字段（W3C Web Annotation，只有批注收）：`pos_start`/`pos_end`（`mb_strlen` 口径）、
    `quote_exact`、`quote_prefix`/`quote_suffix`。
  - `commentary` 的 `content` 是下一层句子模板 `{{book-para-start-end}}`（可并列多个）。
  - `severity` 随 type：`issue`→`error/warning/suggestion`，`help`→`urgent/normal`，其它类型传了 422。
  - `notify` 缺省 true；AI 批量写显式给 `false`。
- **返回**：201 `data: { id, …, editor, co_editor }`。

## 42. 回复 —— `POST {API}/v3/discussions/{话题id}/replies`

- **入参**：body 只有 `{ content, notify }`（类型、挂靠对象由服务端继承）。
- **返回**：201 `data: { … }`；话题已关闭 409，对回复再回复 422。

## 43. 修改 —— `PATCH {API}/v3/discussions/{id}`

- **入参**：body 只提交要改的字段（**局部更新，无 PUT**）。`title`/`status`/`type`/`severity`
  只对话题有效；批注 `type` 只能在 `note`/`commentary` 之间改。
- **返回**：200 `data: { … }`。

## 44. 删除 —— `DELETE {API}/v3/discussions/{id}`

- **入参**：路径 `{id}`。
- **返回**：200 + 删除后的记录（**软删除**；有回复的话题以「已删除」占位保留）。

---

# 附录

## 常见错误约定

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

## 自动 fallback

线上四站共享同一数据库和 JWT 密钥，网络层不可达时会按「同版本另一域名 → 另一版本同域名 →
其余」的顺序自动 fallback，但**绝不回退到 127.0.0.1**（那是另一个库）。

## 未调用 / 已知故障

- `GET {API}/v2/search?view=pali`、`GET {API}/v2/search-book-list`：**500**（gRPC 不可达），
  本插件不使用；短语检索靠拆词分别展开词形再检索。
- `GET {API}/v2/chapter/{book}-{para}` 与 `palitext/{book}-{para}` 返回一致，本插件用 `palitext`。
