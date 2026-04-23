import streamlit as st
import pandas as pd
import mysql.connector
from datetime import date
import plotly.express as px
from mysql.connector import Error

# ====================== MySQL 配置 ======================
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "songming",
    "database": "stock_db"
}


# ======================================================

def get_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        st.error(f"数据库连接失败：{e}")
        return None


def is_weekend(check_date):
    return check_date.weekday() >= 5


def is_date_exists(check_date):
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM stock_data WHERE date = %s", (check_date,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def insert_data(data):
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    sql = """
    INSERT INTO stock_data (
        date, avg_price_dapan, sh_index, liquidity, market_volume,
        limit_up, limit_down, rise_count, fall_count, max_board,
        index_node, auction, star_leader, hexin_stock, sector_core
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    try:
        cursor.execute(sql, data)
        conn.commit()
        return True
    except Error as e:
        st.error(f"保存失败：{e}")
        return False
    finally:
        conn.close()


def get_all_data():
    conn = get_connection()
    if not conn: return pd.DataFrame()
    query = """
    SELECT 
        id, date AS 日期, avg_price_dapan AS 平均股价_大盘,
        sh_index AS 上证指数, liquidity AS 流动资金,
        market_volume AS 大盘成交额, limit_up AS 涨停家数,
        limit_down AS 跌停家数, rise_count AS 上涨家数,
        fall_count AS 下跌家数, max_board AS 最高板,
        index_node AS 指数节点, auction AS 竞价,
        star_leader AS 星星龙头, hexin_stock AS 和信个股,
        sector_core AS 板块核心
    FROM stock_data ORDER BY date ASC
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


def delete_by_id(del_id):
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM stock_data WHERE id=%s", (del_id,))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()


def update_single_field(id, field, value):
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    sql = f"UPDATE stock_data SET {field} = %s WHERE id = %s"
    try:
        cursor.execute(sql, (value, id))
        conn.commit()
        return True
    except Error as e:
        st.error(f"修改失败：{e}")
        return False
    finally:
        conn.close()


# ====================== 情绪分计算 ======================
def get_emotion_score(row):
    score = 0
    zt = int(row["涨停家数"])
    if zt > 80:
        score += 25
    elif zt > 50:
        score += 15
    elif zt > 20:
        score += 5

    dt = int(row["跌停家数"])
    if dt < 5:
        score += 20
    elif dt < 10:
        score += 10

    up = int(row["上涨家数"])
    if up > 3000:
        score += 20
    elif up > 2500:
        score += 10

    dn = int(row["下跌家数"])
    if dn < 2000:
        score += 15
    elif dn < 3000:
        score += 5

    hb = int(row["最高板"])
    if hb >= 7:
        score += 15
    elif hb >= 5:
        score += 8

    vol = int(row["大盘成交额"])
    if vol > 20000: score += 5

    lq = str(row["流动资金"])
    if "红" in lq: score += 5

    avg = str(row["平均股价_大盘"])
    if "金叉" in avg: score += 5
    return min(score, 100)


# ====================== 操作建议 ======================
def get_trade_suggest(score):
    if score >= 80:
        return "🔥 重仓参与 → 主线龙头大胆做"
    elif score >= 60:
        return "😊 轻仓参与 → 做强势股"
    elif score >= 40:
        return "😐 观望为主 → 小仓试错"
    else:
        return "❄️ 空仓休息 → 严控回撤"


# ====================== 页面 UI ======================
st.set_page_config(page_title="股票大盘系统", layout="wide")
st.title("📈 股票大盘复盘系统（专业版）")

df = get_all_data()


