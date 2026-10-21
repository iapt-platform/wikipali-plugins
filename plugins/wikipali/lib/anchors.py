"""批注锚点：按原文摘录在句子原始 content 里定位，算出 pos_start / pos_end 与前后缀。

锚点是 W3C Web Annotation 的 TextPosition（`pos_start` / `pos_end`）+ TextQuote
（`quote_exact` / `quote_prefix` / `quote_suffix`）。位置按句子**原始 content** 的字符计
（0 起、含标点、`pos_end` 不含），与服务端 `mb_strlen` 同一口径——Python 的 str 下标就是。

位置交给程序算，不让模型数：模型数中文字符位极易数错，而摘录（原样抄一段文字）很少出错。
`note-push`（注释对照）与 `discuss-add` / `discuss-edit`（批注、issue、外挂术语）都用这里。
"""

import re

from errors import WpError

# 前后缀取多长：设计文档建议 32~64 字符
CONTEXT_CHARS = 32

# 外挂术语渲染成 `[[词头#原文]]`：原文与词头里有这些字符会把标记拆坏，服务端会直接放弃这条
# （api-v13 AnnotationLayout::GLOSSARY_FORBIDDEN）
GLOSSARY_FORBIDDEN = re.compile(r'[\[\]{}|#\r\n]')
# 句子里已有的标记：模板、术语、行内注释、粗体、HTML 标签（AnnotationLayout::PROTECTED_PATTERN）。
# 外挂术语碰到它们，服务端也会放弃这条
PROTECTED = re.compile(r'\[\[.*?\]\]|\{\{.*?\}\}|`[^`]*`|\*\*.+?\*\*|<[^<>]+>', re.S)


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


def check_glossary(text, start, end, title):
    """外挂术语的两样东西能不能渲染成 `[[词头#原文]]`；不能就报错（服务端会静默放弃这条）。"""
    word = (title or '').strip()
    if not word:
        raise WpError('外挂术语要给 --title：术语的词头（巴利词，如 bhikkhu）。')
    if GLOSSARY_FORBIDDEN.search(word):
        raise WpError(f'词头「{word}」里不能有 [ ] {{ }} | # 或换行。')
    if start is None or end is None:
        raise WpError('外挂术语要指明挂在译文的哪一段：给 --quote-exact <原样摘录>。')
    covered = text[start:end]
    if GLOSSARY_FORBIDDEN.search(covered):
        raise WpError(f'摘录「{covered}」里有 [ ] {{ }} | # 或换行，渲染不了外挂术语；换个摘录范围。')
    for m in PROTECTED.finditer(text):
        if m.start() < end and start < m.end():
            raise WpError(f'摘录「{covered}」与句中已有的标记「{m.group(0)}」重叠，'
                          '外挂术语不能套在已有术语 / 模板 / 格式上；换个摘录范围。')
