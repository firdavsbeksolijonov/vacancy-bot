
import pandas as pd
path = __import__("pathlib").Path(__file__).resolve().parent / "tashkent_hh_companies_clean.xlsx"
df = pd.read_excel(path)
df['industry'] = df['industry'].astype(str)  # Convert industry column to string type
filled = df[df['industry'].notna() & (df['industry'].str.strip() != "")].shape[0]
print(f"{filled}")
