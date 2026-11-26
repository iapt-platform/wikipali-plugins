"""用户术语表的读写：my-terms / term-add / term-edit。

与只读的 `terms` 命令（社区权威译名表 v3/glossaries）**不是一回事**：
这里走 v3 术语接口（`/v3/terms`、`/v3/channels/{c}/terms`、`/v3/studios/{s}/terms`），
是自己 studio / channel 名下、可增可改的术语。

写入走 agent 协作：人类用自己的登录 token 为本机模型签一张 channel 授权
（`POST /v3/agent-grants`，与批注共用，见 cmd_discuss.agent_grant），模型用模型 token 写、
请求头带 `X-Agent-Grant`。记录上 editor 是授权人、co_editor 是模型。因此 **AI 写术语必须落在
某个 channel 里**：授权是 channel 级的；不属于任何 channel 的 studio 级术语只能由人在网站上改。

v3 的两条规矩：
- **word + tag 建立后不能改**（引用方写 `[[word@tag]]`）。要改就新建一条，把旧的 `--redirect` 过去。
- 修改带乐观锁：先读到 `etag`，修改时放进 `If-Match`；期间被别人改过服务端回 412，要重新读再改。
"""

import json

from client import WRITE_TIMEOUT, make_client, note
from cmd_discuss import GRANT_HEADER, agent_grant, call_as_model
from cmd_write import confirm, pick_channel
from errors import ApiError, WpError, explain_api_error

# 术语不属于某本书：授权一律签「不限 book」（按 book 限定的授权服务端不认）
TERM_BOOK = 0

QUALITIES = ('featured', 'standard', 'draft', 'pending')
CONTENT_TYPES = ('markdown-e2', 'markdown')

# 可增量提交的字段（v3 PATCH 只改传了的）
EDITABLE = ('meaning', 'other_meaning', 'note', 'summary', 'quality', 'content_type', 'redirect')


def emit(args, payload, render):
    if getattr(args, 'json', False):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        render()


def is_uuid(value):
    return bool(value) and len(value) >= 32 and value.count('-') == 4


# ---------------------------------------------------------------------------
# my-terms —— 列出自己的术语
# ---------------------------------------------------------------------------


def my_id(client):
    me = client.call('GET', 'v3/me', token=client.user_token, v3=True, timeout=60) or {}
    if not me.get('id'):
        raise WpError('读取当前账号失败（v3/me 没有返回 id）。重新登录：wikipali-login')
    return me


def resolve_studio(client, given):
    """--studio 的值化成 uuid：uuid 直接用；自己的用户名 → 本人；否则在「我所在的团队」里按名字找。"""
    if is_uuid(given):
        return given, given
    me = my_id(client)
    if given in (me.get('userName'), me.get('realName'), me.get('nickName')):
        return me['id'], given
    groups = client.call('GET', 'v3/me/groups', token=client.user_token, v3=True, timeout=60,
                         query={'search': given, 'per_page': 50}) or []
    hits = [g for g in groups if g.get('name') == given] or [g for g in groups if given in (g.get('name') or '')]
    if len(hits) != 1:
        raise WpError(f'找不到唯一的 studio「{given}」（命中 {len(hits)} 个）。给 uuid，或用自己的用户名 / 团队全名。')
    return hits[0]['id'], hits[0].get('name') or given


def cmd_my_terms(args):
    client = make_client(args)
    token = client.user_token

    if args.channel:
        uid, name = pick_channel(client, args.channel)
        path = f'v3/channels/{uid}/terms'
        scope = f'channel {name or uid}'
    else:
        if args.studio:
            studio, label = resolve_studio(client, args.studio)
            scope = f'studio {label}'
        else:
            studio = my_id(client)['id']
            scope = '当前账号名下全部'
        path = f'v3/studios/{studio}/terms'

    per_page = max(1, min(args.limit, 200))
    query = {
        'search': args.keyword,
        'order': args.order,
        'dir': args.dir,
        'per_page': per_page,
        'page': args.offset // per_page + 1,
    }
    try:
        payload = client.call('GET', path, token=token, query=query, v3=True, envelope=True, timeout=60) or {}
    except ApiError as exc:
        raise explain_api_error(exc, f'列出术语（{scope}）')

    rows = payload.get('data') or []
    total = (payload.get('meta') or {}).get('total', len(rows))
    if args.tag:
        rows = [r for r in rows if args.tag.lower() in (r.get('tag') or '').lower()]

    def render():
        if not rows:
            print(f'{scope}：没有术语'
                  + (f'（关键词「{args.keyword}」）' if args.keyword else '')
                  + '。')
            print('注意这查的是**你自己的**术语表；社区权威译名表是另一个命令：wikipali terms')
            return
        print(f'{scope}：{len(rows)} 条（服务端合计 {total}）\n')
        for r in rows:
            tag = f'  [{r.get("tag")}]' if r.get('tag') else ''
            other = f'  / {r["other_meaning"]}' if r.get('other_meaning') else ''
            ch = (r.get('channel') or {}).get('name') or ''
            ch = f'  ({ch})' if ch else '  (studio 通用)'
            quality = f'  <{r["quality"]}>' if r.get('quality') else ''
            print(f'  {r.get("id", "")[:8]}  {str(r.get("word"))[:28]:<30} '
                  f'{r.get("meaning")}{other}{tag}{quality}{ch}')
        if total > len(rows) + args.offset:
            print('\n  …… 服务端还有更多（--offset/--limit 翻页）')
        print('\n开头 8 位是 guid 前缀，改术语用完整 guid：wikipali term-edit <guid>（--json 拿完整值）')

    emit(args, rows, render)
    return 0


