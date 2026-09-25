import sqlite3
import os
import requests
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "opendosm.db")
BASE_URL = "https://api.data.gov.my/data-catalogue"

def get_connection():
    """Tạo kết nối tới SQLite Database."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_database():
    """Khởi tạo Schema cơ sở dữ liệu và tải dữ liệu từ OpenDOSM nếu chưa có."""
    conn = get_connection()
    cursor = conn.cursor()

    # Kiểm tra xem dữ liệu đã tồn tại trong database chưa
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fact_cpi_headline'")
    table_exists = cursor.fetchone()

    if not table_exists:
        print("Đang khởi tạo Database và nạp dữ liệu từ OpenDOSM API...")
        try:
            # 1. Fetch CPI Headline
            r_cpi = requests.get(BASE_URL, params={"id": "cpi_headline", "limit": 10000}, timeout=30)
            df_cpi = pd.DataFrame(r_cpi.json())
            df_cpi['date'] = pd.to_datetime(df_cpi['date']).dt.strftime('%Y-%m-%d')
            df_cpi.to_sql('fact_cpi_headline', conn, if_exists='replace', index=False)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cpi_date ON fact_cpi_headline(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cpi_division ON fact_cpi_headline(division)")

            # 2. Fetch CPI State
            r_state = requests.get(BASE_URL, params={"id": "cpi_state", "limit": 10000}, timeout=30)
            df_state = pd.DataFrame(r_state.json())
            df_state['date'] = pd.to_datetime(df_state['date']).dt.strftime('%Y-%m-%d')
            df_state.to_sql('fact_cpi_state', conn, if_exists='replace', index=False)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_state_date ON fact_cpi_state(date)")

            # 3. Fetch HIES State (Household Income)
            r_hies = requests.get(BASE_URL, params={"id": "hies_state", "limit": 2000}, timeout=30)
            df_hies = pd.DataFrame(r_hies.json())
            if 'date' in df_hies.columns:
                df_hies['date'] = pd.to_datetime(df_hies['date']).dt.strftime('%Y-%m-%d')
            df_hies.to_sql('dim_hies_state', conn, if_exists='replace', index=False)

            conn.commit()
            print("Khởi tạo Database thành công!")
        except Exception as e:
            print(f"Lỗi khởi tạo Database: {e}")
    conn.close()

# Các câu truy vấn SQL chuẩn phục vụ bài toán phân tích

def query_cpi_and_inflation():
    """
    Truy vấn SQL sử dụng Window Function LAG() để tính tỷ lệ lạm phát YoY (Year-over-Year).
    """
    sql = """
    WITH cpi_lagged AS (
        SELECT 
            date,
            division,
            "index" AS cpi_index,
            LAG("index", 12) OVER (PARTITION BY division ORDER BY date ASC) AS cpi_12m_ago
        FROM fact_cpi_headline
        WHERE division = 'overall'
    )
    SELECT 
        date,
        cpi_index,
        ROUND(((cpi_index - cpi_12m_ago) / cpi_12m_ago) * 100.0, 2) AS inflation_yoy
    FROM cpi_lagged
    ORDER BY date ASC;
    """
    conn = get_connection()
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df, sql

def query_cpi_by_divisions(divisions):
    """
    Truy vấn SQL lọc theo nhóm hàng hoá (division).
    """
    placeholders = ','.join(['?'] * len(divisions))
    sql = f"""
    SELECT 
        date,
        division,
        "index" AS cpi_index
    FROM fact_cpi_headline
    WHERE division IN ({placeholders})
    ORDER BY date ASC;
    """
    conn = get_connection()
    df = pd.read_sql_query(sql, conn, params=divisions)
    conn.close()
    return df, sql

def query_cpi_by_states(states):
    """
    Truy vấn SQL lọc CPI theo các bang được chọn.
    """
    placeholders = ','.join(['?'] * len(states))
    sql = f"""
    SELECT 
        date,
        state,
        "index" AS cpi_index
    FROM fact_cpi_state
    WHERE state IN ({placeholders}) AND division = 'overall'
    ORDER BY state, date ASC;
    """
    conn = get_connection()
    df = pd.read_sql_query(sql, conn, params=states)
    conn.close()
    return df, sql

def query_state_cpi_joined_income():
    """
    Truy vấn SQL JOIN giữa bảng fact_cpi_state và dim_hies_state
    để phân tích mối tương quan giữa mức giá CPI trung bình gần đây và thu nhập trung bình của bang.
    """
    sql = """
    WITH latest_cpi AS (
        SELECT 
            state,
            ROUND(AVG("index"), 2) AS avg_cpi_recent
        FROM fact_cpi_state
        WHERE date >= '2023-01-01' AND division = 'overall'
        GROUP BY state
    ),
    latest_income AS (
        SELECT 
            state,
            income_mean,
            income_median
        FROM dim_hies_state
        GROUP BY state
        HAVING MAX(date)
    )
    SELECT 
        c.state,
        c.avg_cpi_recent,
        i.income_mean,
        i.income_median
    FROM latest_cpi c
    INNER JOIN latest_income i ON LOWER(c.state) = LOWER(i.state)
    ORDER BY c.avg_cpi_recent DESC;
    """
    conn = get_connection()
    try:
        df = pd.read_sql_query(sql, conn)
    except Exception:
        # Fallback query if columns differ
        sql = "SELECT * FROM fact_cpi_state LIMIT 50;"
        df = pd.read_sql_query(sql, conn)
    conn.close()
    return df, sql

def run_custom_sql(sql):
    """Thực thi câu lệnh SQL tuỳ ý và trả về DataFrame."""
    conn = get_connection()
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df
