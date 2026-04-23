import pandas as pd
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

# ====================== 1. 必须修改！配置信息 ======================
# ---------------------- MySQL 配置 ----------------------
MYSQL_CONFIG = {
    "host": "localhost",  # 默认不用改
    "user": "root",  # 你的MySQL用户名（如root）
    "password": "songming",  # 你的MySQL密码（必须改！）
    "database": "stock_db"  # 数据库名（不用改）
}

# ---------------------- Excel 配置 ----------------------
# 1. Excel文件路径（必须改！）
# Windows示例："C:/Users/你的名字/Desktop/股市复盘笔记.xlsx"
# Mac/Linux示例："/Users/你的名字/Desktop/股市复盘笔记.xlsx"
EXCEL_PATH = "D:/win备份/财富密码/股市复盘笔记.xlsx"

# Excel 工作表名（默认第一个工作表用 "Sheet1"，多个工作表需修改）
SHEET_NAME = "sheet"

# 3. 【关键】Excel列名 → MySQL字段 映射（必须按你的Excel实际表头修改！）
# 格式："Excel中的列名" : "MySQL表字段名"
# 示例：如果你的Excel中“大盘成交额”列叫“成交额(亿)”，就改 "成交额(亿)": "market_volume"
EXCEL_TO_MYSQL_MAP = {
    "日期": "date",  # Excel中“日期”列的表头
    "平均股价_大盘": "avg_price_dapan",  # Excel中“平均股价（大盘）”列的表头
    "上证指数": "sh_index",  # Excel中“上证指数”列的表头
    "流动资金": "liquidity",  # Excel中“流动资金”列的表头
    "大盘成交额": "market_volume",  # Excel中“大盘成交额”列的表头（数字）
    "涨停家数": "limit_up",  # Excel中“涨停家数”列的表头（数字）
    "跌停家数": "limit_down",  # Excel中“跌停家数”列的表头（数字）
    "上涨家数": "rise_count",  # Excel中“上涨家数”列的表头（数字）
    "下跌家数": "fall_count",  # Excel中“下跌家数”列的表头（数字）
    "最高板": "max_board",  # Excel中“最高板”列的表头（数字）
    "指数节点": "index_node",  # Excel中“指数节点”列的表头
    "竞价": "auction",  # Excel中“竞价”列的表头
    "星星龙头": "star_leader",  # Excel中“星星龙头”列的表头
    "和信个股": "hexin_stock",  # Excel中“和信个股”列的表头
    "板块核心": "sector_core"  # Excel中“板块核心”列的表头
}

# ---------------------- 数字字段列表（不用改） ----------------------
NUMERIC_FIELDS = ["market_volume", "limit_up", "limit_down", "rise_count", "fall_count", "max_board"]


# ====================== 2. 工具函数 ======================
def get_mysql_conn():
    """获取MySQL连接"""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        if conn.is_connected():
            print("✅ MySQL连接成功！")
            return conn
    except Error as e:
        print(f"❌ MySQL连接失败：{e}")
        print("🔍 检查：1. MySQL服务是否启动 2. 用户名/密码是否正确 3. 数据库是否存在")
        return None


def clear_mysql_table(conn):
    """清空MySQL表中所有数据（重置自增ID）"""
    if not conn:
        return False
    cursor = conn.cursor()
    try:
        # 1. 删除所有数据
        cursor.execute("DELETE FROM stock_data;")
        # 2. 重置自增ID（下次插入从1开始）
        cursor.execute("ALTER TABLE stock_data AUTO_INCREMENT = 1;")
        conn.commit()
        print("✅ MySQL表中旧数据已全部清空！")
        return True
    except Error as e:
        print(f"❌ 清空表失败：{e}")
        conn.rollback()
        return False
    finally:
        cursor.close()


def read_excel():
    """读取Excel并显示所有列名，方便核对"""
    try:
        df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)
        print(f"\n✅ 成功读取Excel：")
        print(f"📁 文件路径：{EXCEL_PATH}")
        print(f"📋 工作表名：{SHEET_NAME}")
        print(f"📊 总行数：{len(df)} 行")
        print(f"🏷️ Excel中的所有列名：")
        for i, col in enumerate(df.columns, 1):
            print(f"   {i}. '{col}'")
        return df
    except Exception as e:
        print(f"\n❌ 读取Excel失败：{e}")
        print("🔍 检查：1. 文件路径是否正确 2. 文件是否被打开 3. 工作表名是否正确")
        return None


def map_excel_to_mysql(df):
    """按配置映射Excel列到MySQL字段，过滤无效列"""
    # 1. 检查Excel是否包含所有必需列
    excel_cols = set(df.columns)
    required_excel_cols = set(EXCEL_TO_MYSQL_MAP.keys())
    missing_cols = required_excel_cols - excel_cols

    if missing_cols:
        print(f"\n❌ 发现缺失列（Excel中没有以下列）：")
        for col in missing_cols:
            print(f"   - '{col}'")
        print(f"\n🔍 请：1. 检查Excel表头是否和配置中的'Excel列名'一致")
        print(f"       2. 如果Excel列名不同（如'成交额'≠'大盘成交额'），修改配置中的EXCEL_TO_MYSQL_MAP")
        return None

    # 2. 按映射关系重命名列，只保留需要的列
    mapped_df = df[list(required_excel_cols)].rename(columns=EXCEL_TO_MYSQL_MAP)
    print(f"\n✅ 字段映射完成：")
    for excel_col, mysql_col in EXCEL_TO_MYSQL_MAP.items():
        print(f"   'Excel.{excel_col}' → 'MySQL.{mysql_col}'")
    return mapped_df


