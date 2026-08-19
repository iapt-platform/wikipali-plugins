"""句子批注（discussion）的读写：discuss list / add / reply。

批注挂在**某一句**上：`res_type = 'sentence'`、`res_id = sentences.uid`。
uid 是逐句、逐 channel 的——同一段巴利原文和它的中译是两条不同的句子、两个
不同的 uid，所以「挂在哪一句上」必须先解析清楚再写，挂错地方比写错内容更难
发现。

与句子、术语不同，批注**不需要 access token**：服务端建批注只要求有一个有效
身份，不查 channel 权限，`editor_uid` 直接记当前身份。所以模型拿自己的 token
就能建、就能正确署名。
"""

import json

from client import WRITE_TIMEOUT, make_client
from cmd_read import PALI_CHANNEL, READ_TIMEOUT, strip_markup
from cmd_write import confirm, pick_channel, refresh_model_token
from coords import fmt_coord, parse_coord
from errors import ApiError, WpError, explain_api_error

RES_TYPE = 'sentence'
# qa / help 是文章场景，句子批注固定用 discussion
DISCUSS_TYPE = 'discussion'


def emit(args, payload, render):
    if getattr(args, 'json', False):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        render()


def call_as_model(client, method, path, what, body=None, query=None, timeout=READ_TIMEOUT):
    """以模型身份调用；模型 token 被拒时重签一次再试。"""
    token = client.model['token']
    try:
        return client.call(method, path, token=token, body=body, query=query, timeout=timeout)
    except ApiError as exc:
        if exc.status != 401:
            raise explain_api_error(exc, what)
        token = refresh_model_token(client)
        try:
            return client.call(method, path, token=token, body=body, query=query, timeout=timeout)
        except ApiError as retry_exc:
            raise explain_api_error(retry_exc, f'{what}（已重签模型 token 后重试）')


# ---------------------------------------------------------------------------
# 坐标 → 句子 uid
# ---------------------------------------------------------------------------


def resolve_channel(client, given):
    """把 --channel 的值化成 uid。uuid 直接用，否则按可编辑列表里的名字找。"""
    if not given:
        return PALI_CHANNEL, '巴利原文'
    if len(given) >= 32 and given.count('-') == 4:
        return given, None
    return pick_channel(client, given)


def resolve_sentence(args, client):
    """定位要批注的那一句，返回 (uid, 回显用的描述)。

    给 --sent 就直接用；否则按坐标 + channel 查，命中多于一句时**不猜**。
    """
    if getattr(args, 'sent', None):
        return args.sent, f'句子 {args.sent}'

    if not getattr(args, 'coord', None):
        raise WpError('要么给坐标（如 216:35），要么用 --sent <句子uid> 直接指定。')

    book, para = parse_coord(args.coord)
    channel_uid, channel_name = resolve_channel(client, args.channel)
    try:
        data = client.call('GET', 'v2/sentence',
                           query={'view': 'paragraph', 'book': book, 'para': para,
                                  'channels': channel_uid, 'limit': 200},
                           timeout=READ_TIMEOUT)
    except ApiError as exc:
        raise explain_api_error(exc, f'取 {args.coord} 的句子')
    rows = (data or {}).get('rows') or []
    if not rows:
        raise WpError(
            f'{fmt_coord(book, para)} 在该 channel 下没有句子，无法批注。\n'
            '这是「该 channel 在此处没有文本」，不是查询失败——换个 channel，或先确认坐标。'
        )

    if getattr(args, 'words', None):
        try:
            start, end = (int(x) for x in args.words.split('-', 1))
        except ValueError:
            raise WpError('--words 的格式是 起-止，如 2-17')
        rows = [r for r in rows
                if int(r.get('word_start', -1)) == start and int(r.get('word_end', -1)) == end]
        if not rows:
            raise WpError(f'{fmt_coord(book, para)} 下没有 [{args.words}] 这一句。')

    if len(rows) > 1:
        lines = [f'{fmt_coord(book, para)} 有 {len(rows)} 句，指明是哪一句再批注：']
        for r in rows:
            lines.append(f'  --words {r.get("word_start")}-{r.get("word_end")}   '
                         f'{strip_markup(r.get("content"))[:60]}')
        lines.append('  也可以用 --sent <句子uid> 直接指定。')
        raise WpError('\n'.join(lines))

    row = rows[0]
    ch = row.get('channel') or {}
    desc = (f'{fmt_coord(book, para)} [{row.get("word_start")}-{row.get("word_end")}]  '
            f'{ch.get("name") or channel_name or ""}\n'
            f'    {strip_markup(row.get("content"))[:100]}')
    return row.get('id'), desc


# ---------------------------------------------------------------------------
# discuss list
# ---------------------------------------------------------------------------


