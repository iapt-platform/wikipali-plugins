"""用户术语表的读写：my-terms / term-add / term-edit。

与只读的 `terms` 命令（社区权威译名表 v2/term-vocabulary）**不是一回事**：
这里走 v2/terms，是自己 studio / channel 名下、可增可改的术语。

写入沿用句子那条链路：Authorization 带模型身份 token，body 里带人类为该
channel 签出的 access token。因此 **AI 写术语必须落在某个 channel 里**——
access token 是 channel 级的，代持不了 studio 权限，不属于任何 channel 的
术语只有 studio 本人能改。
"""

import json

from client import WRITE_TIMEOUT, make_client
from cmd_write import (confirm, grant_access_token, pick_channel,
                       refresh_model_token)
from errors import ApiError, WpError, explain_api_error

# 术语没有 book 概念，access token 一律签「不限 book」
TERM_BOOK = 0

# 可增量提交的字段。word 单列，因为服务端要据它重算 word_en
EDITABLE = ('meaning', 'other_meaning', 'note', 'tag', 'language')


def emit(args, payload, render):
    if getattr(args, 'json', False):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        render()


# ---------------------------------------------------------------------------
# my-terms —— 列出自己的术语
# ---------------------------------------------------------------------------


def cmd_my_terms(args):
    client = make_client(args)
    token = client.user_token

    if args.channel:
        uid, name = pick_channel(client, args.channel)
        query = {'view': 'channel', 'id': uid}
        scope = f'channel {name or uid}'
    elif args.studio:
        query = {'view': 'studio', 'name': args.studio}
        scope = f'studio {args.studio}'
    else:
        query = {'view': 'user'}
        scope = '当前账号名下全部'

    query.update({
        'search': args.keyword,
        'order': args.order,
        'dir': args.dir,
        'offset': args.offset,
        'limit': args.limit,
    })
    try:
        data = client.call('GET', 'v2/terms', token=token, query=query, timeout=60)
    except ApiError as exc:
        raise explain_api_error(exc, f'列出术语（{scope}）')

    rows = (data or {}).get('rows') or []
    total = (data or {}).get('count', len(rows))
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
            ch = f'  ({ch})' if ch else ''
            print(f'  {r.get("guid", "")[:8]}  {str(r.get("word"))[:28]:<30} '
                  f'{r.get("meaning")}{other}{tag}{ch}')
        if total > len(rows) + args.offset:
            print(f'\n  …… 服务端还有更多（--offset/--limit 翻页）')
        print('\n开头 8 位是 guid 前缀，改术语用完整 guid：wikipali term-edit <guid>')

    emit(args, rows, render)
    return 0


# ---------------------------------------------------------------------------
# 写入共用
# ---------------------------------------------------------------------------


def term_by_guid(client, guid):
    try:
        return client.call('GET', f'v2/terms/{guid}', token=client.user_token, timeout=60)
    except ApiError as exc:
        if exc.status == 404 or '没有查询到' in str(exc):
            raise WpError(f'找不到术语 {guid}。guid 要给完整的，用 wikipali my-terms 查。')
        raise explain_api_error(exc, f'读取术语 {guid}')


def post_as_model(client, method, path, body, what):
    """以模型身份发写请求；模型 token 被拒时重签一次再试。"""
    model = client.model
    token = model['token']
    try:
        return client.call(method, path, token=token, body=body, timeout=WRITE_TIMEOUT)
    except ApiError as exc:
        if exc.status == 401:
            token = refresh_model_token(client)
            try:
                return client.call(method, path, token=token, body=body, timeout=WRITE_TIMEOUT)
            except ApiError as retry_exc:
                raise explain_api_error(retry_exc, f'{what}（已重签模型 token 后重试）')
        if exc.status == 403:
            raise WpError(
                f'{what}：403 无权限。可能的原因：\n'
                '  · 人类账号对这个 channel 没有编辑权（让 owner 授予 ≥ editor）；\n'
                '  · access token 签给了别的 channel；\n'
                '  · 目标术语不属于任何 channel——AI 只能改 channel 内的术语。'
            )
        if exc.status == 200 and 'existed' in str(exc):
            raise WpError(
                f'{what}：该 channel 下已有同 word + tag 的术语。\n'
                '要改就用 wikipali term-edit <guid>；先用 my-terms 找到它的 guid。'
            )
        raise explain_api_error(exc, what)


