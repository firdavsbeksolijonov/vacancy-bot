
import pandas as pd

path = __import__("pathlib").Path(__file__).resolve().parent / "tashkent_hh_companies_clean.xlsx"
df = pd.read_excel(path)

# Expanded keywords for Finance, Insurance, Investment, Audit, and Business Services
# Fixed the 'sug'urta' string by using double quotes or escaping
keywords = [
    'bank', 'banking', 'банк', 'banklar', 
    'finance', 'moliya', 'финансы', 'finans',
    'credit', 'kredit', 'кредит',
    'loan', 'zaym', 'займ',
    'investment', 'investitsiya', 'инвестиции', 'invest',
    'insurance', 'sugurta', 'страхование', "sug'urta",
    'fintech', 'финтех',
    'audit', 'аудит',
    'accounting', 'buxgalteriya', 'бухгалтерия',
    'lombard', 'ломбард',
    'leasing', 'lizing', 'лизинг',
    'consulting', 'konsalting', 'консалтинг',
    'microfinance', 'mikrokredit', 'микрокредит'
]

# Filter the industry column (case-insensitive)
mask = df['industry'].str.contains('|'.join(keywords), case=False, na=False)
related_companies = df[mask][['company_name', 'industry']]

if related_companies.empty:
    print("Kengaytirilgan kalit so'zlar bo'yicha kompaniyalar topilmadi.")
else:
    print(related_companies.to_string(index=False))
