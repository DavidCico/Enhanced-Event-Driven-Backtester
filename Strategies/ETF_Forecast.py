import pandas as pd
from sklearn.discriminant_analysis import QuadraticDiscriminantAnalysis as QDA
from Strategy import Strategy
from Events import SignalEvent
from Events import MarketEvent
from Strategies.CreateLaggedSeries import create_lagged_series

from datetime import datetime


class ETFDailyForecastStrategy(Strategy):
    """
    S&P100 forecast strategy. It uses a Quadratic Discriminant
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

        # FIXME --> Here the models are fit on the training dataset only, especially here with the
        # regime change in 1st quarter 2020
        self.datetime_now = datetime.utcnow()
        self.model_start_date = datetime(2016, 1, 1, 0, 0, 0)
        self.model_end_date = datetime(2021, 1, 1, 0, 0, 0)
        self.model_start_test_date = datetime(2020, 1, 1, 0, 0, 0)
        self.model_interval = '1d'

        self.long_market = False
        self.short_market = False
        self.bar_index = 0

        self.model = self.create_symbol_forecast_model()

    """
    The model here is directly chosen, as for calculating inside the trading signals. For model choice,
    it's better to run a script outside of the backtest strategy. 
    """

    def create_symbol_forecast_model(self):
        # Create a lagged series of the S&P500 US stock market index
        df_ret = create_lagged_series(self.symbol_list[0], self.model_start_date,
                                      self.model_end_date, self.model_interval, lags=5)

        # Use the prior two days of returns as predictor
        # values, with direction as the response
        X = df_ret[["Lag1", "Lag2"]]
        Y = df_ret["Direction"]

        # Create training and test sets
        start_test = self.model_start_test_date
        X_train = X[X.index < start_test]
        X_train = X[X.index > X.index[2]]  # avoid 2 nan values TODO --> filter one is timestamp other datetime index
        X_test = X[X.index >= start_test]
        Y_train = Y[Y.index < start_test]
        Y_train = Y[Y.index > Y.index[2]]
        Y_test = Y[Y.index >= start_test]

        """
        Here we choose QDA, but the strategy would be dependent on different parameters.
        There is requirements to test the strategy with different models, k-fold cross validation,
        and also grid searching for parameters optimization
        """
        model = QDA()
        model.fit(X_train, Y_train)  # TODO --> The model could be fit on the whole dataset, this is on model validation
        return model

    def calculate_signals(self, event):
        """
        Calculate the SignalEvents based on market data.
        """
        symbol = self.symbol_list[0]
        dt = self.datetime_now

        if isinstance(event, MarketEvent):
            self.bar_index += 1

            # make sure we wait 5 days to get the latest "bar" values
            if self.bar_index > 5:
                lags = self.bars.get_latest_bars_values(self.symbol_list[0], "returns", N=3)

                # series of lags for 2 days prior
                pred_series = pd.Series(
                    {
                        "Lag1": lags[1] * 100.0,
                        "Lag2": lags[2] * 100.0
                    }
                )

                # reshape the array as it needs to be 2d
                pred_values = pred_series.values.reshape(1, -1)
                pred = self.model.predict(pred_values)

                # if price prediction is up and not LONG then BUY
                if pred > 0 and not self.long_market:
                    self.long_market = True
                    signal = SignalEvent(symbol, dt, "LONG", 1.0)
                    self.events.put(signal)

                # if price prediction down and LONG then SELL
                if pred < 0 and self.long_market:
                    self.long_market = False
                    signal = SignalEvent(symbol, dt, "EXIT", 1.0)
                    self.events.put(signal)
