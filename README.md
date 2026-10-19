# textclean 🧹

Clean messy text copied from PDFs and web pages — Chinese-aware. Stdlib only, zero dependencies.

专治从 PDF / 网页复制来的脏文本：硬换行、全半角混乱、零宽字符。纯标准库，零依赖。

## Install

```bash
pip install .
# or just run it: python3 textclean.py
```

## Usage

```bash
# Pipe mode
cat messy.txt | textclean
pbpaste | textclean | pbcopy

# File mode
textclean in.txt -o out.txt

# Preview the diff without writing anything
textclean in.txt --dry-run

# Skip punctuation normalization
textclean in.txt --no-punct
```

## Example

Before (copied from a PDF — broken lines, mixed punctuation, zero-width chars):

```
这是从 PDF 里复制出
来的一段中文，被硬换行
切断了，标点还是半角,很乱;还有全角ＡＢＣ１２３。

This is an English sen-
tence broken by hyphen,
and here is 3.14 with numbers.

​零宽字符​在这里，还有不少空
　　行　　和全角空格。



多余的空行上面有三个。
```

After (`cat messy.txt | textclean`):

```
这是从 PDF 里复制出来的一段中文，被硬换行切断了，标点还是半角，很乱；还有全角ABC123。

This is an English sentence broken by hyphen， and here is 3.14 with numbers。

零宽字符在这里，还有不少空行 和全角空格。

多余的空行上面有三个。
```

## Cleaning rules 清洗规则

- **Merge hard-wrapped lines**：中文字符间的换行直接合并，英文单词间的换行转空格，连字符断行（`sen-\ntence`）自动拼接
- **Punctuation normalization**：中文标点转全角（`,`→`，` `;`→`；`），字母数字转半角（`ＡＢＣ`→`ABC`），小数点 `3.14` 不动，引号自动配对（`"`→`""`）
- **Whitespace**：连续空白压缩，首尾空行去除，多余空行合并为一段分隔
- **Invisible chars**：去除零宽字符（`\u200b` 等）与 BOM

## License

MIT
