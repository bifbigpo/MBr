import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from mbr.calculator import BetType
from mbr.finder import find_matches
from mbr.oddsapi import parse_events
from mbr.offers import Offer

FIXTURE = Path(__file__).parent / "fixtures" / "epl_odds.json"
NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
COMMISSIONS = {"smarkets": 0.02, "betfair_ex_uk": 0.05}


def events():
    return parse_events(json.loads(FIXTURE.read_text()), set(COMMISSIONS))


def offer(**kw):
    base = dict(id="o", bookie="williamhill", bet_type=BetType.QUALIFIER, stake=10)
    return Offer(**{**base, **kw})


def test_parse_splits_back_and_lay():
    e = events()[0]
    assert set(e.back) == {"williamhill", "skybet"}
    assert set(e.lay) == {"smarkets", "betfair_ex_uk"}
    assert e.lay["smarkets"]["Arsenal"].odds == 1.84


def test_exchange_back_prices_are_not_used_as_lay():
    # Smarkets also sends an h2h (back) market; only h2h_lay counts as lay.
    assert events()[0].lay["smarkets"]["Draw"].odds == 4.00


def test_best_match_first_and_sorted():
    matches = find_matches(offer(), events(), COMMISSIONS, NOW, limit=10)
    profits = [m.result.profit for m in matches]
    assert profits == sorted(profits, reverse=True)
    assert all(m.bookie == "williamhill" for m in matches)


def test_skips_started_events_and_stale_lay_prices():
    names = {m.event.name for m in find_matches(offer(), events(), COMMISSIONS, NOW, limit=50)}
    assert "Brighton v Newcastle United" not in names  # already kicked off
    assert "Liverpool v Fulham" not in names  # lay price 3 hours old


def test_stale_prices_allowed_with_wider_window():
    names = {
        m.event.name
        for m in find_matches(offer(), events(), COMMISSIONS, NOW, max_price_age=timedelta(hours=4), limit=50)
    }
    assert "Liverpool v Fulham" in names


def test_min_odds_and_expiry_filters():
    matches = find_matches(offer(min_odds=2.0), events(), COMMISSIONS, NOW, limit=50)
    assert all(m.back.odds >= 2.0 for m in matches)
    expires = datetime(2026, 11, 1, 23, 0, tzinfo=timezone.utc)
    matches = find_matches(offer(expires=expires), events(), COMMISSIONS, NOW, limit=50)
    assert all(m.event.commence_time <= expires for m in matches)
    assert matches


def test_picks_exchange_with_better_result_after_commission():
    # Arsenal: Smarkets 1.84 at 2% beats Betfair 1.82 at 5%.
    m = [m for m in find_matches(offer(), events(), COMMISSIONS, NOW, limit=50) if m.outcome == "Arsenal"][0]
    assert m.exchange == "smarkets"


def test_free_bet_prefers_longer_odds():
    matches = find_matches(offer(bet_type=BetType.FREE_BET_SNR, bookie="skybet"), events(), COMMISSIONS, NOW)
    assert matches[0].back.odds >= 4.0
    assert matches[0].result.profit > 0


def test_unknown_bookie_gives_nothing():
    assert find_matches(offer(bookie="bet365"), events(), COMMISSIONS, NOW) == []
