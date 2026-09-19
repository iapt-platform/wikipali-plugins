"""坐标与引用。

WikiPali 的最小可引用单位是 (book, paragraph)，句子再细分到 word_start/word_end。
一切给用户看的内容都必须带得回坐标——这是研究型产出可信度的地基。

坐标的书写形式统一为 `book:paragraph`，例如 `216:35`。
"""

import re

from errors import WpError

COORD_RE = re.compile(r'^\s*(\d+)\s*[:\-_]\s*(\d+)\s*$')


def parse_coord(text):
    """把 '216:35' 解析成 (216, 35)。也接受 216-35 / 216_35。"""
    m = COORD_RE.match(str(text))
    if not m:
        raise WpError(f"坐标格式不对：{text}（应为 book:paragraph，如 216:35）")
    return int(m.group(1)), int(m.group(2))


def parse_coords(items):
    """解析一串坐标，按 book 分组，返回 {book: [paragraph, ...]}（去重、保序）。"""
    grouped = {}
    for item in items:
        for part in str(item).split(','):
            if not part.strip():
                continue
            book, para = parse_coord(part)
            paras = grouped.setdefault(book, [])
            if para not in paras:
                paras.append(para)
    return grouped


def fmt_coord(book, paragraph):
    return f"{book}:{paragraph}"


# 检索结果 ref[].type → 显示名；WP 另行处理（它的 page 就是段落号）
REF_EDITIONS = (('My', '缅'), ('PTS', 'PTS'), ('VRI', 'VRI'), ('Thai', '泰'))


def fmt_cite(book, paragraph, refs, link=None):
    """出处 = citation + WikiPali 链接，合成一个 Markdown 链接：

        [dī.ni.ṭī.2. 186:1411; 缅 dī-ṭī 2 p.340; PTS DnT II p.429](https://…/read#1411)

    citation 取自检索结果的 ref：WP 缩写 + 坐标，再加该段真有的印本页码。没有链接时
    只给 citation 文字，不自己拼链接。
    """
    by_type = {r.get('type'): r for r in (refs or []) if isinstance(r, dict)}
    wp = by_type.get('WP')
    head = f"{wp['title']} " if wp and wp.get('title') else ''
    parts = [f"{head}{book}:{paragraph}"]
    for key, label in REF_EDITIONS:
        r = by_type.get(key)
        if r and r.get('page') is not None:
            title = f" {r['title']}" if r.get('title') else ''
            parts.append(f"{label}{title} p.{r['page']}")
    text = '; '.join(parts)
    return f'[{text}]({link})' if link else text


def fmt_path(path, sep=' › ', max_items=4):
    """把检索结果的 path 数组压成一行章节路径。"""
    if not path:
        return ''
    titles = [p.get('title', '') for p in path if isinstance(p, dict) and p.get('title')]
    if len(titles) > max_items:
        titles = [titles[0], '…'] + titles[-(max_items - 2):]
    return sep.join(titles)


def text_layer(tags):
    """按 tags 判断文献层次：根本 / 义注 / 复注。引用时必须标明，混用是学术错误。"""
    names = {t.get('name') for t in (tags or []) if isinstance(t, dict)}
    if 'ṭīkā' in names:
        return 'ṭīkā'
    if 'aṭṭhakathā' in names:
        return 'aṭṭhakathā'
    if 'mūla' in names:
        return 'mūla'
    return ''
