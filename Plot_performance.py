import os.path

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

if __name__ == "__main__":
    data = pd.io.parsers.read_csv("equity.csv", header=0, parse_dates=True, index_col=0)
    # Plot three charts: Equity curve,
    # period returns, drawdowns
    fig, (ax1, ax2, ax3) = plt.subplots(nrows=3, sharex=True)
    # Set the outer colour to white
    fig.patch.set_facecolor("white")
    # Plot the equity curve
    ax1.set_ylabel("Portfolio value, %")
    data["equity_curve"].plot(ax=ax1, color="blue", lw=2.)
    ax1.grid(True)
    # Plot the returns
    ax2.set_ylabel("Period returns, %")
    data["returns"].plot(ax=ax2, color="black", lw=2.)
    ax2.grid(True)
    # Plot the returns
    ax3.set_ylabel("Drawdowns, %")
    data["drawdown"].plot(ax=ax3, color="red", lw=2.)
    ax3.grid(True)
    # Plot the figure

    plt.subplots_adjust(hspace=0.3)
    plt.show()