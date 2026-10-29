"""Lay stake maths for the three standard matched bet types.

Symbols follow the design doc: B = back stake (or free bet value),
b = back odds, l = lay odds, c = exchange commission as a fraction.
The lay stake is chosen so the result is the same whichever side wins.
"""

from dataclasses import dataclass
from enum import Enum


class BetType(str, Enum):
    QUALIFIER = "qualifier"
    FREE_BET_SNR = "free_bet_snr"  # stake not returned
    FREE_BET_SR = "free_bet_sr"  # stake returned


@dataclass(frozen=True)
class LayResult:
    lay_stake: float
    liability: float
    if_back_wins: float
    if_lay_wins: float

    @property
    def profit(self) -> float:
        """The worse of the two outcomes, which is what you lock in."""
        return min(self.if_back_wins, self.if_lay_wins)


def lay_stake(bet_type: BetType, stake: float, back_odds: float, lay_odds: float, commission: float) -> float:
    _check(stake, back_odds, lay_odds, commission)
    if bet_type is BetType.QUALIFIER or bet_type is BetType.FREE_BET_SR:
        return stake * back_odds / (lay_odds - commission)
    return stake * (back_odds - 1) / (lay_odds - commission)


def calculate(bet_type: BetType, stake: float, back_odds: float, lay_odds: float, commission: float) -> LayResult:
    bet_type = BetType(bet_type)
    lay = round(lay_stake(bet_type, stake, back_odds, lay_odds, commission), 2)
    liability = lay * (lay_odds - 1)

    if bet_type is BetType.QUALIFIER:
        back_win_return = stake * (back_odds - 1)
        cash_staked = stake
    elif bet_type is BetType.FREE_BET_SNR:
        back_win_return = stake * (back_odds - 1)
        cash_staked = 0.0
    else:
        back_win_return = stake * back_odds
        cash_staked = 0.0

    return LayResult(
        lay_stake=lay,
        liability=round(liability, 2),
        if_back_wins=round(back_win_return - liability, 2),
        if_lay_wins=round(lay * (1 - commission) - cash_staked, 2),
    )


def retention(result: LayResult, free_bet_value: float) -> float:
    """Share of a free bet's value you keep, e.g. 0.76 for 76%."""
    return result.profit / free_bet_value


def _check(stake: float, back_odds: float, lay_odds: float, commission: float) -> None:
    if stake <= 0:
        raise ValueError("stake must be positive")
    if back_odds <= 1 or lay_odds <= 1:
        raise ValueError("odds must be above 1.0 (decimal odds)")
    if not 0 <= commission < 1:
        raise ValueError("commission is a fraction, e.g. 0.02 for 2%")
