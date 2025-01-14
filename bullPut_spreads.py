import yfinance as yf
import pandas as pd
from datetime import datetime, time
from pandas.tseries.offsets import BDay
import pytz

# Helper Function: Check Time Difference Tolerance
def is_time_within_tolerance(short_leg_time, long_leg_time, tolerance_minutes=15):
    if isinstance(short_leg_time, (pd.Timestamp, datetime)):
        short_time = short_leg_time
    else:
        short_time = datetime.strptime(short_leg_time, "%H:%M")
        
    if isinstance(long_leg_time, (pd.Timestamp, datetime)):
        long_time = long_leg_time
    else:
        long_time = datetime.strptime(long_leg_time, "%H:%M")
    
    return abs((short_time - long_time).total_seconds()) <= tolerance_minutes * 60


# Define Parameters
ticker = "NVDA"  # Replace with your desired ticker
min_days_to_expiration = 50  # Minimum days to expiration
min_daily_distance = 0.5  # Minimum daily distance for short leg (%)
min_return = 6  # Minimum return (%)
min_distance = 10  # Minimum distance (%) for the short leg

# Define Market Timing
market_tz = pytz.timezone('US/Eastern')
market_open_time = time(9, 30)  # Market opens at 9:30 AM ET
market_close_time = time(16, 0)  # Market closes at 4:00 PM ET

# Determine the Latest Trading Day
now_gmt = datetime.now(pytz.utc)
now_market = now_gmt.astimezone(market_tz)
if (
    now_market.time() < market_open_time or  # Before market opens
    now_market.weekday() >= 5  # Weekend (Saturday=5, Sunday=6)
):
    latest_trading_day = (now_market - BDay(1)).date()  # Previous business day
else:
    latest_trading_day = now_market.date()  # Current day if market is open


# Step 1: Fetch Option Chain Data from Yahoo Finance
stock = yf.Ticker(ticker)
current_price = stock.history(period="1d")["Close"].iloc[-1]
expiration_dates = stock.options


# Step 2: Process Option Chains
results = []
for exp_date in expiration_dates:
    # Parse expiration date
    exp_date_dt = datetime.strptime(exp_date, "%Y-%m-%d")
    # Skip expired options or those with less than the minimum days to expiration
    days_to_exp = (exp_date_dt - datetime.now()).days
    if days_to_exp > min_days_to_expiration:
        continue
    
    # Fetch puts for the expiration date
    options_chain = stock.option_chain(exp_date)
    puts = options_chain.puts
    puts["expiration_date"] = exp_date
    puts["days_to_expiration"] = days_to_exp
    puts = puts[
        (puts['strike'] < current_price) & 
        (pd.to_datetime(puts['lastTradeDate']).dt.date == latest_trading_day)
    ]
    puts = puts.sort_values(by="strike", ascending=False)
    for i in range(len(puts) - 1):
        short_leg = puts.iloc[i]
        for j in range(i + 1, len(puts)):
            long_leg = puts.iloc[j]
            # Ensure the long leg is lower than the short leg
            if long_leg['strike'] < short_leg['strike']:
                margin_requirement = short_leg['strike'] - long_leg['strike']
                net_premium = short_leg['lastPrice'] - long_leg['lastPrice']
                return_percentage = (net_premium / margin_requirement) * 100
                distance = ((current_price - short_leg['strike']) / current_price) * 100
                daily_distance = distance / short_leg['days_to_expiration']
                
                # Extract expiration date and days to expiration from the short leg symbol
                short_leg_symbol = short_leg['contractSymbol']
                exp_date_str = short_leg_symbol[4:10]  # Extract the YYMMDD part of the symbol
                exp_date_dt = datetime.strptime(exp_date_str, "%y%m%d")
                business_days = len(pd.date_range(datetime.now(), short_leg['expiration_date'], freq='B'))

                if is_time_within_tolerance(short_leg['lastTradeDate'], long_leg['lastTradeDate']):

                # Apply filters
                    if (
                        return_percentage >= min_return
                        and daily_distance >= min_daily_distance
                        and distance >= min_distance
                    ):
                        results.append({
                            "Short Leg Strike": short_leg['strike'],
                            "Short Leg Premium": short_leg['lastPrice'],
                            "Short Leg Volume": short_leg['volume'],
                            "Short Leg Open Interest": short_leg['openInterest'],
                            "Long Leg Strike": long_leg['strike'],
                            "Long Leg Premium": long_leg['lastPrice'],
                            "Margin Requirement": margin_requirement,
                            "Net Premium": round(net_premium, 2),
                            "Return (%)": round(return_percentage, 2),
                            "Distance (%)": round(distance, 2),
                            "Daily Distance (%)": round(daily_distance, 2),
                            "Days to Expiration": short_leg['days_to_expiration'],
                            "Business Days to Expiration": business_days,
                            "Expiration Date": short_leg['expiration_date'],
                            "last_trade_short": short_leg['lastTradeDate'],
                            "last_trade_long": long_leg['lastTradeDate'],
                            "IV_short": round(short_leg['impliedVolatility'], 2),
                            "IV_long": round(long_leg['impliedVolatility'],2)
                        })

# Step 3: Export Results
if results:
    results_df = pd.DataFrame(results).sort_values(by="Return (%)", ascending=False)
    results_df.drop_duplicates(inplace=True)
    results_df.to_csv('bull_put_spreads.csv', index=False)
    print(f"Results saved to 'bull_put_spreads.csv'.")
else:
    print("\nNo qualifying bull put spreads found that meet the criteria.")