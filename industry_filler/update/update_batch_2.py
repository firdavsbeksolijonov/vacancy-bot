
import pandas as pd

path = __import__("pathlib").Path(__file__).resolve().parent.parent / "tashkent_hh_companies_clean.xlsx"
df = pd.read_excel(path)

updates = {
    50: "Individual Entrepreneur | Индивидуальный предприниматель | Yakka tadbirkor",
    51: "AdTech / Media | Рекламные технологии / Медиа | Reklama texnologiyalari / Media",
    52: "Construction Materials (Stone) | Строительные материалы (Камень) | Qurilish materiallari (Tosh)",
    53: "Tourism | Туризм | Turizm",
    54: "Advertising | Реклама | Reklama",
    55: "Legal/Consulting | Юридические услуги / Консалтинг | Huquqiy xizmatlar / Konsalting",
    56: "Logistics / Freight | Логистика / Грузоперевозки | Logistika / Yuk tashish",
    57: "Healthcare / Medicine | Здравоохранение / Медицина | Sog'liqni saqlash / Tibbiyot",
    58: "Transport / Logistics | Транспорт / Логистика | Transport / Logistika",
    59: "Investment | Инвестиции | Investitsiyalar",
    60: "Research | Исследования | Tadqiqotlar",
    61: "Trade | Торговля | Savdo",
    62: "Construction Materials (Concrete) | Строительные материалы (Бетон) | Qurilish materiallari (Beton)",
    63: "Real Estate | Недвижимость | Ko'chmas mulk",
    64: "Healthcare | Здравоохранение | Sog'liqni saqlash",
    65: "Agriculture / Tourism | Сельское хозяйство / Туризм | Qishloq xo'jaligi / Turizm",
    66: "Gov / AgTech | Гос / Агротехнологии | Davlat / Agrotexnologiyalar",
    67: "Education | Образование | Ta'lim",
    68: "Finance / Brokerage | Финансы / Брокерские услуги | Moliya / Brokerlik xizmatlari",
    69: "Trade/Group | Торговля/Группа | Savdo/Guruh",
    70: "IT / AI | IT / ИИ | IT / Sun'iy intellekt",
    71: "Education | Образование | Ta'lim",
    72: "Trade/Group | Торговля/Группа | Savdo/Guruh",
    73: "Tourism / Booking | Туризм / Бронирование | Turizm / Bron qilish",
    74: "IT / Networking | IT / Сети | IT / Tarmoqlar",
    75: "IT / CG | IT / Компьютерная графика | IT / Kompyuter grafikasi",
    76: "Investment | Инвестиции | Investitsiyalar",
    77: "Trade | Торговля | Savdo",
    78: "IT / AI | IT / ИИ | IT / Sun'iy intellekt",
    79: "Trade/Family | Торговля/Семейный бизнес | Savdo/Oila biznesi",
    80: "IT / Professional Services | IT / Профессиональные услуги | IT / Professional xizmatlar",
    81: "Machinery | Машиностроение | Mashinasozlik",
    82: "Construction Materials | Строительные материалы | Qurilish materiallari",
    83: "Healthcare | Здравоохранение | Sog'liqni saqlash",
    84: "Trade | Торговля | Savdo",
    85: "Construction | Строительство | Qurilish",
    86: "Energy / Electricity | Энергетика / Электричество | Energetika / Elektr energiya",
    87: "Food / Cafe | Общепит / Кафе | Oziq-ovqat / Kafe",
    88: "Real Estate | Недвижимость | Ko'chmas mulk",
    89: "Management / Group | Менеджмент / Группа | Menejment / Guruh"
}

for idx, val in updates.items():
    if idx < len(df):
        df.loc[idx, 'industry'] = val

df.to_excel(path, index=False)
print("Updated 40 rows.")