def print_header(client, model, channel_name, channel_uid):
    print('=' * 72)
    print(f'API      : {client.api_note()}')
    print(f'channel  : {channel_name or "(未知)"}  {channel_uid}')
    print(f'模型身份 : {model.get("name")}  uid={model.get("uid")}')
    print('-' * 72)


def report_saved(saved):
    editor = (saved.get('editor') or {}).get('nickName') or (saved.get('editor') or {}).get('name')
    print(f'guid     : {saved.get("guid")}')
    print(f'署名核对 : editor = {editor}')


# ---------------------------------------------------------------------------
# term-add —— 新建术语
# ---------------------------------------------------------------------------


def cmd_term_add(args):
    client = make_client(args)
    client.user_token
    model = client.model

    uid, name = pick_channel(client, args.channel)
    print_header(client, model, name, uid)
    print(f'  word          : {args.word}')
    print(f'  meaning       : {args.meaning}')
    for label, value in (('other_meaning', args.other_meaning), ('tag', args.tag),
                         ('language', args.language)):
        if value:
            print(f'  {label:<14}: {value}')
    if args.note:
        first = args.note.splitlines()[0] if args.note.splitlines() else ''
        more = '' if len(args.note.splitlines()) <= 1 else f'（共 {len(args.note)} 字符）'
        print(f'  note          : {first[:50]}{more}')
    print('-' * 72)
    print('⚠ 同 channel 下 word + tag 相同的术语已存在时，服务端会拒绝而不是覆盖。')
    print('=' * 72)

    if args.dry_run:
        print('--dry-run：未发送任何请求。')
        return 0
    if not args.yes and not confirm('确认新建？'):
        print('已取消，未写入任何内容。')
        return 1

    access = grant_access_token(client, uid, name, TERM_BOOK)
    body = {
        'word': args.word,
        'meaning': args.meaning,
        'channel': uid,
        'access_token': access['token'],
    }
    for field, value in (('other_meaning', args.other_meaning), ('note', args.note),
                         ('tag', args.tag), ('language', args.language)):
        if value is not None:
            body[field] = value

    saved = post_as_model(client, 'POST', 'v2/terms', body, '新建术语')
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

    old = term_by_guid(client, args.guid)
    channel_uid = old.get('channel_id') or old.get('channal')
    if not channel_uid:
        raise WpError(
            f'术语 {args.guid}（{old.get("word")}）不属于任何 channel，AI 改不了。\n'
            'access token 是 channel 级的，代持不了 studio 权限——这类术语只能由\n'
            'studio 本人在网站上修改。'
        )
    channel_name = (old.get('channel') or {}).get('name')

    # 只提交显式给出的字段：服务端是增量更新，没提交的保持原值
    patch = {}
    if args.word is not None:
        patch['word'] = args.word
    for field in EDITABLE:
        value = getattr(args, field, None)
        if value is not None:
            patch[field] = value
    if not patch:
        raise WpError('没有要改的字段。至少给一个：--word/--meaning/--other-meaning/--note/--tag/--language')

    # 与原值相同的字段不必提交，也别在回显里冒充改动
    unchanged = [f for f, v in patch.items() if (old.get(f) or '') == (v or '')]
    for field in unchanged:
        del patch[field]
    if not patch:
        raise WpError('提交的字段与原值完全相同，无需修改。')

    print_header(client, model, channel_name, channel_uid)
    print(f'  guid : {args.guid}')
    print(f'  word : {old.get("word")}')
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

    access = grant_access_token(client, channel_uid, channel_name, TERM_BOOK)
    body = dict(patch)
    body['access_token'] = access['token']

    saved = post_as_model(client, 'PUT', f'v2/terms/{args.guid}', body, '修改术语')
    print('-' * 72)
    print(f'已修改：{saved.get("word")} — {saved.get("meaning")}')
    report_saved(saved)
    return 0


def fmt_value(value):
    if value is None or value == '':
        return '(空)'
    text = str(value).replace('\n', ' ⏎ ')
    return text if len(text) <= 60 else text[:60] + '…'
