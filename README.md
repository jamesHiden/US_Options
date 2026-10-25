# US Credit-Spread Screener

Two screeners that scan a US option chain (via Yahoo Finance) for **vertical credit spreads** that meet
distance-from-spot and return-on-margin rules. I used them to shortlist trades for a premium-selling book.

| Script | Spread | Short leg |
|---|---|---|
| `bullPut_spreads.py` | bull put (sell put, buy lower put) | below spot |
| `bearCall_spreads.py` | bear call (sell call, buy higher call) | above spot |

## Filters (top of each script)

| Parameter | Default | Meaning |
|---|---|---|
| `ticker` | `NVDA` | underlying |
| `max_days_to_expiration` | 50 | only expirations within this many days |
| `min_distance` | 10% | short strike at least this far out-of-the-money |
| `min_daily_distance` | 0.5% | OTM distance per day to expiry, so short-dated trades need less cushion than long-dated ones |
| `min_return` | 6% | net premium / width of spread (max-loss margin) |
| `tolerance_minutes` | 15 | both legs must have last-traded within this window, which avoids stale quotes |

Legs are only paired if both traded on the latest session. Output includes premiums, volume, open interest,
implied vol of each leg, and business days to expiry, saved to `bull_put_spreads.csv` / `bear_call_spreads.csv`
(sample output from Jan 2025 included).

## Caveats

- Uses `lastPrice`, not bid/ask, so real fills will be worse. A production version should use mid or a bid/ask-based price.
- Return on margin ignores the probability of loss. A natural extension is ranking by expected value using the
  implied-vol-based probability that the short strike finishes in-the-money.

## Run

```bash
pip install -r requirements.txt
python bullPut_spreads.py
```
