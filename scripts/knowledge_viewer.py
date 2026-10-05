#!/usr/bin/env python3
"""Write a self-contained HTML viewer for the knowledge bundle in docs/knowledge/.

One file, no external requests: the bundle is rendered to HTML here (a small markdown
subset: headings, paragraphs, nested lists, tables, code fences, links, emphasis, footnote
references) and embedded as JSON; the page draws a map of the concepts (one node per concept,
one edge per link or cited source), a list with each concept's review state, and a detail panel
with the rendered text, its sources, its links and what cites it. Links into the bundle open
the concept in the viewer; links to code and docs outside the bundle point to GitHub.

    python scripts/knowledge_viewer.py                      # work/knowledge-viewer.html
    python scripts/knowledge_viewer.py --out viewer.html
    python scripts/knowledge_viewer.py --fragment           # no <html>/<head>/<body> wrapper

The fonts (IBM Plex Sans and Mono, SIL Open Font License) are embedded from the GUI's static
files. No network access; reads only files in this repository.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger("knowledge_viewer")

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "docs" / "knowledge"
FONTS = ROOT / "src" / "qpcr_assay_check" / "gui" / "static" / "fonts"
GITHUB = "https://github.com/zmeel/qpcr-assay-check"
BRANCH = "main"
RESERVED = {"index.md", "log.md"}

# Folder -> (label, colour slot 1-8 or 0 for neutral, shape). Slots follow the validated
# categorical order (blue, orange, aqua, yellow, magenta, green, violet, red); the shape is the
# second encoding, so identity never rests on colour alone.
FOLDERS: dict[str, tuple[str, int, str]] = {
    "decisions": ("Decisions", 1, "square"),
    "rules": ("Rules", 2, "diamond"),
    "sources": ("Sources", 3, "circle"),
    "sessions": ("Sessions", 4, "triangle"),
    "runs": ("Runs", 5, "hexagon"),
    "assays": ("Assays", 6, "pentagon"),
    "ncbi": ("NCBI facts", 7, "star"),
    "open": ("Open items", 8, "ring"),
    "components": ("Components", 0, "circle"),
    "settings": ("Settings", 0, "square"),
    "releases": ("Releases", 0, "triangle"),
    "": ("Bundle", 0, "diamond"),
}


# ---------------------------------------------------------------- reading


def split_doc(text: str) -> tuple[dict[str, Any], str]:
    """Frontmatter and body of a markdown document."""
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end >= 0:
            meta = yaml.safe_load(text[4:end]) or {}
            return (meta if isinstance(meta, dict) else {}), text[end + 5 :]
    return {}, text


def concept_id(path: Path) -> str:
    """The OKF concept ID: the path within the bundle without ``.md``."""
    return path.relative_to(BUNDLE).with_suffix("").as_posix()


def github_url(target: Path) -> str:
    """A GitHub link to a file or folder in this repository."""
    rel = target.relative_to(ROOT).as_posix()
    kind = "tree" if target.is_dir() else "blob"
    return f"{GITHUB}/{kind}/{BRANCH}/{rel}"


def resolve(href: str, base: Path) -> dict[str, str]:
    """Where a link or path-valued field from the document ``base`` points.

    Returns one of ``{"concept": id}``, ``{"folder": name}``, ``{"url": url}`` or
    ``{"text": href}`` (a scope descriptor or a path outside the repository).
    """
    if re.match(r"^[a-z][a-z0-9+.-]*:", href):
        return {"url": href}
    if " " in href or not href:
        return {"text": href}
    path_part, _, anchor = href.partition("#")
    if not path_part:
        return {"text": href}
    target = (base.parent / path_part).resolve()
    try:
        target.relative_to(ROOT)
    except ValueError:
        return {"text": href}
    try:
        inside = target.relative_to(BUNDLE)
    except ValueError:
        url = github_url(target) if target.exists() else f"{GITHUB}/blob/{BRANCH}/{path_part}"
        return {"url": url + (f"#{anchor}" if anchor else "")}
    if target.is_dir() or target.name == "index.md":
        folder = (inside if target.is_dir() else inside.parent).as_posix()
        return {"folder": "" if folder == "." else folder}
    if target.name == "log.md" or target.suffix != ".md":
        return {"url": github_url(target)}
    return {"concept": inside.with_suffix("").as_posix()}


# ---------------------------------------------------------------- markdown


_INLINE = re.compile(r"(`[^`]+`)|(\[\^[\w.-]+\])|(\[(?:[^\]\[]|\[[^\]]*\])*\]\([^)\s]+\))")


def inline(text: str, ctx: dict[str, Any]) -> str:
    """Inline markdown: code, footnote references, links, bold, emphasis; the rest escaped."""
    out = []
    pos = 0
    for m in _INLINE.finditer(text):
        out.append(_emphasis(html.escape(text[pos : m.start()], quote=False)))
        code, foot, link = m.groups()
        if code:
            out.append(f"<code>{html.escape(code[1:-1], quote=False)}</code>")
        elif foot:
            sid = foot[2:-1]
            n = ctx["footnotes"].get(sid)
            label = str(n) if n else html.escape(sid)
            ref = f'<a href="#" data-src="{html.escape(sid)}">{label}</a>'
            out.append(f'<sup class="fn">{ref}</sup>')
        else:
            lm = re.match(r"\[(.*)\]\(([^)\s]+)\)$", link, flags=re.S)
            label, href = lm.group(1), lm.group(2)
            out.append(_anchor(inline(label, ctx), resolve(href, ctx["path"]), ctx))
        pos = m.end()
    out.append(_emphasis(html.escape(text[pos:], quote=False)))
    return "".join(out)


def _emphasis(escaped: str) -> str:
    escaped = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", r"<strong>\1</strong>", escaped)
    return re.sub(r"(?<![\w*])\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?![\w*])", r"<em>\1</em>", escaped)


def _anchor(label: str, where: dict[str, str], ctx: dict[str, Any]) -> str:
    if "concept" in where:
        ctx["links"].add(where["concept"])
        return f'<a href="#" data-concept="{html.escape(where["concept"])}">{label}</a>'
    if "folder" in where:
        return f'<a href="#" data-folder="{html.escape(where["folder"])}">{label}</a>'
    if "url" in where:
        url = html.escape(where["url"])
        return f'<a href="{url}" target="_blank" rel="noopener">{label}</a>'
    return label


_LIST = re.compile(r"^(\s*)([-*]|\d+[.)])\s+(.*)$")


def render(body: str, ctx: dict[str, Any]) -> str:
    """Block markdown to HTML (headings shift down two levels: the panel title is h2)."""
    lines = body.splitlines()
    out: list[str] = []
    para: list[str] = []
    i = 0

    def flush() -> None:
        if para:
            out.append(f"<p>{inline(' '.join(x.strip() for x in para), ctx)}</p>")
            para.clear()

    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            flush()
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            code = html.escape("\n".join(lines[i + 1 : j]), quote=False)
            out.append(f'<div class="scroll"><pre><code>{code}</code></pre></div>')
            i = j + 1
            continue
        if re.match(r"^\[\^[\w.-]+\]:", line):  # footnote definitions: shown as Sources
            flush()
            i += 1
            continue
        h = re.match(r"^(#{1,6})\s+(.*)$", line)
        if h:
            flush()
            level = min(len(h.group(1)) + 2, 6)
            out.append(f"<h{level}>{inline(h.group(2), ctx)}</h{level}>")
            i += 1
            continue
        next_line = lines[i + 1] if i + 1 < len(lines) else ""
        if line.startswith("|") and re.match(r"^\|[\s:|-]+\|$", next_line):
            flush()
            rows = []
            j = i
            while j < len(lines) and lines[j].startswith("|"):
                if j != i + 1:
                    rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            head = "".join(f"<th>{inline(c, ctx)}</th>" for c in rows[0])
            body_rows = "".join(
                "<tr>" + "".join(f"<td>{inline(c, ctx)}</td>" for c in r) + "</tr>"
                for r in rows[1:]
            )
            out.append(
                f'<div class="scroll"><table><thead><tr>{head}</tr></thead>'
                f"<tbody>{body_rows}</tbody></table></div>"
            )
            i = j
            continue
        if _LIST.match(line):
            flush()
            items: list[list[Any]] = []  # [indent, tag, text]
            while i < len(lines):
                m = _LIST.match(lines[i])
                if m:
                    tag = "ol" if m.group(2)[0].isdigit() else "ul"
                    items.append([len(m.group(1)), tag, m.group(3).strip()])
                elif lines[i].strip() and lines[i].startswith(" ") and items:
                    items[-1][2] += " " + lines[i].strip()
                else:
                    break
                i += 1
            out.append(_list_html(items, ctx))
            continue
        if not line.strip():
            flush()
        else:
            para.append(line)
        i += 1
    flush()
    return "\n".join(out)


def _list_html(items: list[list[Any]], ctx: dict[str, Any]) -> str:
    out: list[str] = []
    stack: list[tuple[int, str]] = []
    for indent, tag, text in items:
        while stack and indent < stack[-1][0]:
            out.append(f"</li></{stack.pop()[1]}>")
        if stack and indent == stack[-1][0]:
            out.append("</li>")
        else:
            stack.append((indent, tag))
            out.append(f"<{tag}>")
        out.append(f"<li>{inline(text, ctx)}")
    while stack:
        out.append(f"</li></{stack.pop()[1]}>")
    return "".join(out)


# ---------------------------------------------------------------- data


def _iso(v: Any) -> str | None:
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat().replace("+00:00", "Z")
    return str(v)


def _verified(meta: dict[str, Any]) -> list[dict[str, str]]:
    v = meta.get("verified") or []
    v = v if isinstance(v, list) else [v]
    return [{"by": str(x.get("by", "")), "at": _iso(x.get("at")) or ""} for x in v]


def concept(path: Path) -> dict[str, Any]:
    """One concept as the viewer needs it."""
    meta, body = split_doc(path.read_text(encoding="utf-8"))
    cid = concept_id(path)
    folder = cid.rsplit("/", 1)[0] if "/" in cid else ""
    sources = meta.get("sources") or []
    ctx: dict[str, Any] = {
        "path": path,
        "links": set(),
        "footnotes": {str(s.get("id")): n for n, s in enumerate(sources, 1) if s.get("id")},
    }
    rendered = render(body, ctx)
    src_out = []
    for n, s in enumerate(sources, 1):
        where = resolve(str(s.get("resource", "")), path)
        if "concept" in where:
            ctx["links"].add(where["concept"])
        src_out.append(
            {"n": n, "id": str(s.get("id") or ""), "title": str(s.get("title") or ""), **where}
        )
    resource = meta.get("resource")
    verified = _verified(meta)
    gen = meta.get("generated") or {}
    by = str(gen.get("by", "")) if isinstance(gen, dict) else ""
    tier = "unverified"
    if verified:
        tier = "human" if any(v["by"].startswith("human:") for v in verified) else "machine"
    ctx["links"].discard(cid)
    return {
        "id": cid,
        "folder": folder,
        "type": str(meta.get("type") or ""),
        "title": str(meta.get("title") or path.stem),
        "description": str(meta.get("description") or ""),
        "status": str(meta.get("status") or "stable"),
        "tier": tier,
        "verified": verified,
        "generatedBy": by,
        "generatedAt": _iso(gen.get("at")) if isinstance(gen, dict) else None,
        "staleAfter": _iso(meta.get("stale_after")),
        "tags": [str(t) for t in meta.get("tags") or []],
        "date": _iso(meta.get("session_date") or meta.get("decided_on")),
        "resource": resolve(str(resource), path) if resource else None,
        "html": rendered,
        "sources": src_out,
        "links": sorted(ctx["links"]),
        "path": f"docs/knowledge/{cid}.md",
        "url": github_url(path),
    }


def bundle_data() -> dict[str, Any]:
    """Every concept of the bundle, the folders and the bundle's OKF version."""
    paths = sorted(p for p in BUNDLE.rglob("*.md") if p.name not in RESERVED)
    concepts = [concept(p) for p in paths]
    ids = {c["id"] for c in concepts}
    for c in concepts:
        c["links"] = [x for x in c["links"] if x in ids]
    root_meta, _ = split_doc((BUNDLE / "index.md").read_text(encoding="utf-8"))
    folders = [
        {"key": k, "label": v[0], "slot": v[1], "shape": v[2]}
        for k, v in FOLDERS.items()
        if any(c["folder"] == k for c in concepts)
    ]
    return {
        "okfVersion": str(root_meta.get("okf_version", "")),
        "folders": folders,
        "concepts": concepts,
        "github": GITHUB,
    }


