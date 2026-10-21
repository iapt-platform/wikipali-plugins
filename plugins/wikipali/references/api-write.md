# WikiPali API 参考（写入路径）

本文只记 Skill 用到的端点。契约以**稳定版**（`www.*`）为准；标注「最新版」的能力可能在稳定版上还是 404。

基址记为 `{API}`，形如 `https://www.wikipali.org/api`。所有响应统一形如：

```json
{ "ok": true, "data": <任意>, "message": "" }
```

`ok: false` 时 `message` 是原因，HTTP 状态码同时表达语义。**HTTP 200 不等于全部成功**——见文末「静默跳过」。

## 三种 token，职责不能混

| Token | 从哪来 | 代表谁 | 用在哪 | 有效期 |
|---|---|---|---|---|
| userToken | `POST /v2/sign-in` | 人类操作者 | 查/建 ai-model、签 access token、列 channel | 365 天 |
| modelToken | `GET /v2/ai-model-token/{uid}` | AI 模型身份 | **写句子时的 `Authorization`** | 30 天，可撤销 |
| accessToken | `POST /v2/access-token` | 被委托的 channel 编辑权 | **写句子时的 body 字段** | 7 天 |

写句子时两者同时出现：`Authorization: Bearer <modelToken>`，句子对象里带 `access_token: <accessToken>`。用错会让 `editor_uid` 落成人类用户，署名与审计就废了。

---

## 1. 登录

`POST {API}/v2/sign-in`　body `{ "username": "<用户名或邮箱>", "password": "<明文>" }`

- `data` 是 JWT 字符串本身（不是对象）。
- 失败返回 **HTTP 400**，`message` 是 `invalid token`——措辞误导，实际含义是用户名或密码不对。

`GET {API}/v2/auth/current`（Bearer = userToken）

- `data: { id, nickName, realName, avatar, token, roles }`
- **`realName` 就是后面 `studio_name` 参数要用的值**，不是 `nickName`。

## 2. AI Model

`GET {API}/v2/ai-model?view=studio&name={studio_name}&keyword={模型名}`（Bearer = userToken）

- `data: { rows: [...], count }`；`keyword` 是 `like %kw%` **模糊**匹配，客户端必须自己做 `name` 精确比对。
- `view` 只接受 `all` / `studio` / `usable` / `chat`。**传别的值会 500**（服务端 switch 缺 default 分支，已知缺陷）。
- 行里的 `key` / `system_prompt` 只在请求者是 owner 本人时才返回。

`POST {API}/v2/ai-model`（Bearer = userToken）　body `{name, studio_name, model?, url?, key?, privacy?, description?, system_prompt?}`

- 一次 POST 即可带全字段，不需要再 PUT 补。
- 同一 studio 内 `name` 重复 → **409**，客户端据此判定「已存在」。
- `name` / `studio_name` 缺失 → 422。
- 鉴权要求 `studio_name` 就是操作者本人的 studio（个人 studio），group studio 一律 403。

`PUT {API}/v2/ai-model/{uid}`（Bearer = userToken）

- **增量更新**：只改请求里出现的字段，未提交的保持原值；显式传 `null` 才会清空。
- 改名撞上同 studio 内已有名字 → 409。

## 3. 模型身份 token

`GET {API}/v2/ai-model-token/{uid}`（Bearer = userToken）→ `data: { uid, name, token }`

- 只有模型 owner 本人能调；未登录 401，非 owner 403，模型不存在 404。
- 签出的 token 有效期 30 天，payload 带 `typ: "ai-model"` 与 `ver`。

`DELETE {API}/v2/ai-model-token/{uid}`（Bearer = userToken）→ `data: { uid, name, token_version }`

- 语义是**作废该模型已签出的全部 token**，无法只废一张。撤销后旧凭据一律 401。
- 这两个端点较新，稳定版站点上可能还没有 → 404 时先怀疑「站点代码版本旧」，而不是「模型不存在」。

