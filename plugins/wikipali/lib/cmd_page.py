"""page —— 把印本页码换算成 WikiPali 坐标。

**只做换算，不认书。** 「这个缩写是哪部著作」交给模型判断——表格发出去就冻在
用户机器上了，靠程序做字符串比对，遇到新写法只能等下次发版。模型看着
`references/citation-abbrev.tsv` 自己认，认完把候选 `pcd` 传进来。

换算走线上的 `GET /v2/nav-page/{版本}-{pcd}-{册}-{页}`：它直接返回该页起始处的
`book`/`paragraph`，`next` 则是下一页的起点，两者之间就是这一页的段落区间。

**`pcd`（`pcd_book_id`）是按著作编的**，一本 book 收几部就有几个 pcd。这正是
nav-page 需要的键，也天然分开了同一本书里各自编页的多部著作（book 173 前半是
根本复注 pcd 192、后半是随复注 pcd 193，两部的页码会撞，pcd 不会）。
"""

import json
import os
import re

from client import make_client
from cmd_read import pali_channel, strip_markup
from errors import ApiError, WpError, explain_api_error

REF_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'references')
BOOKS_TSV = os.path.join(REF_DIR, 'citation-books.tsv')

EDITIONS = {'M': '缅甸版', 'V': 'VRI 版', 'P': 'PTS 版', 'T': '泰版'}
# M2.241 / 2.241 / 241 / 2.249-250
MARKER = re.compile(r'^(?:(?P<ed>[MVPT])\s*)?(?:(?P<vol>\d+)\s*[.:]\s*)?'
                    r'(?P<page>\d+)(?:\s*-\s*(?P<page_end>\d+))?$')


def _load_tsv(path):
    if not os.path.exists(path):
        raise WpError(f'缺少数据文件 {path}——插件没装全，重装一次。')
    with open(path, encoding='utf-8') as fh:
        head = fh.readline().rstrip('\n').split('\t')
        return [dict(zip(head, line.rstrip('\n').split('\t'))) for line in fh if line.strip()]


def parse_marker(raw):
    """`M2.241` / `2.241` / `241` / `2.249-250` → (版本, 册, 起页, 止页 或 None)。

    不写册号的按第 0 册算——不分册的著作在库里就是这么标的。
    """
    m = MARKER.match(raw.strip())
    if not m:
        raise WpError(f'看不懂页码 {raw!r}——写成 <册>.<页>（如 2.241）或只写页码（如 47）。')
    end = int(m.group('page_end')) if m.group('page_end') else None
    return (m.group('ed') or 'M', int(m.group('vol') or 0), int(m.group('page')), end)


def parse_pcds(raw):
    out = []
    for part in re.split(r'[,\s;]+', raw or ''):
        if part.strip().isdigit():
            out.append(int(part))
    if not out:
        raise WpError('要给 --pcd：模型判断出的候选著作编号，逗号分隔，'
                      '取自 references/citation-abbrev.tsv 的 pcd 列。')
    return out


def nav_page(client, ed, pcds, vol, page):
    """GET /v2/nav-page/{版本}-{pcd_pcd…}-{册}-{页}。查无此页返回 None，不算错误。"""
    ident = f"{ed}-{'_'.join(str(p) for p in pcds)}-{vol}-{page}"
    try:
        return client.call('GET', f'v2/nav-page/{ident}', timeout=60)
    except ApiError as exc:
        msg = str(getattr(exc, 'message', '') or exc)
        if 'not found' in msg.lower() or getattr(exc, 'status', None) == 404:
            return None
        raise explain_api_error(exc, f'查 {ident}')


def fetch_meta(client, book, para):
    """章节路径与著作名，取自 palitext 的 path。"""
    try:
        meta = client.call('GET', f'v2/palitext/{book}-{para}', timeout=60) or {}
    except ApiError as exc:
        raise explain_api_error(exc, f'取 {book}:{para} 的章节路径')
    path = meta.get('path')
    if isinstance(path, str):
        try:
            path = json.loads(path)
        except ValueError:
            path = []
    return path or []


def fetch_text(client, book, start, end):
    paras = list(range(start, (end if end and end >= start else start) + 1))
    query = {'view': 'paragraph', 'book': book, 'para': ','.join(str(p) for p in paras),
             'channels': pali_channel(client), 'limit': 500}
    try:
        data = client.call('GET', 'v2/sentence', query=query, timeout=60) or {}
    except ApiError as exc:
        raise explain_api_error(exc, f'取 {book}:{start}–{paras[-1]} 的原文')
    return data.get('rows') or []