def clean_data(df):
    """数据清洗：处理日期、强制转换数字类型"""
    cleaned_df = df.copy()

    # 1. 处理日期格式（统一转为MySQL的YYYY-MM-DD）
    print(f"\n🔧 开始数据清洗：")
    cleaned_df["date"] = cleaned_df["date"].apply(lambda x: parse_date(x))
    date_null_count = cleaned_df["date"].isna().sum()
    if date_null_count > 0:
        print(f"⚠️  日期格式错误的行数：{date_null_count} 行（已过滤）")
        cleaned_df = cleaned_df.dropna(subset=["date"])

    # 2. 强制转换数字字段（确保为数值类型，无法转换的设为0并提示）
    for field in NUMERIC_FIELDS:
        if field in cleaned_df.columns:
            # 先记录原始数据类型
            original_types = cleaned_df[field].apply(type).value_counts().to_dict()
            # 强制转换为数值
            cleaned_df[field] = pd.to_numeric(cleaned_df[field], errors="coerce").fillna(0)
            # 转为整数（大盘成交额保留2位小数）
            if field == "market_volume":
                cleaned_df[field] = cleaned_df[field].round(2)
            else:
                cleaned_df[field] = cleaned_df[field].astype(int)
            # 统计转换情况
            zero_count = (cleaned_df[field] == 0).sum()
            print(f"   - {field}：转换完成，0值数量：{zero_count} 个")

    print(f"✅ 数据清洗完成，有效数据行数：{len(cleaned_df)} 行")
    return cleaned_df


def parse_date(date_val):
    """解析多种日期格式"""
    if pd.isna(date_val):
        return None
    try:
        # 支持的日期格式：2024-03-26、2024/3/26、2024年3月26日、26/3/2024
        if isinstance(date_val, str):
            if "年" in date_val:
                return datetime.strptime(date_val, "%Y年%m月%d日").strftime("%Y-%m-%d")
            else:
                return pd.to_datetime(date_val, dayfirst=True).strftime("%Y-%m-%d")
        else:
            return pd.to_datetime(date_val, dayfirst=True).strftime("%Y-%m-%d")
    except:
        return None


def insert_data(conn, df):
    """插入清洗后的数据到MySQL"""
    if not conn or df.empty:
        print("❌ 无有效数据或连接，插入终止")
        return

    cursor = conn.cursor()
    success = 0
    fail = 0

    # 插入SQL（严格按MySQL字段顺序）
    insert_sql = """
    INSERT INTO stock_data (
        date, avg_price_dapan, sh_index, liquidity, market_volume,
        limit_up, limit_down, rise_count, fall_count, max_board,
        index_node, auction, star_leader, hexin_stock, sector_core
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    print(f"\n🚀 开始插入数据（共 {len(df)} 行）：")
    for idx, row in df.iterrows():
        try:
            # 组装数据（严格按SQL字段顺序）
            data = (
                row["date"],
                str(row["avg_price_dapan"]).strip(),
                str(row["sh_index"]).strip(),
                str(row["liquidity"]).strip(),
                row["market_volume"],
                row["limit_up"],
                row["limit_down"],
                row["rise_count"],
                row["fall_count"],
                row["max_board"],
                str(row["index_node"]).strip(),
                str(row["auction"]).strip(),
                str(row["star_leader"]).strip(),
                str(row["hexin_stock"]).strip(),
                str(row["sector_core"]).strip()
            )
            cursor.execute(insert_sql, data)
            success += 1
            # 每10行打印一次进度
            if (idx + 1) % 10 == 0 or (idx + 1) == len(df):
                print(f"   进度：{idx + 1}/{len(df)} 行，成功：{success} 行")
        except Error as e:
            fail += 1
            print(f"   ❌ 第 {idx + 1} 行插入失败：{e}")
            conn.rollback()

    conn.commit()
    cursor.close()

    # 输出最终结果
    print("\n" + "=" * 50)
    print("📊 数据导入最终结果：")
    print(f"总数据行数：{len(df)} 行")
    print(f"成功插入：{success} 行")
    print(f"插入失败：{fail} 行")
    print("=" * 50)


# ====================== 3. 主执行流程（不用改） ======================
if __name__ == "__main__":
    print("🚀 重置版 Excel → MySQL 数据导入脚本")
    print("=" * 50)

    # 步骤1：读取Excel并显示列名
    excel_df = read_excel()
    if excel_df is None:
        exit()

    # 步骤2：映射Excel列到MySQL字段
    mapped_df = map_excel_to_mysql(excel_df)
    if mapped_df is None:
        exit()

    # 步骤3：清洗数据（处理日期和数字）
    cleaned_df = clean_data(mapped_df)
    if cleaned_df.empty:
        print("❌ 无有效数据可导入，程序退出")
        exit()

    # 步骤4：连接MySQL并清空旧数据
    mysql_conn = get_mysql_conn()
    if not mysql_conn:
        exit()
    if not clear_mysql_table(mysql_conn):
        mysql_conn.close()
        exit()

    # 步骤5：插入新数据
    insert_data(mysql_conn, cleaned_df)

    # 步骤6：关闭连接
    mysql_conn.close()
    print("\n✅ MySQL连接已关闭，脚本执行结束！")