"""cite —— 把缅文/罗马化的引用缩写解析成 WikiPali 的坐标。

**纯离线**：只读插件自带的三个数据文件，不发任何请求、不需要凭据。

引用里的数字是**缅甸版页码**，不是段落号。换算靠 `citation-pages.tsv.gz`——
它是 WikiPali 正文里那些页码标记（`M2.0241` 这类）的索引，一条标记落在一个
段落上，所以「清净道论第 2 册第 241 页」能直接定到 `65:1461`。
"""

import gzip
import json
import os
import re
import unicodedata

from errors import WpError

REF_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'references')
ABBREV_TSV = os.path.join(REF_DIR, 'citation-abbrev.tsv')
BOOKS_TSV = os.path.join(REF_DIR, 'citation-books.tsv')
PAGES_GZ = os.path.join(REF_DIR, 'citation-pages.tsv.gz')

# 缅文数字 ၀-၉
MY_DIGITS = {chr(0x1040 + i): str(i) for i in range(10)}
# 引用里用过的分隔符：缅文逗号/句号、各种横线、顿号、全角逗号、点、空白。
# 括号一并吃掉——脚注里的引用多半是括起来的，(ဝိသုဒ္ဓိ၊၂၊၂၄၁) 要能直接查。
SEPARATORS = re.compile("[၊။\\-‐-―、，,.\\s·・"
                        "()（）\\[\\]【】〔〕《》"
                        "「」'\"]+")


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
        keys = {ab.strip() for ab in row['abbrev_my'].split('|')}
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
        hits = [(k, r) for k, r in idx.items() if len(k) > 3 and (folded in k or k in folded)]
        if hits:
            return max(hits, key=lambda kv: len(kv[0]))[1], 'fuzzy'
    return None, None


def parse_volmap(spec):
    """`1=96;2=97;3=98` 或 `2=173:1155` → {册: [(book, para 或 None), …]}。

    有些书组的页码标记里没有册号（缅甸版论藏义注三册都标成 M0.xxxx），
    这时只能靠这张人工核定的册 → 著作对照表把册定下来。
    """
    out = {}
    for part in (spec or '').split(';'):
        if '=' not in part:
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


def find_pages(words, books):
    """在页码索引里查这些标记，限定在候选 book 内。返回 {标记: [(book, para), …]}。

    索引 6 万余行、解压后 1 MB，整扫一遍是毫秒级，不值得再建更复杂的结构。
    """
    if not os.path.exists(PAGES_GZ):
        raise WpError(f'缺少页码索引 {PAGES_GZ}——插件没装全，重装一次。')
    found = {w: [] for w in words}
    with gzip.open(PAGES_GZ, 'rt', encoding='utf-8') as fh:
        for line in fh:
            word, book, para = line.rstrip('\n').split('\t')
            if word in found and int(book) in books:
                found[word].append((int(book), int(para)))
    return found


def scope_works(row, works, vol):
    """候选著作：先按缩写给的 book 列表，再按册号对照表收窄。"""
    ids = [int(x) for x in row['books'].split(',') if x.strip()]
    cands = [w for w in works if int(w['book']) in ids]
    vmap = parse_volmap(row.get('vol_map'))
    if vol is not None and vol in vmap:
        want = vmap[vol]
        scoped = [w for w in cands
                  if (int(w['book']), int(w['para'])) in want or (int(w['book']), None) in want]
        if scoped:
            return scoped, cands, True
    return cands, cands, False


def work_of(book, para, works):
    """段落落在哪一部著作里——同一本书内起始段不大于它的最后一部。"""
    inside = [w for w in works if int(w['book']) == book and int(w['para']) <= para]
    return max(inside, key=lambda w: int(w['para'])) if inside else None


