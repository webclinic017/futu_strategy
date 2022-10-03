import backtrader as bt


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
