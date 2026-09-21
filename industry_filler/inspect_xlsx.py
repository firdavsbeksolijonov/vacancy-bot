
import pandas as pd
path = __import__("pathlib").Path(__file__).resolve().parent / "tashkent_hh_companies_clean.xlsx"
try:
    df = pd.read_excel(path)
    print("COLUMNS:", df.columns.tolist())
    print("FIRST 10 ROWS:")
    print(df.head(10).to_string())
except Exception as e:
    print(f"Error: {e}")
