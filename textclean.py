#!/usr/bin/env python3
"""textclean - Clean messy text copied from PDFs and web pages (Chinese-aware).
Pure stdlib, zero dependencies.

Usage:
    cat messy.txt | textclean              # pipe mode
    pbpaste | textclean | pbcopy           # clipboard mode
    textclean in.txt -o out.txt            # file mode
    textclean in.txt --dry-run             # preview diff only
"""
import argparse
import difflib
import re
import sys

# Zero-width chars / BOM
ZERO_WIDTH = "\u200b\u200c\u200d\u2060\u200e\u200f\ufeff"

# Half-width -> full-width punctuation
HALF2FULL = {
    ",": "\uff0c", ";": "\uff1b", ":": "\uff1a", "?": "\uff1f", "!": "\uff01",
    "(": "\uff08", ")": "\uff09", "[": "\u3010", "]": "\u3011",
}


def is_cjk(ch):
    """True for CJK characters (incl. punctuation and fullwidth forms)."""
    o = ord(ch)
    return (
        0x4E00 <= o <= 0x9FFF      # CJK Unified Ideographs
        or 0x3400 <= o <= 0x4DBF   # Extension A
        or 0x20000 <= o <= 0x2A6DF  # Extension B
        or 0x3040 <= o <= 0x30FF   # Hiragana/Katakana
        or 0xAC00 <= o <= 0xD7AF   # Hangul
        or 0x3000 <= o <= 0x303F   # CJK Symbols and Punctuation
        or 0xFF00 <= o <= 0xFFEF   # Fullwidth Forms
        or 0xF900 <= o <= 0xFAFF   # CJK Compatibility Ideographs
    )


def _join_pair(buf, line):
    """Append next line to buf, return new buf."""
    prev, nxt = buf[-1], line[0]
    # Hyphenated break: infor-\nmation -> information
    if prev == "-" and nxt.isascii() and nxt.islower():
        return buf[:-1] + line
    cjk_p, cjk_n = is_cjk(prev), is_cjk(nxt)
    if cjk_p or cjk_n:
        return buf + line  # CJK-CJK or CJK-latin: join directly
    # Pure ASCII region
    if prev.isalnum() and nxt.isalnum():
        return buf + " " + line
    if prev in ",;:!?":
        return buf + " " + line      # space after punctuation
    if nxt in ".,;:!?%)]}":
        return buf + line            # no space before closing punct
    if prev in "([{":
        return buf + line            # no space after opening punct
    return buf + " " + line


def join_lines(text):
    """Merge hard-wrapped lines; blank lines stay as paragraph breaks."""
    paras = []
    buf = ""

    def flush():
        nonlocal buf
        if buf:
            paras.append(buf)
            buf = ""

    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            flush()
            continue
        buf = line if not buf else _join_pair(buf, line)
    flush()
    return "\n\n".join(paras)


def _pair_quotes(text, ascii_q, open_q, close_q):
    """Pair straight quotes into open/close quotes in order."""
    res = []
    opening = True
    for ch in text:
        if ch == ascii_q:
            res.append(open_q if opening else close_q)
            opening = not opening
        else:
            res.append(ch)
    return "".join(res)


def normalize_punct(text):
    """Full/half-width normalization: CJK punct -> full-width, alnum -> half-width."""
    # Full-width alphanumerics -> half-width
    out = []
    for ch in text:
        o = ord(ch)
        if (0xFF10 <= o <= 0xFF19 or 0xFF21 <= o <= 0xFF3A
                or 0xFF41 <= o <= 0xFF5A or 0xFF61 <= o <= 0xFF7A):
            out.append(chr(o - 0xFEE0))
        else:
            out.append(ch)
    text = "".join(out)
    # Ellipsis
    text = text.replace("...", "\u2026\u2026").replace("\u2026", "\u2026\u2026")
    # Protect decimal points: keep the dot in 3.14
    text = re.sub(r"(?<=\d)\.(?=\d)", "\x00", text)
    for half, full in HALF2FULL.items():
        text = text.replace(half, full)
    text = text.replace(".", "\u3002")  # remaining half-width periods
    text = text.replace("\x00", ".")
    # Pair quotes
    text = _pair_quotes(text, '"', "\u201c", "\u201d")
    text = _pair_quotes(text, "'", "\u2018", "\u2019")
    return text


def clean(text, punct=True):
    # 1. Strip zero-width chars / BOM
    for z in ZERO_WIDTH:
        text = text.replace(z, "")
    # 2. Normalize newlines
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 3. Merge hard-wrapped lines
    text = join_lines(text)
    # 4. Full/half-width punctuation normalization
    if punct:
        text = normalize_punct(text)
    # 5. Compress whitespace inside paragraphs, drop edge blank lines
    paras = [re.sub(r"[ \t\u00a0\u3000]+", " ", p).strip()
             for p in text.split("\n\n")]
    return "\n\n".join(p for p in paras if p)


def main():
    ap = argparse.ArgumentParser(
        prog="textclean",
        description="Clean messy text copied from PDFs/web pages (Chinese-aware). Stdlib only.",
    )
    ap.add_argument("infile", nargs="?", help="input file (reads stdin if omitted)")
    ap.add_argument("-o", "--out", help="output file (stdout if omitted)")
    ap.add_argument("--dry-run", action="store_true",
                    help="show diff preview only, write nothing")
    ap.add_argument("--no-punct", action="store_true",
                    help="skip full/half-width punctuation normalization")
    ap.add_argument("--encoding", default="utf-8",
                    help="input file encoding (default utf-8)")
    args = ap.parse_args()

    if args.infile:
        enc = ("utf-8-sig"
               if args.encoding.lower().replace("-", "") == "utf8"
               else args.encoding)
        with open(args.infile, encoding=enc) as f:
            text = f.read()
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        ap.error("no input: give a file or pipe text via stdin")

    cleaned = clean(text, punct=not args.no_punct)

    if args.dry_run:
        diff = difflib.unified_diff(
            text.splitlines(), cleaned.splitlines(),
            "before", "after", lineterm="",
        )
        sys.stdout.write("\n".join(diff) + "\n")
        return

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(cleaned)
    else:
        sys.stdout.write(cleaned)


if __name__ == "__main__":
    main()
