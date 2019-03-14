
##### Main program to run the backtest on a particular strategy

# Importing datetime
from datetime import datetime

# Import the different components of the backtester
from Backtester_loop import Backtest
from DataHandler import HistoricCSVDataHandler #HistoricMySQLDataHandler
from Execution import SimpleSimulatedExecutionHandler
from Portfolio import Portfolio

#The different strategies that can be used in the backtester
from Strategies.Buy_and_hold_strat import BuyAndHoldStrat
from Strategies.Moving_average_crossover_strat import MovingAverageCrossOverStrat

if __name__ == "__main__":
    data_dir = '~/Backtester_model/Data_directory' # Needs to be specified based on your own path
    symbol_list = ['AAPL']
    initial_capital = 100000.0
    start_date = datetime(1990,1,1,0,0,0)
    heartbeat = 0.0

    backtest = Backtest(data_dir,  # data directory of CSV files
                        symbol_list,  # list of symbols
                        initial_capital, # initial capital available for trading
                        heartbeat, # heartbeat to count time in real live trading simulation
                        start_date, # starting time of the trading
                        HistoricCSVDataHandler, # data management method
                        SimpleSimulatedExecutionHandler, # Type of execution in relationship to broker
                        Portfolio, # portfolio management method
                        MovingAverageCrossOverStrat) # strategy chosen
    
    backtest.simulate_trading()