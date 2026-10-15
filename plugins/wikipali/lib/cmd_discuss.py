"""句子批注（discussion）的读写：discuss list / add / reply / edit / delete。走 v3 `/v3/discussions`。

批注挂在**某一句**上：`target_type = 'sentence'`、`target_id = sentences.uid`。
uid 是逐句、逐 channel 的——同一段巴利原文和它的中译是两条不同的句子、两个
不同的 uid，所以「挂在哪一句上」必须先解析清楚再写，挂错地方比写错内容更难
发现。

**写入要人类授权**（v3 的 agent 协作，见 mint 仓库 CLAUDE.md「agent 协作」）：
人类用自己的登录 token 调 `POST /v3/agent-grants`，给本机的模型签一张「某 channel、
某 book」的写入授权；模型用模型 token 登录，写入时带请求头 `X-Agent-Grant`。
服务端记 editor = 授权人（对内容负责的人）、co_editor = 模型，权限按授权人判断，
只能写授权覆盖的 channel / book 里的句子上的批注。授权按 (channel, book) 缓存在凭据文件里，7 天有效。
读（列表、单条、回复）只要模型 token，不要授权。
"""

import json
import time

from client import TOKEN_REFRESH_MARGIN, WRITE_TIMEOUT, make_client, note, token_expiry
from cmd_read import READ_TIMEOUT, pali_channel, row_text
from cmd_write import confirm, iso_now, pick_channel, refresh_model_token
from coords import fmt_coord, parse_coord
from errors import ApiError, WpError, explain_api_error

TARGET_TYPE = 'sentence'
GRANT_HEADER = 'X-Agent-Grant'
# 句子上的六类批注（按用户的说法选，见 skills/write）：
#   note        批注 / 脚注——正文就是注解本身
#   commentary  注释对照 / 义注对照 / 复注对照——正文是下一层句子模板，见 cmd_notes
#   discussion  审稿意见 / 讨论（默认）
#   qa          问答
#   help        求助
#   issue       问题报告（错误 / 待修）
# 锚点只有批注（note / commentary）收；它们会被注入阅读页
# （api-v13 的 PaliContentService::injectAnnotationNotes），其余四类只在批注列表里，
# 而且必须有标题。v3 不带 type 列表时只列后三类（评论线程），批注要显式 --type。
DISCUSS_TYPES = ['note', 'commentary', 'discussion', 'qa', 'help', 'issue']
ANNOTATION_TYPES = ['note', 'commentary']
# 严重 / 紧急程度，取值随 type（与 api-v13 Discussion::SEVERITIES 一致），其余类型不收
SEVERITIES = {'issue': ['error', 'warning', 'suggestion'], 'help': ['urgent', 'normal']}
SEVERITY_CHOICES = sorted({v for values in SEVERITIES.values() for v in values})


def check_severity(type_, severity):
    if severity is None:
        return
    allowed = SEVERITIES.get(type_, [])
    if severity not in allowed:
        raise WpError(f'--severity {severity} 不适用于 {type_}：'
                      + (f'可选 {" / ".join(allowed)}' if allowed else '这一类没有严重程度'))
DISCUSS_TYPE = 'discussion'
ANCHOR_FIELDS = ['pos_start', 'pos_end', 'quote_exact', 'quote_prefix', 'quote_suffix']


def emit(args, payload, render):
    if getattr(args, 'json', False):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        render()


def call_as_model(client, method, path, what, body=None, query=None, timeout=READ_TIMEOUT,
                  headers=None, envelope=False):
    """以模型身份调 v3；模型 token 被拒时重签一次再试。"""
    def go(token):
        return client.call(method, path, token=token, body=body, query=query, timeout=timeout,
                           v3=True, headers=headers, envelope=envelope)

    try:
        return go(client.model['token'])
    except ApiError as exc:
        if exc.status != 401:
            raise explain_discuss_error(exc, what)
        token = refresh_model_token(client)
        try:
            return go(token)
        except ApiError as retry_exc:
            raise explain_discuss_error(retry_exc, f'{what}（已重签模型 token 后重试）')


def explain_discuss_error(exc, what):
    """403 / 409 / 422 带上服务端的说明（v3 Problem 的 detail），其余按通用口径。"""
    if exc.status in (403, 409, 422):
        return WpError(f'{what}：HTTP {exc.status} {exc}')
    return explain_api_error(exc, what)