# ---------------------------------------------------------------------------
# 写入共用
# ---------------------------------------------------------------------------


def term_by_guid(client, guid):
    try:
        return client.call('GET', f'v3/terms/{guid}', token=client.user_token, v3=True, timeout=60)
    except ApiError as exc:
        if exc.status == 404:
            raise WpError(f'找不到术语 {guid}。guid 要给完整的，用 wikipali my-terms --json 查。')
        raise explain_api_error(exc, f'读取术语 {guid}')


def write_as_agent(client, method, path, what, channel_uid, body, extra_headers=None):
    """以模型身份、带人类授权写术语。授权被拒（过期 / 撤销）时重签一次再试。

    出错信息都以 `HTTP <状态码>` 开头（errors.ApiError），按它分辨 412 / 403。
    """
    def go(force):
        headers = {GRANT_HEADER: agent_grant(client, channel_uid, TERM_BOOK, force=force)}
        headers.update(extra_headers or {})
        return call_as_model(client, method, path, what, body=body, timeout=WRITE_TIMEOUT,
                             headers=headers)

    try:
        return go(False)
    except WpError as exc:
        if 'HTTP 412' in str(exc):
            raise WpError(
                f'{what}：这条术语在你读取之后被别人改过（HTTP 412）。重新运行本命令，'
                '会读到最新的内容再改；不要直接覆盖别人的修改。'
            )
        if 'HTTP 403' not in str(exc):
            raise
        note('⚠ 写入被拒，重新签发授权后再试一次……')
        try:
            return go(True)
        except WpError as retry:
            raise WpError(
                f'{retry}\n可能的原因：\n'
                '  · 人类账号对这个 channel 没有编辑权（让 owner 授予 ≥ editor）；\n'
                '  · 目标术语不属于任何 channel——AI 只能写 channel 内的术语。'
            )


def print_header(client, model, channel_name, channel_uid):
    print('=' * 72)
    print(f'API      : {client.api_note()}')
    print(f'channel  : {channel_name or "(未知)"}  {channel_uid}')
    print(f'模型身份 : {model.get("name")}  uid={model.get("uid")}')
    print('-' * 72)


def report_saved(saved):
    editor = (saved.get('editor') or {}).get('nickName')
    co_editor = (saved.get('co_editor') or {}).get('nickName')
    print(f'guid     : {saved.get("id")}')
    print(f'署名核对 : editor = {editor}' + (f'，co_editor = {co_editor}' if co_editor else ''))
    if saved.get('categories'):
        print(f'分类     : {", ".join(saved["categories"])}（取自 note 里的 {{{{category|…}}}}）')


def check_choices(args):
    quality = getattr(args, 'quality', None)
    if quality not in (None, '') and quality not in QUALITIES:
        raise WpError(f'--quality 只能是 {" / ".join(QUALITIES)}（给空串清掉）。')
    content_type = getattr(args, 'content_type', None)
    if content_type is not None and content_type not in CONTENT_TYPES:
        raise WpError(f'--content-type 只能是 {" / ".join(CONTENT_TYPES)}。')


def empty_to_none(value):
    """命令行给空串 = 清掉这个字段。"""
    return None if value == '' else value


def preview(label, value):
    lines = value.splitlines()
    more = '' if len(lines) <= 1 else f'（共 {len(value)} 字符）'
    print(f'  {label:<14}: {(lines[0] if lines else "")[:50]}{more}')


# ---------------------------------------------------------------------------
# term-add —— 新建术语
# ---------------------------------------------------------------------------


