import backtrader as bt
import pandas as pd
import datetime
from my_sizer import FixedPerc
from all_strategy import KDJ_Strategy


def runstrat(data_path, cash, benchmark_data_path=None, **plot_info):
    cerebro = bt.Cerebro(cheat_on_open=True)
    cerebro.broker.set_cash(cash)
    comminfo = bt.commissions.CommInfo_Stocks_Perc(commission=0.0003, percabs=True)

    cerebro.broker.addcommissioninfo(comminfo)

    data = pd.read_excel(data_path)
    # 加载数据
    data['datetime'] = data['time_key'].map(lambda x: datetime.datetime.strptime(x.split(' ')[0], '%Y-%m-%d'))
    data = data.set_index('datetime')
    df = bt.feeds.PandasData(dataname=data)
    cerebro.adddata(df)

    cerebro.addstrategy(KDJ_Strategy)
    cerebro.addsizer(FixedPerc)
    # Add TimeReturn Analyzers for self and the benchmark data
    cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='alltime_roi',
                        timeframe=bt.TimeFrame.NoTimeFrame)

    if benchmark_data_path is not None:
        start_date = data.index.min()
        end_date = data.index.max()
        data_benchmark = pd.read_excel(benchmark_data_path)
        data_benchmark['datetime'] = data_benchmark['time_key'].map(
            lambda x: datetime.datetime.strptime(x.split(' ')[0], '%Y-%m-%d'))
        data_benchmark = data_benchmark[data_benchmark['datetime'].map(lambda x: x >= start_date and x <= end_date)]
        data_benchmark = data_benchmark.set_index('datetime')
        df_benchmark = bt.feeds.PandasData(dataname=data_benchmark)
        cerebro.adddata(df_benchmark)

        cerebro.addanalyzer(bt.analyzers.TimeReturn, data=df_benchmark, _name='benchmark',
                            timeframe=bt.TimeFrame.NoTimeFrame)

    # Add TimeReturn Analyzers fot the annuyl returns
    cerebro.addanalyzer(bt.analyzers.TimeReturn, timeframe=bt.TimeFrame.Years, _name='_TimeReturn')
    # Add a SharpeRatio
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, timeframe=bt.TimeFrame.Years, riskfreerate=0.01)

    # Add SQN to qualify the trades
    cerebro.addanalyzer(bt.analyzers.SQN)
    cerebro.addobserver(bt.observers.DrawDown)

    results = cerebro.run()
    st0 = results[0]

    for anlyzer in st0.analyzers:
        anlyzer.print()

    if plot_info['is_plot']:
        cerebro.plot(iplot=False, stdstats=False, start=plot_info['plot_start'], end=plot_info['plot_end'])


if __name__ == '__main__':
    data_path = '../data/kj_tx.xlsx'
    benchmark_data_path = '../data/hs_index_day.xlsx'
    cash = 50000
    plotinfo = {
        'is_plot': True,
        'plot_start': datetime.date(2013, 1, 1),
        'plot_end': datetime.date(2090, 1, 1)
    }
    runstrat(data_path, cash, None, **plotinfo)
