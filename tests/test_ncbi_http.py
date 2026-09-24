import pytest
import requests

from qpcr_assay_check import __version__
from qpcr_assay_check.ncbi.http import NcbiError, NcbiHttp, RateLimiter
from qpcr_assay_check.ncbi.settings import Credentials, credentials_from_env

from .fake_ncbi import FakeClock, FakeResponse, ScriptedSession, connection_error

BLAST = "https://blast.example/Blast.cgi"
EUTILS = "https://eutils.example/esearch.fcgi"


def make(cfg, script, key=None):
    fc = FakeClock()
    session = ScriptedSession(script)
    http = NcbiHttp(
        cfg.ncbi,
        Credentials("lab@example.org", key),
        session=session,
        clock=fc.monotonic,
        sleep=fc.sleep,
        jitter=lambda: 0.0,
    )
    return http, session, fc


def test_rate_limiter_enforces_the_minimum_interval():
    fc = FakeClock()
    rl = RateLimiter(10, clock=fc.monotonic, sleep=fc.sleep)
    rl.wait()
    fc.t += 3
    rl.wait()
    assert fc.slept == [7.0]
    fc.t += 30
    rl.wait()
    assert fc.slept == [7.0]  # already long enough, no extra sleeping


def test_blast_requests_are_spaced_at_least_ten_seconds(cfg):
    http, _, fc = make(cfg, [FakeResponse(200, "a"), FakeResponse(200, "b")])
    http.request("GET", BLAST, service="blast", params={"CMD": "Get"})
    http.request("GET", BLAST, service="blast", params={"CMD": "Get"})
    assert sum(fc.slept) >= 10


def test_eutils_spacing_depends_on_the_api_key(cfg):
    no_key, _, fc1 = make(cfg, [FakeResponse(200, "a")] * 2)
    for _ in range(2):
        no_key.request("GET", EUTILS, service="eutils", params={"db": "nuccore"})
    with_key, _, fc2 = make(cfg, [FakeResponse(200, "a")] * 2, key="SECRETKEY")
    for _ in range(2):
        with_key.request("GET", EUTILS, service="eutils", params={"db": "nuccore"})
    assert sum(fc1.slept) >= 0.5  # at most ~2 requests/second without a key
    assert 0.15 <= sum(fc2.slept) < 0.25  # at most ~6-7 requests/second with a key
    assert sum(fc1.slept) > sum(fc2.slept)


def test_requests_identify_the_tool_and_only_eutils_carry_the_api_key(cfg):
    http, session, _ = make(cfg, [FakeResponse(200, "a"), FakeResponse(200, "b")], key="SECRETKEY")
    http.request("POST", BLAST, service="blast", data={"CMD": "Put"})
    http.request("GET", EUTILS, service="eutils", params={"db": "nuccore"})
    blast_payload, eutils_payload = session.calls[0]["data"], session.calls[1]["params"]
    assert (
        blast_payload["tool"] == "qpcr-assay-check" and blast_payload["email"] == "lab@example.org"
    )
    assert "api_key" not in blast_payload
    assert eutils_payload["api_key"] == "SECRETKEY"
    assert __version__ in session.headers["User-Agent"]


def test_transient_errors_are_retried_with_exponential_backoff(cfg):
    http, session, fc = make(cfg, [FakeResponse(503), FakeResponse(502), FakeResponse(200, "ok")])
    assert http.request("GET", BLAST, service="blast", params={}).text == "ok"
    assert len(session.calls) == 3
    assert 2.0 in fc.slept and 4.0 in fc.slept


def test_retry_after_header_is_honoured(cfg):
    http, _, fc = make(
        cfg, [FakeResponse(429, headers={"Retry-After": "7"}), FakeResponse(200, "ok")]
    )
    http.request("GET", BLAST, service="blast", params={})
    assert 7.0 in fc.slept


def test_connection_errors_are_retried(cfg):
    http, session, _ = make(cfg, [connection_error(), FakeResponse(200, "ok")])
    assert http.request("GET", BLAST, service="blast", params={}).text == "ok"
    assert len(session.calls) == 2


