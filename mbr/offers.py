"""Offers you're working, bookie statuses and exchange settings, read from data/."""

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from mbr.calculator import BetType


@dataclass(frozen=True)
class Offer:
    id: str
    bookie: str  # The Odds API bookmaker key, e.g. "williamhill"
    bet_type: BetType
    stake: float
    sports: tuple[str, ...] = ("soccer_epl",)
    min_odds: float = 1.01
    max_odds: float | None = None
    expires: datetime | None = None
    notes: str = ""


@dataclass(frozen=True)
class Bookie:
    name: str
    group: str
    odds_api_key: str
    status: str

    @property
    def active(self) -> bool:
        return self.status.strip().lower() == "active"


def load_offers(path: Path) -> list[Offer]:
    items = json.loads(Path(path).read_text())
    offers = []
    for item in items:
        if not item.get("open", True):
            continue
        expires = item.get("expires")
        offers.append(
            Offer(
                id=item["id"],
                bookie=item["bookie"],
                bet_type=BetType(item["bet_type"]),
                stake=float(item["stake"]),
                sports=tuple(item.get("sports", ["soccer_epl"])),
                min_odds=float(item.get("min_odds", 1.01)),
                max_odds=float(item["max_odds"]) if item.get("max_odds") else None,
                expires=_parse_expiry(expires) if expires else None,
                notes=item.get("notes", ""),
            )
        )
    return offers


def load_bookies(path: Path) -> list[Bookie]:
    with open(path, newline="") as f:
        return [Bookie(r["name"], r["group"], r["odds_api_key"], r["status"]) for r in csv.DictReader(f)]


def load_commissions(path: Path) -> dict[str, float]:
    with open(path, newline="") as f:
        return {r["odds_api_key"]: float(r["commission"]) for r in csv.DictReader(f) if r["enabled"].lower() == "yes"}


def _parse_expiry(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
