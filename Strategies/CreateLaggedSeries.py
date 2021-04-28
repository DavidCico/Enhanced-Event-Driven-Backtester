import yfinance as yf
import pandas as pd
import numpy as np


def create_lagged_series(symbol, start_date, end_date, interval, lags=5):
    """
    This creates a Pandas DataFrame that stores the
    percentage returns of the adjusted closing value of
    a stock obtained from Yahoo Finance, along with a
    number of lagged returns from the prior trading days
    (lags defaults to 5 days). Trading volume, as well as
    the Direction from the previous day, are also included.
    """
    # Obtain stock information from Yahoo Finance
    df_data = yf.download(tickers=[symbol], start=start_date, end=end_date, interval=interval)

    # Create the new lagged DataFrame
    df_lag = pd.DataFrame(index=df_data.index)
    df_lag["Today"] = df_data["Adj Close"]
    df_lag["Volume"] = df_data["Volume"]

    # Create the shifted lag series of prior trading period close values
    for i in range(0, lags):
        df_lag[f"Lag{i + 1}"] = df_data["Adj Close"].shift(i + 1)

    # Create the returns DataFrame
    df_ret = pd.DataFrame(index=df_lag.index)
    df_ret['Volume'] = df_lag['Volume']
    df_ret['Today'] = df_lag['Today'].pct_change() * 100  # daily returns

    # If any of the values of percentage returns equal zero, set them to
    # a small number (stops issues with QDA model in Scikit-Learn)
    df_ret.loc[abs(df_ret['Today']) < 0.0001, 'Today'] = 0.0001

    # Create the lagged percentage returns columns
    for i in range(0, lags):
        df_ret[f'Lag{i + 1}'] = df_lag[f'Lag{i + 1}'].pct_change() * 100.0

    # Create the "Direction" column (+1 or -1) indicating an up/down day
    df_ret['Direction'] = np.sign(df_ret['Today'])
    df_ret = df_ret[df_ret.index >= start_date]

    return df_ret
