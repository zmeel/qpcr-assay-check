"""scripts/knowledge_viewer.py: the self-contained viewer of the knowledge bundle."""

import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "knowledge_viewer", ROOT / "scripts" / "knowledge_viewer.py"
)
kv = importlib.util.module_from_spec(spec)
sys.modules["knowledge_viewer"] = kv
spec.loader.exec_module(kv)

RULE = kv.BUNDLE / "rules" / "r9-probes.md"


def _ctx(path=RULE, footnotes=None):
    return {"path": path, "links": set(), "footnotes": footnotes or {}}


def test_links_resolve_to_concepts_folders_github_or_text():
    assert kv.resolve("r1-last-five.md", RULE) == {"concept": "rules/r1-last-five"}
    assert kv.resolve("../decisions/index.md", RULE) == {"folder": "decisions"}
    assert kv.resolve("../index.md", RULE) == {"folder": ""}
    url = kv.resolve("../../../src/qpcr_assay_check/oligo/grade.py", RULE)["url"]
    assert url == f"{kv.GITHUB}/blob/main/src/qpcr_assay_check/oligo/grade.py"
    assert kv.resolve("https://doi.org/10.1/x", RULE) == {"url": "https://doi.org/10.1/x"}
    assert kv.resolve("the user's report on the NAS", RULE) == {
        "text": "the user's report on the NAS"
    }
    assert kv.resolve("../../../../../etc/passwd", RULE)["text"]  # outside the repository


def test_markdown_blocks_and_inline():
    ctx = _ctx(footnotes={"kutyavin": 1})
    out = kv.render(
        "# Rule\n\nText with `MGB_REGION = 7`, a **bold** word, an *aside* and\n"
        "snake_case_names kept.[^kutyavin] See [R1](r1-last-five.md).\n\n"
        "| A | B |\n|---|---|\n| 1 | <script> |\n\n"
        "- one\n  continued\n  - nested\n- two\n\n1. first\n2. second\n\n"
        "```yaml\nkey: <v>\n```\n\n[^kutyavin]: Kutyavin et al. 2000\n",
        ctx,
    )
    assert "<h3>Rule</h3>" in out
    assert "<code>MGB_REGION = 7</code>" in out
    assert "<strong>bold</strong>" in out and "<em>aside</em>" in out
    assert "snake_case_names" in out
    assert '<sup class="fn"><a href="#" data-src="kutyavin">1</a></sup>' in out
    assert '<a href="#" data-concept="rules/r1-last-five">R1</a>' in out
    assert ctx["links"] == {"rules/r1-last-five"}
    assert "<td>&lt;script&gt;</td>" in out and "<script>" not in out
    assert "<ul><li>one continued<ul><li>nested</li></ul></li><li>two</li></ul>" in out
    assert "<ol><li>first</li><li>second</li></ol>" in out
    assert "<pre><code>key: &lt;v&gt;</code></pre>" in out
    assert "Kutyavin et al. 2000" not in out  # footnote definitions become the Sources list


def test_every_concept_is_in_the_viewer_with_resolvable_links():
    data = kv.bundle_data()
    ids = {c["id"] for c in data["concepts"]}
    on_disk = {kv.concept_id(p) for p in kv.BUNDLE.rglob("*.md") if p.name not in kv.RESERVED}
    assert ids == on_disk
    assert {"status", "about", "rules/r9-probes"} <= ids
    for c in data["concepts"]:
        assert set(c["links"]) <= ids and c["id"] not in c["links"]
        assert c["folder"] in kv.FOLDERS
    r9 = next(c for c in data["concepts"] if c["id"] == "rules/r9-probes")
    assert "sources/kutyavin-2000" in r9["links"]
    # The tier follows the concept's own frontmatter, so pinning one concept's tier breaks as
    # soon as the user marks that page verified. Check every tier against the YAML on disk - an
    # oracle outside the viewer, not a copy of its rule (code review, 2026-10-08).
    import yaml

    seen = {"unverified": 0, "human": 0}
    for c in data["concepts"]:
        text = (kv.BUNDLE / f"{c['id']}.md").read_text(encoding="utf-8")
        meta = yaml.safe_load(text.split("---", 2)[1]) or {}
        raw = meta.get("verified")
        entries = raw if isinstance(raw, list) else ([raw] if raw else [])
        actors = [str(v.get("by", "")) for v in entries]
        want = "unverified"
        if actors:
            want = "human" if any(a.startswith("human:") for a in actors) else "machine"
        assert c["tier"] == want, c["id"]
        seen[want] = seen.get(want, 0) + 1
    assert seen["unverified"] and seen["human"]  # both tiers really occur in the bundle
    assert data["okfVersion"] == "0.2"


def test_the_page_is_self_contained(tmp_path):
    out = tmp_path / "viewer.html"
    assert kv.main(["--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert text.startswith("<!doctype html>") and "<title>Knowledge Map</title>" in text
    assert not re.search(r"<(script|link|img)[^>]+(src|href)=\"https?:", text)
    assert "@import" not in text and "fonts.googleapis" not in text
    payload = re.search(r'<script type="application/json" id="bundle-data">(.*?)</script>', text,
                        flags=re.S).group(1)  # fmt: skip
    assert len(json.loads(payload)["concepts"]) == len(kv.bundle_data()["concepts"])
    assert "font/woff2;base64," in text
    frag = tmp_path / "fragment.html"
    kv.main(["--out", str(frag), "--fragment"])
    assert frag.read_text(encoding="utf-8").startswith("<title>Knowledge Map</title>")
