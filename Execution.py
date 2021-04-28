from abc import ABCMeta, abstractmethod

from Events import FillEvent, OrderEvent
from datetime import datetime


class ExecutionHandler(object):
    """
    Execution handler class to handle Order and Fill events
    for different types of APIs (brokers, exchanges), or protocols such as FIX
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def execute_order(self, event):
        """
        Takes an Order event and executes it, producing
        a Fill event that gets placed onto the Events queue.

        Parameters:
        event - Contains an Event object with order information.
        """
        raise NotImplementedError("Should implement execute_order()")


class SimpleSimulatedExecutionHandler(ExecutionHandler):
    """
    Simple handler with no latency or slippage modelling
    """

    def __init__(self, events):
        """
        Initialises the handler, setting the event queues
        up internally.

        Parameters:
        events - The Queue of Event objects.
        """
        self.events = events

    def execute_order(self, event):
        """
        Order event converted to Fill event to
        execute the order on "live" broker. The event is
        then added to the queue

        Parameters:
        event - Contains an Event object with order information.
        """

        if isinstance(event, OrderEvent):
            fill_event = FillEvent(datetime.utcnow(), event.symbol, "FAKE_EXCHANGE", event.quantity, event.direction,
                                   None)
            self.events.put(fill_event)