## 4. 可编辑 channel 列表

`GET {API}/v2/channel?view=user-edit`（Bearer = userToken）→ `data: { rows: [...], count }`

- 语义：owner 是自己的 channel ∪ 协作权限 power ≥ 20 的 channel。
- 行内含 `uid / name / summary / type / owner_uid / lang / status / updated_at / created_at / role / studio`。
- 支持 `order` / `dir` / `limit`（默认 200）/ `offset` / `search`。

`GET {API}/v2/channel/{uid}` 可用于回显单个 channel 的名字。

## 5. 签发 channel access token

`POST {API}/v2/access-token`（Bearer = userToken）

```json
{ "payload": [ { "res_type": "channel", "res_id": "<channel uid>", "power": "edit", "book": 0 } ] }
```

→ `data: { rows: [ { payload, token } ], count }`

- **无权时该条被静默跳过**，返回 `count: 0` 和空 rows，HTTP 仍是 200。必须判空，等同 403 处理，**不可继续写入**。
- 返回的 `payload` 里含 `nbf` / `exp`，据此判断何时重签。
- ⚠ **`book` 必须是整数**。服务端校验用 `$jwt->book !== $book` 严格比较，而 `$book` 已被转成 int，写成 `"1"` 会让 `"1" !== 1` 恒真而永远鉴权失败。`0` 表示不限 book。

## 6. 写入句子

`POST {API}/v2/sentence`（Bearer = **modelToken**）

```json
{
  "sentences": [
    {
      "book_id": 1,
      "paragraph": 10,
      "word_start": 0,
      "word_end": 12,
      "channel_uid": "<channel uid>",
      "content": "译文",
      "content_type": "markdown",
      "access_token": "<第 5 步签出的 JWT>"
    }
  ]
}
```

→ `data: { rows: [ ... ], count }`

- 语义：按 `(book_id, paragraph, word_start, word_end, channel_uid)` 做 `firstOrNew`——**存在即覆盖，不存在则新建**。天然幂等，但也意味着会静默覆盖别人写的同位置句子，写前必须向用户确认。
- 副作用：写 `sent_histories`（可追溯）、清缓存、发进度消息。
- 返回的 rows 用的是另一套字段名：`book`（不是 `book_id`）、`paragraph`、`word_start`、`word_end`、`channel.uid`、`editor`。核对写入结果要按这套字段匹配。
- 缺 `sentences` 字段时返回 **HTTP 200** 且 `message: "no date"`——这是客户端 bug，不是成功。

### 静默跳过

`store()` 对**逐句**鉴权失败是 `continue` 掉的，不报错。所以：

> 提交 N 条、HTTP 200、`count` 却小于 N，意味着有句子没写进去。

必须把返回的 rows 与提交的句子逐条比对，把差集报给用户。

---

## 7. 术语（用户自己的术语表）

与只读的**社区权威译名表**（`v2/term-vocabulary`，对应 `wikipali terms`）不是一回事。
这里是 `v2/terms`，自己 studio / channel 名下、可增可改的术语。

### 铁律：AI 写术语必须落在 channel 里

模型的权限全部由人类签出的 **channel access token** 代持，而 access token 是
channel 级的，代持不了 studio 权限。因此**不属于任何 channel 的术语（studio 级），
模型一律 403**——建不了也改不了，只能由 studio 本人在网站上操作。不要试图绕过。

### 列出

`GET {API}/v2/terms`（Bearer = **userToken**，人类身份）

| view | 额外参数 | 含义 |
|---|---|---|
| `user` | 无 | 当前账号名下全部术语 |
| `studio` | `name`=studio 名 | 某个 studio 的 |
| `channel` | `id`=channel uid | 某个 channel 的 |

通用参数：`search`（对 word / word_en 前缀匹配、对 meaning 子串匹配）、`order`、
`dir`、`offset`、`limit`。→ `data: { rows: [...], count }`。

### 新建