def sentence_scope(client, sent_uid):
    """句子所在的 (channel uid, book)——agent 授权按这两样划范围。"""
    try:
        data = client.call('GET', f'v2/sentence/{sent_uid}', timeout=READ_TIMEOUT)
    except ApiError as exc:
        raise explain_api_error(exc, f'取句子 {sent_uid}')
    channel = (data or {}).get('channel') or {}
    if not channel.get('id'):
        raise WpError(f'句子 {sent_uid} 查不到所在的 channel，无法申请写入授权。')
    return channel['id'], int(data.get('book') or 0)


def agent_grant(client, channel_uid, book, force=False):
    """取（或签发）本机模型在 (channel, book) 上的写入授权，缓存在凭据文件里。"""
    key = f'{channel_uid}:{book}'
    cache = client.bucket.setdefault('agent_grants', {})
    item = cache.get(key)
    if item and not force:
        exp = item.get('exp') or token_expiry(item['token'])
        if exp and exp - time.time() > TOKEN_REFRESH_MARGIN:
            return item['token']

    model = client.model
    try:
        data = client.call('POST', 'v3/agent-grants', token=client.user_token, v3=True, body={
            'ai_model': model['uid'], 'target_type': 'channel', 'target_id': channel_uid, 'book': book,
        })
    except ApiError as exc:
        if exc.status == 403:
            raise WpError(
                f'签发写入授权：403 {exc}\n'
                f'当前登录账号对 channel {channel_uid} 没有编辑权，或模型 {model.get("name")} 不归它所有。\n'
                '不要继续写入。确认选对了 channel，或让 owner 授予编辑权限。'
            )
        raise explain_discuss_error(exc, '签发写入授权')
    cache[key] = {'token': data['token'], 'exp': token_expiry(data['token']), 'granted_at': iso_now()}
    client.save()
    return data['token']


def call_as_agent(client, method, path, what, scope, body=None, timeout=WRITE_TIMEOUT):
    """以模型身份、带人类授权写 v3。授权被拒（过期 / 撤销）时重签一次再试。"""
    channel_uid, book = scope
    try:
        return call_as_model(client, method, path, what, body=body, timeout=timeout,
                             headers={GRANT_HEADER: agent_grant(client, channel_uid, book)})
    except WpError as exc:
        if 'HTTP 403' not in str(exc):
            raise
        note('⚠ 写入授权被拒，重新签发后再试一次……')
        return call_as_model(client, method, path, what, body=body, timeout=timeout,
                             headers={GRANT_HEADER: agent_grant(client, channel_uid, book, force=True)})


# ---------------------------------------------------------------------------
# 坐标 → 句子 uid
# ---------------------------------------------------------------------------


def resolve_channel(client, given):
    """把 --channel 的值化成 uid。uuid 直接用，否则按可编辑列表里的名字找。"""
    if not given:
        return pali_channel(client), '巴利原文'
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
                         f'{row_text(r)[:60]}')
        lines.append('  也可以用 --sent <句子uid> 直接指定。')
        raise WpError('\n'.join(lines))

    row = rows[0]
    ch = row.get('channel') or {}
    desc = (f'{fmt_coord(book, para)} [{row.get("word_start")}-{row.get("word_end")}]  '
            f'{ch.get("name") or channel_name or ""}\n'
            f'    {row_text(row)[:100]}')
    return row.get('id'), desc


# ---------------------------------------------------------------------------
# discuss list
# ---------------------------------------------------------------------------


def fetch_replies(client, topic_id):
    return call_as_model(client, 'GET', f'v3/discussions/{topic_id}/replies', '取批注的回复',
                         query={'per_page': 200}) or []


