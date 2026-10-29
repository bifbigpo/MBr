"""Client for The Odds API (https://the-odds-api.com), v4.

The free plan gives 500 credits a month. Each call costs
(number of markets) x (number of regions), so one sport with back and lay
odds for the UK costs 2 credits. Responses are cached on disk so repeated
scans inside the cache window cost nothing.
"""

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from mbr.models import Event, Price

BASE_URL = "https://api.the-odds-api.com/v4"
BACK_MARKET = "h2h"
LAY_MARKET = "h2h_lay"


class OddsApiError(RuntimeError):
    pass


class CreditBudgetError(OddsApiError):
    pass


class OddsApiClient:
    def __init__(
        self,
        api_key: str,
        cache_dir: Path = Path(".cache/odds"),
        cache_seconds: int = 900,
        min_credits_left: int = 20,
        fetch=None,
    ):
        if not api_key:
            raise OddsApiError("ODDS_API_KEY is not set. Get a free key at https://the-odds-api.com")
        self.api_key = api_key
        self.cache_dir = Path(cache_dir)
        self.cache_seconds = cache_seconds
        self.min_credits_left = min_credits_left
        self._fetch = fetch or _http_get

    def odds(self, sport: str, regions: str = "uk", markets: tuple[str, ...] = (BACK_MARKET, LAY_MARKET)) -> list[dict]:
        params = {
            "regions": regions,
            "markets": ",".join(markets),
            "oddsFormat": "decimal",
            "dateFormat": "iso",
        }
        cached = self._read_cache(sport, params)
        if cached is not None:
            return cached

        credits = self.credits()
        cost = len(markets) * len(regions.split(","))
        if credits is not None and credits["remaining"] - cost < self.min_credits_left:
            raise CreditBudgetError(
                f"Only {credits['remaining']} Odds API credits left this month; "
                f"keeping {self.min_credits_left} in reserve, so not fetching {sport}."
            )

        url = f"{BASE_URL}/sports/{urllib.parse.quote(sport)}/odds/?" + urllib.parse.urlencode(
            {**params, "apiKey": self.api_key}
        )
        body, headers = self._fetch(url)
        data = json.loads(body)
        self._write_cache(sport, params, data)
        self._record_credits(headers)
        return data

    def credits(self) -> dict | None:
        """Last known credit usage, from the most recent response headers."""
        path = self.cache_dir / "credits.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def _cache_path(self, sport: str, params: dict) -> Path:
        key = hashlib.sha1(json.dumps([sport, params], sort_keys=True).encode()).hexdigest()[:16]
        return self.cache_dir / f"{sport}-{key}.json"

    def _read_cache(self, sport: str, params: dict):
        path = self._cache_path(sport, params)
        if path.exists() and time.time() - path.stat().st_mtime < self.cache_seconds:
            return json.loads(path.read_text())
        return None

    def _write_cache(self, sport: str, params: dict, data) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_path(sport, params).write_text(json.dumps(data))

    def _record_credits(self, headers) -> None:
        remaining = headers.get("x-requests-remaining")
        used = headers.get("x-requests-used")
        if remaining is None:
            return
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        (self.cache_dir / "credits.json").write_text(
            json.dumps({"remaining": int(float(remaining)), "used": int(float(used or 0)), "checked": time.time()})
        )


def _http_get(url: str) -> tuple[str, dict]:
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return resp.read().decode(), headers
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        raise OddsApiError(f"The Odds API returned {e.code}: {detail}") from e


def parse_events(raw: list[dict], exchanges: set[str]) -> list[Event]:
    """Split each event's prices into bookie back odds and exchange lay odds."""
    events = []
    for item in raw:
        event = Event(
            id=item["id"],
            sport=item["sport_key"],
            commence_time=_parse_time(item["commence_time"]),
            home_team=item.get("home_team", ""),
            away_team=item.get("away_team", ""),
        )
        for book in item.get("bookmakers", []):
            for market in book.get("markets", []):
                updated = _parse_time(market.get("last_update") or book["last_update"])
                prices = {o["name"]: Price(float(o["price"]), updated) for o in market.get("outcomes", [])}
                if market["key"] == LAY_MARKET and book["key"] in exchanges:
                    event.lay[book["key"]] = prices
                elif market["key"] == BACK_MARKET and book["key"] not in exchanges:
                    event.back[book["key"]] = prices
        events.append(event)
    return events


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
