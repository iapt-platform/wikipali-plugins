"""注释书对应（commentary）：把义注 / 复注的句子挂到上一层译文句子的某个位置上。

一条对应 = 一条 `type='commentary'` 的 discussion：

- target：`res_type='sentence'`、`res_id=<上一层某句译文的 uid>`，加上锚点
  `pos_start` / `pos_end` / `quote_exact` / `quote_prefix` / `quote_suffix`；
- body：`content = '{{book-para-start-end}}'`——下一层（义注 / 复注）句子的模板，
  **不是**译文本身，渲染时才按当前 channel 取译文。一个片段由多句解释时并列多个
  模板 `{{…}}{{…}}`，仍是一条记录。

同一个注入口还收 `type='note'`（普通边注）：正文就是注解本身，渲染出来的边注没有
出处；写它用 `wikipali discuss-add --type note`，不走这里。

字符位的口径由服务端 `PaliContentService::injectAnnotationNotes` 定：它在译文句子
的**原始 content**（未渲染的 markdown，按 mb_strlen 计字符）第 `pos_end` 个字符处
插入 `{{note}}`。所以位置只能由本工具对着原始 content 数，不让模型数——模型只负责
给出 `quote_exact`（原样摘录）。

两个命令：

- `note-context <book_name> <cs_para> --channel C`：取三层（根本 / 义注 / 复注）在该
  CS 锚点下的全部句子，每句给巴利原文 + 该 channel 的译文，供模型做对应；
- `note-push <file> --channel C`：读模型给出的对应，逐条定位、校验、去重后写入。
"""

import json
import sys

from client import WRITE_TIMEOUT, make_client
from cmd_discuss import call_as_model, resolve_channel, who
from cmd_read import READ_TIMEOUT, pali_channel, fetch_books, fetch_paragraphs_info, row_text
from cmd_write import confirm
from errors import ApiError, WpError, explain_api_error

COMMENTARY_TYPE = 'commentary'
LAYERS = [('mūla', '根本'), ('aṭṭhakathā', '义注'), ('ṭīkā', '复注')]
LAYER_ALIAS = {'mula': 'mūla', 'mūla': 'mūla', 'pāḷi': 'mūla', 'pali': 'mūla',
               'att': 'aṭṭhakathā', 'aṭṭhakathā': 'aṭṭhakathā', 'atthakatha': 'aṭṭhakathā',
               'tika': 'ṭīkā', 'ṭīkā': 'ṭīkā'}
# 前后缀取多长：设计文档建议 32~64 字符
CONTEXT_CHARS = 32


def emit(args, payload, render):
    if getattr(args, 'json', False):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        render()


def book_layer(tags):
    """书目 tags → 层次。复注类（mūlaṭīkā / anuṭīkā）都并入 ṭīkā。"""
    tags = set(tags or [])
    if tags & {'ṭīkā', 'mūlaṭīkā', 'anuṭīkā'}:
        return 'ṭīkā'
    if 'aṭṭhakathā' in tags:
        return 'aṭṭhakathā'
    if tags & {'mūla', 'pāḷi'}:
        return 'mūla'
    return None


def sid_of(row):
    return f'{row.get("book")}-{row.get("paragraph")}-{row.get("word_start")}-{row.get("word_end")}'


def parse_sid(text):
    raw = str(text or '').strip()
    if raw.startswith('{{') and raw.endswith('}}'):
        raw = raw[2:-2]
    parts = raw.split('-')
    if len(parts) != 4 or not all(p.isdigit() for p in parts):
        raise WpError(f'「{text}」不是句子坐标，应为 book-para-start-end，如 101-513-2-23')
    return tuple(int(p) for p in parts)


# ---------------------------------------------------------------------------
# (book_name, cs_para) → 各层段落
# ---------------------------------------------------------------------------


def locate(client, book_name, cs_para):
    """返回 [{layer, book, title, paras:[…]}]，按 根本→义注→复注 排序。

    书目清单的 related_name 就是 CST 书名；对每本同名书取段落清单，挑出锚点等于
    cs_para 的**正文段**（level=100）——标题行的 cs_para 常与上一段正文共用，
    拿来对齐会选错层（见 wikipali-mobile docs/commentary-layers.md §3）。
    """
    books = [b for b in fetch_books(client) if b.get('related_name') == book_name]
    if not books:
        raise WpError(f'书目清单里没有 CST 书名为「{book_name}」的书。书名形如 an6、dn1、mn1。\n'
                      '清单有本地缓存，书目刚更新过可加 --refresh-books。')
    found = []
    for b in books:
        layer = book_layer(b.get('tags'))
        rows = fetch_paragraphs_info(client, int(b['book']), int(b['paragraph']))
        paras = [int(r['paragraph']) for r in rows
                 if r.get('book_name') == book_name and r.get('cs_para') == cs_para
                 and int(r.get('level') or 0) == 100]
        if paras:
            found.append({'layer': layer, 'book': int(b['book']),
                          'title': b.get('toc') or b.get('title'), 'paras': sorted(paras)})
    order = {name: i for i, (name, _) in enumerate(LAYERS)}
    found.sort(key=lambda f: (order.get(f['layer'], 9), f['book']))
    return found


