"""cite —— 把缅文/罗马化的引用缩写解析成 WikiPali 的书。

**纯离线**：只读插件自带的两张表，不发任何请求、不需要凭据。

引用里的数字是**缅甸版页码**，不是 WikiPali 的段落号，两者不是一回事。
本命令只做到「是哪本书」——把页码换成段落号要读正文里的 <code>M册.页</code>
标记，那是下一步的事，这里不猜。
"""

import json
import os
import re
import unicodedata

from errors import WpError

REF_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'references')
ABBREV_TSV = os.path.join(REF_DIR, 'citation-abbrev.tsv')
BOOKS_TSV = os.path.join(REF_DIR, 'citation-books.tsv')

# 缅文数字 ၀-၉
MY_DIGITS = {chr(0x1040 + i): str(i) for i in range(10)}
# 引用里用过的分隔符：缅文逗号/句号、各种横线、顿号、全角逗号、点、空白。
# 括号一并吃掉——脚注里的引用多半是括起来的，(ဝိသုဒ္ဓိ၊၂၊၂၄၁) 要能直接查。
SEPARATORS = re.compile("[\u104a\u104b\\-\u2010-\u2015\u3001\uff0c,.\\s\u00b7\u30fb()\uff08\uff09\\[\\]\u3010\u3011\u3014\u3015\u300a\u300b\u300c\u300d'\"]+")


def _load_tsv(path):
    if not os.path.exists(path):
        raise WpError(f'缺少数据文件 {path}——插件没装全，重装一次。')
    with open(path, encoding='utf-8') as fh:
        head = fh.readline().rstrip('\n').split('\t')
        return [dict(zip(head, line.rstrip('\n').split('\t'))) for line in fh if line.strip()]


def _fold(text):
    """罗马化写法归一：去变音符、小写。ā→a、ṭ→t、ṃ→m，这样 mahatika 也能命中。"""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return text.lower().replace('ṃ', 'm').replace('ḷ', 'l')


def to_arabic(text):
    return ''.join(MY_DIGITS.get(c, c) for c in text)


def parse(raw):
    """拆成 (书名部分, 数字列表)。名字部分用 '-' 连接，与表里的写法对齐。

    ဝိသုဒ္ဓိ၊၂၊၂၄၁ → ('ဝိသုဒ္ဓိ', [2, 241])
    အဘိ၊ဋ္ဌ၊၂၊၂၅၂ → ('အဘိ-ဋ္ဌ', [2, 252])   ← 名字本身带一节，拆开后要拼回去
    """
    tokens = [t for t in SEPARATORS.split(to_arabic(raw).strip()) if t]
    names, nums = [], []
    for tok in tokens:
        if tok.isdigit():
            nums.append(int(tok))
        else:
            names.append(tok)
    return '-'.join(names), nums


def _index(rows):
    """名字 → 行。缅文写法、巴利书名、中文名、人工别名都进索引。"""
    idx = {}
    for row in rows:
        keys = set()
        for ab in row['abbrev_my'].split('|'):
            keys.add(ab.strip())
        for extra in (row['work_pali'], row['work_zh']):
            if extra:
                keys.add(_fold(extra))
        for alias in (row.get('aliases') or '').split('|'):
            if alias.strip():
                keys.add(_fold(alias.strip()))
        for k in keys:
            idx.setdefault(k, row)
    return idx


def lookup(name, rows):
    idx = _index(rows)
    hit = idx.get(name) or idx.get(_fold(name))
    if hit:
        return hit, 'exact'
    # 退一步：含入关系里取**最长**的那个键，避免「ဝိသုဒ္ဓိ」抢走
    # 「ပြည်-ဝိသုဒ္ဓိမဂ်နိဿယ」这种更具体的写法。
    folded = _fold(name)
    if len(folded) > 3:
        hits = [(k, r) for k, r in idx.items()
                if len(k) > 3 and (folded in k or k in folded)]
        if hits:
            return max(hits, key=lambda kv: len(kv[0]))[1], 'fuzzy'
    return None, None


