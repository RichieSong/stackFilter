import akshare as ak
import pandas as pd
import datetime


def get_limit_up_candidates():
    print(f"--- 正在执行选股策略，当前时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")

    # 1. 获取 A 股实时行情数据 (包含当前涨幅、量比、换手率等)
    try:
        df_spot = ak.stock_zh_a_spot_em()
    except Exception as e:
        print(f"获取数据失败: {e}")
        return None

    # 2. 基础过滤（初步清洗数据）
    # 剔除ST股、剔除北交所(以82、83、87、43开头)、剔除退市整理期
    df_filter = df_spot[~df_spot['名称'].str.contains("ST|退")]
    df_filter = df_filter[~df_filter['代码'].str.startswith(('8', '4'))]

    # 3. 核心量化因子筛选
    # 逻辑说明：
    # (1) 涨跌幅在 2% 到 5% 之间：高开代表资金认可，但不过高（防止开盘即巅峰）
    # (2) 量比 > 2.0：竞价成交量能大，说明主力参与度高
    # (3) 换手率 > 0.5%：开盘即有活跃度
    # (4) 总市值 < 200亿：小盘股更容易被拉至涨停

    candidates = df_filter[
        (df_filter['涨跌幅'] >= 2.0) &
        (df_filter['涨跌幅'] <= 5.5) &
        (df_filter['量比'] >= 2.0) &
        (df_filter['换手率'] >= 0.3) &
        (df_filter['总市值'] <= 20000000000)
        ].copy()

    # 4. 排序：按量比降序排列，量比越大代表异动越明显
    candidates = candidates.sort_values(by='量比', ascending=False)

    return candidates[['代码', '名称', '最新价', '涨跌幅', '量比', '换手率', '总市值']]


if __name__ == "__main__":
    # 执行选股
    results = get_limit_up_candidates()

    if results is not None and not results.empty:
        print(f"\n找到 {len(results)} 只潜力个股：")
        print(results.head(10))  # 显示前10只

        # 可选：保存到Excel
        # results.to_excel(f"limit_up_candidates_{datetime.date.today()}.xlsx", index=False)
    else:
        print("当前未筛选到符合条件的个股。")