def resolve(row, works, vol, page):
    """返回 (命中列表, 用到的标记, 说明)。命中是 (book, para, 著作行)。"""
    scoped, cands, mapped = scope_works(row, works, vol)
    if not scoped:
        return [], '', '该书在 WikiPali 里没有对应'
    if page is None:
        return [], '', '引用里没有页码，定不到位置'

    books = {int(w['book']) for w in scoped}
    # 分册的著作标记成 M<册>.<页>，不分册的标记成 M0.<页>；页码在索引里补足四位。
    primary = 'M%d.%04d' % (vol, page) if vol is not None else None
    fallback = 'M0.%04d' % page
    words = [w for w in (primary, fallback) if w]
    found = find_pages(words, books)

    for word in words:
        hits = []
        for book, para in found[word]:
            work = work_of(book, para, works)
            # vol_map 收窄过的，命中还要落在被指到的那几部里
            if mapped and (work is None or work not in scoped):
                continue
            hits.append((book, para, work))
        if hits:
            return hits, word, ''
    return [], words[0], f'页码索引里没有 {words[0]}——这一页在候选著作里没有标记'


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
        hits, word, why = resolve(row, works, vol, page)
        item['marker'] = word
        if len(hits) == 1:
            book, para, work = hits[0]
            item.update({'book': book, 'paragraph': para,
                         'toc': work['toc'] if work else '',
                         'work_start': int(work['para']) if work else None})
            if page_end:
                tail, _, _ = resolve(row, works, vol, page_end)
                if len(tail) == 1:
                    item['paragraph_end'] = tail[0][1]
        else:
            item['why'] = why or '多部著作的同册同页都有标记，定不到唯一一处'
            if hits:
                item['candidates'] = [{'book': b, 'para': p,
                                       'toc': (w or {}).get('toc', '')} for b, p, w in hits]
            else:
                scoped = scope_works(row, works, vol)[0]
                item['candidates'] = [
                    {'book': int(w['book']), 'para': int(w['para']), 'toc': w['toc'],
                     'm': f"{w['m_vol']}.{w['m_first']}-{w['m_last']}" if w['m_vol'] else ''}
                    for w in scoped]
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
        print(r['input'])
        print(f"  缩写   : {r['name']}   {'  '.join(loc) if loc else '（没有册页）'}")
        if r.get('error'):
            print(f"  ✗ {r['error']}——不在 references/citation-abbrev.tsv 里，别猜。")
            continue
        print(f"  著作   : {r['work_pali']}　{r['work_zh']}　（{r['kind']}）")
        if r.get('note'):
            print(f"  说明   : {r['note']}")
        if r.get('book'):
            coords = f"{r['book']}:{r['paragraph']}"
            shown = f"{r['book']}-{r['paragraph']}"
            if r.get('paragraph_end') and r['paragraph_end'] != r['paragraph']:
                shown += f" … {r['book']}-{r['paragraph_end']}"
                coords += f" {r['book']}:{r['paragraph_end']}"
            print(f"  → 书名 : {r['toc']}")
            print(f"  → 坐标 : {shown}　（页码标记 {r['marker']} 落在这一段）")
            print(f"  取原文 : wikipali get {coords}")
        elif r['kind'] in ('nissaya', 'burmese'):
            print('  → WikiPali 无对应：这是缅文著作，库里收的是巴利文献。'
                  '册页也不能换算——缅文本的分册与巴利本不是一回事。')
        else:
            print(f"  ✗ 定不到位置：{r.get('why', '')}")
            for c in r.get('candidates', [])[:14]:
                tail = f"  M{c['m']}" if c.get('m') else ''
                print(f"      {c['book']}:{c['para']:<6} {c['toc'][:44]}{tail}")
        if r.get('match') == 'fuzzy':
            print('  ⚠ 缩写是模糊匹配上的，核对一下是不是这部书。')

    print('\n页码是缅甸版的，段落号由 references/citation-pages.tsv.gz 里的页码标记换算而来；'
          '标记指的是**该页起始处**，所引内容可能延续到后面几段。')
    return 0
