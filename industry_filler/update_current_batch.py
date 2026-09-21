
import pandas as pd
path = __import__("pathlib").Path(__file__).resolve().parent / "tashkent_hh_companies_clean.xlsx"
df = pd.read_excel(path)
updates = {    389: "Unknown | Неизвестно | Noma'lum",
    390: 'IT / Technology | IT / Технологии | IT / Texnologiyalar',
    391: 'IT / Technology | IT / Технологии | IT / Texnologiyalar',
    392: 'IT / Technology | IT / Технологии | IT / Texnologiyalar',
    393: 'Construction | Строительство | Qurilish',
    394: 'IT / Technology | IT / Технологии | IT / Texnologiyalar',
    395: 'IT / Technology | IT / Технологии | IT / Texnologiyalar',
    396: 'IT / Technology | IT / Технологии | IT / Texnologiyalar',
    397: 'IT / Technology | IT / Технологии | IT / Texnologiyalar',
    401: 'IT / Technology | IT / Технологии | IT / Texnologiyalar',
    404: 'IT / Technology | IT / Технологии | IT / Texnologiyalar',
    438: 'Retail | Розничная торговля | Chakana savdo',
    439: 'IT / Technology | IT / Технологии | IT / Texnologiyalar',
    440: 'Trade/Services | Торговля/Услуги | Savdo/Xizmatlar',
    441: 'Retail | Розничная торговля | Chakana savdo',
    442: "Unknown | Неизвестно | Noma'lum",
    443: 'Construction | Строительство | Qurilish',
    444: 'IT / Technology | IT / Технологии | IT / Texnologiyalar',
    445: 'IT / Technology | IT / Технологии | IT / Texnologiyalar',
    446: "Unknown | Неизвестно | Noma'lum",
    447: 'Construction | Строительство | Qurilish',
    448: 'Trade | Торговля | Savdo',
    449: 'Retail | Розничная торговля | Chakana savdo',
    450: "Unknown | Неизвестно | Noma'lum",
    451: 'IT / Technology | IT / Технологии | IT / Texnologiyalar',
    452: 'Trade/Services | Торговля/Услуги | Savdo/Xizmatlar',
    453: 'IT / Technology | IT / Технологии | IT / Texnologiyalar',
    454: "Unknown | Неизвестно | Noma'lum",
    455: 'IT / Technology | IT / Технологии | IT / Texnologiyalar',
    456: 'Trade/Services | Торговля/Услуги | Savdo/Xizmatlar',
    457: 'IT / Technology | IT / Технологии | IT / Texnologiyalar',
    458: "Unknown | Неизвестно | Noma'lum",
    459: 'IT / Technology | IT / Технологии | IT / Texnologiyalar',
    460: 'IT / Technology | IT / Технологии | IT / Texnologiyalar',
    461: 'IT / Technology | IT / Технологии | IT / Texnologiyalar',
    462: "Unknown | Неизвестно | Noma'lum",
    463: 'IT / Technology | IT / Технологии | IT / Texnologiyalar',
    464: 'Trade/Services | Торговля/Услуги | Savdo/Xizmatlar',
    465: 'IT / Technology | IT / Технологии | IT / Texnologiyalar',
    466: "Unknown | Неизвестно | Noma'lum"}
for idx, val in updates.items():
    if idx < len(df):
        df.loc[idx, 'industry'] = val
df.to_excel(path, index=False)
print(f"Updated {len(updates)} rows.")
