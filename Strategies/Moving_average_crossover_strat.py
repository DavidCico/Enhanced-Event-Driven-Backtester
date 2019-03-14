from Strategy import Strategy
from Events import MarketEvent
from Events import SignalEvent
from DataHandler import HistoricCSVDataHandler

import datetime
import numpy as np
import pandas as pd
import statsmodels.api as sm

class MovingAverageCrossOverStrat(Strategy):
    """
    Carries out a basic Moving Average Crossover strategy with a
    short/long simple weighted moving average. Default short/long
    windows are 100/400 periods respectively.
    """
    
    def __init__(self, bars, events, short_window=100, long_window=400):
        """
        Initialises the Moving Average Cross Strategy.
        Parameters:
        bars - The DataHandler object that provides bar information
        events - The Event Queue object.
        short_window - The short moving average lookback.
        long_window - The long moving average lookback.
        """

        self.bars = bars
        self.symbol_list = self.bars.symbol_list
        self.events = events
        self.short_window = short_window
        self.long_window = long_window

        # Set to True if a symbol is in the market
        self.bought = self._calculate_initial_bought()

    def _calculate_initial_bought(self):
        """
        Adds keys to the bought dictionary for all symbols
        and sets them to 'OUT'.
        """
        
        bought = {symbol: "OUT" for symbol in self.symbol_list}
        return bought

    def calculate_signals(self, event):
        """
        Generates a new set of signals based on the MAC
        SMA with the short window crossing the long window
        meaning a long entry and vice versa for a short entry.
        Parameters
        event - A MarketEvent object.
        """

        if isinstance(event, MarketEvent):
            for symbol in self.symbol_list:
                bars = self.bars.get_latest_bars_values(symbol, "adj_close", N=self.long_window)
                bar_datetime = self.bars.get_latest_bar_datetime(symbol)

                if bars is not None and bars != []:
                    short_sma = np.mean( bars[-self.short_window:] )
                    long_sma = np.mean( bars[-self.long_window:] )

                    dt = datetime.datetime.utcnow()
                    signal_type = ""
                    strength = 1.0

                    if short_sma > long_sma and self.bought[symbol] == "OUT":
                        print("LONG position at: %s" % bar_datetime)
                        signal_type = "LONG"
                        signal = SignalEvent(symbol, dt, signal_type, strength)
                        self.events.put(signal)
                        self.bought[symbol] = "LONG"

                    elif short_sma < long_sma and self.bought[symbol] == "LONG":
                        print("SHORT position at: %s" % bar_datetime)
                        signal_type = "EXIT"
                        signal = SignalEvent(symbol, dt, signal_type, strength)
                        self.events.put(signal)
                        self.bought[symbol] = "OUT"



