from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import math

import pandas as pd

import argparse
import datetime
import random

import backtrader as bt
from backtrader.indicators import EMA

BTVERSION = tuple(int(x) for x in bt.__version__.split('.'))


class KDJ(bt.Indicator):
    lines = ("RSV", "K", "D", "J",)
    params = (('period_me1', 3), ('period_me2', 3), ('period_signal', 9),)

    def __init__(self):
        self.l.high = bt.indicators.Highest(self.data.high, period=self.p.period_signal)
        self.l.low = bt.indicators.Lowest(self.data.low, period=self.p.period_signal)
        self.l.RSV = 100 * bt.DivByZero(self.data_close - self.l.low, self.l.high - self.l.low, zero=None)
        self.l.K = CusExponentialSmoothing(self.l.RSV, period=self.p.period_me1, alpha=1 / 3, first_value=66.464)
        self.l.D = CusExponentialSmoothing(self.l.K, period=self.p.period_me2, alpha=1 / 3, first_value=69.635)
        self.l.J = 3 * self.l.K - 2 * self.l.D


#
# class Nine(bt.Indicator):
#     lines = ('nine',)
#     params = (('period', 3), ('cond', 'up'))
#
#     def __init__(self):
#         self.l.nine = PinNine(self.data.close, period=self.p.period, cond=self.p.cond)


class PinNine(bt.indicators.PeriodN):
    params = (('cond', 'up'), ('period', 3))
    lines = ('nine',)

    def __init__(self):
        super(PinNine, self).__init__()

    def oncestart(self, start, end):
        pass

    def once(self, start, end):
        darray = self.data.array
        larray = self.line.array
        for i in range(start, end):
            now_c = darray[i]
            if i <= 4:
                larray[i] = 0
            else:
                ref_c = darray[i - 4]
                my_cond = now_c > ref_c if self.p.cond == 'up' else now_c < ref_c
                if my_cond:
                    if flag_i <= 8:
                        flag_i += 1
                    elif flag_i == 9:
                        flag_i = 1
                    else:
                        raise ValueError
                else:
                    flag_i = 0
                if 5 <= flag_i <= 9:
                    larray[i] = flag_i
                elif flag_i < 5:
                    larray[i] = 0
                else:
                    raise ValueError()


