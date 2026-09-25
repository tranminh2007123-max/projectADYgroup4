# 🇲🇾 projectADYgroup4 — Price & Inflation Analytics Dashboard

Dự án Phân tích Dữ liệu Giá cả & Lạm phát tại Malaysia sử dụng dữ liệu mở từ **OpenDOSM** (Department of Statistics Malaysia), kết hợp **Python** và **SQL (SQLite)**.

---

## 🏗️ Kiến trúc Hệ thống (Data Architecture & ETL)

```
OpenDOSM API (Public Data)
         │
         ▼ (Extract)
    Python Script
         │
         ▼ (Load)
SQLite Database (`data/opendosm.db`)
    ├── fact_cpi_headline (Chỉ số CPI theo nhóm hàng)
    ├── fact_cpi_state    (Chỉ số CPI theo 16 bang)
    └── dim_hies_state    (Thu nhập & chi tiêu hộ gia đình)
         │
         ▼ (SQL Transform & Analytics)
SQL Queries (Window Functions, Aggregation, INNER JOIN)
         │
         ▼
Streamlit Interactive Dashboard (`app.py`)
```

---

## 🗄️ Thiết kế Cơ sở dữ liệu (Database Schema)

1. **`fact_cpi_headline`**:
   - `date` (TEXT): Thời gian theo tháng (YYYY-MM-DD).
   - `division` (TEXT): Nhóm hàng hoá (overall, food, transport, housing,...).
   - `index` (REAL): Điểm chỉ số giá tiêu dùng CPI.

2. **`fact_cpi_state`**:
   - `date` (TEXT): Thời gian.
   - `state` (TEXT): Tên 16 bang tại Malaysia (Johor, Selangor, KL,...).
   - `index` (REAL): Chỉ số CPI riêng từng bang.

3. **`dim_hies_state`**:
   - `state` (TEXT): Tên bang.
   - `income_mean` (REAL): Thu nhập trung bình hộ gia đình (MYR).
   - `income_median` (REAL): Thu nhập trung vị (MYR).

---

## ⚡ Các kỹ thuật SQL nâng cao được áp dụng

### 1. SQL Window Function (`LAG()`) tính Lạm phát YoY:
```sql
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
```

### 2. SQL INNER JOIN giữa Chỉ số Giá và Thu nhập:
```sql
SELECT 
    c.state,
    ROUND(AVG(c."index"), 2) AS avg_cpi_recent,
    i.income_mean,
    i.income_median
FROM fact_cpi_state c
INNER JOIN dim_hies_state i ON LOWER(c.state) = LOWER(i.state)
WHERE c.date >= '2023-01-01'
GROUP BY c.state, i.income_mean, i.income_median
ORDER BY avg_cpi_recent DESC;
```

---

## 🚀 Hướng dẫn Cài đặt & Khởi chạy

1. Cài đặt các thư viện cần thiết:
   ```bash
   pip install streamlit pandas plotly requests
   ```

2. Khởi chạy Dashboard:
   ```bash
   streamlit run app.py
   ```
   *Hệ thống sẽ tự động tạo cơ sở dữ liệu `data/opendosm.db`, nạp dữ liệu và mở giao diện Web tại `http://localhost:8501`.*
