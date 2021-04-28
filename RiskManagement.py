from __future__ import print_function


class RiskManagement(object):
    """
    RiskManagement class would be necessary for different things:
    - Risk calculation on position (such as VaR)
    - Calculation/Update of correlation matrix for the different positions
    This would require different methods if the Universe is to big (NxN) matrix
        --> Be careful if data is sparse
        --> Find factors such as calculating NxF with F < N and F particular factors

    - Position sizing, for better capital management (leverage, weight between portfolios)
        --> Kelly Criterion?
        --> Markowitz theory?
    """
