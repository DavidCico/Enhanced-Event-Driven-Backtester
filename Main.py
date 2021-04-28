"""
Main program to run a backtest for a particular strategy
"""

# Importing some packages
from datetime import datetime
from pathlib import Path

# Import the different components of the backtester
from BacktesterLoop import Backtest
from DataHandler import HistoricCSVDataHandler
from DataHandler import YahooDataHandler
from Execution import SimpleSimulatedExecutionHandler
from Portfolio import Portfolio
from Strategies.ETF_Forecast import ETFDailyForecastStrategy
from Strategies.MAC_Strat import MovingAverageCrossOverStrat

if __name__ == "__main__":
    data_dir = Path.cwd() / 'DataDir'  # For reading from CSV files
    symbol_list = ['^OEX']
    initial_capital = 100000.0
    start_date = datetime(2016, 1, 1, 0, 0, 0)
    end_date = datetime(2021, 1, 1, 0, 0, 0)
    interval = '1d'
    heartbeat = 0.0  # necessary for live feed

    backtest = Backtest(data_dir,  # data directory of CSV files
                        symbol_list,  # list of symbols
                        initial_capital,  # initial capital available for trading
                        heartbeat,  # heartbeat to count time in real live trading simulation
                        start_date,  # starting time of the trading
                        end_date,  # ending time of the trading
                        interval,  # interval of the data
                        YahooDataHandler,  # data management method
                        SimpleSimulatedExecutionHandler,  # Type of execution in relationship to broker
                        Portfolio,  # portfolio management method
                        ETFDailyForecastStrategy)  # strategy chosen

    backtest.simulate_trading()
