---
name: citation
description: "Use this skill to resolve an abbreviated Pali/Burmese source citation — such as ဝိသုဒ္ဓိ၊၂၊၂၄၁, မဟာဋီ-၂-၄၀၁, ပြည်-ဝိသုဒ္ဓိမဂ်နိဿယ-၃-၂၄၁, 阿毗达摩义注 2,47, or a romanised form like vism-2-241 — into the work it names and the WikiPali coordinate book-paragraph, optionally with the full page of Pali text and its chapter path. Trigger whenever the user shows a citation abbreviation from a Burmese Buddhist text and asks which book and where it is, what 缩写/引用/出处 it refers to, where to find it in WikiPali, or pastes a bracketed reference they cannot read. Do not use for searching the corpus by word (that is the research skill)."
---

# 解析引用缩写

缅甸佛教著作的脚注写成 `<书的缩写>၊<册>၊<页>`，例如 `ဝိသုဒ္ဓိ၊၂၊၂၄၁`。把它解析成
**哪一部著作、WikiPali 的哪个坐标**，需要时连整页原文与章节路径一起给出。

## 分工

| 谁 | 干什么 | 为什么 |
|---|---|---|
| **你** | 认出这是哪部著作，拆出册与页 | 缩写写法千变万化——缅文、罗马化、中文异名、简写、错字。这是判断，不是查表 |
| `wikipali page` | 把页码换算成坐标与段落区间 | 走服务端的 `nav-page`，页码标记的权威数据在那边 |

**表格发出去就冻在用户机器上了。** 所以认书这一步绝不能靠程序做字符串比对——遇到一个
新写法就得等下次发版。`references/citation-abbrev.tsv` 是给**你**看的参考，不是查找键：
看懂它，然后自己判断。

## 流程

**1. 读参考表，判断是哪部著作。**

```bash
cat ${CLAUDE_PLUGIN_ROOT}/references/citation-abbrev.tsv     # 75 行 8KB，可以整读
```

列是 `abbrev_my`（缅文写法，`|` 分隔多种）、`work_pali`、`work_zh`、`kind`（文献层次）、
`pcd`、`note`。判断时该用上你知道的一切：

- **缅文缩写**：`ဋ္ဌ` = `အဋ္ဌကထာ`（义注）、`ဋီ` = `ဋီကာ`（复注）、
  `ပြည်` = 卑谬版（版本前缀，不是书名的一部分）
- **中文异名**：表里写「论藏义注」，用户可能说「阿毗达摩义注」「阿毗昙义注」；
  「大复注」也叫「清净道论大疏钞」
- **罗马化**：`vism` / `visuddhimagga` / `Vism`，变音符可有可无
- **子著作名**：用户可能直接说「殊胜义」「迷惑冰消」——那是论藏义注的第 1、2 册，
  要落到 `books` 列里对应的那个 book

**认不出就说认不出。** 缅文缩写彼此形近（`မ`＝中部、`မဟာဋီ`＝大复注、`မူလဋီ`＝根本复注），
差一个字就是另一部书。请用户给上下文（脚注前后常有全名），**不要挑一个像的顶上**。

**2. 拆出册与页。** 缅文数字 `၀၁၂၃၄၅၆၇၈၉` = `0123456789`。分隔符 `၊ ။ - 、 , .` 空格
都用过，同一篇里还会混用。最后一个数字是页码，前一个（若有）是册号；
`သံ၊၂၊၂၄၉-၂၅၀` 是页码范围；只有一个数字的是不分册的书。

**3. 定候选 pcd。** 看 `pcd` 列——**`pcd` 是按著作编的号**（`pcd_book_id`），
一本 book 收几部就有几个 pcd，正好能分开同一本书里各自编页的多部著作：

- `*=70,71` —— 页码自带册号，把这些 pcd 全给命令，它按册页自己挑
- `1=102;2=103;3=104,105,106,107,108` —— 页码里**没有**册号（缅甸版论藏义注三册
  都从第 1 页起编），必须你按册号挑：第 2 册就只给 `--pcd 103`。全给会撞车，
  命令会警告但仍以第一处作答

**4. 跑命令。**