def cmd_discuss_list(args):
    client = make_client(args)
    client.model
    sent_uid, desc = resolve_sentence(args, client)

    target = {'target_type': TARGET_TYPE, 'target_id': sent_uid, 'type': args.type}
    page = call_as_model(client, 'GET', 'v3/discussions', '列出批注', envelope=True,
                         query={**target, 'status': args.status,
                                'per_page': args.limit, 'page': args.page}) or {}
    rows = page.get('data') or []
    summary = call_as_model(client, 'GET', 'v3/discussions/summary', '统计批注', query=target) or {}
    for row in rows:
        row['replies'] = fetch_replies(client, row['id']) if row.get('reply_count') else []

    def render():
        print(f'批注对象：{desc}')
        print(f'句子 uid：{sent_uid}')
        counts = summary.get('status_counts') or {}
        meta = page.get('meta') or {}
        print(f'话题：本页 {len(rows)} 条，第 {meta.get("current_page", 1)}/{meta.get("last_page", 1)} 页'
              f'（active {counts.get("active", 0)} / close {counts.get("close", 0)}）')
        if not rows:
            print('\n这一句还没有这一类批注。')
            return
        for row in rows:
            print('\n' + '-' * 72)
            print(f'  id     : {row.get("id")}')
            if row.get('title'):
                print(f'  标题   : {row.get("title")}')
            print(f'  作者   : {who(row)}   {row.get("status")}   {(row.get("created_at") or "")[:10]}')
            if fmt_anchor(row):
                print(f'  锚点   : {fmt_anchor(row)}')
            for line in (row.get('content') or '').splitlines():
                print(f'  | {line}')
            for reply in row['replies']:
                print(f'    ↳ {who(reply)}  {(reply.get("created_at") or "")[:10]}')
                for line in (reply.get('content') or '').splitlines():
                    print(f'      | {line}')
        print('\n' + '-' * 72)
        print('回复某条：wikipali discuss-reply <id> --content "…"')

    emit(args, rows, render)
    return 0


def fmt_anchor(row):
    if row.get('pos_start') is None and row.get('pos_end') is None and not row.get('quote_exact'):
        return ''
    text = f'[{row.get("pos_start")}-{row.get("pos_end")}]'
    if row.get('quote_exact'):
        text += f' 「{row.get("quote_exact")}」'
    return text


def anchor_body(args):
    """命令行给出的锚点字段。只收显式给了的——编辑时没给的字段要原样保留。"""
    body = {}
    for field in ANCHOR_FIELDS:
        value = getattr(args, field, None)
        if value is None:
            continue
        if field.startswith('pos_'):
            if value == '':
                value = None
            else:
                try:
                    value = int(value)
                except ValueError:
                    raise WpError(f'--{field.replace("_", "-")} 要给非负整数（给空串表示清空）')
                if value < 0:
                    raise WpError(f'--{field.replace("_", "-")} 不能为负')
        body[field] = value
    start, end = body.get('pos_start'), body.get('pos_end')
    if start is not None and end is not None and start > end:
        raise WpError('pos_start 不能大于 pos_end')
    return body


def actor_name(actor):
    actor = actor or {}
    return actor.get('nickName') or actor.get('userName') or '(未知)'


def who(row):
    """署名：AI 凭授权代写的显示「授权人（与 模型）」；v2 时期模型直接署名的显示「模型（AI）」。"""
    editor = row.get('editor') or {}
    if row.get('co_editor'):
        return f'{actor_name(editor)}（与 {actor_name(row["co_editor"])}）'
    return f'{actor_name(editor)}（AI）' if 'ai' in (editor.get('roles') or []) else actor_name(editor)


# ---------------------------------------------------------------------------
# discuss add / reply / edit / delete
# ---------------------------------------------------------------------------


def confirm_and_send(client, args, body, header_lines, what, method, path, scope):
    """回显将要写入的内容、确认后以模型身份 + 人类授权提交。"""
    print('=' * 72)
    print(f'API      : {client.api_note()}')
    model = client.model
    print(f'模型身份 : {model.get("name")}  uid={model.get("uid")}')
    print(f'授权范围 : channel {scope[0]}，book {scope[1]}（署名为授权人，模型记为协作者）')
    for line in header_lines:
        print(line)
    print('-' * 72)
    if body.get('title'):
        print(f'  标题 : {body["title"]}')
    if fmt_anchor(body):
        print(f'  锚点 : {fmt_anchor(body)}')
    for line in (body.get('content') or '').splitlines():
        print(f'  | {line}')
    if 'notify' in body:
        print('-' * 72)
        print('通知     : ' + ('会发站内通知' if body['notify'] else '不发（--notify 可开）'))
    print('=' * 72)

    if args.dry_run:
        print('--dry-run：未发送任何请求。')
        return None
    if not args.yes and not confirm('确认提交？'):
        print('已取消，未写入任何内容。')
        return None
    return call_as_agent(client, method, path, what, scope, body=body)


def report_saved(saved):
    print('-' * 72)
    print(f'已提交：{saved.get("id")}')
    print(f'署名核对：{who(saved)}')


