#!/usr/bin/env python3
"""Convert Finlex consolidated-legislation Akoma Ntoso XML (as extracted by
fetch.py) into LawCodex Markdown files, in Finnish (fi/) and Swedish (sv/).

Only statutes flagged as in force (finlex:isInForce = true) and carrying a
consolidated text (i.e. not a `contentAbsent` stub) are written.

Usage: convert.py [RAW_DIR] [REPO_DIR]
  RAW_DIR  default ../../_raw/fi        (expects RAW_DIR/xml/<year>/<number>/{fin,swe}.xml)
  REPO_DIR default ..                   (the fi repository checkout)
"""
import datetime
import json
import os
import re
import sys
import unicodedata

from lxml import etree

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "_raw", "fi"))
REPO = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, ".."))
RETRIEVED = os.environ.get("RETRIEVED", datetime.date.today().isoformat())

A = "{http://docs.oasis-open.org/legaldocml/ns/akn/3.0}"
F = "{http://data.finlex.fi/schema/finlex}"
API = "https://opendata.finlex.fi/finlex/avoindata/v1"

LANGS = {
    "fin": {
        "code": "fi",
        "web": "https://www.finlex.fi/fi/lainsaadanto/{year}/{num}",
        "dirs": {
            "constitution": "perustuslaki",
            "act": "lait",
            "decree": "asetukset",
            "decision": "paatokset",
            "other": "muut",
        },
    },
    "swe": {
        "code": "sv",
        "web": "https://www.finlex.fi/sv/lagstiftning/{year}/{num}",
        "dirs": {
            "constitution": "grundlag",
            "act": "lagar",
            "decree": "forordningar",
            "decision": "beslut",
            "other": "ovriga",
        },
    },
}

CONSTITUTION = ("1999", "731")

CONTAINERS = {"part", "book", "title", "chapter", "subchapter", "division", "subdivision"}
ITEMS = {"paragraph", "subparagraph", "point", "item", "list"}
TRANSPARENT_HC = {"statuteProvisionsWrapper", "statuteTextWrapper", "entryIntoForceStart"}


def local(tag):
    if not isinstance(tag, str):
        return ""
    if tag.startswith(A):
        return tag[len(A):]
    if tag.startswith(F):
        return "finlex:" + tag[len(F):]
    return tag


# ---------------------------------------------------------------------------
# inline rendering


def _indent_of(text):
    """Indentation inserted by the XML pretty-printer before child elements."""
    if text and "\n" in text:
        tail = text.rsplit("\n", 1)[1]
        if tail.strip() == "":
            return len(tail)
    return None


def _clean(s, n):
    if not s:
        return ""
    if n is not None:
        s = s.replace("\n" + " " * n, "")
    return s.replace("\n", " ").replace("\t", " ")


def esc_md(s):
    s = s.replace("\\", "\\\\")
    s = re.sub(r"<(?=[A-Za-z/!?])", "&lt;", s)
    s = re.sub(r"([*_`\[\]])", r"\\\1", s)
    return s