def fetch_sentences(client, book, paras, channels):
    try:
        data = client.call('GET', 'v2/sentence',
                           query={'view': 'paragraph', 'book': book,
                                  'para': ','.join(str(p) for p in paras),
                                  'channels': ','.join(channels), 'limit': 1000},
                           timeout=READ_TIMEOUT)
    except ApiError as exc:
        raise explain_api_error(exc, f'取 {book} 的句子')
    return (data or {}).get('rows') or []


def channel_of(row):
    ch = row.get('channel') or {}
    return ch.get('id') or ch.get('uid')


def build_layer(client, entry, channel_uid):
    pali = pali_channel(client)
    rows = fetch_sentences(client, entry['book'], entry['paras'], [pali, channel_uid])
    by_sid = {}
    for r in rows:
        item = by_sid.setdefault(sid_of(r), {'sid': sid_of(r), 'pali': None,
                                             'translation': None, 'translation_uid': None})
        if channel_of(r) == pali:
            item['pali'] = row_text(r)
        elif channel_of(r) == channel_uid:
            item['translation'] = r.get('content') or ''
            item['translation_uid'] = r.get('id')
    sents = sorted(by_sid.values(), key=lambda s: parse_sid(s['sid']))
    return dict(entry, sentences=sents)


def cmd_note_context(args):
    client = make_client(args)
    if args.refresh_books:
        fetch_books(client, refresh=True)
    channel_uid, channel_name = resolve_channel(client, args.channel)
    if channel_uid == pali_channel(client):
        raise WpError('要给 --channel（译文所在的版本）：对应挂在译文句子上，位置按译文数。')
    wanted = None
    if args.layers:
        wanted = []
        for name in args.layers.split(','):
            if name.strip() not in LAYER_ALIAS:
                raise WpError(f'不认识的层次：{name}（可用 mula / att / tika）')
            wanted.append(LAYER_ALIAS[name.strip()])

    located = locate(client, args.book_name, args.cs_para)
    if wanted:
        located = [e for e in located if e['layer'] in wanted]
    layers = [build_layer(client, e, channel_uid) for e in located]
    payload = {'book_name': args.book_name, 'cs_para': args.cs_para,
               'channel': {'uid': channel_uid, 'name': channel_name}, 'layers': layers}

    def render():
        print(f'{args.book_name} / cs_para {args.cs_para}   channel：{channel_name or channel_uid}')
        if not layers:
            print('\n各层都没有这个锚点下的正文段。这是正常结果（约 2% 的段落没有 CST 锚点），'
                  '不要拿相邻段落凑。')
            return
        for layer in layers:
            label = dict(LAYERS).get(layer['layer'], layer['layer'] or '未标层次')
            print('\n' + '=' * 72)
            print(f'[{label}] {layer["title"]}  book {layer["book"]}  段 '
                  + ', '.join(str(p) for p in layer['paras']))
            for s in layer['sentences']:
                print(f'\n  {{{{{s["sid"]}}}}}')
                print(f'    巴利：{s["pali"] or "（无）"}')
                print(f'    译文：{s["translation"] if s["translation"] is not None else "（该 channel 无译文）"}')
        missing = [s['sid'] for layer in layers[:-1] for s in layer['sentences']
                   if s['translation'] is None]
        if missing:
            print(f'\n⚠ 上层有 {len(missing)} 句在该 channel 没有译文，这些句子上挂不了对应：'
                  + ' '.join(missing[:8]) + (' …' if len(missing) > 8 else ''))

    emit(args, payload, render)
    return 0


# ---------------------------------------------------------------------------
# note-push
# ---------------------------------------------------------------------------


def in_template(text, pos):
    """pos 是否落在 {{…}} 或 [[…]] 里面——在那里插入会把模板劈开。"""
    for open_, close in (('{{', '}}'), ('[[', ']]')):
        start = text.rfind(open_, 0, pos)
        if start != -1 and text.find(close, start, pos) == -1 and text.find(close, pos) != -1:
            return True
    return False