def fetch_replies(client, topic_id):
    data = call_as_model(client, 'GET', 'v2/discussion', '取批注的回复',
                         query={'view': 'answer', 'id': topic_id,
                                'status': 'active', 'limit': 200})
    return (data or {}).get('rows') or []


def cmd_discuss_list(args):
    client = make_client(args)
    client.model
    sent_uid, desc = resolve_sentence(args, client)

    data = call_as_model(client, 'GET', 'v2/discussion', '列出批注',
                         query={'view': 'question', 'res_type': RES_TYPE, 'id': sent_uid,
                                'type': DISCUSS_TYPE, 'status': args.status,
                                'limit': args.limit, 'offset': args.offset})
    rows = (data or {}).get('rows') or []
    for row in rows:
        row['replies'] = fetch_replies(client, row['id']) if row.get('children_count') else []

    def render():
        print(f'批注对象：{desc}')
        print(f'句子 uid：{sent_uid}')
        active = (data or {}).get('active', 0)
        close = (data or {}).get('close', 0)
        print(f'话题：{len(rows)} 条（active {active} / close {close}）')
        if not rows:
            print('\n这一句还没有批注。')
            return
        for row in rows:
            print('\n' + '-' * 72)
            print(f'  id     : {row.get("id")}')
            print(f'  标题   : {row.get("title")}')
            print(f'  作者   : {who(row)}   {row.get("status")}   {row.get("created_at", "")[:10]}')
            for line in (row.get('content') or '').splitlines():
                print(f'  | {line}')
            for reply in row['replies']:
                print(f'    ↳ {who(reply)}  {reply.get("created_at", "")[:10]}')
                for line in (reply.get('content') or '').splitlines():
                    print(f'      | {line}')
        print('\n' + '-' * 72)
        print('回复某条：wikipali discuss-reply <id> --content "…"')

    emit(args, rows, render)
    return 0


def who(row):
    editor = row.get('editor') or {}
    name = editor.get('nickName') or editor.get('userName') or '(未知)'
    return f'{name}（AI）' if 'ai' in (editor.get('roles') or []) else name


# ---------------------------------------------------------------------------
# discuss add / reply
# ---------------------------------------------------------------------------


def create(client, args, body, header_lines, what):
    print('=' * 72)
    print(f'API      : {client.api_note()}')
    model = client.model
    print(f'模型身份 : {model.get("name")}  uid={model.get("uid")}')
    for line in header_lines:
        print(line)
    print('-' * 72)
    if body.get('title'):
        print(f'  标题 : {body["title"]}')
    for line in (body.get('content') or '').splitlines():
        print(f'  | {line}')
    print('-' * 72)
    print('通知     : ' + ('会发站内通知' if body.get('notification') else '不发（--notify 可开）'))
    print('=' * 72)

    if args.dry_run:
        print('--dry-run：未发送任何请求。')
        return 0
    if not args.yes and not confirm('确认提交？'):
        print('已取消，未写入任何内容。')
        return 1

    saved = call_as_model(client, 'POST', 'v2/discussion', what,
                          body=body, timeout=WRITE_TIMEOUT)
    print('-' * 72)
    print(f'已提交：{saved.get("id")}')
    print(f'署名核对：editor = {who(saved)}')
    return 0


def cmd_discuss_add(args):
    client = make_client(args)
    client.model
    sent_uid, desc = resolve_sentence(args, client)
    content = read_content(args)

    body = {
        'res_id': sent_uid,
        'res_type': RES_TYPE,
        'type': DISCUSS_TYPE,
        'title': args.title,
        'content': content,
        'content_type': args.content_type,
        'notification': bool(args.notify),
    }
    header = [f'批注对象 : {desc}', f'句子 uid : {sent_uid}']
    return create(client, args, body, header, '新建批注')


def cmd_discuss_reply(args):
    client = make_client(args)
    client.model
    content = read_content(args)

    body = {
        'parent': args.id,
        'content': content,
        'content_type': args.content_type,
        'notification': bool(args.notify),
    }
    # res_id / res_type 由服务端从 parent 继承，不用（也不该）自己给
    header = [f'回复      : {args.id}']
    return create(client, args, body, header, '回复批注')


def read_content(args):
    if args.content == '-':
        import sys
        content = sys.stdin.read()
    elif args.content_file:
        try:
            with open(args.content_file, encoding='utf-8') as fh:
                content = fh.read()
        except OSError as exc:
            raise WpError(f'读不了内容文件：{exc}')
    else:
        content = args.content
    if not content or not content.strip():
        raise WpError('批注内容为空。用 --content "…"、--content-file <文件>，或 --content - 从 stdin 读。')
    return content
