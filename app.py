import streamlit as st
import pandas as pd
import plotly.express as px
import os
import sys

# Thêm thư mục hiện tại vào sys.path để import module src.database
sys.path.append(os.path.dirname(__file__))
from src.database import (
    init_database,
    get_connection,
    query_cpi_and_inflation,
    query_cpi_by_divisions,
    query_cpi_by_states,
    query_state_cpi_joined_income,
    run_custom_sql
)

st.set_page_config(
    page_title="projectADYgroup4",
    page_icon="🇲🇾",
    layout="wide"
)

st.title("🇲🇾 projectADYgroup4")
st.caption("Hệ thống Phân tích Giá cả & Lạm phát Malaysia (Sử dụng Python & SQL trên dữ liệu OpenDOSM)")

# ── Khởi tạo Cơ sở dữ liệu SQLite ─────────────────────────────────────────────
with st.spinner("⏳ Đang kết nối SQLite Database & đồng bộ dữ liệu từ OpenDOSM..."):
    init_database()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("🗄️ Cấu hình Hệ thống & SQL")
    st.markdown("**Cơ sở dữ liệu:** SQLite (`opendosm.db`)")
    st.markdown("**Kiến trúc:** ETL (Extract API -> Load SQLite -> SQL Analytics)")
    
    st.markdown("---")
    st.subheader("Bảng dữ liệu trong SQL:")
    st.code("""
• fact_cpi_headline
• fact_cpi_state
• dim_hies_state
    """, language="text")

    st.markdown("---")
    if st.button("🔄 Đồng bộ lại dữ liệu (Re-sync)"):
        st.cache_data.clear()
        st.rerun()

    st.caption("Dữ liệu nguồn: OpenDOSM - Cục Thống kê Malaysia")

# ── TABS CHÍNH ────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 CPI & Lạm phát (SQL Window Function)",
    "🏷️ Phân tích Nhóm hàng (SQL Filter)",
    "🗺️ Phân tích Bang & Thu nhập (SQL JOIN)",
    "💻 SQL Console & Schema"
])

# ── TAB 1: CPI & Lạm phát Quốc gia (Sử dụng SQL Window Function LAG) ───────────
with tab1:
    st.subheader("1. Phân tích Xu hướng CPI và Lạm phát YoY (Year-over-Year)")
    
    df_infl, sql_infl = query_cpi_and_inflation()
    
    with st.expander("🔍 Xem câu lệnh SQL tính Lạm phát (Window Function LAG)"):
        st.code(sql_infl, language="sql")
        st.info("💡 Điểm nổi bật: Sử dụng `LAG(\"index\", 12) OVER (PARTITION BY division ORDER BY date)` để tự động tính tỷ lệ % thay đổi giá so với cùng kỳ năm trước trực tiếp từ SQL.")

    if not df_infl.empty:
        df_infl['date'] = pd.to_datetime(df_infl['date'])
        valid_infl = df_infl.dropna(subset=['inflation_yoy'])

        col1, col2, col3 = st.columns(3)
        latest = valid_infl.iloc[-1]
        prev   = valid_infl.iloc[-2] if len(valid_infl) > 1 else latest
        diff   = latest['inflation_yoy'] - prev['inflation_yoy']

        col1.metric("Chỉ số CPI gần nhất", f"{latest['cpi_index']:.1f}")
        col1.caption(f"Thời điểm: {latest['date'].strftime('%m/%Y')}")
        col2.metric("Lạm phát YoY gần nhất", f"{latest['inflation_yoy']:.2f}%", delta=f"{diff:.2f}%")
        col3.metric("Tổng bản ghi CPI đã phân tích", f"{len(df_infl):,}")

        c1, c2 = st.columns(2)
        with c1:
            fig1 = px.line(df_infl, x='date', y='cpi_index',
                           title='Chỉ số CPI Quốc gia qua các năm (1980 - nay)',
                           labels={'cpi_index': 'Chỉ số CPI', 'date': 'Năm'})
            fig1.update_layout(template='plotly_dark')
            st.plotly_chart(fig1, use_container_width=True)

        with c2:
            fig2 = px.line(valid_infl, x='date', y='inflation_yoy',
                           title='Tỷ lệ Lạm phát hàng năm YoY (%)',
                           labels={'inflation_yoy': 'Lạm phát (%)', 'date': 'Năm'},
                           color_discrete_sequence=['#FF4B4B'])
            fig2.add_hline(y=0, line_dash='dash', line_color='gray')
            fig2.update_layout(template='plotly_dark')
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.error("Chưa có dữ liệu từ Database.")

