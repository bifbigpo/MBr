"""Command line: `python -m mbr calc ...` and `python -m mbr scan`."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from mbr.calculator import BetType, calculate, retention
from mbr.finder import Match, find_matches
from mbr.oddsapi import OddsApiClient, OddsApiError, parse_events
from mbr.offers import Offer, load_bookies, load_commissions, load_offers

DATA = Path("data")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mbr", description="Matched betting helper")
    sub = parser.add_subparsers(dest="command", required=True)

    calc = sub.add_parser("calc", help="work out a lay stake")
    calc.add_argument("bet_type", choices=[t.value for t in BetType])
    calc.add_argument("stake", type=float, help="back stake, or free bet value")
    calc.add_argument("back_odds", type=float)
    calc.add_argument("lay_odds", type=float)
    calc.add_argument("--commission", type=float, default=0.02, help="exchange commission, default 0.02 (Smarkets)")

    scan = sub.add_parser("scan", help="find the best matches for your open offers")
    scan.add_argument("--offers", type=Path, default=DATA / "offers.json")
    scan.add_argument("--offer", help="only scan this offer id")
    scan.add_argument("--limit", type=int, default=5, help="matches to show per offer")
    scan.add_argument("--fixture", type=Path, help="read odds from a saved JSON file instead of the API")
    scan.add_argument("--now", help=argparse.SUPPRESS)

    sub.add_parser("credits", help="show Odds API credits left")

    args = parser.parse_args(argv)
    _load_dotenv(Path(".env"))
    try:
        if args.command == "calc":
            return _calc(args)
        if args.command == "scan":
            return _scan(args)
        return _credits()
    except (OddsApiError, FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def _calc(args) -> int:
    r = calculate(BetType(args.bet_type), args.stake, args.back_odds, args.lay_odds, args.commission)
    print(f"Lay stake:      £{r.lay_stake:.2f}")
    print(f"Liability:      £{r.liability:.2f}")
    print(f"If back wins:   {_money(r.if_back_wins)}")
    print(f"If lay wins:    {_money(r.if_lay_wins)}")
    if args.bet_type != BetType.QUALIFIER.value:
        print(f"Kept:           {retention(r, args.stake):.0%} of the free bet")
    return 0


def _scan(args) -> int:
    if not args.offers.exists():
        raise FileNotFoundError(f"{args.offers} not found. Copy data/offers.example.json to data/offers.json to start.")
    offers = [o for o in load_offers(args.offers) if not args.offer or o.id == args.offer]
    if not offers:
        print("No open offers to scan.")
        return 0
    bookies = {b.odds_api_key: b for b in load_bookies(DATA / "bookies.csv") if b.odds_api_key}
    commissions = load_commissions(DATA / "exchanges.csv")
    now = datetime.fromisoformat(args.now) if args.now else datetime.now(timezone.utc)

    events_by_sport = {}
    if args.fixture:
        raw = json.loads(args.fixture.read_text())
        for event in parse_events(raw, set(commissions)):
            events_by_sport.setdefault(event.sport, []).append(event)
    else:
        client = OddsApiClient(os.environ.get("ODDS_API_KEY", ""))
        for sport in sorted({s for o in offers for s in o.sports}):
            events_by_sport[sport] = parse_events(client.odds(sport), set(commissions))

    for offer in offers:
        bookie = bookies.get(offer.bookie)
        if bookie is None:
            print(f"\n{offer.id}: '{offer.bookie}' isn't in the odds feed, so there's nothing to scan.")
            continue
        if not bookie.active:
            print(f"\nNote: {bookie.name} isn't marked Active in data/bookies.csv.")
        events = [e for s in offer.sports for e in events_by_sport.get(s, [])]
        matches = find_matches(offer, events, commissions, now, limit=args.limit)
        _print_offer(offer, bookie.name, matches)

    if not args.fixture:
        _credits()
    return 0


def _print_offer(offer: Offer, bookie_name: str, matches: list[Match]) -> None:
    kind = offer.bet_type.value.replace("_", " ").replace("snr", "SNR").replace("sr", "SR")
    print(f"\n{offer.id} · {bookie_name} · {kind} £{offer.stake:g}")
    if not matches:
        print("  No matches found. Prices may be missing or older than 30 minutes.")
        return
    header = f"  {'#':<2} {'Match':<30} {'Back on':<18} {'Back':>5} {'Lay':>5} {'Exchange':<14} {'Lay stake':>9} {'Liability':>9} {'Result':>13}  Kick-off"
    print(header)
    for i, m in enumerate(matches, 1):
        result = _money(m.result.profit)
        if offer.bet_type is not BetType.QUALIFIER:
            result += f" ({retention(m.result, offer.stake):.0%})"
        print(
            f"  {i:<2} {m.event.name[:30]:<30} {m.outcome[:18]:<18} {m.back.odds:>5.2f} {m.lay.odds:>5.2f} "
            f"{m.exchange:<14} {_money(m.result.lay_stake):>9} {_money(m.result.liability):>9} {result:>13}  "
            f"{m.event.commence_time:%a %d %b %H:%M}"
        )


def _credits() -> int:
    client = OddsApiClient(os.environ.get("ODDS_API_KEY", "") or "unset")
    credits = client.credits()
    if credits is None:
        print("\nOdds API credits: unknown until the first live scan.")
    else:
        print(f"\nOdds API credits left this month: {credits['remaining']} (used {credits['used']})")
    return 0


def _money(value: float) -> str:
    return f"-£{abs(value):.2f}" if value < 0 else f"£{value:.2f}"


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"'))
