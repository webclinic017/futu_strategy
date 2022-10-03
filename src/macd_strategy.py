from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import pandas as pd

import argparse
import datetime
import random

import backtrader as bt
from backtrader.indicators import EMA

BTVERSION = tuple(int(x) for x in bt.__version__.split('.'))


class FixedPerc(bt.Sizer):
    '''This sizer simply returns a fixed size for any operation
    Params:
      - ``perc`` (default: ``0.20``) Perc of cash to allocate for operation
    '''

    params = (
        ('perc', 0.2),  # perc of cash to use for operation
    )

    def _getsizing(self, comminfo, cash, data, isbuy):
        # print(self.strategy.atr[0])
        cashtouse = self.p.perc * cash
        if BTVERSION > (1, 7, 1, 93):
            size = comminfo.getsize(data.close[0], cashtouse)
        else:
            size = cashtouse // data.close[0]
        return size


class TheStrategy(bt.Strategy):
    '''
    This strategy is loosely based on some of the examples from the Van
    K. Tharp book: *Trade Your Way To Financial Freedom*. The logic:
      - Enter the market if:
        - The MACD.macd line crosses the MACD.signal line to the upside
        - The Simple Moving Average has a negative direction in the last x
          periods (actual value below value x periods ago)
     - Set a stop price x times the ATR value away from the close
     - If in the market:
       - Check if the current close has gone below the stop price. If yes,
         exit.
       - If not, update the stop price if the new stop price would be higher
         than the current
    '''

    params = (
        # Standard MACD Parameters
        ('macd1', 12),
        ('macd2', 26),
        ('macdsig', 9),
        ('atrperiod', 14),  # ATR Period (standard)
        ('atrdist', 3.0),  # ATR distance for stop price
        ('smaperiod', 30),  # SMA Period (pretty standard)
        ('dirperiod', 10),  # Lookback period to consider SMA trend direction
    )

    def __init__(self):
        self.macd = bt.indicators.MACD(self.data,
                                       period_me1=self.p.macd1,
                                       period_me2=self.p.macd2,
                                       period_signal=self.p.macdsig)

        self.macdhisto = bt.indicators.MACDHisto(self.data,
                                                 period_me1=self.p.macd1,
                                                 period_me2=self.p.macd2,
                                                 period_signal=self.p.macdsig)

        # Cross of macd.macd and macd.signal
        self.mcross = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)

        # To set the stop price
        self.atr = bt.indicators.AverageTrueRange(self.data)

        # Control market trend
        # self.sma = bt.indicators.SMA(self.data, period=self.p.smaperiod)
        # self.smadir = self.sma - self.sma(-self.p.dirperiod)

        self.order = None
        self.buyprice = None
        self.buycomm = None

    def notify_order(self, order):
        if order.status == order.Completed:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))

        if not order.alive():
            self.order = None  # indicate no order is pending

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' % (trade.pnl, trade.pnlcomm))

    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def start(self):
        self.order = None  # sentinel to avoid operrations on pending order

    def next(self):
        if self.order:
            return  # pending order execution

        if not self.position:  # not in the market
            if self.mcross[0] > 0.0 and self.macdhisto.macd > 0:
                self.order = self.buy()
                # self.log('--buy_signal,histo %.2f' % self.macdhisto.histo[0])
            # elif self.mcross[0] < 0.0:
            #     self.order = self.sell()
            # self.log('--sell_signal, %.2f' % self.macdhisto[0])

        else:
            if self.mcross[0] < 0.0 and self.macdhisto.macd < 0:
                self.close()

                # self.log('--closs_signal, %.2f' % self.macdhisto.histo[0])

        # else:  # in the market
        #     pclose = self.data.close[0]
        #     pstop = self.pstop
        #
        #     if pclose < pstop:
        #         self.close()  # stop met - get out
        #     else:
        #         pdist = self.atr[0] * self.p.atrdist
        #         # Update only if greater than
        #         self.pstop = max(pstop, pclose - pdist)


#
# DATASETS = {
#     'yhoo': '../../datas/yhoo-1996-2014.txt',
#     'orcl': '../../datas/orcl-1995-2014.txt',
#     'nvda': '../../datas/nvda-1999-2014.txt',
# }


