"""GUI phase G2: assay files, the comment-preserving form, live validation, QC-only runs."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("ruamel.yaml")

from fastapi.testclient import TestClient  # noqa: E402

from qpcr_assay_check.gui.app import GuiSettings, create_app  # noqa: E402
from qpcr_assay_check.gui.assays import (  # noqa: E402
    AssayFileError,
    AssayFiles,
    check_name,
    validate_text,
)
from qpcr_assay_check.gui.auth import AuthStore  # noqa: E402
from qpcr_assay_check.gui.form import FormValues, OligoRow, apply, values_of  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "docs" / "examples"
NEISSERIA = (EXAMPLES / "neisseria_gonorrhoeae_two_probes.yaml").read_text(encoding="utf-8")
PASSWORD = "correct horse battery"

SIMPLE = """\
# provenance: test file, sequences made up for the test
assay_name: Test assay   # the name
forward: ACGTACGTACGTACGTAC
reverse: {name: R1, sequence: TTGCAGTTGCAGTTGCAGTT}
probe:
  - {name: P1, sequence: CCGGTTAACCGGTTAACCGG, reporter: FAM}
template_type: DNA
target:
  taxid: 562   # E. coli
"""


@pytest.mark.parametrize("bad", ["", "../x.yaml", "a/b.yaml", ".hidden.yaml", "x.txt", "x y.yaml"])
def test_file_names_are_checked(bad: str) -> None:
    with pytest.raises(AssayFileError):
        check_name(bad)
    assert check_name("ng_two-probes.v2.yaml")


def test_save_keeps_history_and_delete_moves(tmp_path: Path) -> None:
    files = AssayFiles(tmp_path / "assays")
    files.create("a.yaml", SIMPLE)
    with pytest.raises(AssayFileError):
        files.create("a.yaml", SIMPLE)
    files.save("a.yaml", SIMPLE)  # unchanged: no history entry
    assert not (tmp_path / "assays" / ".history").exists()
    files.save("a.yaml", SIMPLE.replace("Test assay", "Renamed"))
    kept = list((tmp_path / "assays" / ".history" / "a").iterdir())
    assert len(kept) == 1 and kept[0].read_text() == SIMPLE
    [entry] = files.list()
    assert entry.assay_name == "Renamed" and entry.valid
    files.delete("a.yaml")
    assert files.list() == []
    assert len(list((tmp_path / "assays" / ".deleted").iterdir())) == 1


def test_validation_is_the_command_lines(tmp_path: Path) -> None:
    ok = validate_text(NEISSERIA, None)
    assert ok.ok and ok.assay is not None and ok.qc is not None
    assert [c.name for c in ok.assay.channels] == ["N. gonorrhoeae"]
    bad = validate_text(SIMPLE.replace("taxid: 562", "taxid: -1"), None)
    assert not bad.ok and any("taxid" in e for e in bad.errors)
    broken = validate_text("assay_name: [unclosed", None)
    assert not broken.ok and broken.errors[0].startswith("not valid YAML")
    cfg = tmp_path / "config.yaml"
    cfg.write_text("reaction:\n  annealing_temp_C: 55\n")
    assert validate_text(SIMPLE, cfg).cfg.reaction.annealing_temp_C == 55


def test_form_round_trip_changes_nothing() -> None:
    assert apply(NEISSERIA, values_of(NEISSERIA)) == NEISSERIA
    assert apply(SIMPLE, values_of(SIMPLE)) == SIMPLE


def test_form_edit_keeps_comments_and_renames_references() -> None:
    v = values_of(NEISSERIA)
    assert [o.name for o in v.oligos] == ["NG-F", "NG-R", "NG-P1", "NG-P2"]
    assert v.annealing == "60" and v.taxid == "485"
    p2 = next(o for o in v.oligos if o.name == "NG-P2")
    p2.name = "NG-P2b"
    v.annealing = "62"
    out = apply(NEISSERIA, v)
    assert "# PROVENANCE" in out and "# Neisseria gonorrhoeae" in out  # comments kept
    assert "annealing_temp_C: 62" in out
    assert "{name: NG-P2b, sequence: CTTTGAACCATCAGTGAAA" in out
    assert "probes: [NG-P1, NG-P2b]" in out  # locus and channel follow the rename
    assert "NG-P2]" not in out
    assert validate_text(out, None).ok
    # only the changed lines differ
    changed = [a for a, b in zip(NEISSERIA.splitlines(), out.splitlines(), strict=True) if a != b]
    assert len(changed) == 4


def test_form_adds_and_removes_oligos() -> None:
    v = values_of(SIMPLE)
    v.oligos.append(OligoRow("forward", "F2", "ACGTACGTACGTACGTTT"))
    out = apply(SIMPLE, v)
    assert "forward:\n  - ACGTACGTACGTACGTAC\n  - {name: F2," in out  # now a list
    check = validate_text(out, None)
    assert not check.ok  # the first forward primer has no name: the model says so
    assert any("name" in e for e in check.errors)
    v = values_of(SIMPLE)
    v.oligos[0].name = "F1"
    v.oligos.append(OligoRow("forward", "F2", "ACGTACGTACGTACGTTT"))
    out = apply(SIMPLE, v)
    assert validate_text(out, None).ok
    v = values_of(out)
    next(o for o in v.oligos if o.name == "F2").remove = True
    out2 = apply(out, v)
    assert "F2" not in out2 and validate_text(out2, None).ok
    v = values_of(SIMPLE)
    v.oligos = [o for o in v.oligos if o.role != "probe"] + [
        OligoRow("probe", "P1", "CCGGTTAACCGGTTAACCGG", original="P1", remove=True)
    ]
    with pytest.raises(AssayFileError, match="at least one"):
        apply(SIMPLE, v)


def test_form_rejects_bad_numbers() -> None:
    v = values_of(SIMPLE)
    v.taxid = "five"
    with pytest.raises(AssayFileError, match="target taxon"):
        apply(SIMPLE, v)
    v = values_of(SIMPLE)
    v.annealing = "58.5"
    out = apply(SIMPLE, v)
    assert "annealing_temp_C: 58.5" in out
    assert validate_text(out, None).cfg.reaction.annealing_temp_C == 58.5


# --- the pages -------------------------------------------------------------------------------


@pytest.fixture()
def work(tmp_path: Path) -> Path:
    AuthStore(tmp_path).set_password(PASSWORD)
    return tmp_path


@pytest.fixture()
def client(work: Path) -> TestClient:
    c = TestClient(
        create_app(GuiSettings(work_dir=work, examples_dir=EXAMPLES)), follow_redirects=False
    )
    token = _csrf(c.get("/login").text)
    assert c.post("/login", data={"password": PASSWORD, "csrf": token}).status_code == 303
    return c


def _csrf(html: str) -> str:
    m = re.search(r'name="csrf" value="([^"]+)"', html)
    assert m
    return m.group(1)


def test_assay_pages_need_a_login(work: Path) -> None:
    c = TestClient(create_app(GuiSettings(work_dir=work)), follow_redirects=False)
    assert c.get("/assays").status_code == 303
    assert c.post("/assays/new", data={"name": "x"}).status_code == 303


def test_copy_example_edit_as_yaml_and_validate(client: TestClient, work: Path) -> None:
    page = client.get("/assays").text
    assert "Neisseria gonorrhoeae (two probes)" in page  # offered as an example
    token = _csrf(page)
    r = client.post(
        "/assays/new",
        data={
            "csrf": token,
            "name": "ng",
            "source": "example:neisseria_gonorrhoeae_two_probes.yaml",
        },
    )
    assert r.status_code == 303 and r.headers["location"] == "/assays/ng.yaml"
    assert (work / "assays" / "ng.yaml").read_text() == NEISSERIA
    editor = client.get("/assays/ng.yaml?tab=yaml").text
    assert "Valid" in editor and "NG-R: " not in editor
    # live check of an unsaved edit
    frag = client.post(
        "/assays/ng.yaml/validate",
        data={"csrf": token, "text": NEISSERIA.replace("taxid: 485", "taxid: x")},
    )
    assert frag.status_code == 200 and "Not valid yet" in frag.text
    assert (
        client.post("/assays/ng.yaml/validate", data={"csrf": "x", "text": ""}).status_code == 400
    )
    # saving text that is not YAML is refused, and the text stays in the editor
    r = client.post("/assays/ng.yaml/yaml", data={"csrf": token, "text": "a: [b"})
    assert r.status_code == 400 and "Not saved" in r.text and "a: [b" in r.text
    assert (work / "assays" / "ng.yaml").read_text() == NEISSERIA
    # schema problems are saved (work in progress) and shown
    edited = NEISSERIA.replace("assay_name: Neisseria", "assay_name: Gonococcus")
    r = client.post("/assays/ng.yaml/yaml", data={"csrf": token, "text": edited})
    assert r.status_code == 303
    assert (work / "assays" / "ng.yaml").read_text() == edited
    assert len(list((work / "assays" / ".history" / "ng").iterdir())) == 1


def test_form_save_from_the_page(client: TestClient, work: Path) -> None:
    (work / "assays").mkdir()
    (work / "assays" / "simple.yaml").write_text(SIMPLE)
    page = client.get("/assays/simple.yaml").text
    assert 'name="o_sequence" value="ACGTACGTACGTACGTAC"' in page
    form = {
        "csrf": _csrf(page), "assay_name": "Test assay", "template_type": "RNA", "taxid": "562",
        "annealing": "", "exclusivity": "Shigella flexneri\n",
        "o_role": ["forward", "reverse", "probe", "probe"],
        "o_original": ["forward", "R1", "P1", ""],
        "o_name": ["forward", "R1", "P1", "P2"],
        "o_sequence": ["ACGTACGTACGTACGTAC", "TTGCAGTTGCAGTTGCAGTT", "CCGGTTAACCGGTTAACCGG",
                       "CCGGTTAACCGGTTAACCGA"],
        "o_reporter": ["", "", "FAM", "FAM"], "o_quencher": ["", "", "", ""],
        "o_mods": ["", "", "", "MGB"],
    }  # fmt: skip
    r = client.post("/assays/simple.yaml/form", data=form)
    assert r.status_code == 303, r.text
    text = (work / "assays" / "simple.yaml").read_text()
    assert "# provenance: test file" in text and "# E. coli" in text
    assert "template_type: RNA" in text
    assert "{name: P2, sequence: CCGGTTAACCGGTTAACCGA, reporter: FAM, modifications: [MGB]}" in text
    assert "exclusivity_organisms:" in text and "Shigella flexneri" in text
    assert validate_text(text, None).ok
    form["taxid"] = "abc"
    r = client.post("/assays/simple.yaml/form", data=form)
    assert r.status_code == 400 and "Not saved" in r.text and 'value="abc"' in r.text


def test_qc_only_run_writes_a_record(client: TestClient, work: Path) -> None:
    (work / "assays").mkdir()
    (work / "assays" / "ng.yaml").write_text(NEISSERIA)
    token = _csrf(client.get("/assays/ng.yaml").text)
    r = client.post("/assays/ng.yaml/qc", data={"csrf": token})
    assert r.status_code == 303
    page = client.get(r.headers["location"])
    assert page.status_code == 200 and "Oligo QC" in page.text and "NG-P2" in page.text
    [record] = list((work / "results").glob("*/*/results.json"))
    data = json.loads(record.read_text())
    assert data["mode"] == "qc-only"
    assert "Neisseria" in client.get("/").text  # on the dashboard too


def test_qc_only_refused_while_invalid(client: TestClient, work: Path) -> None:
    (work / "assays").mkdir()
    (work / "assays" / "bad.yaml").write_text("assay_name: only a name\n")
    token = _csrf(client.get("/assays/bad.yaml").text)
    r = client.post("/assays/bad.yaml/qc", data={"csrf": token})
    assert r.status_code == 303 and "error=" in r.headers["location"]
    assert not (work / "results").exists()


def test_unknown_and_unsafe_names_are_not_found(client: TestClient, work: Path) -> None:
    assert client.get("/assays/missing.yaml").status_code == 404
    assert client.get("/assays/..%2Fgui%2Fauth.json").status_code == 404
    token = _csrf(client.get("/assays").text)
    r = client.post("/assays/new", data={"csrf": token, "name": "../evil", "source": "template"})
    assert r.status_code == 400
    r = client.post("/assays/new", data={"csrf": token, "name": "x",
                                         "source": "example:../../pyproject.toml"})  # fmt: skip
    assert r.status_code == 400
    (work / "assays").mkdir(exist_ok=True)
    (work / "assays" / "a.yaml").write_text(SIMPLE)
    assert client.get("/assays/a.yaml/qc/..%2F..%2Fgui/x").status_code == 404


def test_delete_from_the_page(client: TestClient, work: Path) -> None:
    (work / "assays").mkdir()
    (work / "assays" / "a.yaml").write_text(SIMPLE)
    token = _csrf(client.get("/assays/a.yaml").text)
    client.post("/assays/a.yaml/delete", data={"csrf": "forged"})
    assert (work / "assays" / "a.yaml").exists()
    r = client.post("/assays/a.yaml/delete", data={"csrf": token})
    assert r.status_code == 303 and not (work / "assays" / "a.yaml").exists()


def test_new_from_template(client: TestClient, work: Path) -> None:
    token = _csrf(client.get("/assays").text)
    r = client.post("/assays/new", data={"csrf": token, "name": "blank", "source": "template"})
    assert r.status_code == 303
    page = client.get("/assays/blank.yaml").text
    assert "Not valid yet" in page  # the template's empty sequences
    form_values = values_of((work / "assays" / "blank.yaml").read_text())
    assert isinstance(form_values, FormValues)