def work_of(book, para, works):
    """段落落在哪一部著作里——同一本书内起始段不大于它的最后一部。"""
    inside = [w for w in works if int(w['book']) == book and int(w['para']) <= para]
    return max(inside, key=lambda w: int(w['para'])) if inside else None


def cmd_page(args):
    works = _load_tsv(BOOKS_TSV)
    pcds = parse_pcds(args.pcd)
    ed, vol, page, page_end = parse_marker(args.page)
    client = make_client(args)

    data = nav_page(client, ed, pcds, vol, page)
    label = f'{EDITIONS.get(ed, ed)} ' + (f'第 {vol} 册 ' if vol else '') + \
            f'第 {page}' + (f'–{page_end}' if page_end else '') + ' 页'
    if not data or not (data.get('curr')):
        print(f'{label}　（候选 pcd {",".join(map(str, pcds))}）')
        print('  ✗ 这些著作里没有这一页。')
        print('    要么册号或页码不对，要么候选著作判断错了——重新判断，别拿相近的书顶上。')
        return 0

    curr, nxt = data['curr'], data.get('next') or {}
    book, para = curr['book'], curr['paragraph']
    hit_pcd = curr.get('pcd_book_id')
    result = {'edition': ed, 'vol': vol, 'page': page, 'page_end': page_end,
              'pcd': hit_pcd, 'book': book, 'paragraph': para, 'wid': curr.get('wid'),
              'next_paragraph': nxt.get('paragraph')}

    # nav-page 只回第一处。候选给了多个时再查一次余下的，撞车要说出来，不能闷着。
    others = [p for p in pcds if p != hit_pcd]
    if others:
        rival = nav_page(client, ed, others, vol, page)
        if rival and rival.get('curr'):
            r = rival['curr']
            result['ambiguous'] = {'pcd': r.get('pcd_book_id'),
                                   'book': r['book'], 'paragraph': r['paragraph']}

    work = work_of(book, para, works)
    result['toc'] = work['toc'] if work else ''

    end_para = result.get('next_paragraph') or para
    if page_end:
        tail = nav_page(client, ed, [hit_pcd], vol, page_end + 1)
        if tail and tail.get('curr'):
            end_para = tail['curr']['paragraph']
        result['paragraph_end'] = end_para

    if getattr(args, 'text', False):
        result['path'] = fetch_meta(client, book, para)
        result['rows'] = fetch_text(client, book, para, end_para)
        result['span_end'] = end_para

    if getattr(args, 'json', False):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(f'{label}　（pcd {hit_pcd}）')
    if amb := result.get('ambiguous'):
        print(f"  ⚠ 候选里还有一处也有这一页：pcd {amb['pcd']} 的 "
              f"{amb['book']}:{amb['paragraph']}。候选给窄一点，或按册号收窄——"
              '每部著作各有一套自己的页码。')
    print(f"  → 书名 : {result['toc']}")
    span = f"{book}-{para}"
    coords = f"{book}:{para}"
    if page_end and end_para != para:
        span += f" … {book}-{end_para}"
        coords += f" {book}:{end_para}"
    print(f"  → 坐标 : {span}"
          + (f"　（页起于第 {curr.get('wid')} 词）" if curr.get('wid') else ''))
    if path := result.get('path'):
        print('  章节路径: ' + ' › '.join(str(x.get('title') or '') for x in path))
    if result.get('rows') is None:
        print(f'  本页止于 : {book}:{end_para}（与下一页共享这一段）')
        print(f'  取原文 : wikipali get {coords}　（加 --text 直接取这一页）')
        return 0

    rows = result['rows']
    print(f"\n  ── 第 {page} 页原文（{book}:{para}–{end_para}，{len(rows)} 句）──")
    if not rows:
        print('  该区间取不到巴利原文。')
    current = None
    for row in rows:
        if row.get('paragraph') != current:
            current = row.get('paragraph')
            print(f'  [{book}:{current}]')
        print('    ' + strip_markup(row.get('content')))
    print('  末段与下一页共享——本页在其中某处结束，不是整段都属于这一页。')
    return 0