def runstrat(args=None):
    args = parse_args(args)

    cerebro = bt.Cerebro()
    cerebro.broker.set_cash(args.cash)
    comminfo = bt.commissions.CommInfo_Stocks_Perc(commission=args.commperc,
                                                   percabs=True)

    cerebro.broker.addcommissioninfo(comminfo)

    # dkwargs = dict()
    # if args.fromdate is not None:
    #     fromdate = datetime.datetime.strptime(args.fromdate, '%Y-%m-%d')
    #     dkwargs['fromdate'] = fromdate
    #
    # if args.todate is not None:
    #     todate = datetime.datetime.strptime(args.todate, '%Y-%m-%d')
    #     dkwargs['todate'] = todate

    # if dataset is None, args.data has been given
    # dataname = DATASETS.get(args.dataset, args.data)
    # data0 = bt.feeds.YahooFinanceCSVData(dataname=dataname, **dkwargs)
    # cerebro.adddata(data0)

    data = pd.read_excel('../data/kj_tx.xlsx')
    # 加载数据
    print(data.dtypes)
    data['datetime'] = data['time_key'].map(lambda x: datetime.datetime.strptime(x.split(' ')[0], '%Y-%m-%d'))
    data = data.set_index('datetime')

    df = bt.feeds.PandasData(dataname=data)

    cerebro.adddata(df)

    cerebro.addstrategy(TheStrategy,
                        macd1=args.macd1, macd2=args.macd2,
                        macdsig=args.macdsig,
                        atrperiod=args.atrperiod,
                        atrdist=args.atrdist,
                        smaperiod=args.smaperiod,
                        dirperiod=args.dirperiod)

    cerebro.addsizer(FixedPerc, perc=args.cashalloc)

    # Add TimeReturn Analyzers for self and the benchmark data
    cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='alltime_roi',
                        timeframe=bt.TimeFrame.NoTimeFrame)

    # cerebro.addanalyzer(bt.analyzers.TimeReturn, data=data0, _name='benchmark',
    #                     timeframe=bt.TimeFrame.NoTimeFrame)

    # Add TimeReturn Analyzers fot the annuyl returns
    cerebro.addanalyzer(bt.analyzers.TimeReturn, timeframe=bt.TimeFrame.Years)
    # Add a SharpeRatio
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, timeframe=bt.TimeFrame.Years,
                        riskfreerate=args.riskfreerate)

    # Add SQN to qualify the trades
    cerebro.addanalyzer(bt.analyzers.SQN)
    cerebro.addobserver(bt.observers.DrawDown)  # visualize the drawdown evol

    results = cerebro.run()
    st0 = results[0]

    for alyzer in st0.analyzers:
        alyzer.print()

    print(args.plot)

    if True:
        # pkwargs = dict(style='bar')
        # if args.plot is not True:  # evals to True but is not True
        #     npkwargs = eval('dict(' + args.plot + ')')  # args were passed
        #     pkwargs.update(npkwargs)

        cerebro.plot(iplot=False, stdstats=False)


def parse_args(pargs=None):
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Sample for Tharp example with MACD')

    # group1 = parser.add_mutually_exclusive_group(required=True)
    # group1.add_argument('--data', required=False, default=None,
    #                     help='Specific data to be read in')
    #
    # group1.add_argument('--dataset', required=False, action='store',
    #                     default=None, choices=DATASETS.keys(),
    #                     help='Choose one of the predefined data sets')

    parser.add_argument('--fromdate', required=False,
                        default='2013-01-01',
                        help='Starting date in YYYY-MM-DD format')

    parser.add_argument('--todate', required=False,
                        default=None,
                        help='Ending date in YYYY-MM-DD format')

    parser.add_argument('--cash', required=False, action='store',
                        type=float, default=50000,
                        help=('Cash to start with'))

    parser.add_argument('--cashalloc', required=False, action='store',
                        type=float, default=0.9,
                        help=('Perc (abs) of cash to allocate for ops'))

    parser.add_argument('--commperc', required=False, action='store',
                        type=float, default=0.0033,
                        help=('Perc (abs) commision in each operation. '
                              '0.001 -> 0.1%%, 0.01 -> 1%%'))

    parser.add_argument('--macd1', required=False, action='store',
                        type=int, default=12,
                        help=('MACD Period 1 value'))

    parser.add_argument('--macd2', required=False, action='store',
                        type=int, default=26,
                        help=('MACD Period 2 value'))

    parser.add_argument('--macdsig', required=False, action='store',
                        type=int, default=9,
                        help=('MACD Signal Period value'))

    parser.add_argument('--atrperiod', required=False, action='store',
                        type=int, default=14,
                        help=('ATR Period To Consider'))

    parser.add_argument('--atrdist', required=False, action='store',
                        type=float, default=3.0,
                        help=('ATR Factor for stop price calculation'))

    parser.add_argument('--smaperiod', required=False, action='store',
                        type=int, default=30,
                        help=('Period for the moving average'))

    parser.add_argument('--dirperiod', required=False, action='store',
                        type=int, default=10,
                        help=('Period for SMA direction calculation'))

    parser.add_argument('--riskfreerate', required=False, action='store',
                        type=float, default=0.01,
                        help=('Risk free rate in Perc (abs) of the asset for '
                              'the Sharpe Ratio'))
    # Plot options
    parser.add_argument('--plot', '-p', nargs='?', required=False,
                        metavar='kwargs', const=True,
                        help=('Plot the read data applying any kwargs passed\n'
                              '\n'
                              'For example:\n'
                              '\n'
                              '  --plot style="candle" (to plot candles)\n'))

    if pargs is not None:
        return parser.parse_args(pargs)

    return parser.parse_args()


if __name__ == '__main__':
    runstrat()