`POST {API}/v2/terms`（Bearer = **modelToken**）

```json
{
  "word": "satipaṭṭhāna",
  "meaning": "念处",
  "other_meaning": "念住",
  "note": "markdown 注解",
  "tag": "abhidhamma",
  "channel": "<channel uid>",
  "access_token": "<第 5 步签出的 JWT>"
}
```

- 参数名是 **`channel`**（不是 `channel_uid`）；库里的列名是 **`channal`**（服务端拼写如此）。
- `word_en` 由服务端从 `word` 生成，不要自己提交。
- `language` 有 channel 时跟随 channel，给了也会被覆盖。
- `owner` 是 channel 所属的 studio，不是写入者。
- 唯一性：同一 channel 下 `word + tag` 唯一。**冲突时服务端拒绝而不是覆盖**——这点与句子相反。

### 修改

`PUT {API}/v2/terms/{guid}`（Bearer = **modelToken**），body 同上但**只提交要改的字段**，
另带 `access_token`。路由参数是 **guid**（uuid），不是 `id`（雪花）。

服务端是增量更新：没提交的字段保持原值，`create_time` 不会被刷新。

### 署名

写入落到 `editor_uid`（uuid），模型写入即模型的 uid；返回的 `editor` 已解析成
模型信息。核对写入结果就看它。

`editor_id` 存的是人类用户的自增 sn，模型没有，一律记 **-1**（0 与「缺省/未知」
撞车，分不清是模型写的还是数据有问题）。判断是不是模型写的，看 `editor_uid`。

---

## 8. 批注（discussion）——v3

对**某一句**的批注，走 `/v3/discussions`。v3 的约定：成功直接 `{data: …}`（列表另有
`meta` 分页），失败是 Problem Details（`{type, title, status, detail}`），**成败只看状态码**；
请求带 `Accept-Language: zh-Hans` 时 `detail` 是中文。

### 写入要人类授权：agent-grants

模型自己没有任何 channel 权限。写批注前，人类用 **userToken** 为模型签一张写入授权：

`POST {API}/v3/agent-grants`（Bearer = **userToken**）

```json
{ "ai_model": "<模型 uid>", "target_type": "channel", "target_id": "<channel uid>", "book": 1935 }
```

→ 201 `{data: {token, grantor, ai_model, target_type, target_id, book, expires_at}}`。
`book` 给 0 或不给表示不限 book。7 天有效；撤销模型 token（`DELETE v2/ai-model-token/{uid}`）
时它签出的授权一并失效。签发条件：模型归当前用户所有、当前用户能编辑该 channel，否则 403。

写入时：`Authorization: Bearer <modelToken>`，另加请求头 `X-Agent-Grant: <授权 token>`。服务端记
**editor = 授权人**（对内容负责的人）、**co_editor = 模型**，权限按授权人判，只能写授权覆盖的
channel / book 里的句子上的批注。模型不带授权写入一律 403。人亲自改了内容，co_editor 会被清空。

读（列表、单条、回复、统计）只要 Bearer，不要授权。

### 挂在哪：target_id 是句子 uid，不是坐标

`target_type = 'sentence'`、`target_id = sentences.uid`。这个 uid 是**逐句、逐 channel** 的：
同一段巴利原文和它的中译是两条不同的句子、两个不同的 uid。

拿 uid 的办法就是读句子——`GET v2/sentence?view=paragraph&book=&para=&channels=` 返回的
**`id` 字段就是 `sentences.uid`**（`wikipali get <坐标> --json` 直接可见）。一个段落常有
多句，必须按 `word_start`/`word_end` 认准是哪一句，**不要猜**。句子所在的 channel 与 book
（申请授权用）可以 `GET v2/sentence/{uid}` 取：`data.channel.id`、`data.book`。

### 列出