def parse_volmap(spec):
    """`1=96;2=97;3=98` 或 `2=173:1155` → {册: [(book, para 或 None), …]}。

    有些书组的页码标记里根本没有册号（缅甸版论藏义注三册都标成 M0.x），
    这时只能靠这张人工核定的册 → 著作对照表定册，再用页码定册内的哪一部。
    """
    out = {}
    for part in (spec or '').split(';'):
        part = part.strip()
        if not part or '=' not in part:
            continue
        vol, targets = part.split('=', 1)
        if not vol.strip().isdigit():
            continue
        items = []
        for t in targets.split(','):
            t = t.strip()
            if ':' in t:
                b, para = t.split(':', 1)
                items.append((int(b), int(para)))
            elif t.isdigit():
                items.append((int(t), None))
        out[int(vol)] = items
    return out


def pick_work(row, works, vol, page):
    """在候选著作里按缅甸版册·页定位。返回 (命中, 候选, 说明)。

    候选的单位是**著作**不是书——一本 book 里可能收好几部（book 98 收了五论义注
    中的五部），页码在一册之内跨著作连续编下去。
    """
    ids = [int(x) for x in row['books'].split(',') if x.strip()]
    cands = [b for b in works if int(b['book']) in ids]
    if not cands:
        return None, [], '该书在 WikiPali 里没有对应'

    scoped, mapped = cands, False
    vmap = parse_volmap(row.get('vol_map'))
    if vol is not None and vol in vmap:
        want = vmap[vol]
        scoped = [b for b in cands
                  if (int(b['book']), int(b['para'])) in want or (int(b['book']), None) in want]
        mapped = True
        if not scoped:
            return None, cands, f'册号对照表里第 {vol} 册指向的著作不在候选里'

    if page is None:
        if len(scoped) == 1:
            return scoped[0], cands, ''
        return None, scoped, '引用里没有页码，定不到具体是哪一部'

    ranged = [b for b in scoped if b['m_first']]
    if not ranged:
        if len(scoped) == 1:
            return scoped[0], cands, ''
        return None, scoped, '这些著作没有缅甸版页码标记，无法按页定位'

    if mapped:
        pool = ranged            # 册已由对照表定死，不再比对 m_vol
    else:
        same_vol = [b for b in ranged
                    if vol is not None and b['m_vol'] and int(b['m_vol']) == vol]
        pool = same_vol or (ranged if vol is None else [])
        # 不分册的著作页码标记记作 M0.x。引用给了册号而候选只有这么一部时，
        # 按同一部算，别因为 0≠1 就判定找不到。
        if not pool and len(ranged) == 1 and ranged[0]['m_vol'] in ('0', ''):
            pool = ranged
        if not pool:
            return None, cands, f'候选著作里没有缅甸版第 {vol} 册'

    # 页码在一册之内跨著作连续编下去，所以「起始页不大于该页的最后一部」就是答案。
    # 不靠 m_last——末尾几章没有页码标记的著作，m_last 本来就取不到。
    pool = sorted(pool, key=lambda b: int(b['m_first']))
    before = [b for b in pool if int(b['m_first']) <= page]
    if not before:
        return None, pool, f"页码 {page} 比这一册最早的一部（起于第 {pool[0]['m_first']} 页）还靠前"
    hit = before[-1]
    if hit['m_last'] and page > int(hit['m_last']):
        # 同一册里还有没抓到页码的著作时，越界就不能硬断——真正的答案很可能
        # 就是那几部之一。宁可报不确定，也不要指到一部明显装不下这一页的著作上。
        blind = [b for b in scoped if not b['m_first']]
        if blind:
            return None, pool + blind, (
                f"页码 {page} 超出 {hit['toc'][:24]} 的区间（止于第 {hit['m_last']} 页），"
                f"而同册另有 {len(blind)} 部没有页码数据")
        if hit is pool[-1]:
            return hit, cands, ''      # 该册最后一部，上界只是没扫到，不算越界
        return None, pool, (f"页码 {page} 落在 {hit['toc'][:24]}（止于第 {hit['m_last']} 页）"
                            f"与下一部之间的接缝上")
    return hit, cands, ''


