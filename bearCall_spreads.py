import yfinance as yf
import pandas as pd
from datetime import datetime, time
from pandas.tseries.offsets import BDay
import pytz

# Define Parameters
ticker = "NVDA"  # Replace with your desired ticker
min_days_to_expiration = 50  # Minimum days to expiration
min_daily_distance = 0.5  # Minimum daily distance for short leg (%)
min_return = 6  # Minimum return (%)
min_distance = 10  # Minimum distance (%) for the short leg
tolerance_minutes = 15  # Time difference tolerance for matching legs

# Define Market Timing
market_tz = pytz.timezone('US/Eastern')
market_open_time = time(9, 30)
market_close_time = time(16, 0)

# Determine the Latest Trading Day
now_gmt = datetime.now(pytz.utc)
now_market = now_gmt.astimezone(market_tz)
if now_market.time() < market_open_time or now_market.weekday() >= 5:
    latest_trading_day = (now_market - BDay(1)).date()
else:
    latest_trading_day = now_market.date()

# Helper Function: Check Time Difference Tolerance
def is_time_within_tolerance(short_leg_time, long_leg_time, tolerance_minutes=15):
    short_time = pd.to_datetime(short_leg_time)
    long_time = pd.to_datetime(long_leg_time)
    return abs((short_time - long_time).total_seconds()) <= tolerance_minutes * 60

# Step 1: Fetch Option Chain Data
stock = yf.Ticker(ticker)
current_price = stock.history(period="1d")["Close"].iloc[-1]
expiration_dates = stock.options

# Step 2: Process Option Chains for Bear Call
results = []
for exp_date in expiration_dates:
    exp_date_dt = datetime.strptime(exp_date, "%Y-%m-%d")
    days_to_exp = (exp_date_dt - datetime.now()).days
    if days_to_exp > min_days_to_expiration:
        continue

    options_chain = stock.option_chain(exp_date)
    calls = options_chain.calls
    calls["expiration_date"] = exp_date
    calls["days_to_expiration"] = days_to_exp
    calls = calls[
        (calls['strike'] > current_price) & 
        (pd.to_datetime(calls['lastTradeDate']).dt.date == latest_trading_day)
    ]
    calls = calls.sort_values(by="strike", ascending=True)

    for i in range(len(calls) - 1):
        short_leg = calls.iloc[i]
        for j in range(i + 1, len(calls)):
            long_leg = calls.iloc[j]
            if long_leg['strike'] <= short_leg['strike']:
                continue
            
            margin_requirement = round(long_leg['strike'] - short_leg['strike'], 2)
            net_premium = round(short_leg['lastPrice'] - long_leg['lastPrice'], 2)
            return_percentage = round((net_premium / margin_requirement) * 100, 2)
            distance = round(((short_leg['strike'] - current_price) / current_price) * 100, 2)
            daily_distance = round(distance / days_to_exp, 2)
            business_days = len(pd.date_range(datetime.now(), exp_date_dt, freq='B'))

            if is_time_within_tolerance(short_leg['lastTradeDate'], long_leg['lastTradeDate']):
                if (
                    return_percentage >= min_return
                    and daily_distance >= min_daily_distance
                    and distance >= min_distance
                ):
                    results.append({
                        "Short Leg Strike": round(short_leg['strike'], 2),
                        "Short Leg Premium": round(short_leg['lastPrice'], 2),
                        "Short Leg Volume": short_leg['volume'],
                        "Short Leg Open Interest": short_leg['openInterest'],
                        "Long Leg Strike": round(long_leg['strike'], 2),
                        "Long Leg Premium": round(long_leg['lastPrice'], 2),
                        "Margin Requirement": margin_requirement,
                        "Net Premium": net_premium,
                        "Return (%)": return_percentage,
                        "Distance (%)": distance,
                        "Daily Distance (%)": daily_distance,
                        "Days to Expiration": days_to_exp,
                        "Business Days to Expiration": business_days,
                        "Expiration Date": exp_date_dt,
                        "Last Trade (Short Leg)": short_leg['lastTradeDate'],
                        "Last Trade (Long Leg)": long_leg['lastTradeDate'],
                        "IV (Short Leg)": round(short_leg['impliedVolatility'], 2),
                        "IV (Long Leg)": round(long_leg['impliedVolatility'], 2),
                    })

# Step 3: Export Results
if results:
    results_df = pd.DataFrame(results).sort_values(by="Return (%)", ascending=False)
    results_df.drop_duplicates(inplace=True)
    results_df.to_csv('bear_call_spreads.csv', index=False)
    print(f"Results saved to 'bear_call_spreads.csv'.")
else:
    print("\nNo qualifying bear call spreads found that meet the criteria.")