@pytest.mark.parametrize(
    "error",
    [requests.exceptions.ChunkedEncodingError("Response ended prematurely"),
     requests.exceptions.ContentDecodingError("bad gzip")],
)  # fmt: skip
def test_a_download_cut_off_mid_transfer_is_retried_then_an_ncbi_error(cfg, error):
    """Live: a Datasets genome download ended prematurely and crashed a long run."""
    http, session, _ = make(cfg, [error, FakeResponse(200, "ok")])
    assert http.request("GET", BLAST, service="blast", params={}).text == "ok"
    n = cfg.ncbi.max_retries + 1
    http, session, _ = make(cfg, [error] * n)
    with pytest.raises(NcbiError, match="ended prematurely|bad gzip"):
        http.request("GET", BLAST, service="blast", params={})


def test_client_errors_fail_immediately_and_never_leak_the_key(cfg):
    http, session, _ = make(
        cfg, [FakeResponse(400, "bad request api_key=SECRETKEY")], key="SECRETKEY"
    )
    with pytest.raises(NcbiError) as exc:
        http.request("GET", EUTILS, service="eutils", params={})
    assert len(session.calls) == 1
    assert "SECRETKEY" not in str(exc.value) and "HTTP 400" in str(exc.value)


def test_retries_are_bounded(cfg):
    n = cfg.ncbi.max_retries + 1
    http, session, _ = make(cfg, [FakeResponse(503)] * n)
    with pytest.raises(NcbiError, match=f"after {n} attempts"):
        http.request("GET", BLAST, service="blast", params={})
    assert len(session.calls) == n


def test_credentials_come_from_the_environment_only():
    c = credentials_from_env({"NCBI_EMAIL": " a@b.org ", "NCBI_API_KEY": "k"})
    assert (c.email, c.api_key) == ("a@b.org", "k")
    assert credentials_from_env({"NCBI_EMAIL": "a@b.org"}).api_key is None
    for env in ({}, {"NCBI_EMAIL": "not-an-address"}, {"NCBI_EMAIL": ""}):
        with pytest.raises(Exception, match="NCBI_EMAIL"):
            credentials_from_env(env)


def test_redact_hides_key_and_email():
    c = Credentials("a@b.org", "KEY123")
    assert c.redact("x KEY123 y a@b.org") == "x *** y <email>"


def test_requests_module_is_the_real_one():
    assert hasattr(requests, "Session")


def test_redaction_covers_url_encoded_addresses_and_query_parameters():
    """Field bug: the e-mail appeared as %40 in an error message and was not masked."""
    from qpcr_assay_check.ncbi.settings import scrub

    c = Credentials("dummy.person@example.org", "KEY123")
    url = "/Blast.cgi?CMD=Get&RID=X&tool=t&email=dummy.person%40example.org&api_key=KEY123"
    out = c.redact(f"ConnectionError: Max retries exceeded with url: {url} (Caused by ...)")
    assert "dummy.person" not in out and "%40" not in out and "KEY123" not in out
    assert "CMD=Get" in out and "RID=X" in out  # the rest of the message stays useful
    assert "dummy.person" not in c.redact(
        "plain dummy.person@example.org, encoded dummy.person%40example.org"
    )
    assert "dummy.person" not in c.redact(
        "plus form dummy.person%40EXAMPLE.org".replace("EXAMPLE", "example")
    )
    assert scrub("email=a%40b.org&x=1") == "email=<redacted>&x=1"
    assert c.redact("nothing secret here") == "nothing secret here"


def test_errors_and_logs_never_contain_the_address(cfg, caplog):
    import logging

    err = connection_error()
    err.args = (
        "HTTPSConnectionPool(host='blast.example', port=443): Max retries exceeded with url: "
        "/Blast.cgi?CMD=Get&tool=qpcr-assay-check&email=lab%40example.org "
        "(Caused by NameResolutionError)",
    )
    n = cfg.ncbi.max_retries + 1
    http, _, _ = make(cfg, [err] * n)
    with caplog.at_level(logging.DEBUG), pytest.raises(NcbiError) as exc:
        http.request("GET", BLAST, service="blast", params={})
    everything = str(exc.value) + caplog.text
    assert "lab%40example.org" not in everything and "lab@example.org" not in everything
    assert "NameResolutionError" in everything  # still diagnosable
