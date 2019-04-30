from __future__ import print_function

from abc import ABCMeta, abstractmethod

import datetime
import os, os.path

import numpy as np
import pandas as pd
from Events import MarketEvent

import requests                  # [handles the http interactions](http://docs.python-requests.org/en/master/) 
from bs4 import BeautifulSoup    # beautiful soup handles the html to text conversion and more
import re                        # regular expressions are necessary for finding the crumb (more on crumbs later)
from datetime import datetime    # string to datetime object conversion
from time import mktime    

#import MySQLdb
    
class DataManagement(object):
    """
    DataManagement is an abstract base class providing an interface for
    all subsequent (inherited) data handlers (both live and historic).
    The goal of a (derived) DataHandler object is to output a generated
    set of bars (OHLCVI) for each symbol requested.
    This will replicate how a live strategy would function as current
    market data would be sent "down the pipe". Thus a historic and live
    system will be treated identically by the rest of the backtesting suite.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_latest_bar(self, symbol):
        """
        Returns the last bar updated.
        """
        raise NotImplementedError("Should implement get_latest_bar()")

    @abstractmethod
    def get_latest_bars(self, symbol, N=1):
        """
        Returns the last N bars updated.
        """
        raise NotImplementedError("Should implement get_latest_bars()")

    @abstractmethod
    def get_latest_bar_datetime(self, symbol):
        """
        Returns a Python datetime object for the last bar.
        """
        raise NotImplementedError("Should implement get_latest_bar_datetime()")

    @abstractmethod
    def get_latest_bar_value(self, symbol, val_type):
        """
        Returns one of the Open, High, Low, Close, Volume or OI
        from the last bar.
        """
        raise NotImplementedError("Should implement get_latest_bar_value()")

    @abstractmethod
    def get_latest_bars_values(self, symbol, val_type, N=1):
        """
        Returns the last N bar values from the
        latest_symbol list, or N-k if less available.
        """
        raise NotImplementedError("Should implement get_latest_bars_values()")

    @abstractmethod
    def update_bars(self):
        """
        Pushes the latest bars to the bars_queue for each symbol
        in a tuple OHLCVI format: (datetime, open, high, low,
        close, volume, adj closing price).
        """
        raise NotImplementedError("Should implement update_bars()")


class HistoricCSVDataHandler(DataManagement):

    """
    HistoricCSVDataHandler is designed to read CSV files for
    each requested symbol from disk and provide an interface
    to obtain the "latest" bar in a manner identical to a live
    trading interface.
    """

    def __init__(self, events, csv_dir, symbol_list):

        """
        Initialises the historic data handler by requesting
        the location of the CSV files and a list of symbols.
        It will be assumed that all files are of the form
        'symbol.csv', where symbol is a string in the list.
        Parameters:
        events - The Event Queue.
        csv_dir - Absolute directory path to the CSV files.
        symbol_list - A list of symbol strings.
        """

        self.events = events
        self.csv_dir = csv_dir
        self.symbol_list = symbol_list

        self.symbol_data = {}
        self.latest_symbol_data = {}
        self.continue_backtest = True
        self._data_conversion_from_csv_files()


    def _data_conversion_from_csv_files(self):
        """
        Opens the CSV files from the data directory, converting
        them into pandas DataFrames within a symbol dictionary.
        """

        combined_index = None
        for symbol in self.symbol_list:
            # Load the CSV file with no header information, indexed on date
            self.symbol_data[symbol] = pd.io.parsers.read_csv(
                                      os.path.join(self.csv_dir, "%s.csv" % symbol),
                                      header=0, index_col=0, 
                                      names=["datetime","open","high","low","close","adj_close","volume"]
                                  )

            # Combine the index to pad forward values
            if combined_index is None:
                combined_index = self.symbol_data[symbol].index
            else:
                combined_index.union(self.symbol_data[symbol].index)

            # Set the latest symbol_data to None
            self.latest_symbol_data[symbol] = []

        # Reindex the dataframes
        for symbol in self.symbol_list:
            self.symbol_data[symbol] = self.symbol_data[symbol].reindex(index=combined_index, method="pad").iterrows()

    def _get_new_bar(self, symbol):
        """
        Returns the latest bar from the data feed as a tuple of 
        (symbol, datetime, open, low, high, close, volume, adj_close).
        """
        for bar in self.symbol_data[symbol]:
            yield bar


    def get_latest_bar(self, symbol):
        """
        Returns the last bar from the latest_symbol list.
        """
        
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            return bars_list[-1]

    def get_latest_bars(self, symbol, N=1):
        """
        Returns the last N bars from the latest_symbol list,
        or N-k if less available.
        """
        
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            return bars_list[-N:]

    def get_latest_bar_datetime(self, symbol):
        """
        Returns a Python datetime object for the last bar.
        """
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            return bars_list[-1][0]

    def get_latest_bar_value(self, symbol, value_type):
        """
        Returns one of the Open, High, Low, Close, Volume or OI
        values from the pandas Bar series object.
        """
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
                print("That symbol is not available in the historical data set.")
                raise
        else:
            return getattr(bars_list[-1][1], value_type)


    def get_latest_bars_values(self, symbol, value_type, N=1):
        """
        Returns the last N bar values from the
        latest_symbol list, or N-k if less available.
        """
        try:
            bars_list = self.get_latest_bars(symbol, N) # bars_list = bars_list[-N:]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            return np.array([getattr(bar[1], value_type) for bar in bars_list])

    def update_bars(self):
        """
        Pushes the latest bar to the latest_symbol_data structure
        for all symbols in the symbol list.
        """
        for symbol in self.symbol_list:
            try:
                bar = next(self._get_new_bar(symbol))
            except StopIteration:
                self.continue_backtest = False
            else:
                if bar is not None:
                    self.latest_symbol_data[symbol].append(bar)
        self.events.put(MarketEvent())


class YahooDataHandler(DataManagement):
    """
    Get data directly from Yahoo Finance website, and provide an interface
    to obtain the "latest" bar in a manner identical to a live
    trading interface.
    """

    def __init__(self, events, symbol_list, interval, start_date, end_date):
        """
        Initialize Queries from yahoo finance api to 
        receive historical data transformed to dataframe
        
        Parameters: 
        events - The Event Queue.
        symbol_list - A list of symbol strings.
        interval - 1d, 1wk, 1mo - daily, weekly monthly data
        start_date - starting date for the historical data (format: datetime)
        end_date - final date of the data (format: datetime)
        
        """

        self.events = events
        self.symbol_list = symbol_list
        self.interval = interval
        self.start_date = start_date
        self.end_date = end_date

        self.symbol_data = {}
        self.latest_symbol_data = {}
        self.continue_backtest = True

        #self._load_data_from_Yahoo_finance()

    def _get_crumbs_and_cookies(self, symbol):
        """
        Get crumb and cookies for historical data csv download from yahoo finance
        
        Parameters: 
        symbol - short-handle identifier of the company 
        returns a tuple of header, crumb and cookie
        """
        
        url = 'https://finance.yahoo.com/quote/{}/history'.format(symbol)
        with requests.session():
            header = {'Connection': 'keep-alive',
                    'Expires': '-1',
                    'Upgrade-Insecure-Requests': '1',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) \
                    AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36'
                    }
            
            website = requests.get(url, headers=header)
            soup = BeautifulSoup(website.text, 'lxml')
            crumb = re.findall('"CrumbStore":{"crumb":"(.+?)"}', str(soup))

            return (header, crumb[0], website.cookies)

    def convert_to_unix(self, date):
        """
        Converts date to unix timestamp
        
        Parameters: 
        date - datetime format
        returns integer unix timestamp
        """
        
        datum = datetime.date(date)
        
        return int(mktime(datum.timetuple()))
        
    def _get_yahoo_data(self):
        """
        queries yahoo finance api to receive historical data in csv file format
        """
    
        start_date_unix = self.convert_to_unix(self.start_date)
        end_date_unix = self.convert_to_unix(self.end_date)
        
        combined_index = None
        for symbol in self.symbol_list:
            header, crumb, cookies = self._get_crumbs_and_cookies(symbol)
        
            with requests.session():
                url = 'https://query1.finance.yahoo.com/v7/finance/download/' \
                    '{stock}?period1={day_begin}&period2={day_end}&interval={interval}&events=history&crumb={crumb}' \
                    .format(stock=symbol, day_begin=start_date_unix, day_end=end_date_unix, interval=self.interval, crumb=crumb)
                        
                website = requests.get(url, headers=header, cookies=cookies)
            
                yf_data = website.text.split('\n')[:-1]

                self.symbol_data[symbol] = pd.DataFrame([y.split(",") for y in yf_data]) # separate each strings of data by ','
                self.symbol_data[symbol].drop(self.symbol_data[symbol].index[0], inplace=True) # drop first columns
                self.symbol_data[symbol][0] =  pd.to_datetime(self.symbol_data[symbol][0])

                for i in range(1,6):
                    self.symbol_data[symbol][i] = pd.to_numeric(self.symbol_data[symbol][i])
                self.symbol_data[symbol].columns = ["datetime","open","high","low","close","adj_close","volume"] # define column names
                
                self.symbol_data[symbol].set_index("datetime", inplace = True)

                # Combine the index to pad forward values
                if combined_index is None:
                    combined_index = self.symbol_data[symbol].index
                else:
                    combined_index.union(self.symbol_data[symbol].index)

                # Set the latest symbol_data to None
                self.latest_symbol_data[symbol] = []

        # Reindex the dataframes
        for symbol in self.symbol_list:
            self.symbol_data[symbol] = self.symbol_data[symbol].reindex(index=combined_index, method="pad").iterrows()

    def _get_new_bar(self, symbol):
        """
        Returns the latest bar from the data feed as a tuple of 
        (symbol, datetime, open, low, high, close, volume, adj_close).
        """
        for bar in self.symbol_data[symbol]:
            yield bar


    def get_latest_bar(self, symbol):
        """
        Returns the last bar from the latest_symbol list.
        """
        
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            return bars_list[-1]

    def get_latest_bars(self, symbol, N=1):
        """
        Returns the last N bars from the latest_symbol list,
        or N-k if less available.
        """
        
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            return bars_list[-N:]

    def get_latest_bar_datetime(self, symbol):
        """
        Returns a Python datetime object for the last bar.
        """
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            return bars_list[-1][0]

    def get_latest_bar_value(self, symbol, value_type):
        """
        Returns one of the Open, High, Low, Close, Volume or OI
        values from the pandas Bar series object.
        """
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
                print("That symbol is not available in the historical data set.")
                raise
        else:
            return getattr(bars_list[-1][1], value_type)


    def get_latest_bars_values(self, symbol, value_type, N=1):
        """
        Returns the last N bar values from the
        latest_symbol list, or N-k if less available.
        """
        try:
            bars_list = self.get_latest_bars(symbol, N) # bars_list = bars_list[-N:]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            return np.array([getattr(bar[1], value_type) for bar in bars_list])

    def update_bars(self):
        """
        Pushes the latest bar to the latest_symbol_data structure
        for all symbols in the symbol list.
        """
        for symbol in self.symbol_list:
            try:
                bar = next(self._get_new_bar(symbol))
            except StopIteration:
                self.continue_backtest = False
            else:
                if bar is not None:
                    self.latest_symbol_data[symbol].append(bar)
        self.events.put(MarketEvent())


class CryptoCMCDataHandler(DataManagement):
    """
    Get data directly from CoinMarketCap website, and provide an interface
    to obtain the "latest" bar in a manner identical to a live
    trading interface.
    """

    def __init__(self, events, symbol_list, start_date, end_date):
        """
        Initialize Queries from CMC api to 
        receive historical data transformed to dataframe
        
        Parameters: 
        events - The Event Queue.
        symbol_list - A list of symbol strings.
        start_date - starting date for the historical data (format: dd-mm-yyyy)
        end_date - final date of the data (format: dd-mm-yyyy)
        
        """

        self.events = events
        self.symbol_list = symbol_list
        self.start_date = start_date
        self.end_date = end_date

        self.symbol_data = {}
        self.latest_symbol_data = {}
        self.continue_backtest = True

    def convert_to_string(self, date):
        """
        Converts date to string format "%Y%M%D"
        
        Parameters: 
        date - in format (datetime)
        returns string of characters
        """

        return date.strftime("%Y%m%d")

    def _get_cmc_data(self):
        """
        queries CMC api to receive historical data in csv file format
        """
        
        start_date_str = self.convert_to_string(self.start_date)
        end_date_str = self.convert_to_string(self.end_date)
        
        combined_index = None

        for symbol in self.symbol_list:
            url = "https://coinmarketcap.com/currencies/{cryptocurrency}/historical-data/?start={day_begin}&end={day_end}" \
            .format(cryptocurrency=symbol, day_begin=start_date_str, day_end=end_date_str)

            content = requests.get(url).content
            soup = BeautifulSoup(content,'html.parser')
            table = soup.find('table', {'class': 'table'})

            cmc_data = [[td.text.strip() for td in tr.findChildren('td')] for tr in table.findChildren('tr')]

            self.symbol_data[symbol] = pd.DataFrame(cmc_data)
            self.symbol_data[symbol].drop(self.symbol_data[symbol].index[0], inplace=True) # first row is empty
            self.symbol_data[symbol][0] =  pd.to_datetime(self.symbol_data[symbol][0]) # date
            for i in range(1,7):
                self.symbol_data[symbol][i] = pd.to_numeric(self.symbol_data[symbol][i].str.replace(",","").str.replace("-","")) # some vol is missing and has -
            self.symbol_data[symbol].columns = ["datetime","open","high","low","close","volume","market_cap"]
            self.symbol_data[symbol].set_index("datetime",inplace=True)
            self.symbol_data[symbol].sort_index(inplace=True)
            self.symbol_data[symbol] = self.symbol_data[symbol].drop(columns = ["market_cap"]) 
            self.symbol_data[symbol]["adj_close"] = self.symbol_data[symbol]["close"] # adj_close is taken as closing price for crypto

            cols = ["open","high","low","close","adj_close","volume"] # change order of columns to match format

            self.symbol_data[symbol] = self.symbol_data[symbol][cols]

            # Combine the index to pad forward values
            if combined_index is None:
                combined_index = self.symbol_data[symbol].index
            else:
                combined_index.union(self.symbol_data[symbol].index)

            # Set the latest symbol_data to None
            self.latest_symbol_data[symbol] = []

        # Reindex the dataframes
        for symbol in self.symbol_list:
            self.symbol_data[symbol] = self.symbol_data[symbol].reindex(index=combined_index, method="pad").iterrows()

    def _get_new_bar(self, symbol):
        """
        Returns the latest bar from the data feed as a tuple of 
        (symbol, datetime, open, low, high, close, volume, adj_close).
        """
        for bar in self.symbol_data[symbol]:
            yield bar


    def get_latest_bar(self, symbol):
        """
        Returns the last bar from the latest_symbol list.
        """
        
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            return bars_list[-1]

    def get_latest_bars(self, symbol, N=1):
        """
        Returns the last N bars from the latest_symbol list,
        or N-k if less available.
        """
        
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            return bars_list[-N:]

    def get_latest_bar_datetime(self, symbol):
        """
        Returns a Python datetime object for the last bar.
        """
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            return bars_list[-1][0]

    def get_latest_bar_value(self, symbol, value_type):
        """
        Returns one of the Open, High, Low, Close, Volume or OI
        values from the pandas Bar series object.
        """
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
                print("That symbol is not available in the historical data set.")
                raise
        else:
            return getattr(bars_list[-1][1], value_type)


    def get_latest_bars_values(self, symbol, value_type, N=1):
        """
        Returns the last N bar values from the
        latest_symbol list, or N-k if less available.
        """
        try:
            bars_list = self.get_latest_bars(symbol, N) # bars_list = bars_list[-N:]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            return np.array([getattr(bar[1], value_type) for bar in bars_list])

    def update_bars(self):
        """
        Pushes the latest bar to the latest_symbol_data structure
        for all symbols in the symbol list.
        """
        for symbol in self.symbol_list:
            try:
                bar = next(self._get_new_bar(symbol))
            except StopIteration:
                self.continue_backtest = False
            else:
                if bar is not None:
                    self.latest_symbol_data[symbol].append(bar)
        self.events.put(MarketEvent())


'''
class HistoricMySQLDataHandler(DataManagement):
    """
    HistoricMySQLDataHandler is designed to read a MySQL database for each requested symbol from disk and 
    provide an interface to obtain the "latest" bar in a manner identical to a live trading interface.
    """

    def __init__(self, events, db_host, db_user, db_pass, db_name, symbol_list):

        """
        Initialises the historic data handler by requesting
        the location of the database and a list of symbols.
        It will be assumed that all price data is in a table called 
        'symbols', where the field 'symbol' is a string in the list.
        Parameters:
        events - The Event Queue.
        db_host - host of the database
        db_user - database user
        db_pass - password to access database
        db_name - database's name
        symbol_list - A list of symbol stringss
        """

        self.events = events
        self.db_host = db_host
        self.db_user = db_user
        self.db_pass = db_pass
        self.db_name = db_name  
        
        self.symbol_list = symbol_list
        self.symbol_data = {}
        self.latest_symbol_data = {}

        self.continue_backtest = True
        self._data_conversion_from_database()


    def _get_data_from_database(self, symbol, columns):
        try:
            connection = MySQLdb.connect(host=self.db_host, user=self.db_user, passwd=self.db_pass, db=self.db_name)
        except MySQLdb.Error as e:  
            print("Error:%d:%s" % (e.args[0], e.args[1]))

        sql = SELECT {},{},{},{},{},{},{}
                FROM {}.format(columns[0],
                                    columns[1],
                                        columns[2],
                                            columns[3],
                                              columns[4],
                                                columns[5],
                                                    columns[6],
                                                        symbol)

        return pd.read_sql_query(sql, con=connection, index_col="datetime")

    def _data_conversion_from_database(self):
        """
        Opens the database files, converting them into 
        pandas DataFrames within a symbol dictionary.
        For this handler it will be assumed that the data is
        assumed to be stored in a database with similar columns 
        as the pandas dataframes. Thus, the format will be respected.
        """

        combined_index = None
        columns = ["datetime","open","high","low","close","volume","adj_close"]

        for symbol in self.symbol_list:
            self.symbol_data[symbol] = self._get_data_from_database(symbol, columns)

        
            # Combine the index to pad forward values
            if combined_index is None:
                combined_index = self.symbol_data[symbol].index
            else:
                combined_index.union(self.symbol_data[symbol].index)

            # Set the latest symbol_data to None
            self.latest_symbol_data[symbol] = []

        # Reindex the dataframes
        for symbol in self.symbol_list:
            self.symbol_data[symbol] = self.symbol_data[symbol].reindex(index=combined_index, method="pad").iterrows()

    def _get_new_bar(self, symbol):
        """
        Returns the latest bar from the data feed as a tuple of 
        (symbol, datetime, open, low, high, close, volume, adj_close).
        """
        for bar in self.symbol_data[symbol]:
            yield bar


    def get_latest_bar(self, symbol):
        """
        Returns the last bar from the latest_symbol list.
        """
        
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            return bars_list[-1]

    def get_latest_bars(self, symbol, N=1):
        """
        Returns the last N bars from the latest_symbol list,
        or N-k if less available.
        """
        
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            return bars_list[-N:]

    def get_latest_bar_datetime(self, symbol):
        """
        Returns a Python datetime object for the last bar.
        """
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            return bars_list[-1][0]

    def get_latest_bar_value(self, symbol, value_type):
        """
        Returns one of the Open, High, Low, Close, Volume or OI
        values from the pandas Bar series object.
        """
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
                print("That symbol is not available in the historical data set.")
                raise
        else:
            return getattr(bars_list[-1][1], value_type)


    def get_latest_bars_values(self, symbol, value_type, N=1):
        """
        Returns the last N bar values from the
        latest_symbol list, or N-k if less available.
        """
        try:
            bars_list = self.get_latest_bars(symbol, N) # bars_list = bars_list[-N:]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            return np.array([getattr(bar[1], value_type) for bar in bars_list])

    def update_bars(self):
        """
        Pushes the latest bar to the latest_symbol_data structure
        for all symbols in the symbol list.
        """
        for symbol in self.symbol_list:
            try:
                bar = next(self._get_new_bar(symbol))
            except StopIteration:
                self.continue_backtest = False
            else:
                if bar is not None:
                    self.latest_symbol_data[symbol].append(bar)
        self.events.put(MarketEvent())
'''