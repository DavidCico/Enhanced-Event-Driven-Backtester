from __future__ import print_function
import pprint

try:
    import Queue as queue
except ImportError:
    import queue
import time

from Events import MarketEvent
from Events import SignalEvent
from Events import OrderEvent
from Events import FillEvent


class Backtest(object):
    """
    Encapsulates the settings and components for carrying out
    an event-driven backtest.
    """

    def __init__(self, data_dir, symbol_list, initial_capital,
                 heartbeat, start_date, end_date, interval,
                 data_handler, execution_handler, portfolio, strategy
                 ):
        """
        Initialises the backtest

        Parameters:
        data_dir - The hard root to the CSV data directory.
        symbol_list - The list of symbol strings.
        initial_capital - The starting capital for the portfolio.
        heartbeat - Backtest "heartbeat" in seconds
        start_date - The start datetime of the strategy.
        end_date - The end datetime of the strategy
        interval - Interval for the data
        data_handler - (Class) Handles the market data feed.
        execution_handler - (Class) Handles the orders/fills for trades.
        portfolio - (Class) Keeps track of portfolio current and prior positions.
        strategy - (Class) Generates signals based on market data.
        """

        self.data_dir = data_dir
        self.symbol_list = symbol_list
        self.initial_capital = initial_capital
        self.heartbeat = heartbeat
        self.start_date = start_date
        self.end_date = end_date
        self.interval = interval

        self.data_handler_cls = data_handler
        self.execution_handler_cls = execution_handler
        self.portfolio_cls = portfolio
        self.strategy_cls = strategy

        self.events = queue.Queue()
        self.signals = 0
        self.orders = 0
        self.fills = 0
        self.num_strats = 1

        self._generate_trading_instances()

    def _generate_trading_instances(self):
        """
        Generates the trading instance objects from
        their class types.
        """

        print("Creating DataHandler, Strategy, Portfolio and ExecutionHandler")

        # Select data handler if from HistoricCSV file or from Yahoo Finance
        if self.data_handler_cls.__name__ == 'HistoricCSVDataHandler':
            self.data_handler = self.data_handler_cls(self.events, self.data_dir, self.symbol_list)

        # TODO --> Implement a better selection mode
        else:
            self.data_handler = self.data_handler_cls(self.events, self.symbol_list, self.interval,
                                                      self.start_date, self.end_date)

        # similar, here the strategy class could have different type of strategies (vol clustering, intraday, etc)
        self.strategy = self.strategy_cls(self.data_handler, self.events)

        self.portfolio = self.portfolio_cls(self.data_handler, self.events, self.start_date, self.initial_capital)

        self.execution_handler = self.execution_handler_cls(self.events)

    def _run_backtest(self):
        """
        Executes the backtest. The backtest is implemented on an event driven architecture, with 2 infinite while loop
        The outer loop runs as long as the data can be updated from the source. If historical data after iterator
        updates the last "bar", the while loop will break.
        The inner loop corresponds to the events added and popped from a queue. As long as the queue is not empty,
        it will keep running and being updated based on the different events realized

        After each outer iteration, the system is put to sleep by the heartbeat time. When receiving live datafeed,
        it is important to get the data at a precise time.
        """

        i = 0
        while True:
            i += 1
            print(i)
            # Update the market bars
            if self.data_handler.continue_backtest:
                self.data_handler.update_bars()
            else:
                break

            # Handle the events
            while True:
                try:
                    event = self.events.get(False)
                except queue.Empty:
                    break
                else:
                    if event is not None:
                        if isinstance(event, MarketEvent):
                            self.strategy.calculate_signals(event)
                            self.portfolio.update_timeindex(event)

                        elif isinstance(event, SignalEvent):
                            self.signals += 1
                            self.portfolio.update_signal(event)

                        elif isinstance(event, OrderEvent):
                            self.orders += 1
                            self.execution_handler.execute_order(event)

                        elif isinstance(event, FillEvent):
                            self.fills += 1
                            self.portfolio.update_fill(event)

            time.sleep(self.heartbeat)

    def _output_performance(self):
        """
        Outputs the strategy performance from the backtest.
        """
        self.portfolio.create_equity_curve_dataframe()

        print("Creating summary stats...")
        stats = self.portfolio.output_summary_stats()

        print("Creating equity curve...")
        print(self.portfolio.equity_curve.tail(10))

        pprint.pprint(stats)
        print("Signals: %s" % self.signals)
        print("Orders: %s" % self.orders)
        print("Fills: %s" % self.fills)

    def simulate_trading(self):
        """
        Simulates the backtest and outputs portfolio performance.
        """
        self._run_backtest()
        self._output_performance()