| 端点 | 参数 | 返回 |
|---|---|---|
| `GET v3/discussions` | `target_type`、`target_id`（必填）、`type`、`status`、`per_page`（≤200）、`page` | 该句上的顶层话题 / 批注，带 `reply_count`、`abilities` |
| `GET v3/discussions/summary` | `target_type`、`target_id`、`type` | `{status_counts: {active, close}, creatable_types}` |
| `GET v3/discussions/{id}` | — | 单条 |
| `GET v3/discussions/{id}/replies` | `per_page`、`page` | 某话题下的回复，按时间正序 |

- **不带 `type` 只列话题**（discussion / qa / help / issue / glossary），批注要显式 `type=note` / `commentary`。
- 未登录看不到 discussion；`basic` 角色在自己管不了的句子上只看得到自己发的 discussion。
  issue / glossary 会注入公开的阅读页，所以对所有人可见。

### 新建

`POST {API}/v3/discussions`

```json
{
  "target_type": "sentence",
  "target_id": "<句子 uid>",
  "type": "discussion",
  "title": "标题（话题必填，批注可省）",
  "content": "正文（markdown）",
  "notify": false
}
```

句子上的批注按 `type` 分七类：

| type | 用户的说法 | 标题 | content | 锚点 | 阅读页 |
|---|---|---|---|---|---|
| `note` | 批注、脚注 | 可省 | 注解正文本身（必填） | 收 | 边注正文就是它，**没有**出处 |
| `commentary` | 注释对照、义注对照、复注对照 | 可省 | 下一层句子模板 `{{book-para-start-end}}`（必填，格式不对 422；一个片段由多句解释时并列多个模板，仍是一条记录） | 收 | 边注正文是那几句在当前 channel 的译文，末尾带 `<cite>义注</cite>` |
| `discussion` | 审稿意见、讨论（默认） | **必填** | 正文 | 不收（422） | 不进阅读页 |
| `qa` / `help` | 问答 / 求助 | **必填** | 正文 | 不收 | 不进阅读页 |
| `issue` | 问题（译错、漏译、标点…） | **必填** | 正文 | 收 | 有锚点：那段文字加波浪下划线（颜色随 severity），点开看内容；没锚点：句尾一个三角叹号。关闭后不再显示 |
| `glossary` | 外挂术语 | **必填，填术语词头** | 说明（可省） | **必须有** | 那段文字换成 `[[词头#原文]]`，渲染成术语。关闭后不再显示 |

`glossary`（外挂术语）**不改译文**，给一段译文临时挂上术语，供讨论该词值不值得正式收进术语表；
与术语表（`v2/terms`，`term-add`）是两回事。只能挂在句子上，只有该句所在 channel 的编辑者能建。
词头与被挂的那段原文里都不能有 `[ ] { } | #`，那段原文也不能和句中已有的 `[[…]]` / `{{…}}` /
粗体等标记重叠——否则渲染不了，服务端会直接不显示这条。

**锚点字段**（W3C Web Annotation 的 TextPosition / TextQuote 选择器），`note` / `commentary` /
`issue` / `glossary` 收，其余类型传了 422：

| 字段 | 类型 | 含义 |
|---|---|---|
| `pos_start` / `pos_end` | 非负整数，可空 | 锚点在句子**原始 content** 里的字符位（0 起，`mb_strlen` 口径，`pos_end` 不含，≥ `pos_start`） |
| `quote_exact` | 字符串，可空 | 被锚定文本的原样摘录 |
| `quote_prefix` / `quote_suffix` | 字符串，可空 | 摘录前后的上下文（建议 32~64 字符），抗文本位移 |

这四类被**注入阅读页**（`PaliContentService::injectAnnotationNotes`，排版在 `AnnotationLayout`）：
批注在锚点末尾插一条边注（没有锚点挂到句尾），glossary 把锚点处的原文换成术语，issue 高亮锚点处
的原文（没有锚点就在句尾放三角图标）。位置以 `pos_*` 为准；与 `quote_exact` 对不上（译文改过）时，
服务端按摘录（参考前后缀）重新定位，找不到的 issue 显示成句尾图标、glossary 不显示。交叠的 issue
合并成一个高亮；issue 与 glossary 交叠时 issue 扩展到包住 glossary；两个 glossary 交叠只留一个。
写入后服务端会清该段的阅读页缓存。回复不注入。