# bt.indicators.ExponentialSmoothing
class CusExponentialSmoothing(bt.indicators.Average):
    alias = ('ExpSmoothing',)
    params = (('alpha', None), ('first_value', 0), ('period', 3))

    def __init__(self):
        self.alpha = self.p.alpha
        if self.alpha is None:
            self.alpha = 2.0 / (1.0 + self.p.period)  # def EMA value

        self.alpha1 = 1.0 - self.alpha

        super(CusExponentialSmoothing, self).__init__()

    def nextstart(self):
        # Fetch the seed value from the base class calculation
        super(CusExponentialSmoothing, self).next()

    def next(self):
        # self.line[0] = self.line[-1] * self.alpha1 + self.data[0] * self.alpha
        pass

    def oncestart(self, start, end):
        pass

    def once(self, start, end):
        darray = self.data.array
        larray = self.line.array
        alpha = self.alpha
        alpha1 = self.alpha1

        # Seed value from SMA calculated with the call to oncestart
        prev = self.p.first_value
        if prev is None:
            prev = larray[start - 1]
        for i in range(start, end):
            larray[i] = prev = prev * alpha1 + darray[i] * alpha


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
        # self.macd = bt.indicators.MACD(self.data,
        #                                period_me1=self.p.macd1,
        #                                period_me2=self.p.macd2,
        #                                period_signal=self.p.macdsig)

        self.macd = bt.indicators.MACDHisto(self.data,
                                            period_me1=self.p.macd1,
                                            period_me2=self.p.macd2,
                                            period_signal=self.p.macdsig)

        # To set the stop price
        self.atr = bt.indicators.AverageTrueRange(self.data)

        self.kdj = KDJ(self.data)

        self.nineturnover = PinNine(self.data, cond='up')

        self.cross_kdj = bt.indicators.CrossOver(self.kdj.K, self.kdj.D)

        self.cross_j_100 = bt.indicators.CrossOver(self.kdj.J, 100)
        self.cross_j_90 = bt.indicators.CrossOver(self.kdj.J, 90)

        self.cross_macd = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)

        # Control market trend
        # self.sma = bt.indicators.SMA(self.data, period=self.p.smaperiod)
        # self.smadir = self.sma - self.sma(-self.p.dirperiod)

        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.buy_flag = False
        self.sell_flag = False
        self.highest_J = 1
        self.predict_cross = False

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

    def next_open(self):
        if self.buy_flag:
            if self.data.open[0] > self.data.low[-1]:
                self.order = self.buy(coc=False)
                self.buy_flag = False
        if self.sell_flag:
            # if self.data.open[0] > self.data.low[-1]:
            self.order = self.close(coc=False)
            self.sell_flag = False

    def next(self):
        if self.order:
            return  # pending order execution

        # self.log('macd.macd:, %.2f,macd.signal: %.2f,macd.histo: %.2f' % (
        #     self.macd.macd[0], self.macd.signal[0], self.macd.histo[0]))
        #
        # self.log('kdj.K:, %.2f,kdj.D: %.2f,kdj.J: %.2f' % (
        #     self.kdj.K[0], self.kdj.D[0], self.kdj.J[0]))
        #
        # self.log('kdj.k_d_cross:, %.2f' % self.cross_kdj[0])
        # self.log('macd.macd_signal_cross:, %.2f' % self.cross_macd[0])
        # self.log('macd.nineturnover:, %.2f' % self.nineturnover[0])

        # self.log('macd.cross_j_80:, %.2f' % self.cross_j_80[0])
        # self.log('macd.cross_j_100:, %.2f' % self.cross_j_100[0])
        ref_k_d_1 = self.kdj.D[-1] - self.kdj.K[-1]
        ref_k_d_0 = self.kdj.D[0] - self.kdj.K[0]

        if self.predict_cross:
            if self.kdj.J[0] <= self.kdj.J[-1]:
                self.sell_flag = True
            self.predict_cross = False

        # if not self.position:
        #     if ref_k_d_0 > 0 and ref_k_d_1 > 0 and ref_k_d_0 / ref_k_d_1 < 0.5 and self.kdj.D[0] - self.kdj.K[0] < 5:
        #         self.buy_flag = True
        #         self.predict_cross = True

        if not self.position:
            if ref_k_d_0 > 0 and ref_k_d_1 > 0 and ref_k_d_0 / ref_k_d_1 < 0.5 and self.kdj.D[0] - self.kdj.K[0] < 5:
                self.buy_flag = True
                self.predict_cross = True
        else:

            # if self.cross_kdj[0] < 0.0 and self.kdj.K > 80 and self.kdj.D > 80:
            #     self.close()
            self.highest_J = self.kdj.J[0] if self.kdj.J[0] > self.highest_J else self.highest_J

            ref_j_1 = self.kdj.J[-1]
            ref_j_0 = self.kdj.J[0]
            ref_j_2 = self.kdj.J[-2]
            ref_j_3 = self.kdj.J[-3]
            # if self.cross_kdj == -1:
            #     self.sell_flag = True

            if ref_j_0 >= 90:
                # self.sell_flag = True
                if (ref_j_0 - ref_j_1) / ref_j_1 < -0.10:
                    self.sell_flag = True
                elif (ref_j_0 - ref_j_1) / ref_j_1 < -0.05 and (ref_j_1 - ref_j_2) / ref_j_2 < -0.05:
                    self.sell_flag = True

            # elif self.highest_J >= 80 and self.kdj.J[0] < self.highest_J / 2 and self.kdj.K[0]<self.kdj.D[0]:
            #     self.sell_flag = True

            # elif self.cross_macd == -1 and self.kdj.K[0] - self.kdj.D[0] < 0:
            #     self.sell_flag = True

            # else:
            #     if self.data.close[0] < 0 and self.data.close[-1] < 0 and self.data.close[-2] < 0:
            #         self.sell_flag = True
            # else:
            #     diff_k_d_1 = self.kdj.K[-1] - self.kdj.D[-1]
            #     diff_j_k_1 = self.kdj.J[-1] - self.kdj.K[-1]
            #     diff_k_d_0 = self.kdj.K[0] - self.kdj.D[0]
            #     diff_j_k_0 = self.kdj.J[0] - self.kdj.K[0]
            #     if diff_j_k_0 < 0 and diff_k_d_0 < 0 and diff_j_k_1<0 and diff_k_d_1<0:
            #         if diff_k_d_0 < diff_k_d_1 and diff_j_k_0 < diff_j_k_1 and self.kdj.J[0]<10:
            #             self.sell_flag = True
            #             self.log('here')


def runstrat(args=None):
    args = parse_args(args)

    cerebro = bt.Cerebro(cheat_on_open=True)
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
                        type=float, default=0.95,
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
