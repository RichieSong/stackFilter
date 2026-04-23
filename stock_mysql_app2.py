import streamlit as st
import pandas as pd
import mysql.connector
from datetime import date
import plotly.express as px
from mysql.connector import Error
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
    # print(data)
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
    # 如果ID不存在
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
# ====================== 页面 UI ======================
st.set_page_config(page_title="大盘情绪系统 | A股专业版", layout="wide", page_icon="📈")

# 自定义专业金融风格 CSS
# 稳定清晰版 CSS —— 永不见字体看不见问题
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
    # ====================== 🔗 全局快捷导航 ======================
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
    st.divider()
    st.caption("📌 A股大盘情绪分析系统 V1.0")

# 顶部标题
st.title("📈 A股大盘情绪分析系统（专业版）")
st.markdown("<hr style='margin-top: -10px; margin-bottom: 20px;'>", unsafe_allow_html=True)
st.markdown('<a id="大盘情绪"></a>', unsafe_allow_html=True)

df = get_all_data()

# ====================== 1. 今日大盘总览（卡片） ======================
if not df.empty:
    latest = df.iloc[-1]
    score = get_emotion_score(latest)
    suggest = get_trade_suggest(score)

    with st.container(border=True):
        st.subheader("🧠 今日大盘实时情绪")
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            st.metric("大盘综合情绪分", f"{score} 分")
        with c2:
            st.metric("操作建议", suggest)
        with c3:
            status = "📈 强势区" if score >= 60 else "📊 震荡区" if score >= 40 else "📉 弱市区"
            st.metric("市场状态", status)

    st.divider()

    # ====================== 2. 核心市场数据卡片 ======================
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

        # ====================== 【新增：晋级率】 ======================
        g6, g7, g8, g9 = st.columns(4)  # 改成4列，加入晋级率
        with g6:
            vol_now = int(latest["大盘成交额"])
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

        # 晋级率计算
        with g9:
            try:
                first_plate = int(latest["昨日首板家数"])
                con_plate = int(latest["昨日连板家数"])
                if first_plate == 0:
                    rate = 0
                else:
                    rate = round(con_plate / first_plate * 100, 1)
            except:
                rate = 0

            delta_text = "接力强" if rate >= 30 else "接力弱"
            delta_color = "normal" if rate >= 30 else "inverse"
            st.metric("连板晋级率", f"{rate}%", delta=delta_text, delta_color=delta_color)

    st.divider()