def esc_html(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Ctx:
    def __init__(self, year, num, langver, lang):
        self.year, self.num, self.langver, self.lang = year, num, langver, lang

    def media(self, src):
        if re.match(r"https?://", src):
            return src
        src = src.lstrip("./")
        return f"{API}/akn/fi/act/statute-consolidated/{self.year}/{self.num}/{self.langver}/{src}"


def inline(el, ctx, html=False, skip=("num", "heading")):
    """Render the mixed content of `el` as a single line (Markdown or HTML)."""
    n = _indent_of(el.text) if len(el) else None
    e = esc_html if html else esc_md
    out = [e(_clean(el.text, n))]
    for c in el:
        t = local(c.tag)
        if t in skip and el.tag != c.tag:
            pass
        elif not isinstance(c.tag, str):
            pass
        else:
            out.append(inline_el(c, ctx, html))
        out.append(e(_clean(c.tail, n)))
    return "".join(out)


def _wrap(inner, l, r):
    m = re.match(r"^(\s*)(.*?)(\s*)$", inner, re.S)
    if not m.group(2):
        return inner
    return f"{m.group(1)}{l}{m.group(2)}{r}{m.group(3)}"


def inline_el(c, ctx, html):
    t = local(c.tag)
    inner = inline(c, ctx, html, skip=())
    if t in ("i", "em"):
        return _wrap(inner, "<i>", "</i>") if html else _wrap(inner, "*", "*")
    if t in ("b", "strong"):
        return _wrap(inner, "<b>", "</b>") if html else _wrap(inner, "**", "**")
    if t == "u":
        return _wrap(inner, "<u>", "</u>")
    if t in ("sup", "sub"):
        return _wrap(inner, f"<{t}>", f"</{t}>")
    if t == "br":
        return "<br>"
    if t == "img":
        url = ctx.media(c.get("src", ""))
        return f'<img src="{url}" alt="">' if html else f"![]({url})"
    if t == "a":
        href = c.get("href", "")
        if href and not href.startswith("#"):
            url = ctx.media(href)
            return f'<a href="{url}">{inner.strip()}</a>' if html else f"[{inner.strip()}]({url})"
        return inner
    if t == "authorialNote":
        txt = " ".join(inline(p, ctx, html) for p in c if isinstance(p.tag, str))
        return f" [{txt.strip()}]"
    if t == "finlex:latex":
        tex = (c.text or "").strip().strip("$").strip()
        return f"${tex}$"
    if t == "p":
        return inner + (" <br> " if html else " ")
    # ref, affectedDocument, span, docNumber, docTitle, foreign, etc.
    return inner


def norm(s):
    s = re.sub(r"[  ]{2,}", lambda m: " " if " " not in m.group(0) else m.group(0), s)
    s = re.sub(r" {2,}", " ", s)
    return s.strip()


def text_line(el, ctx, html=False):
    return norm(inline(el, ctx, html))


def safe_line(s):
    """Escape characters that would turn a plain paragraph into Markdown block syntax."""
    s = re.sub(r"^(#{1,6}\s|>|[-+*]\s|=+\s*$|-{3,}\s*$)", lambda m: "\\" + m.group(1), s)
    s = re.sub(r"^(\d+)([.)])(\s)", r"\1\\\2\3", s)
    return s


# ---------------------------------------------------------------------------
# block rendering


def plain(el):
    return norm(" ".join("".join(el.itertext()).split()))


def heading_text(el, ctx):
    num = el.find(A + "num")
    head = el.find(A + "heading")
    parts = []
    if num is not None:
        parts.append(text_line(num, ctx))
    if head is not None:
        parts.append(text_line(head, ctx))
    txt = " ".join(p for p in parts if p)
    label = el.get(F + "originalVersionLabel")
    if label and label not in txt:
        txt = f"{txt} ({label})".strip()
    if head is not None:
        hl = head.get(F + "originalVersionLabel")
        if hl and hl not in txt:
            txt = f"{txt} ({hl})"
    return txt


def H(level, txt):
    txt = txt.strip()
    if level <= 6:
        return "#" * level + " " + (txt or "—")
    return f"**{txt}**"


def add_label(blocks, el):
    label = el.get(F + "originalVersionLabel")
    if label and blocks:
        last = blocks[-1].rstrip()
        if not last.endswith(f"({label})") and not last.startswith("|") and not last.startswith("<table"):
            blocks[-1] = f"{last} ({label})"
    return blocks


def table(el, ctx):
    rows = [r for r in el.iter(A + "tr")]
    if not rows:
        return []
    simple = True
    grid = []
    for r in rows:
        cells = [c for c in r if local(c.tag) in ("td", "th")]
        row = []
        for c in cells:
            if c.get("colspan") not in (None, "1") or c.get("rowspan") not in (None, "1"):
                simple = False
            kids = [k for k in c if isinstance(k.tag, str)]
            if len(kids) > 1 or any(local(k.tag) not in ("p",) for k in kids) or c.find(".//" + A + "img") is not None:
                simple = False
            row.append(c)
        grid.append(row)
    widths = {len(r) for r in grid}
    if simple and len(widths) == 1 and widths != {0}:
        lines = []
        for i, row in enumerate(grid):
            cells = [text_line(c, ctx).replace("|", "\\|") for c in row]
            lines.append("| " + " | ".join(cells) + " |")
            if i == 0:
                lines.append("|" + "|".join(["---"] * len(row)) + "|")
        return ["\n".join(lines)]
    out = ["<table>"]
    caption = el.find(A + "caption")
    if caption is not None:
        out.append(f"<caption>{text_line(caption, ctx, html=True)}</caption>")
    for row in grid:
        out.append("<tr>")
        for c in row:
            attrs = ""
            for a in ("colspan", "rowspan"):
                if c.get(a) not in (None, "1"):
                    attrs += f' {a}="{c.get(a)}"'
            tag = "th" if local(c.tag) == "th" else "td"
            paras = [k for k in c if isinstance(k.tag, str)]
            if paras:
                content = "<br>".join(cell_html(k, ctx) for k in paras)
            else:
                content = text_line(c, ctx, html=True)
            out.append(f"<{tag}{attrs}>{content}</{tag}>")
        out.append("</tr>")
    out.append("</table>")
    return ["\n".join(out)]


def cell_html(k, ctx):
    t = local(k.tag)
    if t == "table":
        return "".join(table(k, ctx)).replace("\n", "")
    if t == "block" and k.get("name") == "image":
        return " ".join(cell_html(x, ctx) for x in k if isinstance(x.tag, str))
    if t == "img":
        return inline_el(k, ctx, True)
    return text_line(k, ctx, html=True)


def image_block(el, ctx):
    out = []
    for c in el:
        t = local(c.tag)
        if t == "img":
            out.append(f"![]({ctx.media(c.get('src', ''))})")
        elif isinstance(c.tag, str):
            s = text_line(c, ctx)
            if s:
                out.append(f"*{s}*" if c.get("class") == "caption" else s)
    return ["\n\n".join(out)] if out else []


def render_children(el, ctx, level, skip=("num", "heading")):
    blocks = []
    kids = [c for c in el if isinstance(c.tag, str)]
    has_cross = any(local(c.tag) == "crossHeading" for c in kids)
    for c in kids:
        t = local(c.tag)
        if t in skip:
            continue
        if t == "crossHeading":
            blocks.append(H(level, heading_text_inline(c, ctx)))
            continue
        blocks.extend(render(c, ctx, level + 1 if has_cross and t in ("section",) else level))
    return blocks


def heading_text_inline(el, ctx):
    txt = text_line(el, ctx)
    label = el.get(F + "originalVersionLabel")
    if label and label not in txt:
        txt = f"{txt} ({label})"
    return txt


def render(el, ctx, level):
    """Return a list of Markdown blocks for element `el` whose headings start at `level`."""
    t = local(el.tag)
    if t in CONTAINERS:
        has_head = el.find(A + "num") is not None or el.find(A + "heading") is not None
        blocks = [H(level, heading_text(el, ctx))] if has_head else []
        blocks += render_children(el, ctx, level + 1)
        return blocks
    if t in ("section", "article", "rule"):
        has_head = el.find(A + "num") is not None or el.find(A + "heading") is not None
        blocks = [H(level, heading_text(el, ctx))] if has_head else []
        blocks += render_children(el, ctx, level + 1)
        return blocks
    if t == "hcontainer":
        name = el.get("name")
        if name == "contentAbsent":
            return []
        if name in TRANSPARENT_HC:
            return render_children(el, ctx, level)
        if name == "noteAuthorial":
            inner = render_children(el, ctx, level)
            return [quote("\n\n".join(inner))] if inner else []
        if name == "attachments":
            return render_children(el, ctx, level)
        head = el.find(A + "heading")
        num = el.find(A + "num")
        outline = el.get(F + "outline")
        blocks = []
        if head is not None or num is not None:
            blocks.append(H(level, heading_text(el, ctx)))
        elif outline and name not in ("statuteWrapUp",):
            blocks.append(H(level, outline))
        blocks += render_children(el, ctx, level + 1)
        return blocks
    if t in ("subsection", "clause"):
        blocks = []
        num = el.find(A + "num")
        head = el.find(A + "heading")
        if head is not None:
            blocks.append(H(level, heading_text(el, ctx)))
        body = render_children(el, ctx, level)
        if num is not None and head is None and body:
            n = text_line(num, ctx)
            if n:
                body[0] = f"{n} {body[0]}"
        blocks += body
        return add_label(blocks, el)
    if t in ITEMS:
        return [list_item(el, ctx, level)]
    if t in ("intro", "wrapUp", "content", "tblock", "blockContainer", "formula", "preamble", "blockList"):
        return add_label(render_children(el, ctx, level), el)
    if t == "crossHeading":
        return [H(level, heading_text_inline(el, ctx))]
    if t == "p":
        cls = el.get("class")
        if cls == "horizontalRule":
            return ["* * *"]
        if cls == "omission":
            return ["…"]
        s = text_line(el, ctx)
        return [safe_line(s)] if s else []
    if t == "table":
        return table(el, ctx)
    if t == "block":
        name = el.get("name")
        if name == "image":
            return image_block(el, ctx)
        if name in ("noteAuthorial", "alert"):
            s = text_line(el, ctx) if not any(local(c.tag) == "p" for c in el) else "\n\n".join(render_children(el, ctx, level))
            return [quote(s)] if s else []
        s = text_line(el, ctx)
        return [safe_line(s)] if s else []
    if t == "foreign":
        out = []
        for c in el:
            if local(c.tag) == "finlex:latex":
                tex = (c.text or "").strip().strip("$").strip()
                out.append(f"$$\n{tex}\n$$")
            elif isinstance(c.tag, str):
                out.extend(render(c, ctx, level))
        return out
    if t == "img":
        return [f"![]({ctx.media(el.get('src', ''))})"]
    if t in ("num", "heading"):
        s = text_line(el, ctx)
        return [f"**{s}**"] if s else []
    if t in ("toc", "ul", "ol"):
        out = []
        for c in el:
            if isinstance(c.tag, str):
                s = text_line(c, ctx)
                if s:
                    out.append("- " + s)
        return ["\n".join(out)] if out else []
    # unknown element: render children / text
    if len(el):
        return render_children(el, ctx, level, skip=())
    s = text_line(el, ctx)
    return [safe_line(s)] if s else []


def quote(s):
    return "\n".join(("> " + l) if l.strip() else ">" for l in s.split("\n"))


def list_item(el, ctx, level, depth=0):
    num = el.find(A + "num")
    n = text_line(num, ctx) if num is not None else ""
    n = re.sub(r"^(\d+)([.)])", r"\1\\\2", n)
    blocks = []
    for c in el:
        if not isinstance(c.tag, str):
            continue
        t = local(c.tag)
        if t in ("num",):
            continue
        if t in ITEMS:
            blocks.append(list_item(c, ctx, level, depth + 1))
        elif t == "heading":
            blocks.append(f"**{text_line(c, ctx)}**")
        elif t in ("content", "intro", "wrapUp"):
            for b in render_children(c, ctx, level):
                blocks.append(b)
            if c.get(F + "originalVersionLabel"):
                add_label(blocks, c)
        else:
            blocks.extend(render(c, ctx, level))
    add_label(blocks, el)
    first = blocks[0] if blocks and not blocks[0].startswith("- ") and not blocks[0].startswith("|") and not blocks[0].startswith("<") else ""
    rest = blocks[1:] if first else blocks
    head = f"{n} {first}".strip() if first else n
    if not head:
        head = "—"
    lines = ["- " + head.replace("\n", "\n  ")]
    for b in rest:
        if b.startswith("- "):
            lines.append("  " + b.replace("\n", "\n  "))
        else:
            lines.append("")
            lines.append("  " + b.replace("\n", "\n  "))
    return "\n".join(lines)


def join_blocks(blocks):
    """Join blocks; consecutive list items are kept as one tight list."""
    out = []
    prev_list = False
    for b in blocks:
        if not b.strip():
            continue
        is_list = b.startswith("- ")
        if out:
            out.append("\n" if (is_list and prev_list) else "\n\n")
        out.append(b)
        prev_list = is_list
    return "".join(out)


# ---------------------------------------------------------------------------
# document


def slugify(s, maxlen=80):
    s = s.replace("ß", "ss")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if len(s) > maxlen:
        cut = s[:maxlen]
        if "-" in cut[maxlen // 2:]:
            cut = cut[: cut.rfind("-")]
        s = cut.strip("-")
    return s or "untitled"


def yq(s):
    return json.dumps(s, ensure_ascii=False)


def meta(root):
    m = {}
    expr = root.find(f".//{A}FRBRExpression")
    work = root.find(f".//{A}FRBRWork")
    for d in work.findall(A + "FRBRdate"):
        m["w_" + d.get("name")] = d.get("date")
    for d in expr.findall(A + "FRBRdate"):
        m["e_" + d.get("name")] = d.get("date")
    m["langver"] = expr.find(A + "FRBRuri").get("value").rsplit("/", 1)[1]
    alias = work.find(A + "FRBRalias")
    m["eli"] = alias.get("value") if alias is not None else None
    ts = root.find(f".//{F}typeStatute")
    m["type"] = ts.get("refersTo", "").lstrip("#") if ts is not None else ""
    inf = root.find(f".//{F}isInForce")
    m["in_force"] = inf.get("value") if inf is not None else ""
    m["absent"] = root.find(f".//{A}hcontainer[@name='contentAbsent']") is not None
    eif = root.find(f".//{A}proprietary/{F}inForce/{F}dateEntryIntoForce")
    m["entry_into_force"] = eif.get("date") if eif is not None else None
    title = root.find(f".//{A}preface//{A}docTitle")
    m["title"] = plain(title) if title is not None else ""
    docnum = root.find(f".//{A}preface//{A}docNumber")
    m["docnum"] = plain(docnum) if docnum is not None else ""
    cn = root.find(f".//{F}commonName")
    m["common_name"] = plain(cn) if cn is not None else None
    ab = root.find(f".//{F}administrativeBranch")
    m["branch"] = None
    if ab is not None:
        ref = ab.get("refersTo", "").lstrip("#")
        org = root.find(f".//{A}TLCOrganization[@eId='{ref}']")
        m["branch"] = org.get("showAs") if org is not None else ref
    return m


def convert_one(path, year, num, lang):
    root = etree.parse(path).getroot()
    m = meta(root)
    if m["absent"] or m["in_force"] != "true":
        return None
    L = LANGS[lang]
    ctx = Ctx(year, num, m["langver"], lang)
    if (year, num) == CONSTITUTION:
        cat = "constitution"
    elif m["type"] in ("act", "decree", "decision"):
        cat = m["type"]
    else:
        cat = "other"
    title = m["title"] or m["docnum"] or f"{num}/{year}"
    ident = m["docnum"] or f"{num}/{year}"
    date = m.get("w_dateIssued")
    last = m.get("e_dateConsolidated")

    fm = ["---", f"title: {yq(title)}", f"identifier: {yq(ident)}"]
    if m["eli"]:
        fm.append(f"eli: {yq(m['eli'])}")
    fm.append(f"type: {'constitution' if cat == 'constitution' else (m['type'] or 'unknown')}")
    fm += [f"jurisdiction: fi", f"language: {L['code']}"]
    if date:
        fm.append(f"date: {date}")
    if m["entry_into_force"]:
        fm.append(f"entry_into_force: {m['entry_into_force']}")
    if last:
        fm.append(f"last_amended: {last}")
    fm.append("status: in_force")
    if m["common_name"]:
        fm.append(f"common_name: {yq(m['common_name'])}")
    if m["branch"]:
        fm.append(f"administrative_branch: {yq(m['branch'])}")
    fm.append(f"source: {yq(L['web'].format(year=year, num=num))}")
    fm.append(f"source_data: {yq(f'{API}/akn/fi/act/statute-consolidated/{year}/{num}/{m['langver']}')}")
    fm.append(f"retrieved: {RETRIEVED}")
    fm.append("---")

    blocks = [f"# {esc_md(title)}"]
    if m["docnum"]:
        blocks.append(f"*{esc_md(m['docnum'])}*")
    act = root.find(A + "act") if root.find(A + "act") is not None else root[0]
    for part in act:
        t = local(part.tag)
        if t in ("preamble",):
            blocks += render_children(part, ctx, 2, skip=())
        elif t in ("body", "mainBody"):
            blocks += render_children(part, ctx, 2, skip=())
        elif t in ("conclusions",):
            blocks += render_children(part, ctx, 2, skip=())
        elif t == "attachments":
            blocks += render_children(part, ctx, 2, skip=())
    md = "\n".join(fm) + "\n\n" + join_blocks(blocks).rstrip() + "\n"
    md = re.sub(r"\n{3,}", "\n\n", md)

    if cat == "constitution":
        rel = os.path.join(L["dirs"][cat], f"{year}-{num}-{slugify(title)}.md")
    else:
        rel = os.path.join(L["dirs"][cat], year, f"{num}-{slugify(title)}.md")
    return rel, md, cat


def main():
    xmlroot = os.path.join(RAW, "xml")
    counts = {}
    written = set()
    for year in sorted(os.listdir(xmlroot)):
        ydir = os.path.join(xmlroot, year)
        if not os.path.isdir(ydir):
            continue
        for num in sorted(os.listdir(ydir)):
            for lang in ("fin", "swe"):
                p = os.path.join(ydir, num, lang + ".xml")
                if not os.path.exists(p):
                    continue
                try:
                    res = convert_one(p, year, num, lang)
                except Exception as ex:  # keep going, report
                    print(f"ERROR {p}: {ex!r}", file=sys.stderr)
                    continue
                if not res:
                    continue
                rel, md, cat = res
                full = os.path.join(REPO, LANGS[lang]["code"], rel)
                os.makedirs(os.path.dirname(full), exist_ok=True)
                with open(full, "w", encoding="utf-8", newline="\n") as f:
                    f.write(md)
                written.add(os.path.relpath(full, REPO))
                k = (LANGS[lang]["code"], cat)
                counts[k] = counts.get(k, 0) + 1
    # remove stale files from previous runs
    for lc in ("fi", "sv"):
        base = os.path.join(REPO, lc)
        if not os.path.isdir(base):
            continue
        for dp, _, fns in os.walk(base):
            for fn in fns:
                rp = os.path.relpath(os.path.join(dp, fn), REPO)
                if fn.endswith(".md") and rp not in written:
                    os.remove(os.path.join(dp, fn))
    for k in sorted(counts):
        print(k, counts[k])
    with open(os.path.join(RAW, "counts.json"), "w") as f:
        json.dump({f"{a}/{b}": v for (a, b), v in counts.items()}, f, indent=1)


if __name__ == "__main__":
    main()
