import streamlit as st
import pandas as pd
import plotly.express as px
import requests

st.set_page_config(page_title="projectADYgroup4", layout="wide")
st.title("🇲🇾 projectADYgroup4")
st.caption("Price & Inflation Analytics Dashboard")

BASE_URL = "https://api.data.gov.my/data-catalogue"

@st.cache_data(ttl=3600)
def fetch(dataset_id, limit=5000):
    try:
        params = {"id": dataset_id, "limit": limit}
        r = requests.get(BASE_URL, params=params, timeout=30)
        r.raise_for_status()
        return pd.DataFrame(r.json())
    except Exception as e:
        st.error(f"Lỗi tải dữ liệu `{dataset_id}`: {e}")
        return None

with st.sidebar:
    st.header("⚙️ Nguồn Dữ Liệu")
    st.markdown("**API:** [OpenDOSM](https://api.data.gov.my)")
    st.markdown("**Datasets:** CPI Headline, CPI by State, HIES")
    if st.button("🔄 Làm mới dữ liệu (Refresh)"):
        st.cache_data.clear()
        st.rerun()
    st.markdown("---")
    st.caption("Dữ liệu từ Cục Thống kê Malaysia (DOSM)")

with st.spinner("📡 Đang tải trực tiếp dữ liệu từ OpenDOSM..."):
    df_cpi   = fetch("cpi_headline", limit=5000)
    df_state = fetch("cpi_state", limit=5000)
    df_hies  = fetch("hies_state", limit=2000)

if df_cpi is not None and not df_cpi.empty:
    df_cpi['date'] = pd.to_datetime(df_cpi['date'])
    df_cpi = df_cpi.sort_values('date')
    df_overall = df_cpi[df_cpi['division'] == 'overall'].copy()
    df_overall['inflation_yoy'] = df_overall['index'].pct_change(12) * 100
else:
    df_overall = pd.DataFrame()

tab1, tab2, tab3 = st.tabs(["📈 CPI & Lạm phát Quốc gia", "🏷️ Phân tích theo Nhóm hàng", "🗺️ So sánh theo Bang"])

with tab1:
    st.subheader("Chỉ số CPI & Tỷ lệ lạm phát (National)")
    if not df_overall.empty:
        valid_infl = df_overall.dropna(subset=['inflation_yoy'])
        if not valid_infl.empty:
            col1, col2, col3 = st.columns(3)
            latest = valid_infl.iloc[-1]
            prev   = valid_infl.iloc[-2] if len(valid_infl) > 1 else latest
            col1.metric("Chỉ số CPI gần nhất", f"{latest['index']:.1f}")
            col1.caption(f"Thời điểm: {latest['date'].strftime('%m/%Y')}")
            diff = latest['inflation_yoy'] - prev['inflation_yoy']
            col2.metric("Lạm phát YoY", f"{latest['inflation_yoy']:.2f}%", delta=f"{diff:.2f}%")
            col3.metric("Tổng số bản ghi", f"{len(df_cpi):,}")

        c1, c2 = st.columns(2)
        with c1:
            fig = px.line(df_overall, x='date', y='index',
                          title='Chỉ số CPI qua các năm (1980 - nay)',
                          labels={'index': 'Chỉ số CPI', 'date': 'Năm'})
            fig.update_layout(template='plotly_dark')
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig2 = px.line(valid_infl, x='date', y='inflation_yoy',
                           title='Tỷ lệ Lạm phát theo năm YoY (%)',
                           labels={'inflation_yoy': 'Lạm phát (%)', 'date': 'Năm'},
                           color_discrete_sequence=['#FF4B4B'])
            fig2.add_hline(y=0, line_dash='dash', line_color='gray')
            fig2.update_layout(template='plotly_dark')
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.error("Chưa tải được dữ liệu CPI từ OpenDOSM API.")

with tab2:
    st.subheader("Chỉ số CPI theo từng nhóm mặt hàng (Division)")
    if df_cpi is not None and not df_cpi.empty:
        divisions = sorted(df_cpi['division'].unique().tolist())
        default_div = [d for d in ['overall', 'food', 'housing', 'transport'] if d in divisions]
        selected = st.multiselect("Chọn nhóm mặt hàng:", divisions, default=default_div if default_div else divisions[:3])

        if selected:
            filtered = df_cpi[df_cpi['division'].isin(selected)].copy()
            filtered['date'] = pd.to_datetime(filtered['date'])

            fig3 = px.line(filtered, x='date', y='index', color='division',
                           title='Xu hướng giá theo nhóm hàng hóa',
                           labels={'index': 'Chỉ số CPI', 'division': 'Nhóm hàng'})
            fig3.update_layout(template='plotly_dark')
            st.plotly_chart(fig3, use_container_width=True)

            latest_div = filtered.groupby('division').last().reset_index()
            fig4 = px.bar(latest_div.sort_values('index', ascending=False),
                          x='division', y='index', color='division',
                          title='Mức CPI hiện tại của từng nhóm hàng',
                          labels={'index': 'Chỉ số CPI', 'division': 'Nhóm hàng'})
            fig4.update_layout(template='plotly_dark', showlegend=False)
            st.plotly_chart(fig4, use_container_width=True)

with tab3:
    st.subheader("Chỉ số CPI và Thu nhập theo Bang (State)")
    if df_state is not None and not df_state.empty:
        df_state['date'] = pd.to_datetime(df_state['date'])
        state_col = next((c for c in df_state.columns if c.lower() == 'state'), None)
        idx_col   = next((c for c in df_state.columns if 'index' in c.lower() or 'cpi' in c.lower()), None)

        if state_col and idx_col:
            states = sorted(df_state[state_col].unique().tolist())
            sel_states = st.multiselect("Chọn các bang muốn so sánh:", states, default=states[:5])
            if sel_states:
                df_s = df_state[df_state[state_col].isin(sel_states)]
                fig5 = px.line(df_s, x='date', y=idx_col, color=state_col,
                               title='So sánh biến động giá giữa các bang',
                               labels={idx_col: 'Chỉ số CPI', state_col: 'Bang'})
                fig5.update_layout(template='plotly_dark')
                st.plotly_chart(fig5, use_container_width=True)
        else:
            st.dataframe(df_state.head(30))

    if df_hies is not None and not df_hies.empty:
        st.divider()
        st.subheader("Thu nhập hộ gia đình theo Bang (HIES)")
        st.dataframe(df_hies.head(20))
