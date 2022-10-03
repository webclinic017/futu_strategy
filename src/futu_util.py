from configparser import ConfigParser
from futu import *
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

cfg = ConfigParser()
cfg.read('../config/base.ini')


def send_mail(subject, content):
    cfg.sections()
    from_mail = cfg.get('email', 'from')
    to_mail = cfg.get('email', 'to')
    pwd = cfg.get('email', 'pwd')
    server = cfg.get('email', 'server')
    smtp = smtplib.SMTP()
    smtp.connect(server, 25)
    smtp.login(from_mail, pwd)
    mail = MIMEText(content)
    mail['Subject'] = subject
    mail['From'] = 'futu_ai@ai.com'
    mail['To'] = 'The_great_star_and_moon_ruler@sun.com'
    # send
    smtp.sendmail(from_mail, to_mail, mail.as_string())
    smtp.quit()


def is_trade_today():
    quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
    ret, data = quote_ctx.request_trading_days(start='2020-04-01', end='2030-04-10', code='HK.00700')
    quote_ctx.close()
    today_str = datetime.today().strftime('%Y-%m-%d')
    for one_date in data:
        if one_date['time'] == today_str:
            return True
    return False


def get_stock_k_line(code, start_date, end_date, k_type):
    quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
    datalist = []
    ret, data, page_req_key = quote_ctx.request_history_kline(code, start=start_date, end=end_date, ktype=k_type,
                                                              max_count=50)  # 每页5个，请求第一页
    if ret == RET_OK:
        print('reading data')
    else:
        print('error:', data)
    datalist.append(data)
    while page_req_key != None:  # 请求后面的所有结果
        ret, data, page_req_key = quote_ctx.request_history_kline(code, start=start_date, end=end_date, ktype=k_type,
                                                                  max_count=50, page_req_key=page_req_key)  # 请求翻页后的数据
        if ret != RET_OK:
            print('error:', data)
        datalist.append(data)

    print('All pages are finished!')
    quote_ctx.close()
    result = pd.concat(datalist)
    return result


def get_stock_info(market, stock_type, code=None):
    # Market.HK, SecurityType.STOCK
    quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
    ret, data = quote_ctx.get_stock_basicinfo(market, stock_type, code)
    if ret == RET_OK:
        print('reading data')
    else:
        print('error:', data)
    quote_ctx.close()  # 结束后记得关闭当条连接，防止连接条数用尽
    return data


def get_month_std(stock):
    stock['date_ym'] = stock['time_key'].map(lambda x: x.split('-')[0] + '-' + x.split('-')[1])
    stock['month_std'] = stock.groupby('date_ym')['close'].transform(np.std)
    stock['month_mean'] = stock.groupby('date_ym')['close'].transform(np.mean)
    stock['month_cv'] = stock['month_std'] / stock['month_mean']
    return stock[['code', 'date_ym', 'month_mean', 'month_std', 'month_cv']].drop_duplicates().reset_index().drop(
        'index', axis=1)


def plot_k_line(stock, x='date', y='price', hue='hue'):
    import seaborn as sns
    sns.set()
    import matplotlib.pyplot as plt

    plt.figure(figsize=(30, 15))
    plt.xticks(rotation=-90)

    sns.lineplot(data=stock, x=x, y=y, hue=hue)

    plt.show()