def anchor(text, item):
    """在译文原文里定位 quote_exact，返回 (pos_start, pos_end, prefix, suffix)。

    摘录出现多次时用模型给的 prefix / suffix 消歧；仍不唯一就报错，**不猜**。

    不给 quote_exact ＝ **整句挂**（四项都返回 None）：段落在第一个黑体之前的引子没有
    对应片段，挂在章节标题句上，阅读页插在句尾。这是 commentary-align 规则 3 的情形，
    不是漏填——别的情形都该给摘录。
    """
    exact = item.get('quote_exact') or ''
    if not exact:
        return (None, None, None, None)
    hits = []
    i = text.find(exact)
    while i != -1:
        hits.append(i)
        i = text.find(exact, i + 1)
    if not hits:
        raise WpError(f'quote_exact「{exact}」不在该句译文里（必须原样摘录，含标点）')
    if len(hits) > 1:
        pre, suf = item.get('quote_prefix') or '', item.get('quote_suffix') or ''
        hits = [h for h in hits
                if text[:h].endswith(pre) and text[h + len(exact):].startswith(suf)]
        if len(hits) != 1:
            raise WpError(f'quote_exact「{exact}」在句中出现多次，前后缀也无法唯一确定')
    start = hits[0]
    end = start + len(exact)
    if in_template(text, end):
        raise WpError(f'「{exact}」的结束位落在模板 / 链接内部，插入会破坏它；换个摘录范围')
    return (start, end,
            text[max(0, start - CONTEXT_CHARS):start],
            text[end:end + CONTEXT_CHARS])


def note_list(value):
    """note 可以是一个句子坐标，或句子坐标的列表。"""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def note_sentences(values, known):
    """校验 note 的每一句都是真实存在的单句，按原顺序去重返回 [(book, para, start, end)]。

    只校验、不改写：不合并成区间（区间不是真实句子），也不拆成多条——一条对应就是
    一条记录，怎么渲染多句是服务端的事。
    """
    if not values:
        raise WpError('缺 note')
    real = {parse_sid(s) for s in known}
    out = []
    for value in values:
        sid = parse_sid(value)
        if sid not in real:
            raise WpError(f'{"-".join(map(str, sid))} 不是一个真实句子（note 只能列单句，'
                          '不能写区间；多句就列成数组）')
        if sid not in out:
            out.append(sid)
    return out


