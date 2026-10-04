"""docs/knowledge/: the knowledge bundle conforms to OKF v0.2 and its generated parts are current.

OKF v0.2 conformance (SPEC.md section 11): every non-reserved .md file has parseable YAML
frontmatter with a non-empty ``type``; ``index.md`` and ``log.md`` follow sections 8 and 9.
On top of that, for this bundle: links and path-valued fields resolve, every footnote names a
``sources`` id, actors follow section 7, and nothing generated is out of date.
"""

import importlib.util
import re
import sys
from datetime import date, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "build_knowledge", ROOT / "scripts" / "build_knowledge.py"
)
bk = importlib.util.module_from_spec(spec)
sys.modules["build_knowledge"] = bk  # dataclasses look the module up
spec.loader.exec_module(bk)

BUNDLE = bk.BUNDLE
DOCS = sorted(BUNDLE.rglob("*.md"))
CONCEPTS = [p for p in DOCS if p.name not in bk.RESERVED]
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
ACTOR = re.compile(r"^(human:[\w.-]+|process:[\w.-]+|[\w.-]+/[\w.-]+)$")


def _id(p: Path) -> str:
    return p.relative_to(BUNDLE).as_posix()


def _meta(p: Path) -> dict:
    meta = bk.frontmatter(p.read_text(encoding="utf-8"))
    assert meta is not None, f"{_id(p)}: no YAML frontmatter"
    return meta


def _body(p: Path) -> str:
    text = p.read_text(encoding="utf-8")
    return text[text.find("\n---\n", 4) + 5 :] if text.startswith("---\n") else text


def _as_list(v) -> list:
    return v if isinstance(v, list) else [v]


def test_the_generated_files_are_current():
    stale = [
        _id(p) for p, text in bk.build().items()
        if not p.exists() or p.read_text(encoding="utf-8") != text
    ]  # fmt: skip
    assert not stale, f"run: python scripts/build_knowledge.py ({stale})"


def test_the_bundle_has_the_expected_folders():
    folders = {p.name for p in BUNDLE.iterdir() if p.is_dir()}
    assert set(bk.FOLDERS) <= folders
    for name in bk.FOLDERS:
        assert len(list((BUNDLE / name).glob("*.md"))) >= 2, f"{name}/ has no concepts"


@pytest.mark.parametrize("path", CONCEPTS, ids=_id)
def test_every_concept_has_a_type_and_well_formed_families(path):
    meta = _meta(path)
    assert isinstance(meta.get("type"), str) and meta["type"].strip()
    assert meta.get("title") and meta.get("description"), "title and description recommended"
    assert meta.get("status", "stable") in {"draft", "stable", "deprecated"}
    gen = meta.get("generated")
    assert isinstance(gen, dict) and ACTOR.match(str(gen.get("by", ""))), "generated.by actor"
    for v in _as_list(meta.get("verified") or []):
        assert ACTOR.match(str(v["by"])) and isinstance(v["at"], datetime)
    for key in ("stale_after",):
        if key in meta:
            assert isinstance(meta[key], datetime)
    if "at" in gen:
        assert isinstance(gen["at"], datetime)
    ids = set()
    for s in meta.get("sources") or []:
        assert s.get("resource"), "sources[].resource is required"
        ids.add(s.get("id"))
    cited = set(re.findall(r"\[\^([\w.-]+)\]", _body(path)))
    assert cited <= ids, f"footnotes without a sources id: {cited - ids}"


@pytest.mark.parametrize("path", DOCS, ids=_id)
def test_links_and_paths_resolve(path):
    targets = LINK.findall(_body(path))
    if path.name not in bk.RESERVED:
        meta = _meta(path)
        targets += [meta.get("resource") or ""]
        targets += [s["resource"] for s in meta.get("sources") or []]
    for t in targets:
        if not t or re.match(r"^[a-z]+:", t) or " " in t:
            continue  # URLs, mailto, scope descriptors
        target = (path.parent / t.split("#")[0]).resolve()
        assert target.exists(), f"{_id(path)}: broken link {t}"


def test_index_files_follow_section_8():
    for p in BUNDLE.rglob("index.md"):
        text = p.read_text(encoding="utf-8")
        if p.parent == BUNDLE:
            assert bk.frontmatter(text) == {"okf_version": bk.OKF_VERSION}
        else:
            assert not text.startswith("---"), f"{_id(p)}: frontmatter in an index"
        bullets = [x for x in text.splitlines() if x.startswith(("* ", "- "))]
        assert all(x.startswith("* [") for x in bullets), f"{_id(p)}: entries are * [Title](link)"
        listed = set(re.findall(r"^\* \[[^\]]*\]\(([^)]+)\)", text, flags=re.M))
        here = {q.name for q in p.parent.glob("*.md")} - bk.RESERVED
        assert here <= listed, f"{_id(p)} misses {here - listed}"


def test_the_log_follows_section_9():
    text = (BUNDLE / "log.md").read_text(encoding="utf-8")
    dates = re.findall(r"^## (.+)$", text, flags=re.M)
    assert dates and dates == sorted(dates, reverse=True)
    for d in dates:
        date.fromisoformat(d)


def test_progress_entries_are_parsed():
    entries = bk.progress_entries(
        "## 2026-10-03 — A\n## 2026-09-28 (later) — B\n## 2026-09-20/21 — C\n## Open questions\n"
    )
    assert entries == [("2026-10-03", "A"), ("2026-09-28", "B"), ("2026-09-20", "C")]


def test_releases_and_settings_follow_their_sources():
    versions = [r.version for r in bk.releases(bk.CHANGELOG.read_text(encoding="utf-8"))]
    assert versions and "0.1.0" in versions
    assert {p.stem for p in (BUNDLE / "releases").glob("v*.md")} == {f"v{v}" for v in versions}
    keys = [k for k, _ in bk.config_sections(bk.CONFIG.read_text(encoding="utf-8"))]
    assert "inclusivity" in keys and "schema_version" not in keys
    assert {p.stem for p in (BUNDLE / "settings").glob("*.md")} - {"index"} == set(keys)
