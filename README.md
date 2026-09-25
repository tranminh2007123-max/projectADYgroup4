# OpenDOSM Price & Inflation Analytics Dashboard

This project demonstrates how to use data from [OpenDOSM](https://open.dosm.gov.my/) to build a dashboard.

## Project Structure
- `data/`: Contains raw and processed Parquet/CSV files.
- `src/`: Python scripts for fetching and cleaning data.
- `app.py`: Streamlit dashboard.

## Setup Instructions
1. Install dependencies: `pip install -r requirements.txt`
2. Fetch data: `python src/fetch_data.py`
3. Preprocess data: `python src/preprocess.py`
4. Run the dashboard: `streamlit run app.py`

## Data Sources
- CPI Headline & State: Consumer Price Index to track inflation.
- HIES State: Household Income data.
