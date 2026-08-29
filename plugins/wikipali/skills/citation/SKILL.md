---
name: citation
description: "Use this skill to resolve an abbreviated Pali/Burmese source citation — such as ဝိသုဒ္ဓိ၊၂၊၂၄၁, မဟာဋီ-၂-၄၀၁, ပြည်-ဝိသုဒ္ဓိမဂ်နိဿယ-၃-၂၄၁, or a romanised form like vism-2-241 — into the work it names and the WikiPali coordinate book-paragraph. Trigger whenever the user shows a citation abbreviation from a Burmese Buddhist text and asks which book and where it is, what 缩写/引用/出处 it refers to, where to find it in WikiPali, or pastes a bracketed reference they cannot read. Do not use for searching the corpus by word (that is the research skill)."
---

# 解析引用缩写

缅甸佛教著作的脚注习惯写成 `<书的缩写>၊<册>၊<页>`，例如 `ဝိသုဒ္ဓိ၊၂၊၂၄၁`。
本 skill 把它解析成**哪一部著作、WikiPali 的哪个坐标**。

一条命令，**离线**，不发请求也不需要登录，百毫秒出结果：

```bash
wikipali cite 'ဝိသုဒ္ဓိ၊၂၊၂၄၁'
wikipali cite 'မဟာဋီ-၂-၄၀၁' 'ပြည်-ဝိသုဒ္ဓိမဂ်နိဿယ-၃-၂၄၁' 'vism-2-241'
```

```
ဝိသုဒ္ဓိ၊၂၊၂၄၁
  缩写   : ဝိသုဒ္ဓိ   第 2 册  缅甸版第 241 页
  著作   : Visuddhimagga　清净道论　（aṭṭhakathā）
  → 书名 : Visuddhimaggo(Dutiyo bhāgo)
  → 坐标 : 65-1461　（页码标记 M2.0241 落在这一段）
  取原文 : wikipali get 65:1461
```

⚠ **刚装好或刚更新插件时 `wikipali` 可能还不在 PATH 上**——PATH 注入在会话启动时完成。
若 `command -v wikipali` 为空，改用 `${CLAUDE_PLUGIN_ROOT}/bin/wikipali`，并提醒用户重启会话。

## 铁律

1. **页码不是段落号，中间隔着一张索引表。** 清净道论第 2 册第 241 页是 `65:1461`，
   **不是** `65:241`——后者是完全不相干的另一段。**绝不许**把引用里的数字直接当段落号
   写成坐标，一定要经 `wikipali cite` 换算。
2. **表里没有的缩写就说没有。** 缅文缩写彼此形近（`မ`＝中部、`မဟာဋီ`＝大复注、
   `မူလဋီ`＝根本复注），差一个字就是另一部书。命令报「表里没有这个缩写」时，如实说
   不认识，请用户给出上下文（前后文里常有全名），不要挑一个像的顶上。
3. **缅文著作在 WikiPali 里没有对应。** 尼思耶（`နိဿယ`）、缅文复注（`ဘာသာဋီကာ`）、
   缅文纲要书（`ကျမ်း`）都是缅文写的，WikiPali 收的是巴利文献。这类引用只能报出
   **底本**是哪部巴利著作，**册页不能换算**——缅文本的分册与巴利本不是一回事。
4. **标记指的是该页的起始处。** 一页往往横跨好几段，引文可能落在标出的那一段，也可能
   在它后面几段。给用户坐标时说清楚这一点；要精确定位就把那一段前后读出来核对。

## 给用户怎么答

照命令的输出说：**著作名（巴利＋中文）、文献层次、WikiPali 书名、坐标 `book-paragraph`**，
并把 `wikipali get <book>:<para>` 一并给出去，用户想看原文可以直接跑。

定不到位置时命令会说明原因并列出候选，照实转述，**不要从候选里随便挑一个**。

## 数据（都在插件里，不要联网取）