CLI 的 `discuss-add` / `discuss-edit` 只要 `--quote-exact`，位置与前后缀由程序在句子原文里算
（`lib/anchors.py`），不必让模型数字符位。

`commentary` 即注释书对应：`target_id` 是上一层（根本 / 义注）某句**译文**的 uid，写法见
`note-push` 与 `skills/commentary-align`；其余用 `discuss-add --type <type>`。

`severity`（严重 / 紧急程度）取值随 type：`issue` 为 `error` / `warning` / `suggestion`，`help` 为
`urgent` / `normal`，其它类型传了 422。改 type 时新类型不收原 severity 的，服务端自动清空；
锚点不清（留着不显示，改回可带锚点的类型时恢复）。

v3 只收 markdown，没有 `content_type`。`notify` 缺省是 **true**（会发站内通知），AI 批量写时显式给
`false`；新建批注本来就不发。

### 回复

`POST {API}/v3/discussions/{话题id}/replies`，body 只有 `{content, notify}`：类型、挂靠对象由服务端
从话题继承。话题已关闭 409；对一条回复再回复 422。批注也可以回复。

### 改与删

`PATCH {API}/v3/discussions/{id}`：**局部更新**，只改传了的字段（没有 PUT）。`title` / `status` /
`type` / `severity` 只对话题有效；批注没有 `status`，type 只能在 note / commentary 之间改。
改成 `glossary` 须挂在句子上、且是该句的编辑者。

`DELETE {API}/v3/discussions/{id}`：**软删除**，返回 200 + 删除后的记录。作者或该句所在 channel 的
编辑者可删；有回复的话题删后以「已删除」占位保留。

---

## 错误约定

| 现象 | 含义 | 处置 |
|---|---|---|
| 401 | token 失效/过期/被撤销 | 提示重新登录或重取模型 token，**不要自动重试** |
| 403 | 无 channel 编辑权，或不是模型 owner | 指出缺哪一项权限 |
| 404（较新端点） | 站点跑的是旧版代码 | 提示切到最新版站点，别当成「资源不存在」 |
| 409 | 同 studio 内模型重名 | 当作「已存在」，回查列表取 uid |
| 422 | 参数校验失败 | 看 message |
| `access-token` 返回 `count: 0` | 对该 channel 无编辑权（静默跳过） | 当作 403，**中止写入** |
| `sentence` 的 `count` < 提交条数 | 部分句子鉴权失败被跳过 | 逐条比对并报告 |
| `message: "no date"` + 200 | 请求缺 `sentences` | 客户端 bug |
| `message: "word existed"` + 200 | 同 channel 下 `word + tag` 已存在 | **不是成功**；改用 `PUT` 修改已有那条 |

## 站点

四个线上地址**共享同一个数据库和同一把 JWT 密钥**，凭据完全通用，可随时切换：

| 地址 | 地区 | 代码版本 |
|---|---|---|
| `https://www.wikipali.org/api` | .org | 稳定版 |
| `https://www.wikipali.cc/api` | .cc | 稳定版 |
| `https://next.wikipali.org/api` | .org | 最新版 |
| `https://next.wikipali.cc/api` | .cc | 最新版 |
| `http://127.0.0.1:8000/api` | 开发机 | 另一个库、另一把密钥 |

- `.org` / `.cc` 是地区可达性；`www` / `next` 是**代码版本，不是数据环境**。
- 线上四个之间可以自动 fallback（同一套数据），**但绝不能自动退到 127.0.0.1**。
- 真正的风险不是写错库（写不错），而是写到不同版本的代码上，所以写入前要回显当前 api_url。
