import pandas as pd
import json

path = __import__("pathlib").Path(__file__).resolve().parent / "tashkent_hh_companies_clean.xlsx"
df = pd.read_excel(path)

mask = df['industry'].isna() | (df['industry'] == '')
pending = df[mask]

# Get next 40 pending
batch = pending.head(40)
output = []
for idx, row in batch.iterrows():
    output.append({
        "index": int(str(idx)),
        "name": str(row['company_name'])
    })

print(json.dumps(output, ensure_ascii=False))