```bash
wikipali page 2.241 --pcd 70,71                    # <册>.<页>
wikipali page 47 --pcd 103 --text                  # 不分册的只给页；--text 连原文与路径
wikipali page 2.249-250 --pcd 186,187,188,189,190  # 页码范围
wikipali page V2.240 --pcd 71                      # V=VRI P=PTS T=泰版，四版都支持
```

**5. 照结果回答**：著作名（巴利＋中文）、文献层次、WikiPali 书名、坐标
`book-paragraph`、**出处（citation＋WikiPali 链接）**，以及 `wikipali get <book>:<para>`。
出处用 `wikipali ref <book>:<para>` 取，它给出该段在各印本的页码与网页链接，**必须附上**
（格式见 `references/conventions.md`）。其中缅甸版页码应与引用本身一致，不一致就说明
定位有问题，如实告诉用户。

## 铁律

1. **页码不是段落号。** 清净道论第 2 册第 241 页是 `65:1461`，**不是** `65:241`——
   后者是完全不相干的另一段。**绝不许**把引用里的数字直接写成坐标，一律经
   `wikipali page` 换算。
2. **命令报「⚠ 候选里还有一处也有这一页」时，别当成确定答案。** 那说明候选 pcd 给宽了，
   按册号收窄再跑。报「这些著作里没有这一页」则是册页不对或书判断错了——回到第 1 步，
   别拿相近的书顶上。
3. **缅文著作在 WikiPali 里没有对应。** 尼思耶（`နိဿယ`）、缅文复注（`ဘာသာဋီကာ`）、
   缅文纲要书（`ကျမ်း`）都是缅文写的，WikiPali 收的是巴利文献；表里 `kind` 记作
   `nissaya` / `burmese`，`pcd` 为空。这类只能报出**底本**是哪部巴利著作，
   **册页不能换算**——缅文本的分册与巴利本不是一回事。
4. **页码指的是该页起始处。** 一页横跨好几段。命令给出的区间是
   `[本页起始段 … 下一页起始段]`，**末段与下一页共享**，本页在它中间某处结束。
   `wid` 是页在该段内的起始词，需要更精确时用得上。

## `--text` 取到什么

- **整页巴利原文**：`[本页起始段 … 下一页起始段]`。
- **章节路径**：取自 `palitext/{book}-{para}` 的 `path`，从丛书一路到小节，如
  `visuddhimagga › Visuddhimaggo(Dutiyo bhāgo) › 20. Maggāmagga… › Sammasanañāṇakathā`。
  **直接用，不要自己拼章节名。**

原文里夹着的 `[M2.241]`、`[V2.240]` 是各版页码标记，**留在原位**——抽掉就丢了位置信息
（见 `references/conventions.md`）。

请求数：不加 `--text` 是 1–2 次（候选给多个时多一次撞车核查），加了 `--text` 是 3–4 次。

## 数据

| 文件 | 给谁看 |
|---|---|
| `references/citation-abbrev.tsv` | **你**。75 部著作：缅文写法、巴利名、中文名、层次、候选 `pcd` |
| `references/citation-books.tsv` | 对照用。275 部著作：`pcd`、`book`、起始段 `para`、`toc` 书名 |

页码换算走服务端 `GET /v2/nav-page/{版本}-{pcd}-{册}-{页}`（见 `references/api-read.md` §13），
数据源是 `page_numbers` 表，与正文里 `<code>M2.241</code>` 标记同源。表里没有的著作，
只要你能认出是哪部巴利文献，在 `citation-books.tsv` 里按书名 `grep` 出 `pcd` 一样能查。

⚠ **`citation-books.tsv` 不要整读进上下文**（275 行），`grep` 需要的那几行就够。

## 边界

- 缩写表来自一份具体缅文著作的引文统计（173 条引用、75 部著作），**不是全集**。
- **四个版本都支持**：`M`=缅甸版、`V`=VRI、`P`=PTS、`T`=泰版。缅甸引用写的是 M，
  西方学界引的多是 PTS 页码，写成 `P1.123` 一样查。
- 有页码标记的著作约 200 部；语法书、缅文著作等没有，查不到就是没有。
- **这个命令要联网**（换算在服务端）。离线时只能靠你自己按表判断是哪部著作，
  给不出段落号——如实说明。
