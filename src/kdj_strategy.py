from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from my_indicator import KDJ
import backtrader as bt


class KDJ_Strategy(bt.Strategy):
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
        self.macd = bt.indicators.MACDHisto(self.data,
                                            period_me1=self.p.macd1,
                                            period_me2=self.p.macd2,
                                            period_signal=self.p.macdsig)

        # self.atr = bt.indicators.AverageTrueRange(self.data)
        self.kdj = KDJ(self.data)

        self.cross_kdj = bt.indicators.CrossOver(self.kdj.K, self.kdj.D)
        self.cross_j_100 = bt.indicators.CrossOver(self.kdj.J, 100)
        self.cross_j_90 = bt.indicators.CrossOver(self.kdj.J, 90)
        self.cross_macd = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)

        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.buy_flag = False
        self.sell_flag = False
        self.highest_J = 1
        self.predict_cross = False

        # 画图选项
        self.cross_macd.plotinfo.subplot = False
        self.cross_j_90.plotinfo.subplot = False
        self.cross_j_100.plotinfo.subplot = False
        self.cross_kdj.plotinfo.subplot = False
        self.kdj.plotinfo.subplot = False
        self.macd.plotinfo.subplot = False

        self.cross_macd.plotinfo.plot = False
        self.cross_j_90.plotinfo.plot = False
        self.cross_j_100.plotinfo.plot = False
        self.cross_kdj.plotinfo.plot = False
        self.kdj.plotinfo.plot = False
        self.macd.plotinfo.plot = False

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

        ref_k_d_1 = self.kdj.D[-1] - self.kdj.K[-1]
        ref_k_d_0 = self.kdj.D[0] - self.kdj.K[0]

        if self.predict_cross:
            if self.kdj.J[0] <= self.kdj.J[-1]:
                self.sell_flag = True
            self.predict_cross = False

        if not self.position:
            if ref_k_d_0 > 0 and ref_k_d_1 > 0 and ref_k_d_0 / ref_k_d_1 < 0.5 and self.kdj.D[0] - self.kdj.K[0] < 5:
                self.buy_flag = True
                self.predict_cross = True
        else:

            self.highest_J = self.kdj.J[0] if self.kdj.J[0] > self.highest_J else self.highest_J

            ref_j_1 = self.kdj.J[-1]
            ref_j_0 = self.kdj.J[0]
            ref_j_2 = self.kdj.J[-2]
            ref_j_3 = self.kdj.J[-3]

            if ref_j_0 >= 90:
                # self.sell_flag = True
                if (ref_j_0 - ref_j_1) / ref_j_1 < -0.10:
                    self.sell_flag = True
                elif (ref_j_0 - ref_j_1) / ref_j_1 < -0.05 and (ref_j_1 - ref_j_2) / ref_j_2 < -0.05:
                    self.sell_flag = True
