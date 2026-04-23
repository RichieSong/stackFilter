import akshare as ak
import pandas as pd
import datetime


def auction_strategy():
    print(f"正在执行竞价选股策略，当前时间: {datetime.datetime.now()}")

    # 1. 获取实时行情数据 (包含今日开盘价、昨收价、成交额等)
    # akshare 的东方财富接口可以获取全市场快照
    df = ak.stock_zh_a_spot_em()

    # 2. 基础过滤：剔除ST、剔除北交所(可选)、剔除退市
    df = df[~df['名称'].str.contains("ST|退")]
    df = df[df['代码'].str.startswith(('60', '00', '30'))]  # 仅看沪深主板和创业板

    # 3. 计算关键指标
    # 开盘涨幅 (%)
    df['open_pct'] = (df['今开'] - df['昨收']) / df['昨收'] * 100

    # 4. 核心核心筛选条件
    # 条件A: 高开在 2.5% 到 5% 之间 (太高易被埋，太低没力度)
    condition_a = (df['open_pct'] >= 2.5) & (df['open_pct'] <= 5.2)

    # 条件B: 竞价成交额 > 1000万 (确保是真金白银在顶，非散户行为)
    # 注意：9:25-9:30之间，'成交额'字段即为竞价成交额
    condition_b = df['成交额'] >= 10000000

    # 条件C: 流通市值过滤 (优选 30亿-150亿 之间的“小而美”或中盘股，弹性大)
    condition_c = (df['流通市值'] >= 3e9) & (df['流通市值'] <= 15e10)

    # 5. 执行筛选
    result = df[condition_a & condition_b & condition_c].copy()

    # 6. 排序：按涨幅和成交额综合排序
    result = result.sort_values(by=['open_pct', '成交额'], ascending=[False, False])

    return result[['代码', '名称', '今开', '昨收', 'open_pct', '成交额', '流通市值']]


# 执行选股
try:
    candidates = auction_strategy()
    if not candidates.empty:
        print("\n--- 今日竞价强势候选股 ---")
        print(candidates.head(10))  # 展示前10只
    else:
        print("今日竞价阶段未匹配到符合条件的个股。")
except Exception as e:
    print(f"数据获取失败，请检查网络或接口状态: {e}")