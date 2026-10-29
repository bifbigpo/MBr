from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Price:
    odds: float
    updated: datetime


@dataclass
class Event:
    id: str
    sport: str
    commence_time: datetime
    home_team: str
    away_team: str
    # bookie key -> outcome name -> back price
    back: dict[str, dict[str, Price]] = field(default_factory=dict)
    # exchange key -> outcome name -> lay price
    lay: dict[str, dict[str, Price]] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return f"{self.home_team} v {self.away_team}"