def cmd_discuss_add(args):
    client = make_client(args)
    client.model
    sent_uid, desc = resolve_sentence(args, client)
    content = read_content(args)
    anchors = anchor_body(args)
    if args.type not in ANNOTATION_TYPES:
        if not args.title:
            raise WpError(f'{args.type} 类话题必须给 --title（审稿意见 / 问答 / 求助是要被列出来讨论的）。')
        if anchors:
            raise WpError('锚点（--pos-* / --quote-*）只有批注（note / commentary）收，'
                          f'{args.type} 是整句的话题。')

    check_severity(args.type, args.severity)

    body = {
        'target_type': TARGET_TYPE,
        'target_id': sent_uid,
        'type': args.type,
        'content': content,
        'notify': bool(args.notify),
        **anchors,
    }
    if args.title:
        body['title'] = args.title
    if args.severity:
        body['severity'] = args.severity
    header = [f'批注对象 : {desc}', f'句子 uid : {sent_uid}',
              f'类型     : {args.type}' + (f'（{args.severity}）' if args.severity else '')]
    saved = confirm_and_send(client, args, body, header, '新建批注', 'POST', 'v3/discussions',
                             sentence_scope(client, sent_uid))
    if saved is None:
        return 1 if not args.dry_run else 0
    report_saved(saved)
    return 0


def get_discussion(client, discussion_id):
    data = call_as_model(client, 'GET', f'v3/discussions/{discussion_id}', '取批注')
    if not data:
        raise WpError(f'找不到批注 {discussion_id}')
    return data


def cmd_discuss_reply(args):
    client = make_client(args)
    client.model
    content = read_content(args)
    topic = get_discussion(client, args.id)
    if topic.get('parent_id'):
        raise WpError(f'{args.id} 本身是一条回复；回复它所在的话题 {topic["parent_id"]}。')

    # 类型、挂靠对象由服务端从话题继承；回复只有正文
    body = {'content': content, 'notify': bool(args.notify)}
    header = [f'回复      : {args.id}（{topic.get("type")}）{topic.get("title") or ""}']
    saved = confirm_and_send(client, args, body, header, '回复批注', 'POST',
                             f'v3/discussions/{args.id}/replies',
                             sentence_scope(client, topic['target_id']))
    if saved is None:
        return 1 if not args.dry_run else 0
    report_saved(saved)
    return 0


def cmd_discuss_edit(args):
    """改一条批注 / 对应：只把改了的字段发出去（v3 是 PATCH，没传的字段原样保留）。"""
    client = make_client(args)
    client.model
    old = get_discussion(client, args.id)
    body = {}
    if args.title is not None and args.title != old.get('title'):
        body['title'] = args.title
    if args.content or args.content_file:
        content = read_content(args)
        if content != old.get('content'):
            body['content'] = content
    if args.status and args.status != old.get('status'):
        body['status'] = args.status
    if args.severity and args.severity != old.get('severity'):
        check_severity(old.get('type'), args.severity)
        body['severity'] = args.severity
    anchors = anchor_body(args)
    merged = {f: anchors.get(f, old.get(f)) for f in ANCHOR_FIELDS}
    if (merged['pos_start'] is not None and merged['pos_end'] is not None
            and merged['pos_start'] > merged['pos_end']):
        raise WpError('改完后 pos_start 大于 pos_end')
    body.update({f: v for f, v in anchors.items() if v != old.get(f)})
    if not body:
        print('没有要改的字段。')
        return 0
    header = [f'修改      : {args.id}（{old.get("type")}）',
              f'原锚点    : {fmt_anchor(old) or "（无）"}',
              f'改动字段  : {", ".join(body)}']
    saved = confirm_and_send(client, args, body, header, '修改批注', 'PATCH', f'v3/discussions/{args.id}',
                             sentence_scope(client, old['target_id']))
    if saved is None:
        return 1 if not args.dry_run else 0
    report_saved(saved)
    return 0


def cmd_discuss_delete(args):
    client = make_client(args)
    client.model
    old = get_discussion(client, args.id)
    print(f'删除 {args.id}（{old.get("type")}）  作者 {who(old)}')
    if old.get('title'):
        print(f'  标题 : {old.get("title")}')
    if fmt_anchor(old):
        print(f'  锚点 : {fmt_anchor(old)}')
    if args.dry_run:
        print('--dry-run：未发送任何请求。')
        return 0
    if not args.yes and not confirm('确认删除？'):
        print('已取消。')
        return 1
    call_as_agent(client, 'DELETE', f'v3/discussions/{args.id}', '删除批注',
                  sentence_scope(client, old['target_id']))
    print('已删除（软删除；有回复的话题会以「已删除」占位保留，回复照常显示）。')
    return 0


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