def cmd_cite(args):
    abbrevs = _load_tsv(ABBREV_TSV)
    works = _load_tsv(BOOKS_TSV)

    results = []
    for raw in args.citation:
        name, nums = parse(raw)
        row, how = lookup(name, abbrevs)

        # 数字怎么读取决于这部书分不分册：不分册的书（如无碍解道），
        # 「ပဋိသံ၊၅၂-၅၃」的两个数字是页码范围，不是册号和页码。
        volumed = bool(row) and (row['vols_seen'] or '-') != '-'
        vol = page = page_end = None
        if volumed and len(nums) >= 2:
            vol, page = nums[0], nums[1]
            page_end = nums[2] if len(nums) >= 3 else None
        elif nums:
            page = nums[0]
            page_end = nums[1] if len(nums) >= 2 else None
        item = {'input': raw, 'name': name, 'vol': vol, 'page': page,
                'page_end': page_end, 'match': how}
        if not row:
            item['error'] = '表里没有这个缩写'
            results.append(item)
            continue

        item.update({'work_pali': row['work_pali'], 'work_zh': row['work_zh'],
                     'kind': row['kind'], 'note': row['note']})
        hit, cands, why = pick_work(row, works, vol, page)
        item['candidates'] = [{'book': int(b['book']), 'para': int(b['para']), 'toc': b['toc'],
                               'm': f"{b['m_vol']}.{b['m_first']}-{b['m_last']}" if b['m_vol'] else ''}
                              for b in cands]
        if hit:
            item['book'] = int(hit['book'])
            item['toc'] = hit['toc']
            item['work_start'] = int(hit['para'])
            item['m_range'] = f"M{hit['m_vol']}.{hit['m_first']}–{hit['m_last']}"
        else:
            item['why'] = why
        results.append(item)

    if getattr(args, 'json', False):
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    for i, r in enumerate(results):
        if i:
            print()
        loc = []
        if r['vol'] is not None:
            loc.append(f"第 {r['vol']} 册")
        if r['page'] is not None:
            loc.append(f"缅甸版第 {r['page']}{'–' + str(r['page_end']) if r['page_end'] else ''} 页")
        print(f"{r['input']}")
        print(f"  缩写   : {r['name']}   {'  '.join(loc) if loc else '（没有册页）'}")
        if r.get('error'):
            print(f"  ✗ {r['error']}——不在 references/citation-abbrev.tsv 里，别猜。")
            continue
        print(f"  著作   : {r['work_pali']}　{r['work_zh']}　（{r['kind']}）")
        if r.get('note'):
            print(f"  说明   : {r['note']}")
        if r.get('book'):
            print(f"  → 书名 : {r['toc']}　（缅甸版 {r.get('m_range', '')}，起于 "
                  f"{r['book']}:{r['work_start']}）")
            print(f"  → 坐标 : {r['book']}-<段落号>　（段落号未解析：引用给的是页码，不是段落）")
        elif r['kind'] in ('nissaya', 'burmese'):
            print('  → WikiPali 无对应：这是缅文著作，库里收的是巴利文献。'
                  '册页也不能换算——缅文本的分册与巴利本不是一回事。')
        else:
            print(f"  ✗ 定不到具体哪一本：{r.get('why', '')}")
            for c in r.get('candidates', [])[:14]:
                print(f"      {c['book']}:{c['para']:<6} {c['toc'][:42]:<44}"
                      f"{('M' + c['m']) if c['m'] else '（无页码标记）'}")
        if r.get('match') == 'fuzzy':
            print('  ⚠ 缩写是模糊匹配上的，核对一下是不是这部书。')

    print('\n引用里的数字是缅甸版页码。页码 → 段落号要读正文里的 <code>M册.页</code> 标记，'
          '本命令不做这一步。')
    return 0