if not df.empty:
    with st.container(border=True):
        st.subheader("📈 大盘情绪周期 + 平均股价金叉死叉 + 最高板 + 昨日首板/连板 + 短中线上攻 + 涨跌停")

        df_plot = df.copy()
        df_plot["日期"] = pd.to_datetime(df_plot["日期"])
        df_plot["情绪分"] = df_plot.apply(get_emotion_score, axis=1)

        # ============= 提取：金叉/死叉 + 天数 + 显示文本 =============
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

        # 时间筛选
        max_date = df_plot["日期"].max()
        min_date = max_date - pd.Timedelta(days=30)
        df_date_min = pd.to_datetime(df["日期"]).min().date()
        df_date_max = pd.to_datetime(df["日期"]).max().date()

        start_date, end_date = st.slider(
            "时间范围", df_date_min, df_date_max,
            (min_date.date(), max_date.date())
        )
        df_plot = df_plot[
            (df_plot["日期"] >= pd.Timestamp(start_date)) &
            (df_plot["日期"] <= pd.Timestamp(end_date))
        ].reset_index(drop=True)

        # ============= 画图 =============
        import plotly.graph_objects as go

        fig = go.Figure()

        # 1. 情绪分（左Y轴）
        fig.add_trace(go.Scatter(
            x=df_plot["日期"], y=df_plot["情绪分"],
            name="情绪分", line=dict(color="#1f77b4", width=3),
            mode="lines+markers+text", text=df_plot["情绪分"], textposition="top center"
        ))

        df_plot["最高板_真实"] = df_plot["最高板"].fillna(1).astype(int)

        def calc_y(val):
            if val <= 10:
                return val * 10
            else:
                return 100

        df_plot["最高板_缩放"] = df_plot["最高板_真实"].apply(calc_y)
        df_plot["最高板_标签"] = df_plot["最高板_真实"].astype(str) + "板"

        fig.add_trace(go.Scatter(
            x=df_plot["日期"],
            y=df_plot["最高板_缩放"],
            name="最高板",
            line=dict(color="#FF6B35", width=3),
            mode="lines+markers+text",
            text=df_plot["最高板_标签"],
            textposition="top center",
            textfont=dict(size=12, color="#FF6B35", weight="bold"),
            marker=dict(size=8, color="#FF6B35", line=dict(width=1, color="white"))
        ))

        # ==================== 昨日首板家数 ====================
        fig.add_trace(go.Scatter(
            x=df_plot["日期"],
            y=df_plot["昨日首板家数"],
            name="昨日首板家数",
            line=dict(color="#22c55e", width=2),
            mode="lines+markers+text",
            text=df_plot["昨日首板家数"].astype(str) + "家",
            textposition="top center",
            textfont=dict(size=11, color="#22c55e", weight="bold"),
            marker=dict(size=6, color="#22c55e")
        ))

        # ==================== 昨日连板家数 ====================
        fig.add_trace(go.Scatter(
            x=df_plot["日期"],
            y=df_plot["昨日连板家数"],
            name="昨日连板家数",
            line=dict(color="#f59e0b", width=2),
            mode="lines+markers+text",
            text=df_plot["昨日连板家数"].astype(str) + "家",
            textposition="top center",
            textfont=dict(size=11, color="#f59e0b", weight="bold"),
            marker=dict(size=6, color="#f59e0b")
        ))

        # ==================== 新增：短线上攻 ====================
        fig.add_trace(go.Scatter(
            x=df_plot["日期"],
            y=df_plot["短线上攻"],
            name="短线上攻",
            line=dict(color="#8B5CF6", width=2, dash="dot"),
            mode="lines+markers+text",
            text=df_plot["短线上攻"].astype(str),
            textposition="top center",
            textfont=dict(size=11, color="#8B5CF6", weight="bold"),
            marker=dict(size=6, color="#8B5CF6")
        ))

        # ==================== 新增：中线上攻 ====================
        fig.add_trace(go.Scatter(
            x=df_plot["日期"],
            y=df_plot["中线上攻"],
            name="中线上攻",
            line=dict(color="#EC4899", width=2, dash="dot"),
            mode="lines+markers+text",
            text=df_plot["中线上攻"].astype(str),
            textposition="top center",
            textfont=dict(size=11, color="#EC4899", weight="bold"),
            marker=dict(size=6, color="#EC4899")
        ))

        # ==================== 新增：涨停家数 ====================
        fig.add_trace(go.Scatter(
            x=df_plot["日期"],
            y=df_plot["涨停家数"],
            name="涨停家数",
            line=dict(color="#EF4444", width=2),
            mode="lines+markers+text",
            text=df_plot["涨停家数"].astype(str) + "家",
            textposition="top center",
            textfont=dict(size=11, color="#EF4444", weight="bold"),
            marker=dict(size=6, color="#EF4444")
        ))

        # ==================== 新增：跌停家数 ====================
        fig.add_trace(go.Scatter(
            x=df_plot["日期"],
            y=df_plot["跌停家数"],
            name="跌停家数",
            line=dict(color="#6B7280", width=2),
            mode="lines+markers+text",
            text=df_plot["跌停家数"].astype(str) + "家",
            textposition="top center",
            textfont=dict(size=11, color="#6B7280", weight="bold"),
            marker=dict(size=6, color="#6B7280")
        ))

        # 2. 金叉死叉 连续线 + 颜色区分（右Y轴）
        x_list = df_plot["日期"]
        y_list = df_plot["天数"] * df_plot["类型"].map({"金叉": 1, "死叉": -1, "无": 0})
        text_list = df_plot["显示文本"]
        colors = ["#2E8B57" if t == "金叉" else "#DC143C" if t == "死叉" else "#888" for t in df_plot["类型"]]

        fig.add_trace(go.Scatter(
            x=x_list, y=y_list,
            name="平均股价",
            line=dict(color="#888", width=3),
            mode="lines+markers+text",
            text=text_list,
            textposition="bottom center",
            textfont=dict(color=colors, size=11, family="bold"),
            marker=dict(color=colors, size=10, line=dict(width=1, color="white")),
            yaxis="y2"
        ))

        # 3. 情绪线阈值
        fig.add_hline(y=80, line_color="red", line_dash="dot", annotation_text="过热")
        fig.add_hline(y=30, line_color="blue", line_dash="dot", annotation_text="冰点")

        # 4. 双轴设置
        fig.update_layout(
            template="plotly_white", height=500,
            yaxis=dict(title="综合指标", range=[0, 120]),
            yaxis2=dict(title="金叉(+) / 死叉(-)", overlaying="y", side="right", range=[-10, 10]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
        )

        st.plotly_chart(fig, use_container_width=True)
    st.divider()

# if not df.empty:
#     with st.container(border=True):
#         st.subheader("📈 大盘情绪周期 + 平均股价金叉死叉 + 最高板 + 昨日首板/连板")
#
#         df_plot = df.copy()
#         df_plot["日期"] = pd.to_datetime(df_plot["日期"])
#         df_plot["情绪分"] = df_plot.apply(get_emotion_score, axis=1)
#
#
#         # ============= 提取：金叉/死叉 + 天数 + 显示文本 =============
#         def parse_jcsc(text):
#             s = str(text).strip()
#             if "金叉" in s:
#                 num = ''.join([c for c in s if c.isdigit()])
#                 day = int(num) if num else 1
#                 return "金叉", day, f"金叉{day}天"
#             elif "死叉" in s:
#                 num = ''.join([c for c in s if c.isdigit()])
#                 day = int(num) if num else 1
#                 return "死叉", day, f"死叉{day}天"
#             else:
#                 return "无", 0, "无"
#
#
#         df_plot[["类型", "天数", "显示文本"]] = df_plot["平均股价_大盘"].apply(lambda x: pd.Series(parse_jcsc(x)))
#
#         # 时间筛选
#         max_date = df_plot["日期"].max()
#         min_date = max_date - pd.Timedelta(days=30)
#         df_date_min = pd.to_datetime(df["日期"]).min().date()
#         df_date_max = pd.to_datetime(df["日期"]).max().date()
#
#         start_date, end_date = st.slider(
#             "时间范围", df_date_min, df_date_max,
#             (min_date.date(), max_date.date())
#         )
#         df_plot = df_plot[
#             (df_plot["日期"] >= pd.Timestamp(start_date)) &
#             (df_plot["日期"] <= pd.Timestamp(end_date))
#             ].reset_index(drop=True)
#
#         # ============= 画图 =============
#         import plotly.graph_objects as go
#
#         fig = go.Figure()
#
#         # 1. 情绪分（左Y轴）
#         fig.add_trace(go.Scatter(
#             x=df_plot["日期"], y=df_plot["情绪分"],
#             name="情绪分", line=dict(color="#1f77b4", width=3),
#             mode="lines+markers+text", text=df_plot["情绪分"], textposition="top center"
#         ))
#
#         df_plot["最高板_真实"] = df_plot["最高板"].fillna(1).astype(int)
#
#
#         def calc_y(val):
#             if val <= 10:
#                 return val * 10
#             else:
#                 return 100
#
#
#         df_plot["最高板_缩放"] = df_plot["最高板_真实"].apply(calc_y)
#         df_plot["最高板_标签"] = df_plot["最高板_真实"].astype(str) + "板"
#
#         fig.add_trace(go.Scatter(
#             x=df_plot["日期"],
#             y=df_plot["最高板_缩放"],
#             name="最高板",
#             line=dict(color="#FF6B35", width=3),
#             mode="lines+markers+text",
#             text=df_plot["最高板_标签"],
#             textposition="top center",
#             textfont=dict(size=12, color="#FF6B35", weight="bold"),
#             marker=dict(size=8, color="#FF6B35", line=dict(width=1, color="white"))
#         ))
#
#         # ==================== 昨日首板家数（带 xx家 标注）====================
#         fig.add_trace(go.Scatter(
#             x=df_plot["日期"],
#             y=df_plot["昨日首板家数"],
#             name="昨日首板家数",
#             line=dict(color="#22c55e", width=2),
#             mode="lines+markers+text",
#             text=df_plot["昨日首板家数"].astype(str) + "家",
#             textposition="top center",
#             textfont=dict(size=11, color="#22c55e", weight="bold"),
#             marker=dict(size=6, color="#22c55e")
#         ))
#
#         # ==================== 昨日连板家数（带 xx家 标注）====================
#         fig.add_trace(go.Scatter(
#             x=df_plot["日期"],
#             y=df_plot["昨日连板家数"],
#             name="昨日连板家数",
#             line=dict(color="#f59e0b", width=2),
#             mode="lines+markers+text",
#             text=df_plot["昨日连板家数"].astype(str) + "家",
#             textposition="top center",
#             textfont=dict(size=11, color="#f59e0b", weight="bold"),
#             marker=dict(size=6, color="#f59e0b")
#         ))
#
#         # 2. 金叉死叉 连续线 + 颜色区分（右Y轴）
#         x_list = df_plot["日期"]
#         y_list = df_plot["天数"] * df_plot["类型"].map({"金叉": 1, "死叉": -1, "无": 0})
#         text_list = df_plot["显示文本"]
#         colors = ["#2E8B57" if t == "金叉" else "#DC143C" if t == "死叉" else "#888" for t in df_plot["类型"]]
#
#         fig.add_trace(go.Scatter(
#             x=x_list, y=y_list,
#             name="平均股价",
#             line=dict(color="#888", width=3),
#             mode="lines+markers+text",
#             text=text_list,
#             textposition="bottom center",
#             textfont=dict(color=colors, size=11, family="bold"),
#             marker=dict(color=colors, size=10, line=dict(width=1, color="white")),
#             yaxis="y2"
#         ))
#
#         # 3. 情绪线阈值
#         fig.add_hline(y=80, line_color="red", line_dash="dot", annotation_text="过热")
#         fig.add_hline(y=30, line_color="blue", line_dash="dot", annotation_text="冰点")
#
#         # 4. 双轴设置
#         fig.update_layout(
#             template="plotly_white", height=460,
#             yaxis=dict(title="情绪分 / 最高板×10 / 首板连板数量", range=[0, 120]),
#             yaxis2=dict(title="金叉(+) / 死叉(-)", overlaying="y", side="right", range=[-10, 10]),
#             legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
#         )
#
#         st.plotly_chart(fig, use_container_width=True)
#     st.divider()

st.markdown('<a id="大盘周期"></a>', unsafe_allow_html=True)
if not df.empty:
    with st.container(border=True):
        st.subheader("📊 大盘数据趋势")
        df_plot = df.copy()
        df_plot["日期"] = pd.to_datetime(df_plot["日期"])
        start_date, end_date = st.slider("数据时间范围", df_date_min, df_date_max, (min_date.date(), max_date.date()))
        df_plot = df_plot[(df_plot["日期"] >= pd.Timestamp(start_date)) & (df_plot["日期"] <= pd.Timestamp(end_date))]
        df_plot["日期"] = df_plot["日期"].dt.date

        # 这里增加了 tab4：首板 & 连板数
        tab1, tab2, tab3, tab4 = st.tabs(["💰 成交额", "🚥 涨跌停", "📈 涨跌家数", "🔥 首板/连板"])
        with tab1:
            fig = px.line(df_plot, x="日期", y="大盘成交额", markers=True, text="大盘成交额")
            fig.update_traces(textposition="top center")
            st.plotly_chart(fig, use_container_width=True)
        with tab2:
            fig = px.line(df_plot, x="日期", y=["涨停家数", "跌停家数"], markers=True, text="value")
            st.plotly_chart(fig, use_container_width=True)
        with tab3:
            fig = px.line(df_plot, x="日期", y=["上涨家数", "下跌家数"], markers=True, text="value")
            st.plotly_chart(fig, use_container_width=True)
        # 新增：首板数 + 连板数 趋势图
        with tab4:
            fig = px.line(df_plot, x="日期", y=["昨日首板家数", "昨日连板家数"],
                          markers=True, text="value")
            fig.update_layout(title="首板数 vs 连板数 趋势图")
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

st.markdown('<a id="统计分析"></a>', unsafe_allow_html=True)
if not df.empty:
    with st.container(border=True):
        st.subheader("📅 周/月 统计分析 + 多字段总和")

        # 日期处理
        df_stat = df.copy()
        df_stat["日期"] = pd.to_datetime(df_stat["日期"])
        df_stat["周"] = df_stat["日期"].dt.to_period("W").astype(str)
        df_stat["月"] = df_stat["日期"].dt.to_period("M").astype(str)

        # 统一提取数字函数（支持 + - .）
        import re


        def extract_num(s):
            try:
                nums = re.findall(r'[+-]?\d+\.?\d*', str(s))
                return sum(float(n) for n in nums)
            except:
                return 0.0


        # 提取所有需要统计的字段
        df_stat["竞价数值"] = df_stat["竞价"].apply(extract_num)
        df_stat["星星龙头数值"] = df_stat["星星龙头"].apply(extract_num)
        df_stat["和信个股数值"] = df_stat["和信个股"].apply(extract_num)
        df_stat["板块核心数值"] = df_stat["板块核心"].apply(extract_num)
        df_stat["波段先锋数值"] = df_stat["波段先锋"].apply(extract_num)

        # 选择周期
        period = st.radio("选择周期", ["按周统计", "按月统计"], horizontal=True)
        col = "周" if period == "按周统计" else "月"

        # 分组汇总
        agg_df = df_stat.groupby(col).agg(
            天数=("日期", "count"),
            竞价总和=("竞价数值", "sum"),
            星星龙头总和=("星星龙头数值", "sum"),
            和信个股总和=("和信个股数值", "sum"),
            板块核心总和=("板块核心数值", "sum"),
            波段先锋_均值=("波段先锋数值", "sum"),
            # 下跌家数_均值=("下跌家数", "mean"),
        ).reset_index()
        agg_df = agg_df.sort_values(col, ascending=False)

        # 计算胜率
        # agg_df["胜率"] = agg_df.apply(lambda row:
        #     f"{round(row['上涨家数_均值'] / (row['上涨家数_均值'] + row['下跌家数_均值']) * 100, 2)}%"
        #     if (row['上涨家数_均值'] + row['下跌家数_均值']) > 0 else "0%", axis=1)

        # 展示表格
        st.dataframe(agg_df, use_container_width=True)

        # 总汇总卡片
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

    st.divider()

# ====================== 历史数据表格 ======================
st.markdown('<a id="历史数据"></a>', unsafe_allow_html=True)
with st.container(border=True):
    # ====================== 4. 染色表格展示 + 分页 ======================
    st.subheader("📋 历史数据（智能染色）")
    if not df.empty:
        format_df = df.copy().sort_values("日期", ascending=False).reset_index(drop=True)
        format_df["大盘成交额"] = format_df["大盘成交额"].astype(int)

        # 整数字段
        int_fields = ["涨停家数", "跌停家数", "上涨家数", "下跌家数", "最高板", "昨日首板家数", "昨日连板家数"]
        for field in int_fields:
            format_df[field] = pd.to_numeric(format_df[field], errors="coerce").fillna(0).astype(int)

        # 浮点字段
        float_fields = ["中线上攻", "短线上攻"]
        for field in float_fields:
            format_df[field] = pd.to_numeric(format_df[field], errors="coerce").fillna(0)

        # ====================== 核心：4个字段自动对比上一条 ======================
        target_cols = ["昨日首板家数", "昨日连板家数", "中线上攻", "短线上攻"]

        for col in target_cols:
            # 计算差值（当前 - 上一条）
            diff = format_df[col] - format_df[col].shift(-1)
            # 生成箭头
            format_df[col] = format_df[col].astype(str)
            format_df.loc[diff > 0, col] += " ↑"
            format_df.loc[diff < 0, col] += " ↓"
            format_df.loc[diff == 0, col] += " —"


        # ====================== 原有染色逻辑 ======================
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

                # ====================== 箭头染色 ======================
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


        # 分页
        page_size = 15
        total_pages = (len(format_df) + page_size - 1) // page_size
        cols_pag = st.columns([1, 2, 1])
        with cols_pag[1]:
            page_num = st.number_input("页码", min_value=1, max_value=total_pages, value=1, step=1)
        start = (page_num - 1) * page_size
        end = start + page_size
        paginated_df = format_df.iloc[start:end].copy()

        # 染色
        styled_df = paginated_df.style.apply(color_row, axis=1)

        # 冻结样式
        styled_df = styled_df.set_table_styles([
            {'selector': 'thead th', 'props': [
                ('position', 'sticky'),
                ('top', '0'),
                ('z-index', '100'),
                ('background-color', '#4C6EF5'),
                ('color', 'white'),
                ('font-weight', 'bold'),
                ('text-align', 'center')
            ]},
            {'selector': 'tbody td:first-child', 'props': [
                ('position', 'sticky'),
                ('left', '0'),
                ('z-index', '50'),
                ('background-color', 'white'),
                ('border-right', '1px solid #ddd')
            ]},
            {'selector': 'thead th:first-child', 'props': [
                ('position', 'sticky'),
                ('top', '0'),
                ('left', '0'),
                ('z-index', '200')
            ]},
            {'selector': 'td', 'props': [
                ('text-align', 'center'),
                ('white-space', 'pre-wrap'),
                ('word-wrap', 'break-word'),
                ('max-width', '300px'),
                ('vertical-align', 'middle'),
                ('line-height', '1.4')
            ]},
        ])

        html = styled_df.to_html()
        st.html(f'''
            <div style="height:800px; overflow: auto;">
                {html}
            </div>
        ''')

    else:
        st.info("暂无数据")
# with st.container(border=True):
#     # ====================== 4. 染色表格展示 + 分页 ======================
#     st.subheader("📋 历史数据（智能染色）")
#     if not df.empty:
#         format_df = df.copy().sort_values("日期", ascending=False).reset_index(drop=True)
#         format_df["大盘成交额"] = format_df["大盘成交额"].astype(int)
#         int_fields = ["涨停家数", "跌停家数", "上涨家数", "下跌家数", "最高板"]
#         for field in int_fields:
#             format_df[field] = format_df[field].astype(int)
#
#
#         def color_row(row):
#             styles = []
#             for col in format_df.columns:
#                 if col == "平均股价_大盘":
#                     if "金叉" in str(row[col]):
#                         styles.append("background-color: #28a745; color: white; font-weight: bold")
#                     elif "死叉" in str(row[col]):
#                         styles.append("background-color: #dc3545; color: white; font-weight: bold")
#                     else:
#                         styles.append("")
#                 elif col == "上证指数":
#                     if "金叉" in str(row[col]):
#                         styles.append("background-color: #28a745; color: white; font-weight: bold")
#                     elif "死叉" in str(row[col]):
#                         styles.append("background-color: #dc3545; color: white; font-weight: bold")
#                     else:
#                         styles.append("")
#                 elif col == "流动资金":
#                     if "红" in str(row[col]):
#                         styles.append("background-color: #28a745; color: white; font-weight: bold")
#                     elif "绿" in str(row[col]):
#                         styles.append("background-color: #dc3545; color: white; font-weight: bold")
#                     else:
#                         styles.append("")
#                 elif col == "大盘成交额":
#                     try:
#                         v = int(row[col])
#                         if v > 20000:
#                             styles.append("background-color: #28a745; color: white; font-weight: bold")
#                         else:
#                             styles.append("background-color: #dc3545; color: white; font-weight: bold")
#                     except:
#                         styles.append("")
#                 elif col == "涨停家数":
#                     try:
#                         v = int(row[col])
#                         if v > 50:
#                             styles.append("background-color: #28a745; color: white; font-weight: bold")
#                         else:
#                             styles.append("background-color: #dc3545; color: white; font-weight: bold")
#                     except:
#                         styles.append("")
#                 elif col == "跌停家数":
#                     try:
#                         v = int(row[col])
#                         if v > 10:
#                             styles.append("background-color: #dc3545; color: white; font-weight: bold")
#                         else:
#                             styles.append("background-color: #28a745; color: white; font-weight: bold")
#                     except:
#                         styles.append("")
#                 elif col == "上涨家数":
#                     try:
#                         v = int(row[col])
#                         if v > 2500:
#                             styles.append("background-color: #28a745; color: white; font-weight: bold")
#                         else:
#                             styles.append("background-color: #dc3545; color: white; font-weight: bold")
#                     except:
#                         styles.append("")
#                 elif col == "下跌家数":
#                     try:
#                         v = int(row[col])
#                         if v > 2500:
#                             styles.append("background-color: #dc3545; color: white; font-weight: bold")
#                         else:
#                             styles.append("background-color: #28a745; color: white; font-weight: bold")
#                     except:
#                         styles.append("")
#                 elif col == "最高板":
#                     try:
#                         v = int(row[col])
#                         if v > 5:
#                             styles.append("background-color: #28a745; color: white; font-weight: bold")
#                         else:
#                             styles.append("background-color: #dc3545; color: white; font-weight: bold")
#                     except:
#                         styles.append("")
#                 else:
#                     styles.append("")
#             return styles
#
#
#         # 分页控制
#         page_size = 15
#         total_pages = (len(format_df) + page_size - 1) // page_size
#         cols_pag = st.columns([1, 2, 1])
#         with cols_pag[1]:
#             page_num = st.number_input("页码", min_value=1, max_value=total_pages, value=1, step=1)
#         start = (page_num - 1) * page_size
#         end = start + page_size
#         paginated_df = format_df.iloc[start:end].copy()
#
#         # 染色
#         styled_df = paginated_df.style.apply(color_row, axis=1)
#
#         # 冻结：表头 + 第一列
#         styled_df = styled_df.set_table_styles([
#             {'selector': 'thead th', 'props': [
#                 ('position', 'sticky'),
#                 ('top', '0'),
#                 ('z-index', '100'),
#                 ('background-color', '#4C6EF5'),
#                 ('color', 'white'),
#                 ('font-weight', 'bold'),
#                 ('text-align', 'center')
#             ]},
#             {'selector': 'tbody td:first-child', 'props': [
#                 ('position', 'sticky'),
#                 ('left', '0'),
#                 ('z-index', '50'),
#                 ('background-color', 'white'),
#                 ('border-right', '1px solid #ddd')
#             ]},
#             {'selector': 'thead th:first-child', 'props': [
#                 ('position', 'sticky'),
#                 ('top', '0'),
#                 ('left', '0'),
#                 ('z-index', '200')
#             ]},
#             {'selector': 'td', 'props': [
#                 ('text-align', 'center'),
#                 ('white-space', 'pre-wrap'),
#                 ('word-wrap', 'break-word'),
#                 ('max-width', '300px'),
#                 ('vertical-align', 'middle'),
#                 ('line-height', '1.4')
#             ]},
#         ])
#
#         html = styled_df.to_html()
#         st.html(f'''
#             <div style="height:800px; overflow: auto;">
#                 {html}
#             </div>
#         ''')
#
#     else:
#         st.info("暂无数据")

# ------------------- 你的原有录入代码 + 新增OCR图片识别 -------------------

if show_add:
    with st.sidebar:
        with st.container(border=True):
            st.subheader("📥 数据录入")
            with st.form("add_form"):
                input_date = st.date_input("日期")

                # 平均股价（带天数）
                ap_type = st.selectbox("平均股价", ["金叉", "死叉"])
                ap_day = st.number_input("平均股价天数", 0, 30, 0)
                avg_price_dapan = f"{ap_type}{ap_day}日"

                # 上证指数（带天数）
                sh_type = st.selectbox("上证指数", ["金叉", "死叉"])
                sh_day = st.number_input("上证指数天数", 0, 30, 0)
                sh_index = f"{sh_type}{sh_day}日"

                # 其他字段保持不变
                liq = st.selectbox("流动资金", ["翻红", "翻绿"])
                vol = st.number_input("大盘成交额", 0, 9999999, value=0)
                lu = st.number_input("涨停家数", 0, 999, 0)
                ld = st.number_input("跌停家数", 0, 999, 0)
                up = st.number_input("上涨家数", 0, 9999, 0)
                dn = st.number_input("下跌家数", 0, 9999, 0)
                mb = st.number_input("最高板", 0, 20, 0)
                # ==================== 新增字段 ====================
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
                        data = (
                            input_date, avg_price_dapan, sh_index, liq, vol,
                            lu, ld, up, dn, mb, idx, auc, star, hexin, sector, band_pioneer, first_plate_yesterday,
                            con_plate_yesterday,  # 存入波段先锋
                             mid_line_attack, short_line_attack  # 这里补上两个新字段
                        )
                        if insert_data(data):
                            st.success("保存成功")
                            st.rerun()

# ====================== ✏️ 侧边栏控制：修改数据 ======================
if show_edit:
    with st.sidebar:
        with st.container(border=True):
            st.subheader("✏️ 修改数据（ID自动填充原内容）")
            # ===================== 🔥 核心：自动获取最新ID =====================
            max_id = 1
            if not df.empty:
                max_id = int(df["id"].max())  # 取最大ID = 最新数据

            # 默认值 = 最新ID，而不是1！
            edit_id = st.number_input("请输入要修改的数据ID", 1, 9999, step=1, value=max_id)

            # 自动加载该ID的原有数据
            load_data = None
            if not df.empty and edit_id in df["id"].values:
                load_data = df[df["id"] == edit_id].iloc[0]

            # 字段映射
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
                "板块核心": "sector_core",
                "波段先锋": "band_pioneer",
                "昨日首板家数": "first_plate_yesterday",
                "昨日连板家数": "con_plate_yesterday",
                "短线上攻":"short_line_attack",
                "中线上攻":"mid_line_attack"

            }
            selected_field_cn = st.selectbox("选择要修改的字段", list(field_map.keys()))
            field_en = field_map[selected_field_cn]

            # 自动填充原有值
            default_value = ""
            if load_data is not None:
                default_value = str(load_data[selected_field_cn])

            # 输入框（自动带原来的值）
            new_value = st.text_area("输入新内容（已自动加载原值）", value=default_value)

            if st.button("✅ 确认修改"):
                # 数字类型字段校验
                num_fields = ["market_volume", "limit_up", "limit_down", "rise_count", "fall_count", "max_board"]
                if field_en in num_fields:
                    try:
                        new_value = int(new_value)
                    except:
                        st.error("❌ 该字段必须输入数字！")
                        st.stop()

                if update_single_field(edit_id, field_en, new_value):
                    st.success(f"✅ ID {edit_id} 修改成功！")
                    st.rerun()

