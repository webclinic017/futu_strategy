import futu_util
import pandas as pd
from futu import *

# d1 = util.get_stock_k_line('HK.01398', '2013-01-01', '2022-08-30')
# d2 = util.get_stock_k_line('HK.00939', '2013-01-01', '2022-08-30')
# d3 = util.get_stock_k_line('HK.01288', '2013-01-01', '2022-08-30')
d4 = futu_util.get_stock_k_line('HK.800000', '2003-01-01', '2022-08-30', k_type=KLType.K_DAY)

# d1.to_excel('data/yh_gs.xlsx')
# d2.to_excel('data/yh_js.xlsx')
# d3.to_excel('data/yh_ny.xlsx')
d4.to_excel('../data/hs_index_day.xlsx')
