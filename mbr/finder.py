"""Find the best back/lay pairs for an offer."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from mbr.calculator import LayResult, calculate
from mbr.models import Event, Price
from mbr.offers import Offer


@dataclass(frozen=True)
class Match:
    event: Event
    outcome: str
    bookie: str
    back: Price
    exchange: str
    lay: Price
    result: LayResult


def find_matches(
    offer: Offer,
    events: list[Event],
    commissions: dict[str, float],
    now: datetime,
    max_price_age: timedelta = timedelta(minutes=30),
    limit: int = 5,
) -> list[Match]:
    """Rank every outcome the offer's bookie prices by the profit it locks in.

    For each outcome the exchange with the best result is used, so a lower
    commission can beat a slightly better lay price.
    """
    matches = []
    for event in events:
        if event.commence_time <= now:
            continue
        if offer.expires and event.commence_time > offer.expires:
            continue
        for outcome, back in event.back.get(offer.bookie, {}).items():
            if back.odds < offer.min_odds or (offer.max_odds and back.odds > offer.max_odds):
                continue
            best = None
            for exchange, commission in commissions.items():
                lay = event.lay.get(exchange, {}).get(outcome)
                if lay is None or now - lay.updated > max_price_age:
                    continue
                result = calculate(offer.bet_type, offer.stake, back.odds, lay.odds, commission)
                if best is None or result.profit > best.result.profit:
                    best = Match(event, outcome, offer.bookie, back, exchange, lay, result)
            if best:
                matches.append(best)
    matches.sort(key=lambda m: m.result.profit, reverse=True)
    return matches[:limit]