# ====================== 🗑️ 侧边栏控制：删除 ======================
if show_delete:
    with st.sidebar:
        with st.container(border=True):
            st.subheader("🗑️ 删除数据")
            # ===================== 🔥 核心：自动获取最新ID =====================
            max_id = 1
            if not df.empty:
                max_id = int(df["id"].max())  # 取最大ID = 最新数据

            del_id = st.number_input("删除ID", 1, 9999, step=1, value=max_id)
            # 🔥 二次确认开关
            confirm_delete = st.checkbox("✅ 我确认要删除此数据（不可恢复）", value=False)

            # 删除按钮
            if st.button("🗑️ 确认删除", type="primary"):
                # 必须勾选确认才能删
                if not confirm_delete:
                    st.warning("⚠️ 请先勾选确认删除！")
                    st.stop()

                # 执行删除
                if delete_by_id(del_id, df):
                    st.success(f"✅ ID {del_id} 删除成功！")
                    # st.rerun()

                else:
                    st.error("❌ 删除失败，ID不存在")

# ===================== 【Streamlit 全版本通用】悬浮置顶/置底 =====================
st.markdown("""
<style>
.scroll-btn:hover { background-color: #0F4CD0; }
/* 按钮整体容器 */
.scroll-buttons {
    position: fixed;
    right: 20px;
    bottom: 20px;
    z-index: 999999;
    display: flex;
    flex-direction: column;
    gap: 10px;
}
/* 按钮样式 */
.scroll-btn {
    width: 50px;
    height: 50px;
    border-radius: 50%;
    background-color: #165DFF;
    color: white !important;
    font-size: 22px;
    font-weight: bold;
    border: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    text-decoration: none !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
</style>

<div class="scroll-buttons">
    <!-- 利用 HTML 锚点实现跳转 -->
    <a href="#top" class="scroll-btn">↑</a>
    <a href="#bottom" class="scroll-btn">↓</a>
</div>
""", unsafe_allow_html=True)

# 2. 底部锚点 —— 放在你页面【最最最底端】
st.markdown('<div id="bottom"></div>', unsafe_allow_html=True)
