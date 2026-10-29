import pytest

from mbr.calculator import BetType, calculate, lay_stake, retention


def test_qualifier_matches_design_doc_example():
    r = calculate(BetType.QUALIFIER, 10, 3.0, 3.1, 0.02)
    assert r.lay_stake == 9.74
    assert r.liability == 20.45
    assert r.profit == pytest.approx(-0.45, abs=0.005)


def test_free_bet_snr_matches_design_doc_example():
    r = calculate(BetType.FREE_BET_SNR, 10, 5.0, 5.2, 0.02)
    assert r.lay_stake == 7.72
    assert r.profit == pytest.approx(7.57, abs=0.01)
    assert retention(r, 10) == pytest.approx(0.757, abs=0.001)


def test_free_bet_sr_returns_stake():
    r = calculate(BetType.FREE_BET_SR, 10, 2.0, 2.0, 0.0)
    assert r.lay_stake == 10.0
    assert r.if_back_wins == r.if_lay_wins == 10.0


@pytest.mark.parametrize("bet_type", list(BetType))
@pytest.mark.parametrize("back,lay,c", [(2.0, 2.04, 0.02), (6.5, 7.0, 0.05), (1.5, 1.52, 0.0)])
def test_both_outcomes_are_equal_before_rounding(bet_type, back, lay, c):
    stake = 25
    L = lay_stake(bet_type, stake, back, lay, c)
    if bet_type is BetType.QUALIFIER:
        back_wins, lay_wins = stake * (back - 1) - L * (lay - 1), L * (1 - c) - stake
    elif bet_type is BetType.FREE_BET_SNR:
        back_wins, lay_wins = stake * (back - 1) - L * (lay - 1), L * (1 - c)
    else:
        back_wins, lay_wins = stake * back - L * (lay - 1), L * (1 - c)
    assert back_wins == pytest.approx(lay_wins)


def test_bet_type_accepts_strings():
    assert calculate("qualifier", 10, 3.0, 3.1, 0.02).lay_stake == 9.74


@pytest.mark.parametrize("args", [(0, 2, 2, 0.02), (10, 1.0, 2, 0.02), (10, 2, 2, 1.5)])
def test_rejects_bad_input(args):
    with pytest.raises(ValueError):
        calculate(BetType.QUALIFIER, *args)