def load_items(path):
    """读 JSONL：一行一条对应，返回 ([(行号, 对象)], [(行号, 原文, 错误)])。

    用 JSONL 而不是一个大 JSON：条目多时模型的输出容易在中途截断、收不了尾，整份
    JSON 就全废了；JSONL 坏一行只丢一行，其余照常处理（坏行报为问题）。
    也兼容旧格式——整份是 {"items": [...]} 或数组时照旧读。
    """
    try:
        raw = sys.stdin.read() if path == '-' else open(path, encoding='utf-8').read()
    except OSError as exc:
        raise WpError(f'读不了文件：{exc}')
    try:
        data = json.loads(raw)
    except ValueError:
        data = None
    if isinstance(data, dict) and isinstance(data.get('items'), list):
        data = data['items']
    if isinstance(data, list):
        return list(enumerate(data, 1)), []
    items, bad = [], []
    for n, line in enumerate(raw.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('//'):
            continue
        try:
            obj = json.loads(line)
        except ValueError as exc:
            bad.append((n, {'raw': line[:60]}, f'第 {n} 行不是合法 JSON（可能输出被截断）：{exc}'))
            continue
        if not isinstance(obj, dict):
            bad.append((n, {'raw': line[:60]}, f'第 {n} 行应是一个 JSON 对象'))
            continue
        items.append((n, obj))
    if not items and not bad:
        raise WpError('文件里没有任何对应（JSONL：一行一个 {"target": …, "note": …, "quote_exact": …}）')
    return items, bad


def existing_notes(client, res_id):
    data = call_as_model(client, 'GET', 'v2/discussion', '列出已有对应',
                         query={'view': 'question', 'res_type': 'sentence', 'id': res_id,
                                'type': COMMENTARY_TYPE, 'status': 'active', 'limit': 200})
    return (data or {}).get('rows') or []


def cmd_note_push(args):
    client = make_client(args)
    channel_uid, channel_name = resolve_channel(client, args.channel)
    if channel_uid == pali_channel(client):
        raise WpError('要给 --channel：对应挂在该 channel 的译文句子上。')
    items, bad = load_items(args.file)

    # 按 target 所在段批量取译文，按 note 所在段批量确认句子存在
    need = {}
    for _, it in items:
        for key in ('target', 'note'):
            for value in note_list(it.get(key)):
                try:
                    b, p, _, _ = parse_sid(value)
                except WpError:
                    continue
                need.setdefault((key, b), set()).add(p)
    targets, notes = {}, set()
    for (key, b), paras in need.items():
        chans = [channel_uid] if key == 'target' else [pali_channel(client)]
        for r in fetch_sentences(client, b, sorted(paras), chans):
            if key == 'target':
                targets[sid_of(r)] = r
            else:
                notes.add(sid_of(r))

    plan, problems, cache = [], list(bad), {}
    for n, it in items:
        try:
            if isinstance(it.get('target'), list):
                raise WpError('target 只能是一句（上一层的一个句子坐标），不能是列表')
            tsid = '-'.join(str(x) for x in parse_sid(it.get('target')))
            row = targets.get(tsid)
            if not row:
                raise WpError(f'target {tsid} 在该 channel 没有译文句子')
            runs = note_sentences(note_list(it.get('note')), notes)
            start, end, pre, suf = anchor(row.get('content') or '', it)
            if row['id'] not in cache:
                cache[row['id']] = existing_notes(client, row['id'])
            # 一条对应 = 一条记录。一个词由下一层多句解释时，content 按顺序并列
            # 这几句的模板：{{b-p-s-e}}{{b-p-s-e}}…
            tpl = ''.join(f'{{{{{nb}-{np_}-{ns}-{ne}}}}}' for nb, np_, ns, ne in runs)
            body = {'res_id': row['id'], 'res_type': 'sentence', 'type': COMMENTARY_TYPE,
                    'content': tpl, 'content_type': 'markdown', 'notification': False}
            if start is not None:
                body.update({'pos_start': start, 'pos_end': end,
                             'quote_exact': it['quote_exact'],
                             'quote_prefix': pre, 'quote_suffix': suf})
            dup = [e for e in cache[row['id']] if (e.get('content') or '').strip() == tpl]
            plan.append({'n': n, 'target': tsid, 'body': body, 'dup': dup, 'notes': runs})
        except WpError as exc:
            problems.append((n, it, str(exc)))

    print('=' * 72)
    print(f'API      : {client.api_note()}')
    print(f'模型身份 : {client.model.get("name")}  uid={client.model.get("uid")}')
    print(f'channel  : {channel_name or channel_uid}')
    print('-' * 72)
    for p in plan:
        b = p['body']
        mark = '已存在' if p['dup'] and not args.replace else ('替换' if p['dup'] else '新增')
        where = ('整句' if b.get('pos_start') is None
                 else f'[{b["pos_start"]}-{b["pos_end"]}] 「{b["quote_exact"][:30]}」')
        print(f'  #{p["n"]:<3} {mark}  {p["target"]} {where} ← {b["content"]}')
    for n, it, msg in problems:
        where = it['raw'] if 'raw' in it else f'{it.get("target")} ← {it.get("note")}'
        print(f'  #{n:<3} ✗ {msg}   ({where})')
    # 覆盖率：下一层这些段里，没有被任何一条对应引到的句子。规则 4 要求除了段落开头
    # 的引子（挂标题句那几句）之外一句都不漏，所以这里逐句点出来，让人一眼看到漏没漏。
    covered = {'-'.join(str(x) for x in sid) for p in plan for sid in p['notes']}
    uncovered = sorted(notes - covered, key=parse_sid)
    todo = [p for p in plan if not p['dup'] or args.replace]
    print('-' * 72)
    if uncovered:
        print(f'⚠ 下一层有 {len(uncovered)} 句没有进任何一条对应：')
        for sid in uncovered:
            print(f'    {sid}')
        print('  只有「段落第一个黑体之前的引子」允许不挂（那几句该挂在章节标题句上）；'
              '其余是漏了，补进对应的 note 数组。')
    print(f'可写 {len(todo)} 条，已存在跳过 {len(plan) - len(todo)} 条，有问题 {len(problems)} 条，'
          f'下一层未覆盖 {len(uncovered)} 句。')
    print('=' * 72)

    if args.json:
        print(json.dumps({'plan': [p['body'] | {'target': p['target']} for p in todo],
                          'problems': [{'n': n, 'error': m} for n, _, m in problems]},
                         ensure_ascii=False, indent=2))
    if args.dry_run or not todo:
        print('--dry-run：未发送任何请求。' if args.dry_run else '没有要写的。')
        return 1 if problems else 0
    if not args.yes and not confirm('确认提交？'):
        print('已取消，未写入任何内容。')
        return 1

    for p in todo:
        for old in p['dup']:
            call_as_model(client, 'DELETE', f'v2/discussion/{old["id"]}', '删除旧对应',
                          timeout=WRITE_TIMEOUT)
        saved = call_as_model(client, 'POST', 'v2/discussion', '写入对应',
                              body=p['body'], timeout=WRITE_TIMEOUT)
        print(f'  #{p["n"]:<3} 已写入 {saved.get("id")}  editor={who(saved)}')
    print('提示：阅读页按 (book, para, channel) 缓存；若服务端写批注时不清缓存，新对应要等缓存过期才显示。')
    return 1 if problems else 0
