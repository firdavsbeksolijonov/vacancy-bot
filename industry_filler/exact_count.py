
import pandas as pd
path = __import__("pathlib").Path(__file__).resolve().parent / "tashkent_hh_companies_clean.xlsx"
df = pd.read_excel(path)
filled = df[df['industry'].notna() & (df['industry'].astype(str).str.strip() != "")].shape[0]
print(f"{filled}")
