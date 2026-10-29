# MBr

A matched betting helper. It finds the best back/lay matches for the offers you're working and works out the lay stakes. Telegram alerts and tracking come next.

Bookie bets are always placed by hand: automated betting breaks bookie terms.

## Setup

```bash
pip install -e ".[dev]"
cp .env.example .env                          # add your free key from the-odds-api.com
cp data/offers.example.json data/offers.json  # then edit in your own offers
```

Never commit `.env` or `data/offers.json`; both are git-ignored.

## Use it

```bash
python -m mbr calc qualifier 10 3.0 3.1       # lay stake for one bet
python -m mbr calc free_bet_snr 10 5.0 5.2 --commission 0.05
python -m mbr scan                            # best matches for every open offer
python -m mbr scan --offer skybet-free-bet-5 --limit 10
python -m mbr credits                         # Odds API credits left this month
```

Bet types: `qualifier`, `free_bet_snr` (stake not returned), `free_bet_sr` (stake returned).

## Data files

| File | What it holds |
| --- | --- |
| `data/offers.json` | Offers you're working: bookie (Odds API key), bet type, stake, minimum odds, sports, expiry. Set `"open": false` when done. |
| `data/bookies.csv` | UK bookies, their Odds API key, and your status. Set status to `Active` for accounts you use. |
| `data/exchanges.csv` | Exchanges to lay on and their commission. |

## Odds and credits

Odds come from [The Odds API](https://the-odds-api.com). Each scan costs 2 credits per sport (back odds plus exchange lay odds), and responses are cached for 15 minutes so repeat scans are free. The free plan has 500 credits a month; the scanner stops fetching when fewer than 20 are left.

Lay prices older than 30 minutes and matches that have already kicked off are skipped. Always check the live lay price before you place the bet.

## Tests

```bash
pytest -q
```
