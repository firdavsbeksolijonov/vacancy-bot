
import pandas as pd

path = __import__("pathlib").Path(__file__).resolve().parent.parent / "tashkent_hh_companies_clean.xlsx"
df = pd.read_excel(path)

updates = {
    370: "Beauty / Cosmetics | Косметика | Go'zallik",
    371: "Restaurants / Food | Рестораны / Еда | Restoranlar / Oziq-ovqat",
    373: "Industrial Belts / Engineering | Промышленные ленты / Инжиниринг | Sanoat lentalari / Injiniring",
    374: "Beverage Distribution | Дистрибуция напитков | Ichimliklar distributsiyasi",
    398: "Printing / Art | Полиграфия / Искусство | Poligrafiya / San'at",
    399: "E-commerce / Retail | Электронная коммерция / Розничная торговля | Elektron tijorat / Chakana savdo",
    402: "Construction Materials | Строительные материалы | Qurilish materiallari",
    403: "E-commerce / Retail | Электронная коммерция / Розничная торговля | Elektron tijorat / Chakana savdo",
    405: "Energy / Greenhouses | Энергетика / Теплицы | Energetika / Issiqxonalar",
    406: "Health Supplements / Trade | БАДы / Торговля | Biologik qo'shimchalar / Savdo",
    407: "Chemicals / Fertilizers | Химия / Удобрения | Kimyo / O'g'itlar",
    409: "Biotech / Trade | Биотехнологии / Торговля | Biotexnologiyalar / Savdo"
}

for idx, val in updates.items():
    if idx < len(df):
        df.loc[idx, 'industry'] = val

df.to_excel(path, index=False)
print("Updated rows.")