# ====================== 1. 大盘情绪面板（无箭头 · 放量缩量带差值） ======================
if not df.empty:
    latest = df.iloc[-1]
    score = get_emotion_score(latest)
    suggest = get_trade_suggest(score)

    st.subheader("🧠 今日大盘情绪面板")
    c1, c2, c3 = st.columns([1,1,2])
    with c1:
        st.metric("大盘综合情绪分", f"{score} 分")
    with c2:
        st.metric("操作建议", suggest)
    with c3:
        st.markdown(f"**今日市场判定：** {'📈 强势' if score>=60 else '📊 震荡' if score>=40 else '📉 弱势'}")

    st.divider()

    g1, g2, g3, g4, g5 = st.columns(5)
    with g1:
        zt = int(latest["涨停家数"])
        st.metric("涨停家数", zt, delta="偏弱" if zt<=50 else "活跃", delta_color="inverse" if zt<=50 else "normal")
    with g2:
        dt = int(latest["跌停家数"])
        st.metric("跌停家数", dt, delta="安全" if dt<=10 else "风险", delta_color="normal" if dt<=10 else "inverse")
    with g3:
        up = int(latest["上涨家数"])
        st.metric("上涨家数", up, delta="空头" if up<=2500 else "多头", delta_color="inverse" if up<=2500 else "normal")
    with g4:
        dn = int(latest["下跌家数"])
        st.metric("下跌家数", dn, delta="稳定" if dn<=2500 else "抛压", delta_color="normal" if dn<=2500 else "inverse")
    with g5:
        hb = int(latest["最高板"])
        st.metric("最高板", hb, delta="高度低" if hb<=5 else "高度够", delta_color="inverse" if hb<=5 else "normal")

    g6, g7, g8 = st.columns(3)
    with g6:
        vol_now = int(latest["大盘成交额"])
        if len(df) >= 2:
            vol_prev = int(df.iloc[-2]["大盘成交额"])
            diff = vol_now - vol_prev
            if diff > 0:
                vol_text = f"放量 {diff} 亿"
            else:
                vol_text = f"缩量 {abs(diff)} 亿"
        else:
            vol_text = "无昨日数据"
        st.metric("大盘成交额", f"{vol_now:,} 亿", delta=vol_text, delta_color="normal" if diff>0 else "inverse")
    with g7:
        lq = latest["流动资金"]
        st.metric("流动资金", lq, delta="资金向好" if "红" in lq else "资金流出", delta_color="normal" if "红" in lq else "inverse")
    with g8:
        avg = latest["平均股价_大盘"]
        st.metric("平均股价", avg, delta="金叉向好" if "金叉" in avg else "死叉风险", delta_color="normal" if "金叉" in avg else "inverse")

    st.divider()

# ====================== 2. 历史情绪分趋势图 ======================
if not df.empty:
    st.subheader("📈 历史情绪分趋势")

    df_plot = df.copy()
    df_plot["日期"] = pd.to_datetime(df_plot["日期"])
    df_plot["情绪分"] = df_plot.apply(get_emotion_score, axis=1)

    max_date = df_plot["日期"].max()
    min_date = max_date - pd.Timedelta(days=30)
    df_date_min = pd.to_datetime(df["日期"]).min().date()
    df_date_max = pd.to_datetime(df["日期"]).max().date()
    slider_min = min_date.date()
    slider_max = max_date.date()

    start_date, end_date = st.slider(
        "⏱️ 情绪分时间范围",
        min_value=df_date_min,
        max_value=df_date_max,
        value=(slider_min, slider_max),
        format="YYYY-MM-DD"
    )

    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)
    df_plot = df_plot[(df_plot["日期"] >= start_ts) & (df_plot["日期"] <= end_ts)]
    df_plot["日期"] = df_plot["日期"].dt.date

    fig = px.line(
        df_plot, x="日期", y="情绪分",
        title="大盘历史情绪分趋势（红色=过热80 | 蓝色=冰点30）",
        template="plotly_white",
        markers=True,
        text="情绪分"
    )
    fig.update_traces(textposition="top center")

    # ------------------ 新增：过热 + 冰点 水平线 ------------------
    fig.add_hline(y=80, line_color="red", line_dash="dash", annotation_text="过热", annotation_position="top left")
    fig.add_hline(y=30, line_color="blue", line_dash="dash", annotation_text="冰点", annotation_position="bottom left")

    fig.update_layout(yaxis_range=[0, 100])
    st.plotly_chart(fig, use_container_width=True)
    st.divider()