def cmd_term_add(args):
    client = make_client(args)
    client.user_token
    model = client.model
    check_choices(args)

    uid, name = pick_channel(client, args.channel)
    print_header(client, model, name, uid)
    print(f'  word          : {args.word}')
    print(f'  meaning       : {args.meaning}')
    for label, value in (('tag', args.tag), ('other_meaning', args.other_meaning),
                         ('quality', args.quality), ('content_type', args.content_type),
                         ('redirect', args.redirect)):
        if value:
            print(f'  {label:<14}: {value}')
    for label, value in (('summary', args.summary), ('note', args.note)):
        if value:
            preview(label, value)
    print('-' * 72)
    if args.language:
        print(f'⚠ --language {args.language} 不提交：channel 里的术语语言跟随 channel。')
    print('⚠ 同 channel 下 word + tag 相同的术语已存在时，服务端会拒绝（409）而不是覆盖。')
    print('⚠ word + tag 建立后不能改；拼写拿不准就先 --dry-run 核对。')
    print('=' * 72)

    if args.dry_run:
        print('--dry-run：未发送任何请求。')
        return 0
    if not args.yes and not confirm('确认新建？'):
        print('已取消，未写入任何内容。')
        return 1

    body = {'word': args.word, 'meaning': args.meaning}
    for field in ('tag', 'other_meaning', 'note', 'summary', 'quality', 'content_type', 'redirect'):
        value = getattr(args, field, None)
        if value not in (None, ''):
            body[field] = value

    try:
        saved = write_as_agent(client, 'POST', f'v3/channels/{uid}/terms', '新建术语', uid, body)
    except WpError as exc:
        if 'HTTP 409' in str(exc):
            raise WpError(
                f'新建术语：该 channel 下已有同 word + tag 的术语（{exc}）。\n'
                '要改就用 wikipali term-edit <guid>；先用 my-terms 找到它的 guid。'
            )
        raise
    print('-' * 72)
    print(f'已新建：{saved.get("word")} — {saved.get("meaning")}')
    report_saved(saved)
    return 0


# ---------------------------------------------------------------------------
# term-edit —— 修改术语
# ---------------------------------------------------------------------------


def cmd_term_edit(args):
    client = make_client(args)
    client.user_token
    model = client.model
    check_choices(args)

    if args.word is not None or args.tag is not None:
        raise WpError(
            'word 与 tag 建立后不能改（引用方写的是 [[word@tag]]，改了会失效）。\n'
            '要换拼写或义项：用 term-add 新建一条，再把这一条重定向过去：\n'
            f'  wikipali term-edit {args.guid} --redirect <新word>@<新tag>'
        )

    old = term_by_guid(client, args.guid)
    channel_uid = old.get('channel_id')
    if not channel_uid:
        raise WpError(
            f'术语 {args.guid}（{old.get("word")}）不属于任何 channel，AI 改不了。\n'
            '写入授权是 channel 级的，代持不了 studio 权限——这类术语只能由\n'
            'studio 本人在网站上修改。'
        )
    if args.language is not None:
        raise WpError('channel 里的术语语言跟随 channel，不能单独修改。')
    channel_name = (old.get('channel') or {}).get('name')

    # 只提交显式给出的字段：服务端只改传了的，没提交的保持原值。空串 = 清掉
    patch = {}
    for field in EDITABLE:
        value = getattr(args, field, None)
        if value is not None:
            patch[field] = empty_to_none(value)
    if not patch:
        raise WpError('没有要改的字段。至少给一个：--meaning/--other-meaning/--note/--summary/'
                      '--quality/--content-type/--redirect')

    # 与原值相同的字段不必提交，也别在回显里冒充改动
    unchanged = [f for f, v in patch.items() if (old.get(f) or '') == (v or '')]
    for field in unchanged:
        del patch[field]
    if not patch:
        raise WpError('提交的字段与原值完全相同，无需修改。')

    print_header(client, model, channel_name, channel_uid)
    print(f'  guid : {args.guid}')
    print(f'  word : {old.get("word")}' + (f'@{old["tag"]}' if old.get('tag') else ''))
    print('-' * 72)
    for field, value in patch.items():
        print(f'  {field}')
        print(f'    旧 : {fmt_value(old.get(field))}')
        print(f'    新 : {fmt_value(value)}')
    if unchanged:
        print(f'  （与原值相同、不提交：{", ".join(unchanged)}）')
    print('=' * 72)

    if args.dry_run:
        print('--dry-run：未发送任何请求。')
        return 0
    if not args.yes and not confirm('确认修改？'):
        print('已取消，未改动任何内容。')
        return 1

    saved = write_as_agent(client, 'PATCH', f'v3/terms/{args.guid}', '修改术语', channel_uid, patch,
                           extra_headers={'If-Match': old.get('etag') or ''})
    print('-' * 72)
    print(f'已修改：{saved.get("word")} — {saved.get("meaning")}')
    report_saved(saved)
    return 0


def fmt_value(value):
    if value is None or value == '':
        return '(空)'
    text = str(value).replace('\n', ' ⏎ ')
    return text if len(text) <= 60 else text[:60] + '…'
