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
    assert 0.3 < sum(fc1.slept) < 0.4  # ~3 requests/second
    assert 0.1 <= sum(fc2.slept) < 0.15  # ~10 requests/second


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
