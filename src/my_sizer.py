import backtrader as bt

BTVERSION = tuple(int(x) for x in bt.__version__.split('.'))


class FixedPerc(bt.Sizer):
    '''This sizer simply returns a fixed size for any operation
    Params:
      - ``perc`` (default: ``0.20``) Perc of cash to allocate for operation
    '''

    params = (
        ('perc', 1),  # perc of cash to use for operation
    )

    def _getsizing(self, comminfo, cash, data, isbuy):
        # print(self.strategy.atr[0])
        cashtouse = self.p.perc * cash
        if BTVERSION > (1, 7, 1, 93):
            size = comminfo.getsize(data.close[0], cashtouse)
        else:
            size = cashtouse // data.close[0]
        return size
