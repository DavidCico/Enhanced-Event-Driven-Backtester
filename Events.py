class Event(object):
    """
    Event is base class providing an interface for all subsequent 
    (inherited) events, that will trigger further events in the 
    trading infrastructure.   
    """
    pass


class MarketEvent(Event):
    """
    Handles the event of receiving a new market update with corresponding bars.
    """

    def __init__(self):
        """
        Initialises the MarketEvent.
        """
        self.type = "MARKET"


class SignalEvent(Event):
    """
    Signal event generated from a particular strategy, if signal met strategy conditions

    Parameters:
    symbol - The symbol for current asset.
    datetime - A datetime at which the signal is generated.
    signal_type - The signal type ('LONG', 'SHORT', 'EXIT')
    strength - strength of the signal --> TODO: this should be given from a risk class when applying multiple strats
    """

    def __init__(self, symbol, datetime, signal_type, strength):
        self.type = "SIGNAL"
        self.symbol = symbol
        self.datetime = datetime
        self.signal_type = signal_type
        self.strength = strength


class OrderEvent(Event):
    """
    Order event to be sent to a broker api. It takes into account the quantity,
    type of ordering, and direction (long, short, exit...)

    Parameters:
    symbol - The symbol for current asset.
    order_type - Whether is it a 'MARKET' or 'LIMIT' order
    quantity --> TODO: this should be implemented in a risk class (Kelly Criterion, etc)
    direction - 1 or -1 based on the type
    """

    def __init__(self, symbol, order_type, quantity, direction):
        self.type = "ORDER"
        self.symbol = symbol
        self.order_type = order_type
        self.quantity = quantity
        self.direction = direction

    def print_order(self):
        """
        Outputs the values within the Order.
        """
        print("Order: Symbol=%s, Type=%s, Quantity=%s, Direction=%s") % \
        (self.symbol, self.order_type, self.quantity, self.direction)


class FillEvent(Event):
    """
    Fill event once an order based on the response from the broker

    Parameters:
    datetime - A datetime at which the signal is created.
    symbol - The symbol for current asset.
    exchange - The exchange, broker where the order is filled
    quantity - quantity filled
    direction
    fill_cost - can contain commission already
    commission - Defaulted to None if non specified
    """

    def __init__(self, datetime, symbol, exchange, quantity, direction, fill_cost, commission=None):

        self.type = "FILL"
        self.datetime = datetime
        self.symbol = symbol
        self.exchange = exchange
        self.quantity = quantity
        self.direction = direction
        self.fill_cost = fill_cost

        # Calculate commission
        if commission is None:
            self.commission = self._calculate_commission()
        else:
            self.commission = commission

    def _calculate_commission(self):
        """
        TODO: Commission fees to be implemented
        """
        # between 1 and 2%
        return max(1.5, 0.015 * self.quantity)