# ── TAB 2: Phân tích theo nhóm mặt hàng ────────────────────────────────────────
with tab2:
    st.subheader("2. Biến động giá theo từng Nhóm Hàng hóa (Division)")
    
    # Lấy danh sách các nhóm hàng từ SQL
    conn = get_connection()
    divisions_all = [r[0] for r in conn.execute("SELECT DISTINCT division FROM fact_cpi_headline ORDER BY division").fetchall()]
    conn.close()

    default_sel = [d for d in ['overall', 'food', 'housing', 'transport'] if d in divisions_all]
    selected_div = st.multiselect("Chọn các nhóm hàng hoá muốn phân tích:", divisions_all, default=default_sel if default_sel else divisions_all[:4])

    if selected_div:
        df_div, sql_div = query_cpi_by_divisions(selected_div)
        df_div['date'] = pd.to_datetime(df_div['date'])

        with st.expander("🔍 Xem câu lệnh SQL lọc dữ liệu theo nhóm hàng"):
            st.code(sql_div, language="sql")

        c1, c2 = st.columns([2, 1])
        with c1:
            fig3 = px.line(df_div, x='date', y='cpi_index', color='division',
                           title='Chỉ số CPI theo nhóm mặt hàng theo thời gian',
                           labels={'cpi_index': 'Chỉ số CPI', 'division': 'Nhóm hàng'})
            fig3.update_layout(template='plotly_dark')
            st.plotly_chart(fig3, use_container_width=True)
        with c2:
            latest_div = df_div.groupby('division').last().reset_index()
            fig4 = px.bar(latest_div.sort_values('cpi_index', ascending=False),
                          x='division', y='cpi_index', color='division',
                          title='Mức CPI hiện tại của các nhóm đã chọn',
                          labels={'cpi_index': 'CPI hiện tại', 'division': 'Nhóm hàng'})
            fig4.update_layout(template='plotly_dark', showlegend=False)
            st.plotly_chart(fig4, use_container_width=True)

# ── TAB 3: So sánh Bang & Thu nhập (SQL JOIN) ─────────────────────────────────
with tab3:
    st.subheader("3. So sánh CPI giữa các Bang và Mối quan hệ với Thu nhập")

    # 1. So sánh xu hướng CPI theo bang
    conn = get_connection()
    states_all = [r[0] for r in conn.execute("SELECT DISTINCT state FROM fact_cpi_state ORDER BY state").fetchall()]
    conn.close()

    selected_states = st.multiselect("Chọn các bang muốn so sánh CPI:", states_all, default=states_all[:5] if len(states_all) >= 5 else states_all)
    if selected_states:
        df_states, sql_states = query_cpi_by_states(selected_states)
        df_states['date'] = pd.to_datetime(df_states['date'])
        
        fig5 = px.line(df_states, x='date', y='cpi_index', color='state',
                       title='Xu hướng CPI qua các bang',
                       labels={'cpi_index': 'Chỉ số CPI', 'state': 'Bang'})
        fig5.update_layout(template='plotly_dark')
        st.plotly_chart(fig5, use_container_width=True)

    st.divider()
    st.subheader("📊 Phân tích Tương quan CPI vs. Thu nhập bình quân (SQL JOIN)")
    df_join, sql_join = query_state_cpi_joined_income()

    with st.expander("🔍 Xem câu lệnh SQL JOIN 2 bảng (fact_cpi_state & dim_hies_state)"):
        st.code(sql_join, language="sql")
        st.info("💡 Kỹ thuật: INNER JOIN bảng chỉ số giá `fact_cpi_state` với bảng khảo sát thu nhập hộ gia đình `dim_hies_state` thông qua khóa chung `state`.")

    if not df_join.empty and 'avg_cpi_recent' in df_join.columns and 'income_mean' in df_join.columns:
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Bảng kết quả sau khi SQL JOIN:**")
            st.dataframe(df_join, use_container_width=True)
        with c2:
            fig6 = px.scatter(df_join, x='income_mean', y='avg_cpi_recent', text='state',
                              size='income_mean', color='state',
                              title='Tương quan giữa Thu nhập trung bình và Mức giá (CPI)',
                              labels={'income_mean': 'Thu nhập bình quân (MYR)', 'avg_cpi_recent': 'CPI trung bình gần đây'})
            fig6.update_traces(textposition='top center')
            fig6.update_layout(template='plotly_dark', showlegend=False)
            st.plotly_chart(fig6, use_container_width=True)
    else:
        st.dataframe(df_join)