# ====================== 2. 大盘趋势图 ======================
if not df.empty:
    st.subheader("📊 大盘趋势图（节点标数字 + 默认近一个月 + 可缩放）")
    df_plot = df.copy()
    df_plot["日期"] = pd.to_datetime(df_plot["日期"])

    max_date = df_plot["日期"].max()
    min_date = max_date - pd.Timedelta(days=30)

    df_date_min = pd.to_datetime(df["日期"]).min().date()
    df_date_max = pd.to_datetime(df["日期"]).max().date()
    slider_min = min_date.date()
    slider_max = max_date.date()

    start_date, end_date = st.slider(
        "⏱️ 调整时间范围",
        min_value=df_date_min,
        max_value=df_date_max,
        value=(slider_min, slider_max),
        format="YYYY-MM-DD"
    )

    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)
    df_plot = df_plot[(df_plot["日期"] >= start_ts) & (df_plot["日期"] <= end_ts)]
    df_plot["日期"] = df_plot["日期"].dt.date

    tab1, tab2, tab3 = st.tabs(["💰 成交额趋势", "🚥 涨跌停趋势", "📈 涨跌家数趋势"])
    with tab1:
        fig1 = px.line(
            df_plot, x="日期", y="大盘成交额",
            title="大盘成交额趋势",
            template="plotly_white",
            markers=True,
            text="大盘成交额"
        )
        fig1.update_traces(textposition="top center")
        st.plotly_chart(fig1, use_container_width=True)
    with tab2:
        fig2 = px.line(
            df_plot, x="日期", y=["涨停家数", "跌停家数"],
            title="涨跌停家数趋势",
            template="plotly_white",
            markers=True,
            text="value"
        )
        fig2.update_traces(textposition="top center")
        st.plotly_chart(fig2, use_container_width=True)
    with tab3:
        fig3 = px.line(
            df_plot, x="日期", y=["上涨家数", "下跌家数"],
            title="涨跌家数趋势",
            template="plotly_white",
            markers=True,
            text="value"
        )
        fig3.update_traces(textposition="top center")
        st.plotly_chart(fig3, use_container_width=True)

    st.divider()

