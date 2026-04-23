import akshare as ak
import pandas as pd


def catch_limit_up_potential():
    # 1. 获取全市场实时快照
    df_spot = ak.stock_zh_a_spot_em()

    # 2. 基础过滤：剔除杂质
    df = df_spot[~df_spot['名称'].str.contains("ST|退")].copy()

    # 3. 计算竞价溢价率 (Gap Up)
    df['gap_pct'] = (df['今开'] - df['昨收']) / df['昨收'] * 100

    # 4. 关键筛选：寻找超预期品种
    # 条件1：高开在 3%~7% 之间
    mask_gap = (df['gap_pct'] >= 3) & (df['gap_pct'] <= 7.5)

    # 条件2：量比异常 (竞价量能是平时的数倍)
    # 这里的'量比'字段在 9:25-9:30 会显示竞价活跃度
    mask_vol = df['量比'] > 8

    # 条件3：流通市值过滤 (优选 30-100亿 的活跃弹性品种)
    mask_mkt_cap = (df['流通市值'] >= 3e9) & (df['流通市值'] <= 10e10)

    final_targets = df[mask_gap & mask_vol & mask_mkt_cap]

    return final_targets[['代码', '名称', '今开', 'gap_pct', '量比', '成交额']]


# 运行选股
potential_list = catch_limit_up_potential()
print(f"9:25分 潜力涨停池：\n{potential_list}")


