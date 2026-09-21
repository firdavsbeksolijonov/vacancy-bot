
import pandas as pd
import json

path = __import__("pathlib").Path(__file__).resolve().parent / "tashkent_hh_companies_clean.xlsx"
df = pd.read_excel(path)

# Find rows where industry is NaN or empty
mask = df['industry'].isna() | (df['industry'] == '')
pending = df[mask]

print(f"Total companies: {len(df)}")
print(f"Pending companies: {len(pending)}")

# Get list of company names and their original indices
company_list = []
for idx, row in pending.iterrows():
    company_list.append({"index": int(str(idx)), "name": str(row['company_name'])})

print(json.dumps(company_list))
