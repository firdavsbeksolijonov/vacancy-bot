
import pandas as pd

path = __import__("pathlib").Path(__file__).resolve().parent / "tashkent_hh_companies_clean.xlsx"
df = pd.read_excel(path)

# Define banking keywords in three languages
keywords = ['bank', 'banking', 'банк', 'banklar']

# Filter the industry column (case-insensitive)
mask = df['industry'].str.contains('|'.join(keywords), case=False, na=False)
banking_companies = df[mask][['company_name', 'industry']]

if banking_companies.empty:
    print("Bankka doir kompaniyalar topilmadi.")
else:
    print(banking_companies.to_string(index=False))
