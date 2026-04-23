import tushare as ts
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings

warnings.filterwarnings('ignore')

# ====================== 1. 配置项 ======================
# 设置tushare token（需要去tushare官网注册获取）
ts.set_token('你的tushare_token')
pro = ts.pro_api()

# 基础参数
STOCK_CODE = '000001.SZ'  # 平安银行
START_DATE = '20230101'  # 回测开始日期
END_DATE = '20240101'  # 回测结束日期
INIT_CASH = 100000  # 初始资金
POSITION_RATIO = 0.8  # 单仓最大仓位比例
STOP_LOSS_RATIO = 0.05  # 止损比例5%


# ====================== 2. 数据模块 ======================
def get_stock_data(code, start_date, end_date):
    """
    获取股票历史行情数据
    :param code: 股票代码
    :param start_date: 开始日期
    :param end_date: 结束日期
    :return: 包含OHLCV的DataFrame
    """
    try:
        df = pro.daily(ts_code=code, start_date=start_date, end_date=end_date)
        # 调整列顺序并转换日期格式
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df = df.sort_values('trade_date').reset_index(drop=True)
        # 重命名列名方便使用
        df.rename(columns={
            'open': '开盘价', 'high': '最高价', 'low': '最低价',
            'close': '收盘价', 'vol': '成交量', 'trade_date': '日期'
        }, inplace=True)
        return df
    except Exception as e:
        print(f"获取数据失败：{e}")
        return pd.DataFrame()


# ====================== 3. 策略模块（简单均线策略） ======================
def generate_trade_signals(df):
    """
    生成交易信号：5日均线金叉20日均线买入，死叉卖出
    :param df: 行情数据
    :return: 带交易信号的DataFrame
    """
    # 计算均线
    df['MA5'] = df['收盘价'].rolling(window=5).mean()
    df['MA20'] = df['收盘价'].rolling(window=20).mean()

    # 生成交易信号：1=买入，-1=卖出，0=无操作
    df['信号'] = 0
    # 金叉（MA5上穿MA20）
    df.loc[(df['MA5'] > df['MA20']) & (df['MA5'].shift(1) <= df['MA20'].shift(1)), '信号'] = 1
    # 死叉（MA5下穿MA20）
    df.loc[(df['MA5'] < df['MA20']) & (df['MA5'].shift(1) >= df['MA20'].shift(1)), '信号'] = -1

    return df


# ====================== 4. 回测模块 ======================
def backtest_strategy(df, init_cash=100000, position_ratio=0.8, stop_loss_ratio=0.05):
    """
    策略回测
    :param df: 带交易信号的行情数据
    :param init_cash: 初始资金
    :param position_ratio: 单仓仓位比例
    :param stop_loss_ratio: 止损比例
    :return: 回测结果和资金曲线
    """
    cash = init_cash  # 可用现金
    position = 0  # 持仓数量
    avg_cost = 0  # 持仓平均成本
    equity_curve = []  # 资产净值曲线

    for idx, row in df.iterrows():
        # 计算当前资产净值
        current_equity = cash + position * row['收盘价']
        equity_curve.append(current_equity)

        # 跳过无信号或均线未形成的行
        if row['信号'] == 0 or pd.isna(row['MA5']):
            continue

        # 买入信号
        if row['信号'] == 1 and cash > 0:
            # 计算可买入数量（按仓位比例，取整）
            buy_amount = cash * position_ratio
            buy_shares = int(buy_amount / row['收盘价'] / 100) * 100  # A股以100股为单位
            if buy_shares > 0:
                cost = buy_shares * row['收盘价']
                cash -= cost
                avg_cost = (position * avg_cost + cost) / (position + buy_shares) if position + buy_shares > 0 else row[
                    '收盘价']
                position += buy_shares
                print(f"{row['日期'].date()} 买入 {buy_shares} 股，单价 {row['收盘价']:.2f}，剩余现金 {cash:.2f}")

        # 卖出信号 或 止损触发
        stop_loss_trigger = False
        if position > 0 and row['收盘价'] < avg_cost * (1 - stop_loss_ratio):
            stop_loss_trigger = True

        if (row['信号'] == -1 or stop_loss_trigger) and position > 0:
            sell_amount = position * row['收盘价']
            cash += sell_amount
            profit = sell_amount - position * avg_cost
            reason = "止损" if stop_loss_trigger else "卖出信号"
            print(
                f"{row['日期'].date()} {reason} 卖出 {position} 股，单价 {row['收盘价']:.2f}，盈利 {profit:.2f}，现金 {cash:.2f}")
            position = 0
            avg_cost = 0

    # 计算最终资产和收益率
    final_equity = cash + position * df.iloc[-1]['收盘价']
    total_return = (final_equity - init_cash) / init_cash * 100
    df['资产净值'] = equity_curve

    # 打印回测结果
    print("\n===== 回测结果 =====")
    print(f"初始资金：{init_cash:.2f}")
    print(f"最终资产：{final_equity:.2f}")
    print(f"总收益率：{total_return:.2f}%")
    print(f"最大持仓：{position} 股（未平仓）")

    return df, final_equity, total_return


# ====================== 5. 可视化模块 ======================
def plot_results(df):
    """
    绘制行情、均线和资产净值曲线
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    # 绘制股价和均线
    ax1.plot(df['日期'], df['收盘价'], label='收盘价', color='blue')
    ax1.plot(df['日期'], df['MA5'], label='MA5', color='orange')
    ax1.plot(df['日期'], df['MA20'], label='MA20', color='green')
    # 标记买入/卖出点
    buy_signals = df[df['信号'] == 1]
    sell_signals = df[df['信号'] == -1]
    ax1.scatter(buy_signals['日期'], buy_signals['收盘价'], marker='^', color='red', s=100, label='买入')
    ax1.scatter(sell_signals['日期'], sell_signals['收盘价'], marker='v', color='green', s=100, label='卖出')
    ax1.set_title(f"{STOCK_CODE} 行情与交易信号")
    ax1.set_ylabel('价格（元）')
    ax1.legend()
    ax1.grid(True)

    # 绘制资产净值曲线
    ax2.plot(df['日期'], df['资产净值'], label='策略净值', color='purple')
    ax2.axhline(y=INIT_CASH, color='black', linestyle='--', label='初始资金')
    ax2.set_title('资产净值曲线')
    ax2.set_xlabel('日期')
    ax2.set_ylabel('资产（元）')
    ax2.legend()
    ax2.grid(True)

    plt.tight_layout()
    plt.show()


# ====================== 主函数 ======================
if __name__ == "__main__":
    # 1. 获取数据
    stock_data = get_stock_data(STOCK_CODE, START_DATE, END_DATE)
    if stock_data.empty:
        print("数据为空，退出程序")
        exit()

    # 2. 生成交易信号
    stock_data_with_signals = generate_trade_signals(stock_data)

    # 3. 执行回测
    backtest_result, final_equity, total_return = backtest_strategy(stock_data_with_signals)

    # 4. 可视化结果
    plot_results(backtest_result)