# ── TAB 4: SQL CONSOLE & SCHEMA (Trực quan hóa SQL cho Thầy cô) ───────────────
with tab4:
    st.subheader("4. Trung tâm Quản trị SQL (Database Schema & SQL Playground)")
    st.markdown("Tab này dành riêng cho việc trình bày và kiểm tra cấu trúc cơ sở dữ liệu và các câu lệnh SQL trong đề tài.")

    col_schema, col_play = st.columns([1, 1])

    with col_schema:
        st.markdown("### 🗂️ Sơ đồ Thực thể (Database Schema)")
        st.code("""
TABLE fact_cpi_headline (
    date TEXT,
    division TEXT,
    "index" REAL
);

TABLE fact_cpi_state (
    date TEXT,
    state TEXT,
    "index" REAL
);

TABLE dim_hies_state (
    date TEXT,
    state TEXT,
    income_mean REAL,
    income_median REAL,
    expenditure_mean REAL
);
        """, language="sql")
        
        st.markdown("### 📌 Bảng thống kê số dòng (Row Counts)")
        conn = get_connection()
        counts = {
            "fact_cpi_headline": conn.execute("SELECT COUNT(*) FROM fact_cpi_headline").fetchone()[0],
            "fact_cpi_state": conn.execute("SELECT COUNT(*) FROM fact_cpi_state").fetchone()[0],
            "dim_hies_state": conn.execute("SELECT COUNT(*) FROM dim_hies_state").fetchone()[0]
        }
        conn.close()
        st.table(pd.DataFrame(list(counts.items()), columns=["Tên Bảng", "Số lượng bản ghi"]))

    with col_play:
        st.markdown("### ⚡ Trình thực thi SQL (SQL Query Editor)")
        st.write("Gõ hoặc chọn câu lệnh SQL bất kỳ để chạy trực tiếp trên cơ sở dữ liệu:")
        
        sample_query = st.selectbox(
            "Gợi ý câu lệnh mẫu:",
            [
                "SELECT * FROM fact_cpi_headline WHERE division = 'overall' ORDER BY date DESC LIMIT 10;",
                "SELECT division, ROUND(AVG(\"index\"), 2) AS avg_cpi FROM fact_cpi_headline GROUP BY division ORDER BY avg_cpi DESC;",
                "SELECT state, ROUND(AVG(\"index\"), 2) AS avg_cpi_2023 FROM fact_cpi_state WHERE date >= '2023-01-01' GROUP BY state ORDER BY avg_cpi_2023 DESC;",
                "SELECT c.state, c.\"index\" AS cpi, h.income_mean FROM fact_cpi_state c JOIN dim_hies_state h ON c.state = h.state LIMIT 15;"
            ]
        )
        
        user_sql = st.text_area("Câu lệnh SQL muốn thực thi:", value=sample_query, height=120)
        
        if st.button("🚀 Chạy câu lệnh SQL"):
            try:
                result_df = run_custom_sql(user_sql)
                st.success(f"Truy vấn thành công! Trả về {len(result_df)} dòng kết quả:")
                st.dataframe(result_df, use_container_width=True)
            except Exception as e:
                st.error(f"Lỗi SQL: {e}")