| 文件 | 内容 |
|---|---|
| `references/citation-abbrev.tsv` | 缩写（缅文写法 \| 罗马化别名）→ 著作、中文名、候选 book、册号对照 `vol_map`、文献层次、备注。75 部著作、173 个写法 |
| `references/citation-books.tsv` | WikiPali 收的**每一部著作**一行：`book`、起始段 `para`、**toc 书名**（书名取 `toc` 字段，不是 `title`）、tags、缅甸版册与页码区间 |
| `references/citation-pages.tsv.gz` | 页码标记索引：`M<册>.<页四位>` → `book`、`paragraph`。6.2 万条，覆盖 197 本书。就是它把页码变成段落号 |

页码索引是从 WikiPali 数据库的 `wbw_templates` 表导出的（`type='.ctl.'` 的控制词就是
版面标记），与正文里 `<code>M2.241</code>` 的位置是同一份数据。手工查：

```bash
zgrep -P '^M2\.0241\t' ${CLAUDE_PLUGIN_ROOT}/references/citation-pages.tsv.gz
```

## 命令解析不了时，手工按这个来

⚠ **用 `grep` 取需要的那一行，别把表整个读进上下文。** 两张表合起来 40KB、三百多行缅文，整读一遍既占地方又容易看错字——正常路径下这些数据是 Python 读的，模型只该看到结果。

1. **缅文数字转阿拉伯数字**：`၀၁၂၃၄၅၆၇၈၉` = `0123456789`。
2. **按分隔符切开**：`၊`（缅文逗号）、`။`、`-`、`、`、`,`、`.`、空格都用过，同一份文献里
   甚至混着用（`ဝိသုဒ္ဓိ၊၂၊၂၅၁` 与 `ဝိသုဒ္ဓိ-၂-၂၄၁` 是同一种写法）。
3. **非数字的部分拼回书名**，用 `-` 连接：`အဘိ၊ဋ္ဌ၊၂၊၂၅၂` 的书名是 `အဘိ-ဋ္ဌ`（论藏义注）。
   `ဋ္ဌ` 是 `အဋ္ဌကထာ`（义注）的缩写，`ဋီ` 是 `ဋီကာ`（复注）的缩写。
4. **数字部分**：最后一个是页码，前一个（若有）是册号；`သံ၊၂၊၂၄၉-၂၅၀` 是页码范围。
   只有一个数字就是不分册的书（如 `ပဋိသံ၊၅၂` 无碍解道第 52 页）。
5. **版本前缀**要认出来：`ပြည်` 是「卑谬版」，属于版本而非书名的一部分。
6. 拿书名查 `citation-abbrev.tsv` 的 `abbrev_my`（多种写法用 `|` 分隔）或 `aliases`
   （罗马化，去变音符后小写比对），得到候选 book——`grep 'ဝိသုဒ္ဓိ' references/citation-abbrev.tsv`
   取那一行就够。
7. 在页码索引里查 `M<册>.<页补足四位>`，**限定在候选 book 内**——同一个标记在别的书里
   也有（每部著作各有自己的一套页码）。命中的 `book` + `paragraph` 就是答案。

## 两个容易踩的坑

- **不分册的著作标记成 `M0.<页>`**，不是「第 0 册」。命令在 `M<册>` 查不到时会自动
  退回 `M0` 再查一次。
- **有些书组的标记里根本没有册号。** 缅甸版论藏义注三册都标成 `M0.xxxx`，靠标记分不出
  是哪一册，只能靠 `citation-abbrev.tsv` 的 `vol_map`（`1=96;2=97;3=98`）把册定死，
  再用页码定册内的哪一部。根本复注、随复注同此结构。

## 数据的边界

- 缩写表来自一份具体的缅文著作的引文统计（173 条引用、75 部著作），**不是缅甸引用缩写
  的全集**。冷僻缩写查不到很正常，如实说。
- 页码索引只收了**缅甸版（M）**。同一张表里还有 VRI（V）、PTS（P）、泰版（T）的标记，
  需要时可以从 `wbw_templates` 再导。
- 197 本书有缅甸版页码标记；其余的（语法书、缅文著作、部分纲要书）没有，查不到就是没有。
