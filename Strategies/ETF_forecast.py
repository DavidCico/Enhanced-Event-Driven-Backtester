
import pandas as pd
from sklearn.discriminant_analysis import QuadraticDiscriminantAnalysis as QDA
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA

from Strategy import Strategy
from Events import MarketEvent
from Events import SignalEvent

from Create_lagged_series import create_lagged_series

from datetime import datetime



class ETFDailyForecastStrategy(Strategy):
    """
    S&P500 forecast strategy. It uses a Quadratic Discriminant
    Analyser to predict the returns for a subsequent time
    period and then generated long/exit signals based on the
    prediction.
    """

    def __init__(self, bars, events):
        """
        Initialises the buy and hold strategy.

        Parameters:
        bars - The DataHandler object that provides bar information
        events - The Event Queue object.
        """
        self.bars = bars
        self.symbol_list = self.bars.symbol_list
        self.events = events

        self.datetime_now = datetime.utcnow()
        self.model_start_date = datetime(2015,1,1,0,0,0)
        self.model_end_date = datetime(2018,1,1,0,0,0)
        self.model_start_test_date = datetime(2017,1,1,0,0,0)
        
        self.long_market = False
        self.short_market = False
        self.bar_index = 0

        self.model = self.create_symbol_forecast_model()
    
    def create_symbol_forecast_model(self):
        # Create a lagged series of the S&P500 US stock market index
        snpret = create_lagged_series(self.symbol_list[0], self.model_start_date,
        self.model_end_date, lags=5)

        # Use the prior two days of returns as predictor
        # values, with direction as the response
        X = snpret[["Lag1","Lag2"]]
        y = snpret["direction"]

        # Create training and test sets
        start_test = self.model_start_test_date
        X_train = X[X.index < start_test]
        X_test = X[X.index >= start_test]
        y_train = y[y.index < start_test]
        y_test = y[y.index >= start_test]
        model = LDA()
        model.fit(X_train, y_train)
        return model

    def calculate_signals(self, event):
        """
        Calculate the SignalEvents based on market data.
        """
        symbol = self.symbol_list[0]
        dt = self.datetime_now

        if event.type == "MARKET":
            self.bar_index += 1
            if self.bar_index > 5:
                lags = self.bars.get_latest_bars_values(self.symbol_list[0], "today", N=3)
        
                pred_series = pd.Series(
                    {
                    "Lag1": lags[1]*100.0,
                    "Lag2": lags[2]*100.0
                    }
                )

                pred = self.model.predict(pred_series)
        
                if pred > 0 and not self.long_market:
                    self.long_market = True
                    signal = SignalEvent(symbol, dt, "LONG", 1.0)
                    self.events.put(signal)
        
                if pred < 0 and self.long_market:
                    self.long_market = False
                    signal = SignalEvent(symbol, dt, "EXIT", 1.0)
                    self.events.put(signal)