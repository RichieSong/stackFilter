import streamlit as st
import pandas as pd
import mysql.connector
from datetime import date
import plotly.express as px
from mysql.connector import Error
from datetime import datetime
import pytesseract
import cv2
import numpy as np
from PIL import Image

# 1. 顶部锚点 —— 放在你页面【最最最顶端】
st.markdown('<div id="top"></div>', unsafe_allow_html=True)

# 页面锚点跳转支持
st.markdown("""
<style>
.anchor-nav {
    position: sticky;
    top: 0;
    z-index: 999;
    background: #F5F5F5;
    padding: 10px;
    border-radius: 8px;
    margin-bottom: 15px;
}
.anchor-nav a {
    color: white !important;
    text-decoration: none !important;
    background: #0d6efd;
    padding: 6px 10px;
    border-radius: 6px;
    margin: 0 4px;
    font-size: 14px;
    display: inline-block;
}
.anchor-nav a:hover {
    background: #0a58ca;
}
</style>
""", unsafe_allow_html=True)

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

# ====================== 月度大盘分析 函数 ======================
# 判断月份是否已存在
def is_month_exists(month_date):
    conn = get_connection()
    if not conn:
        return False
    cursor = conn.cursor()
    cursor.execute("SELECT month_date FROM market_monthly_analysis WHERE month_date = %s", (month_date,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

# 新增月度分析
def insert_month_analysis(month_date, analysis_content):
    conn = get_connection()
    if not conn:
        return False
    cursor = conn.cursor()
    sql = """
    INSERT INTO market_monthly_analysis (month_date, analysis_content)
    VALUES (%s, %s)
    """
    try:
        cursor.execute(sql, (month_date, analysis_content))
        conn.commit()
        return True
    except Error as e:
        st.error(f"保存失败：{e}")
        return False
    finally:
        conn.close()

# 获取所有月度分析
def get_all_month_analysis():
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    query = """
    SELECT month_date AS 月份, analysis_content AS 大盘分析内容, created_at AS 创建时间, updated_at AS 更新时间
    FROM market_monthly_analysis ORDER BY month_date DESC
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# 删除月度分析
def delete_month(month_date):
    conn = get_connection()
    if not conn:
        return False
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM market_monthly_analysis WHERE month_date = %s", (month_date,))
        conn.commit()
        return True
    except Error as e:
        st.error(f"删除失败：{e}")
        return False
    finally:
        conn.close()

# 修改月度分析内容
def update_month_analysis(month_date, new_content):
    conn = get_connection()
    if not conn:
        return False
    cursor = conn.cursor()
    sql = "UPDATE market_monthly_analysis SET analysis_content = %s WHERE month_date = %s"
    try:
        cursor.execute(sql, (new_content, month_date))
        conn.commit()
        return True
    except Error as e:
        st.error(f"修改失败：{e}")
        return False
    finally:
        conn.close()

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
        index_node, auction, star_leader, hexin_stock, sector_core,
        band_pioneer, first_plate_yesterday, con_plate_yesterday,mid_line_attack, short_line_attack
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s,%s,%s,%s)
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
        sector_core AS 板块核心,
        band_pioneer AS 波段先锋,
        first_plate_yesterday AS 昨日首板家数,
        con_plate_yesterday AS 昨日连板家数,
        mid_line_attack AS 中线上攻,
        short_line_attack AS 短线上攻
    FROM stock_data ORDER BY date ASC
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


def delete_by_id(del_id, df):
    if del_id not in df["id"].values:
        return False

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
st.set_page_config(page_title="大盘情绪系统 | A股专业版", layout="wide", page_icon="📈")

st.markdown("""
<style>
    .main {
        background-color: #FFFFFF;
    }
    html, body, h1, h2, h3, h4, h5, p, div, span, label {
        color: #111111 !important;
    }
    div[data-testid="stMetric"] {
        background-color: #F8F9FA;
        border-radius: 10px;
        padding: 15px;
    }
    div[data-testid="stHorizontalBlock"] {
        gap: 10px;
    }
</style>
""", unsafe_allow_html=True)

# 侧边栏：菜单（增删改 全部放这里）
with st.sidebar:
    st.title("📊 系统菜单")
    st.divider()
    st.markdown("""
     <div class="anchor-nav">
         <a href="#大盘情绪">大盘情绪</a>
         <a href="#大盘周期">大盘周期</a>
         <a href="#历史数据">历史数据</a>
         <a href="#统计分析">统计分析</a>
     </div>
     """, unsafe_allow_html=True)
    show_add = st.checkbox("📥 数据录入")
    show_edit = st.checkbox("✏️ 数据修改")
    show_delete = st.checkbox("🗑️ 数据删除")
    show_add_month = st.checkbox("🗓️ 月度分析录入")
    show_edit_month = st.checkbox("✏️ 月度分析修改")
    show_del_month = st.checkbox("🗑️ 月度分析删除")
    st.divider()
    st.caption("📌 A股大盘情绪分析系统 V1.0")

# 主标题
st.title("📈 A股大盘情绪分析系统（专业版）")

# ====================== ✅ 核心改造：右侧全部内容 → TAB 标签页 ======================
df = get_all_data()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 大盘总览",
    "📈 情绪周期图",
    "📋 历史数据",
    "📅 统计分析",
    "🗓️ 月度分析"  # 新增
])

# -------------------- TAB1：大盘总览 --------------------
with tab1:
    st.subheader("🧠 今日大盘实时情绪")
    if not df.empty:
        latest = df.iloc[-1]
        score = get_emotion_score(latest)
        suggest = get_trade_suggest(score)

        with st.container(border=True):
            c1, c2, c3 = st.columns([1, 1, 2])
            with c1:
                st.metric("大盘综合情绪分", f"{score} 分")
            with c2:
                st.metric("操作建议", suggest)
            with c3:
                status = "📈 强势区" if score >= 60 else "📊 震荡区" if score >= 40 else "📉 弱市区"
                st.metric("市场状态", status)

        st.divider()

        with st.container(border=True):
            st.subheader("📋 核心市场数据")
            g1, g2, g3, g4, g5 = st.columns(5)
            with g1:
                zt = int(latest["涨停家数"])
                st.metric("涨停家数", zt, delta="偏弱" if zt <= 50 else "活跃",
                          delta_color="inverse" if zt <= 50 else "normal")
            with g2:
                dt = int(latest["跌停家数"])
                st.metric("跌停家数", dt, delta="安全" if dt <= 10 else "风险",
                          delta_color="normal" if dt <= 10 else "inverse")
            with g3:
                up = int(latest["上涨家数"])
                st.metric("上涨家数", up, delta="空头" if up <= 2500 else "多头",
                          delta_color="inverse" if up <= 2500 else "normal")
            with g4:
                dn = int(latest["下跌家数"])
                st.metric("下跌家数", dn, delta="稳定" if dn <= 2500 else "抛压",
                          delta_color="normal" if dn <= 2500 else "inverse")
            with g5:
                hb = int(latest["最高板"])
                st.metric("最高板", hb, delta="高度低" if hb <= 5 else "高度够",
                          delta_color="inverse" if hb <= 5 else "normal")

            st.divider()

            g6, g7, g8, g9 = st.columns(4)
            with g6:
                vol_now = int(latest["大盘成交额"])
                diff = 0
                if len(df) >= 2:
                    vol_prev = int(df.iloc[-2]["大盘成交额"])
                    diff = vol_now - vol_prev
                    vol_text = f"放量 {diff} 亿" if diff > 0 else f"缩量 {abs(diff)} 亿"
                else:
                    vol_text = "无昨日数据"
                st.metric("大盘成交额", f"{vol_now:,} 亿", delta=vol_text, delta_color="normal" if diff > 0 else "inverse")
            with g7:
                lq = latest["流动资金"]
                st.metric("流动资金", lq, delta="资金向好" if "红" in lq else "资金流出",
                          delta_color="normal" if "红" in lq else "inverse")
            with g8:
                avg = latest["平均股价_大盘"]
                st.metric("平均股价", avg, delta="金叉向好" if "金叉" in avg else "死叉风险",
                          delta_color="normal" if "金叉" in avg else "inverse")
            with g9:
                try:
                    first_plate = int(latest["昨日首板家数"])
                    con_plate = int(latest["昨日连板家数"])
                    rate = round(con_plate / first_plate * 100, 1) if first_plate != 0 else 0
                except:
                    rate = 0
                delta_text = "接力强" if rate >= 30 else "接力弱"
                delta_color = "normal" if rate >= 30 else "inverse"
                st.metric("连板晋级率", f"{rate}%", delta=delta_text, delta_color=delta_color)
    else:
        st.info("暂无数据")

# -------------------- TAB2：情绪周期图 + 趋势图 --------------------
with tab2:
    if not df.empty:
        with st.container(border=True):
            st.subheader("📈 大盘情绪周期 + 短中线上攻 + 涨跌停")
            df_plot = df.copy()
            df_plot["日期"] = pd.to_datetime(df_plot["日期"])
            df_plot["情绪分"] = df_plot.apply(get_emotion_score, axis=1)

            def parse_jcsc(text):
                s = str(text).strip()
                if "金叉" in s:
                    num = ''.join([c for c in s if c.isdigit()])
                    day = int(num) if num else 1
                    return "金叉", day, f"金叉{day}天"
                elif "死叉" in s:
                    num = ''.join([c for c in s if c.isdigit()])
                    day = int(num) if num else 1
                    return "死叉", day, f"死叉{day}天"
                else:
                    return "无", 0, "无"

            df_plot[["类型", "天数", "显示文本"]] = df_plot["平均股价_大盘"].apply(lambda x: pd.Series(parse_jcsc(x)))
            max_date = df_plot["日期"].max()
            min_date = max_date - pd.Timedelta(days=30)
            df_date_min = pd.to_datetime(df["日期"]).min().date()
            df_date_max = pd.to_datetime(df["日期"]).max().date()

            start_date, end_date = st.slider("时间范围", df_date_min, df_date_max, (min_date.date(), max_date.date()))
            df_plot = df_plot[(df_plot["日期"] >= pd.Timestamp(start_date)) & (df_plot["日期"] <= pd.Timestamp(end_date))].reset_index(drop=True)

            import plotly.graph_objects as go
            fig = go.Figure()

            fig.add_trace(go.Scatter(x=df_plot["日期"], y=df_plot["情绪分"], name="情绪分", line=dict(color="#1f77b4", width=3), mode="lines+markers+text", text=df_plot["情绪分"], textposition="top center"))
            df_plot["最高板_真实"] = df_plot["最高板"].fillna(1).astype(int)

            def calc_y(val):
                return val * 10 if val <= 10 else 100

            df_plot["最高板_缩放"] = df_plot["最高板_真实"].apply(calc_y)
            df_plot["最高板_标签"] = df_plot["最高板_真实"].astype(str) + "板"
            fig.add_trace(go.Scatter(x=df_plot["日期"], y=df_plot["最高板_缩放"], name="最高板", line=dict(color="#FF6B35", width=3), mode="lines+markers+text", text=df_plot["最高板_标签"], textposition="top center", textfont=dict(size=12, color="#FF6B35", weight="bold"), marker=dict(size=8, color="#FF6B35")))

            fig.add_trace(go.Scatter(x=df_plot["日期"], y=df_plot["昨日首板家数"], name="昨日首板家数", line=dict(color="#22c55e", width=2), mode="lines+markers+text", text=df_plot["昨日首板家数"].astype(str) + "家", textposition="top center", textfont=dict(size=11, color="#22c55e", weight="bold")))
            fig.add_trace(go.Scatter(x=df_plot["日期"], y=df_plot["昨日连板家数"], name="昨日连板家数", line=dict(color="#f59e0b", width=2), mode="lines+markers+text", text=df_plot["昨日连板家数"].astype(str) + "家", textposition="top center", textfont=dict(size=11, color="#f59e0b", weight="bold")))
            fig.add_trace(go.Scatter(x=df_plot["日期"], y=df_plot["短线上攻"], name="短线上攻", line=dict(color="#8B5CF6", width=2, dash="dot"), mode="lines+markers+text", text=df_plot["短线上攻"].astype(str), textposition="top center", textfont=dict(size=11, color="#8B5CF6", weight="bold")))
            fig.add_trace(go.Scatter(x=df_plot["日期"], y=df_plot["中线上攻"], name="中线上攻", line=dict(color="#EC4899", width=2, dash="dot"), mode="lines+markers+text", text=df_plot["中线上攻"].astype(str), textposition="top center", textfont=dict(size=11, color="#EC4899", weight="bold")))
            fig.add_trace(go.Scatter(x=df_plot["日期"], y=df_plot["涨停家数"], name="涨停家数", line=dict(color="#EF4444", width=2), mode="lines+markers+text", text=df_plot["涨停家数"].astype(str) + "家", textposition="top center", textfont=dict(size=11, color="#EF4444", weight="bold")))
            fig.add_trace(go.Scatter(x=df_plot["日期"], y=df_plot["跌停家数"], name="跌停家数", line=dict(color="#6B7280", width=2), mode="lines+markers+text", text=df_plot["跌停家数"].astype(str) + "家", textposition="top center", textfont=dict(size=11, color="#6B7280", weight="bold")))

            x_list = df_plot["日期"]
            y_list = df_plot["天数"] * df_plot["类型"].map({"金叉": 1, "死叉": -1, "无": 0})
            text_list = df_plot["显示文本"]
            colors = ["#2E8B57" if t == "金叉" else "#DC143C" if t == "死叉" else "#888" for t in df_plot["类型"]]
            fig.add_trace(go.Scatter(x=x_list, y=y_list, name="平均股价", line=dict(color="#888", width=3), mode="lines+markers+text", text=text_list, textposition="bottom center", textfont=dict(color=colors, size=11, family="bold"), marker=dict(color=colors, size=10), yaxis="y2"))

            fig.add_hline(y=80, line_color="red", line_dash="dot", annotation_text="过热")
            fig.add_hline(y=30, line_color="blue", line_dash="dot", annotation_text="冰点")
            fig.update_layout(template="plotly_white", height=500, yaxis=dict(title="综合指标", range=[0, 120]), yaxis2=dict(title="金叉(+) / 死叉(-)", overlaying="y", side="right", range=[-10, 10]), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5))
            st.plotly_chart(fig, use_container_width=True)

        st.divider()

        with st.container(border=True):
            st.subheader("📊 大盘数据趋势")
            df_plot = df.copy()
            df_plot["日期"] = pd.to_datetime(df_plot["日期"])
            start_date, end_date = st.slider("数据时间范围", df_date_min, df_date_max, (min_date.date(), max_date.date()), key="trend_slider")
            df_plot = df_plot[(df_plot["日期"] >= pd.Timestamp(start_date)) & (df_plot["日期"] <= pd.Timestamp(end_date))]
            df_plot["日期"] = df_plot["日期"].dt.date

            tab11, tab22, tab33, tab44 = st.tabs(["💰 成交额", "🚥 涨跌停", "📈 涨跌家数", "🔥 首板/连板"])
            with tab11:
                fig = px.line(df_plot, x="日期", y="大盘成交额", markers=True, text="大盘成交额")
                fig.update_traces(textposition="top center")
                st.plotly_chart(fig, use_container_width=True)
            with tab22:
                fig = px.line(df_plot, x="日期", y=["涨停家数", "跌停家数"], markers=True, text="value")
                st.plotly_chart(fig, use_container_width=True)
            with tab33:
                fig = px.line(df_plot, x="日期", y=["上涨家数", "下跌家数"], markers=True, text="value")
                st.plotly_chart(fig, use_container_width=True)
            with tab44:
                fig = px.line(df_plot, x="日期", y=["昨日首板家数", "昨日连板家数"], markers=True, text="value")
                fig.update_layout(title="首板数 vs 连板数")
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无数据")

# -------------------- TAB3：历史数据表格（升降箭头+染色） --------------------
with tab3:
    st.subheader("📋 历史数据（智能染色）")
    if not df.empty:
        format_df = df.copy().sort_values("日期", ascending=False).reset_index(drop=True)
        format_df["大盘成交额"] = format_df["大盘成交额"].astype(int)

        int_fields = ["涨停家数", "跌停家数", "上涨家数", "下跌家数", "最高板", "昨日首板家数", "昨日连板家数"]
        for field in int_fields:
            format_df[field] = pd.to_numeric(format_df[field], errors="coerce").fillna(0).astype(int)

        float_fields = ["中线上攻", "短线上攻"]
        for field in float_fields:
            format_df[field] = pd.to_numeric(format_df[field], errors="coerce").fillna(0)

        target_cols = ["昨日首板家数", "昨日连板家数", "中线上攻", "短线上攻"]
        for col in target_cols:
            diff = format_df[col] - format_df[col].shift(-1)
            format_df[col] = format_df[col].astype(str)
            format_df.loc[diff > 0, col] += " ↑"
            format_df.loc[diff < 0, col] += " ↓"
            format_df.loc[diff == 0, col] += " —"

        def color_row(row):
            styles = []
            for col in format_df.columns:
                if col == "平均股价_大盘":
                    styles.append("background-color: #28a745; color: white; font-weight: bold" if "金叉" in str(row[col])
                                  else "background-color: #dc3545; color: white; font-weight: bold" if "死叉" in str(row[col])
                                  else "")
                elif col == "上证指数":
                    styles.append("background-color: #28a745; color: white; font-weight: bold" if "金叉" in str(row[col])
                                  else "background-color: #dc3545; color: white; font-weight: bold" if "死叉" in str(row[col])
                                  else "")
                elif col == "流动资金":
                    styles.append("background-color: #28a745; color: white; font-weight: bold" if "红" in str(row[col])
                                  else "background-color: #dc3545; color: white; font-weight: bold" if "绿" in str(row[col])
                                  else "")
                elif col == "大盘成交额":
                    try:
                        v = int(row[col])
                        styles.append("background-color: #28a745; color: white; font-weight: bold" if v > 20000 else "background-color: #dc3545; color: white; font-weight: bold")
                    except:
                        styles.append("")
                elif col == "涨停家数":
                    try:
                        v = int(row[col])
                        styles.append("background-color: #28a745; color: white; font-weight: bold" if v > 50 else "background-color: #dc3545; color: white; font-weight: bold")
                    except:
                        styles.append("")
                elif col == "跌停家数":
                    try:
                        v = int(row[col])
                        styles.append("background-color: #dc3545; color: white; font-weight: bold" if v > 10 else "background-color: #28a745; color: white; font-weight: bold")
                    except:
                        styles.append("")
                elif col == "上涨家数":
                    try:
                        v = int(row[col])
                        styles.append("background-color: #28a745; color: white; font-weight: bold" if v > 2500 else "background-color: #dc3545; color: white; font-weight: bold")
                    except:
                        styles.append("")
                elif col == "下跌家数":
                    try:
                        v = int(row[col])
                        styles.append("background-color: #dc3545; color: white; font-weight: bold" if v > 2500 else "background-color: #28a745; color: white; font-weight: bold")
                    except:
                        styles.append("")
                elif col == "最高板":
                    try:
                        v = int(row[col])
                        styles.append("background-color: #28a745; color: white; font-weight: bold" if v > 5 else "background-color: #dc3545; color: white; font-weight: bold")
                    except:
                        styles.append("")
                elif col in ["昨日首板家数", "昨日连板家数", "中线上攻", "短线上攻"]:
                    txt = str(row[col])
                    if "↑" in txt:
                        styles.append("color: #28a745; font-weight: bold; font-size:14px;")
                    elif "↓" in txt:
                        styles.append("color: #dc3545; font-weight: bold; font-size:14px;")
                    else:
                        styles.append("color: #666; font-weight: bold;")
                else:
                    styles.append("")
            return styles

        page_size = 15
        total_pages = (len(format_df) + page_size - 1) // page_size
        cols_pag = st.columns([1, 2, 1])
        with cols_pag[1]:
            page_num = st.number_input("页码", min_value=1, max_value=total_pages, value=1, step=1, key="table_pager")
        start = (page_num - 1) * page_size
        end = start + page_size
        paginated_df = format_df.iloc[start:end].copy()

        styled_df = paginated_df.style.apply(color_row, axis=1)
        styled_df = styled_df.set_table_styles([
            {'selector': 'thead th', 'props': [('position', 'sticky'), ('top', '0'), ('z-index', '100'), ('background-color', '#4C6EF5'), ('color', 'white'), ('font-weight', 'bold'), ('text-align', 'center')]},
            {'selector': 'tbody td:first-child', 'props': [('position', 'sticky'), ('left', '0'), ('z-index', '50'), ('background-color', 'white'), ('border-right', '1px solid #ddd')]},
            {'selector': 'thead th:first-child', 'props': [('position', 'sticky'), ('top', '0'), ('left', '0'), ('z-index', '200')]},
            {'selector': 'td', 'props': [('text-align', 'center'), ('white-space', 'pre-wrap'), ('word-wrap', 'break-word'), ('max-width', '300px'), ('vertical-align', 'middle'), ('line-height', '1.4')]},
        ])

        html = styled_df.to_html()
        st.html(f'''<div style="height:700px; overflow:auto;">{html}</div>''')
    else:
        st.info("暂无数据")

# -------------------- TAB4：统计分析 --------------------
with tab4:
    st.subheader("📅 周/月 统计分析 + 多字段总和")
    if not df.empty:
        df_stat = df.copy()
        df_stat["日期"] = pd.to_datetime(df_stat["日期"])
        df_stat["周"] = df_stat["日期"].dt.to_period("W").astype(str)
        df_stat["月"] = df_stat["日期"].dt.to_period("M").astype(str)

        import re
        def extract_num(s):
            try:
                nums = re.findall(r'[+-]?\d+\.?\d*', str(s))
                return sum(float(n) for n in nums)
            except:
                return 0.0

        df_stat["竞价数值"] = df_stat["竞价"].apply(extract_num)
        df_stat["星星龙头数值"] = df_stat["星星龙头"].apply(extract_num)
        df_stat["和信个股数值"] = df_stat["和信个股"].apply(extract_num)
        df_stat["板块核心数值"] = df_stat["板块核心"].apply(extract_num)
        df_stat["波段先锋数值"] = df_stat["波段先锋"].apply(extract_num)

        period = st.radio("选择周期", ["按周统计", "按月统计"], horizontal=True)
        col = "周" if period == "按周统计" else "月"

        agg_df = df_stat.groupby(col).agg(
            天数=("日期", "count"),
            竞价总和=("竞价数值", "sum"),
            星星龙头总和=("星星龙头数值", "sum"),
            和信个股总和=("和信个股数值", "sum"),
            板块核心总和=("板块核心数值", "sum"),
            波段先锋_均值=("波段先锋数值", "sum"),
        ).reset_index().sort_values(col, ascending=False)

        st.dataframe(agg_df, use_container_width=True)

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric("📊 竞价总累计", f"{df_stat['竞价数值'].sum():.2f}")
        with c2:
            st.metric("🌟 星星龙头总累计", f"{df_stat['星星龙头数值'].sum():.2f}")
        with c3:
            st.metric("📝 和信个股总累计", f"{df_stat['和信个股数值'].sum():.2f}")
        with c4:
            st.metric("📊 板块核心总累计", f"{df_stat['板块核心数值'].sum():.2f}")
        with c5:
            st.metric("📊 波段先锋总累计", f"{df_stat['波段先锋数值'].sum():.2f}")
    else:
        st.info("暂无数据")

# -------------------- TAB5：月度大盘分析 --------------------
with tab5:
    st.subheader("🗓️ 月度大盘分析记录")
    df_month = get_all_month_analysis()
    if not df_month.empty:
        st.dataframe(
            df_month,
            use_container_width=True,
            height=600
        )
    else:
        st.info("暂无月度大盘分析数据")
# ====================== 数据录入 / 修改 / 删除（不变） ======================
if show_add:
    with st.sidebar:
        with st.container(border=True):
            st.subheader("📥 数据录入")
            with st.form("add_form"):
                input_date = st.date_input("日期")
                ap_type = st.selectbox("平均股价", ["金叉", "死叉"])
                ap_day = st.number_input("平均股价天数", 0, 30, 0)
                avg_price_dapan = f"{ap_type}{ap_day}日"
                sh_type = st.selectbox("上证指数", ["金叉", "死叉"])
                sh_day = st.number_input("上证指数天数", 0, 30, 0)
                sh_index = f"{sh_type}{sh_day}日"

                liq = st.selectbox("流动资金", ["翻红", "翻绿"])
                vol = st.number_input("大盘成交额", 0, 9999999, value=0)
                lu = st.number_input("涨停家数", 0, 999, 0)
                ld = st.number_input("跌停家数", 0, 999, 0)
                up = st.number_input("上涨家数", 0, 9999, 0)
                dn = st.number_input("下跌家数", 0, 9999, 0)
                mb = st.number_input("最高板", 0, 20, 0)
                mid_line_attack = st.number_input("中线上攻", 0.0, 100.0, 0.0, step=0.1)
                short_line_attack = st.number_input("短线上攻", 0.0, 100.0, 0.0, step=0.1)

                idx = st.text_area("指数节点")
                auc = st.text_area("竞价")
                star = st.text_area("星星龙头")
                hexin = st.text_area("和信个股")
                sector = st.text_area("板块核心")
                band_pioneer = st.text_area("波段先锋")
                first_plate_yesterday = st.number_input("昨日首板家数", 0, 200, 0)
                con_plate_yesterday = st.number_input("昨日连板家数", 0, 100, 0)

                submitted = st.form_submit_button("✅ 提交")
                if submitted:
                    if is_weekend(input_date):
                        st.error("❌ 周末禁止录入")
                    elif is_date_exists(input_date):
                        st.error("❌ 日期已存在")
                    else:
                        data = (input_date, avg_price_dapan, sh_index, liq, vol, lu, ld, up, dn, mb, idx, auc, star, hexin, sector, band_pioneer, first_plate_yesterday, con_plate_yesterday, mid_line_attack, short_line_attack)
                        if insert_data(data):
                            st.success("保存成功")
                            st.rerun()

if show_edit:
    with st.sidebar:
        with st.container(border=True):
            st.subheader("✏️ 修改数据")
            max_id = int(df["id"].max()) if not df.empty else 1
            edit_id = st.number_input("修改ID", 1, 9999, step=1, value=max_id)
            load_data = df[df["id"] == edit_id].iloc[0] if not df.empty and edit_id in df["id"].values else None
            field_map = {"平均股价_大盘": "avg_price_dapan","上证指数": "sh_index","流动资金": "liquidity","大盘成交额": "market_volume","涨停家数": "limit_up","跌停家数": "limit_down","上涨家数": "rise_count","下跌家数": "fall_count","最高板": "max_board","指数节点": "index_node","竞价": "auction","星星龙头": "star_leader","和信个股": "hexin_stock","板块核心": "sector_core","波段先锋": "band_pioneer","昨日首板家数": "first_plate_yesterday","昨日连板家数": "con_plate_yesterday","短线上攻":"short_line_attack","中线上攻":"mid_line_attack"}
            selected_field_cn = st.selectbox("选择字段", list(field_map.keys()))
            field_en = field_map[selected_field_cn]
            default_value = str(load_data[selected_field_cn]) if load_data is not None else ""
            new_value = st.text_area("新内容", value=default_value)
            if st.button("✅ 确认修改"):
                num_fields = ["market_volume", "limit_up", "limit_down", "rise_count", "fall_count", "max_board"]
                if field_en in num_fields:
                    try:
                        new_value = int(new_value)
                    except:
                        st.error("❌ 必须输入数字")
                        st.stop()
                if update_single_field(edit_id, field_en, new_value):
                    st.success("修改成功")
                    st.rerun()

if show_delete:
    with st.sidebar:
        with st.container(border=True):
            st.subheader("🗑️ 删除数据")
            max_id = int(df["id"].max()) if not df.empty else 1
            del_id = st.number_input("删除ID", 1, 9999, step=1, value=max_id)
            confirm_delete = st.checkbox("✅ 确认删除")
            if st.button("🗑️ 确认删除", type="primary"):
                if not confirm_delete:
                    st.warning("⚠️ 请勾选确认")
                    st.stop()
                if delete_by_id(del_id, df):
                    st.success("删除成功")
                else:
                    st.error("删除失败")



# ====================== 🗓️ 月度大盘分析 录入 ======================
# ====================== 🗓️ 月度大盘分析录入（自动年月） ======================
# ====================== 🗓️ 月度大盘分析录入（下拉选年月，不可手写） ======================
if show_add_month:
    with st.sidebar:
        with st.container(border=True):
            st.subheader("🗓️ 月度大盘分析录入")
            with st.form("month_form"):
                # 自动生成近36个月年月列表，下拉选择，禁止手写
                from datetime import datetime
                now = datetime.now()
                month_list = []
                for i in range(36):
                    # 往前倒推36个月
                    if now.month - i <= 0:
                        sub_year = 1 + (i - now.month) // 12
                        sub_month = 12 - ((i - now.month) % 12)
                        select_year = now.year - sub_year
                        select_mon = sub_month
                    else:
                        select_year = now.year
                        select_mon = now.month - i
                    ym_str = f"{select_year:04d}-{select_mon:02d}"
                    month_list.append(ym_str)

                # 下拉选择，不能手动输入
                select_month = st.selectbox(
                    "选择录入月份",
                    options=month_list,
                    index=0,  # 默认选中本月
                    disabled=False
                )

                content = st.text_area("本月大盘分析内容", height=180)
                submitted = st.form_submit_button("✅ 保存月度分析")

                if submitted:
                    if is_month_exists(select_month):
                        st.error(f"❌ {select_month} 月度分析已存在，请勿重复录入")
                    else:
                        if insert_month_analysis(select_month, content):
                            st.success(f"✅ {select_month} 月度分析保存成功！")
                            st.rerun()

# ====================== ✏️ 月度分析修改 ======================
if show_edit_month:
    with st.sidebar:
        with st.container(border=True):
            st.subheader("✏️ 修改月度分析")
            df_month = get_all_month_analysis()
            if not df_month.empty:
                month_list = df_month["月份"].tolist()
                target_month = st.selectbox("选择月份", month_list)
                current_data = df_month[df_month["月份"] == target_month].iloc[0]
                new_content = st.text_area("修改分析内容", value=current_data["大盘分析内容"], height=180)
                if st.button("✅ 确认修改"):
                    if update_month_analysis(target_month, new_content):
                        st.success(f"{target_month} 修改成功！")
                        st.rerun()
            else:
                st.info("暂无月度分析可修改")

# ====================== 🗑️ 月度分析删除 ======================
if show_del_month:
    with st.sidebar:
        with st.container(border=True):
            st.subheader("🗑️ 删除月度分析")
            df_month = get_all_month_analysis()
            if not df_month.empty:
                month_list = df_month["月份"].tolist()
                del_month = st.selectbox("选择要删除的月份", month_list)
                confirm_del = st.checkbox("✅ 确认删除（不可恢复）")
                if st.button("🗑️ 确认删除"):
                    if not confirm_del:
                        st.warning("请勾选确认删除")
                    else:
                        if delete_month(del_month):
                            st.success(f"{del_month} 删除成功！")
                            st.rerun()
            else:
                st.info("暂无数据")


# 底部锚点
st.markdown("""
<style>
.scroll-buttons { position: fixed; right: 20px; bottom: 20px; z-index: 999999; display: flex; flex-direction: column; gap: 10px; }
.scroll-btn { width: 50px; height: 50px; border-radius: 50%; background-color: #165DFF; color: white !important; font-size: 22px; font-weight: bold; border: none; display: flex; align-items: center; justify-content: center; text-decoration: none !important; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
.scroll-btn:hover { background-color: #0F4CD0; }
</style>
<div class="scroll-buttons"><a href="#top" class="scroll-btn">↑</a><a href="#bottom" class="scroll-btn">↓</a></div>
<div id="bottom"></div>
""", unsafe_allow_html=True)