# ---------------------------------------------------------------- page


def font_faces() -> str:
    """@font-face rules with the GUI's IBM Plex files inlined as data URIs."""
    faces = [
        ("IBM Plex Sans", 400, "ibm-plex-sans-latin-400-normal.woff2"),
        ("IBM Plex Sans", 600, "ibm-plex-sans-latin-600-normal.woff2"),
        ("IBM Plex Mono", 400, "ibm-plex-mono-latin-400-normal.woff2"),
    ]
    out = []
    for family, weight, name in faces:
        data = base64.b64encode((FONTS / name).read_bytes()).decode("ascii")
        out.append(
            f'@font-face {{ font-family: "{family}"; font-weight: {weight}; font-style: normal; '
            f'font-display: swap; src: url("data:font/woff2;base64,{data}") format("woff2"); }}'
        )
    return "\n".join(out)


def page(data: dict[str, Any], fragment: bool = False) -> str:
    """The viewer page; ``fragment`` leaves out the document wrapper."""
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    body = (
        TEMPLATE.replace("/*__FONTS__*/", font_faces())
        .replace("__DATA__", payload)
        .replace("__COUNT__", str(len(data["concepts"])))
    )
    if fragment:
        return body
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, '
        'viewport-fit=cover">\n</head>\n<body>\n' + body + "\n</body>\n</html>\n"
    )


TEMPLATE = (Path(__file__).resolve().parent / "knowledge_viewer.html").read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Write the viewer."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=ROOT / "work" / "knowledge-viewer.html")
    parser.add_argument("--fragment", action="store_true", help="no <html>/<head>/<body>")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    data = bundle_data()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(page(data, args.fragment), encoding="utf-8")
    size = args.out.stat().st_size
    log.info("wrote %s (%d concepts, %d kB)", os.path.relpath(args.out), len(data["concepts"]),
             size // 1024)  # fmt: skip
    return 0


if __name__ == "__main__":
    sys.exit(main())
