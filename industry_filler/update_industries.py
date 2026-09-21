
import pandas as pd

path = __import__("pathlib").Path(__file__).resolve().parent / "tashkent_hh_companies_clean.xlsx"
df = pd.read_excel(path)

industries = [
    "IT (Software Testing) | IT (Тестирование ПО) | IT (Dasturiy ta'minotni testlash)",
    "Logistics | Логистика | Logistika",
    "Banking | Банковское дело | Bank ishi",
    "Biotechnology | Биотехнологии | Biotexnologiyalar",
    "Education | Образование | Ta'lim",
    "Marketing | Маркетинг | Marketing",
    "Retail (Clothing/Baby Goods) | Розничная торговля (Одежда/Детские товары) | Chakana savdo (Kiyimlar/Bolalar buyumlari)",
    "Trade (Tech Equipment) | Торговля (Техническое оборудование) | Savdo (Texnika uskunalari)",
    "Pharmaceuticals | Фармацевтика | Farmatsevtika",
    "Healthcare / Pharma | Здравоохранение / Фармацевтика | Sog'liqni saqlash / Farmatsevtika"
]

# Update only the first 10 rows of the 'industry' column
for i in range(len(industries)):
    df.loc[i, 'industry'] = industries[i]

df.to_excel(path, index=False)
print("Successfully updated first 10 rows.")
