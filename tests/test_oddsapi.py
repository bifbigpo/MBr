import json

import pytest

from mbr.oddsapi import CreditBudgetError, OddsApiClient, OddsApiError


def fake_fetch(calls, remaining="480"):
    def fetch(url):
        calls.append(url)
        return json.dumps([]), {"x-requests-remaining": remaining, "x-requests-used": "20"}

    return fetch


def test_requires_key(tmp_path):
    with pytest.raises(OddsApiError):
        OddsApiClient("", cache_dir=tmp_path)


def test_requests_back_and_lay_markets_and_caches(tmp_path):
    calls = []
    client = OddsApiClient("k", cache_dir=tmp_path, fetch=fake_fetch(calls))
    client.odds("soccer_epl")
    client.odds("soccer_epl")
    assert len(calls) == 1
    assert "markets=h2h%2Ch2h_lay" in calls[0] and "regions=uk" in calls[0]
    assert client.credits()["remaining"] == 480


def test_refuses_when_credits_run_low(tmp_path):
    calls = []
    client = OddsApiClient("k", cache_dir=tmp_path, cache_seconds=0, fetch=fake_fetch(calls, remaining="21"))
    client.odds("soccer_epl")
    with pytest.raises(CreditBudgetError):
        client.odds("soccer_fa_cup")
    assert len(calls) == 1
