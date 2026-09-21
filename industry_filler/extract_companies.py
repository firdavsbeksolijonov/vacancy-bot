
import pandas as pd
import json

path = __import__("pathlib").Path(__file__).resolve().parent / "tashkent_hh_companies_clean.xlsx"
df = pd.read_excel(path)

# Get the first 10 company names and the column index of 'industry'
# Assuming the company name column is the first one or named 'company' / 'name'
# I'll list the columns first to be sure.
print(f"Columns: {df.columns.tolist()}")

# Try to find company name column
name_col = None
for col in df.columns:
    if 'name' in col.lower() or 'company' in col.lower():
        name_col = col
        break

if name_col:
    companies = df[name_col].head(10).tolist()
    print(f"Companies: {json.dumps(companies)}")
else:
    print("Company name column not found")