# ====================== 3. 数据录入 ======================
st.subheader("📝 数据录入")
with st.form("form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        input_date = st.date_input("日期", value=date.today())
        st.markdown("##### 平均股价（大盘）")
        ap_choice = st.selectbox("金叉/死叉", ["金叉", "死叉"], label_visibility="collapsed")
        ap_day = st.number_input("日数", min_value=0, step=1, value=0, label_visibility="collapsed")
        avg_price_dapan = f"{ap_choice}{ap_day}日"

        st.markdown("##### 上证指数")
        sh_choice = st.selectbox("上证指数金叉/死叉", ["金叉", "死叉"], label_visibility="collapsed")
        sh_day = st.number_input("上证日数", min_value=0, step=1, value=0, label_visibility="collapsed")
        sh_index = f"{sh_choice}{sh_day}日"
        liquidity = st.selectbox("流动资金", ["翻红", "翻绿"])
        market_volume = st.number_input("大盘成交额", min_value=0, step=1, value=0, format="%d")

    with col2:
        limit_up = st.number_input("涨停家数", min_value=0, step=1, value=0, format="%d")
        limit_down = st.number_input("跌停家数", min_value=0, step=1, value=0, format="%d")
        rise_count = st.number_input("上涨家数", min_value=0, step=1, value=0, format="%d")
        fall_count = st.number_input("下跌家数", min_value=0, step=1, value=0, format="%d")
        max_board = st.number_input("最高板", min_value=0, step=1, value=0, format="%d")

    with col3:
        index_node = st.text_input("指数节点")
        auction = st.text_input("竞价")
        star_leader = st.text_input("星星龙头")
        hexin_stock = st.text_input("和信个股")
        sector_core = st.text_input("板块核心")

    submitted = st.form_submit_button("✅ 提交")

    if submitted:
        if is_weekend(input_date):
            st.error("❌ 周末禁止录入")
        elif is_date_exists(input_date):
            st.error("❌ 日期已存在")
        else:
            data = (
                input_date, avg_price_dapan, sh_index, liquidity, int(market_volume),
                int(limit_up), int(limit_down), int(rise_count), int(fall_count), int(max_board),
                index_node, auction, star_leader, hexin_stock, sector_core
            )
            if insert_data(data):
                st.success("✅ 保存成功！")
                st.rerun()

st.divider()

# ====================== 4. 染色表格展示 ======================
st.subheader("📋 历史数据（智能染色）")
if not df.empty:
    format_df = df.copy()
    format_df["大盘成交额"] = format_df["大盘成交额"].astype(int)
    int_fields = ["涨停家数", "跌停家数", "上涨家数", "下跌家数", "最高板"]
    for field in int_fields:
        format_df[field] = format_df[field].astype(int)


    def color_row(row):
        styles = []
        for col in format_df.columns:
            if col == "平均股价_大盘":
                if "金叉" in str(row[col]):
                    styles.append("background-color: #28a745; color: white; font-weight: bold")
                elif "死叉" in str(row[col]):
                    styles.append("background-color: #dc3545; color: white; font-weight: bold")
                else:
                    styles.append("")
            elif col == "上证指数":
                if "金叉" in str(row[col]):
                    styles.append("background-color: #28a745; color: white; font-weight: bold")
                elif "死叉" in str(row[col]):
                    styles.append("background-color: #dc3545; color: white; font-weight: bold")
                else:
                    styles.append("")
            elif col == "流动资金":
                if "红" in str(row[col]):
                    styles.append("background-color: #28a745; color: white; font-weight: bold")
                elif "绿" in str(row[col]):
                    styles.append("background-color: #dc3545; color: white; font-weight: bold")
                else:
                    styles.append("")
            elif col == "大盘成交额":
                try:
                    v = int(row[col])
                    if v > 20000:
                        styles.append("background-color: #28a745; color: white; font-weight: bold")
                    else:
                        styles.append("background-color: #dc3545; color: white; font-weight: bold")
                except:
                    styles.append("")
            elif col == "涨停家数":
                try:
                    v = int(row[col])
                    if v > 50:
                        styles.append("background-color: #28a745; color: white; font-weight: bold")
                    else:
                        styles.append("background-color: #dc3545; color: white; font-weight: bold")
                except:
                    styles.append("")
            elif col == "跌停家数":
                try:
                    v = int(row[col])
                    if v > 10:
                        styles.append("background-color: #dc3545; color: white; font-weight: bold")
                    else:
                        styles.append("background-color: #28a745; color: white; font-weight: bold")
                except:
                    styles.append("")
            elif col == "上涨家数":
                try:
                    v = int(row[col])
                    if v > 2500:
                        styles.append("background-color: #28a745; color: white; font-weight: bold")
                    else:
                        styles.append("background-color: #dc3545; color: white; font-weight: bold")
                except:
                    styles.append("")
            elif col == "下跌家数":
                try:
                    v = int(row[col])
                    if v > 2500:
                        styles.append("background-color: #dc3545; color: white; font-weight: bold")
                    else:
                        styles.append("background-color: #28a745; color: white; font-weight: bold")
                except:
                    styles.append("")
            elif col == "最高板":
                try:
                    v = int(row[col])
                    if v > 5:
                        styles.append("background-color: #28a745; color: white; font-weight: bold")
                    else:
                        styles.append("background-color: #dc3545; color: white; font-weight: bold")
                except:
                    styles.append("")
            else:
                styles.append("")
        return styles


    styled_df = format_df.style.apply(color_row, axis=1)
    styled_df = styled_df.set_table_styles([
        {'selector': 'th', 'props': [('background-color', '#343a40'), ('color', 'white'), ('font-weight', 'bold')]},
        {'selector': 'td', 'props': [('text-align', 'center')]}
    ])
    st.dataframe(styled_df, use_container_width=True, height=400)

    # ====================== 单字段修改 ======================
    st.subheader("✏️ 修改单个字段")
    edit_id = st.number_input("要修改的ID", min_value=1, format="%d")
    field_map = {
        "平均股价_大盘": "avg_price_dapan",
        "上证指数": "sh_index",
        "流动资金": "liquidity",
        "大盘成交额": "market_volume",
        "涨停家数": "limit_up",
        "跌停家数": "limit_down",
        "上涨家数": "rise_count",
        "下跌家数": "fall_count",
        "最高板": "max_board",
        "指数节点": "index_node",
        "竞价": "auction",
        "星星龙头": "star_leader",
        "和信个股": "hexin_stock",
        "板块核心": "sector_core"
    }
    selected_field_cn = st.selectbox("选择要修改的字段", list(field_map.keys()))
    new_value = st.text_input("输入新内容")

    if st.button("确认修改"):
        field_en = field_map[selected_field_cn]
        if field_en in ["market_volume", "limit_up", "limit_down", "rise_count", "fall_count", "max_board"]:
            try:
                new_value = int(new_value)
            except:
                st.error("❌ 必须输入整数！")
                st.stop()
        if update_single_field(edit_id, field_en, new_value):
            st.success(f"✅ ID {edit_id} 修改成功")
            st.rerun()

    # 删除
    st.subheader("🗑️ 删除数据")
    del_id = st.number_input("删除ID", min_value=1, format="%d")
    if st.button("确认删除"):
        if delete_by_id(del_id):
            st.success(f"ID {del_id} 删除成功")
            st.rerun()
else:
    st.info("暂无数据")