
import pandas as pd

path = __import__("pathlib").Path(__file__).resolve().parent.parent / "tashkent_hh_companies_clean.xlsx"
df = pd.read_excel(path)

updates = {
    10: "Bakery | Пекарня | Nonnovoyna",
    11: "Individual Entrepreneur | Индивидуальный предприниматель | Yakka tadbirkor",
    12: "Fintech | Финтех | Fintexnologiyalar",
    13: "Agriculture | Сельское хозяйство | Qishloq xo'jaligi",
    14: "Individual Entrepreneur | Индивидуальный предприниматель | Yakka tadbirkor",
    15: "Individual Entrepreneur | Индивидуальный предприниматель | Yakka tadbirkor",
    16: "Individual Entrepreneur | Индивидуальный предприниматель | Yakka tadbirkor",
    17: "Food Industry | Пищевая промышленность | Oziq-ovqat sanoati",
    18: "Individual Entrepreneur | Индивидуальный предприниматель | Yakka tadbirkor",
    19: "Individual Entrepreneur | Индивидуальный предприниматель | Yakka tadbirkor",
    20: "Food Industry | Пищевая промышленность | Oziq-ovqat sanoati",
    21: "Individual Entrepreneur | Индивидуальный предприниматель | Yakka tadbirkor",
    22: "Trade | Торговля | Savdo",
    23: "Pharmaceuticals | Фармацевтика | Farmatsevtika",
    24: "HR Services | HR-услуги | HR-xizmatlar",
    25: "Trade | Торговля | Savdo",
    26: "Finance / Investment | Финансы / Инвестиции | Moliya / Investitsiyalar",
    27: "Distribution | Дистрибуция | Distributsiya",
    28: "Education | Образование | Ta'lim",
    29: "Consulting / Services | Консалтинг / Услуги | Konsalting / Xizmatlar",
    30: "IT (Software) | IT (ПО) | IT (Dasturiy ta'minot)",
    31: "Trade/Services | Торговля/Услуги | Savdo/Xizmatlar",
    32: "Logistics | Логистика | Logistika",
    33: "Tourism | Туризм | Turizm",
    34: "Business Services | Бизнес-услуги | Biznes-xizmatlar",
    35: "Education | Образование | Ta'lim",
    36: "Education/Consulting | Образование/Консалтинг | Ta'lim/Konsalting",
    37: "Hospitality/Tourism | Гостиничный бизнес/Туризм | Mehmonxona/Turizm",
    38: "Trade/Services | Торговля/Услуги | Savdo/Xizmatlar",
    39: "IT/Services | IT/Услуги | IT/Xizmatlar",
    40: "Media | Медиа | Media",
    41: "Food/Beverage | Продукты/Напитки | Oziq-ovqat/Ichimliklar",
    42: "Manufacturing/Tech | Производство/Технологии | Ishlab chiqarish/Texnologiyalar",
    43: "Distribution | Дистрибуция | Distributsiya",
    44: "Media | Медиа | Media",
    45: "Consulting/Services | Консалтинг/Услуги | Konsalting/Xizmatlar",
    46: "Trade | Торговля | Savdo",
    47: "Pharmaceuticals | Фармацевтика | Farmatsevtika",
    48: "Logistics | Логистика | Logistika",
    49: "Confectionery | Кондитерские изделия | Konditerlik mahsulotlari"
}

for idx, val in updates.items():
    if idx < len(df):
        df.loc[idx, 'industry'] = val

df.to_excel(path, index=False)
print("Updated 40 rows.")
