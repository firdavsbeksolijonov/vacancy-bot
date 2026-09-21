
import pandas as pd

path = __import__("pathlib").Path(__file__).resolve().parent.parent / "tashkent_hh_companies_clean.xlsx"
df = pd.read_excel(path)

updates = {
    210: "Metal Production / Artistic Forging | Производство металлоизделий / Художественная ковка | Metall mahsulotlari / Badiiy temirchilik",
    211: "Event Agency / Model Agency | Event-агентство / Модельное агентство | Event agentligi / Model agentligi",
    212: "Hospitality / Hotel | Гостиничный бизнес / Отель | Mehmonxona biznesi / Mehmonxona",
    213: "Unknown | Неизвестно | Noma'lum",
    214: "Construction / Trust | Строительство / Трест | Qurilish / Trast",
    215: "Fintech / Payment Systems | Финтех / Платежные системы | Fintex / To'lov tizimlari",
    216: "Unknown | Неизвестно | Noma'lum",
    217: "Tourism | Туризм | Turizm",
    218: "Automotive | Автомобильный сектор | Avtomobil sektori",
    219: "Unknown | Неизвестно | Noma'lum",
    220: "IT Distribution | IT-дистрибуция | IT-distributsiyasi",
    221: "Pharmaceuticals / Medical | Фармацевтика / Медицина | Farmatsevtika / Tibbiyot",
    222: "Construction | Строительство | Qurilish",
    223: "Tourism | Туризм | Turizm",
    224: "Logistics / Distribution | Логистика / Дистрибуция | Logistika / Distributsiyasi",
    225: "Pharmaceuticals | Фармацевтика | Farmatsevtika",
    226: "Real Estate / Commercial | Недвижимость / Коммерческая | Ko'chmas mulk / Tijorat",
    227: "Technology / IT | Технологии / IT | Texnologiyalar / IT",
    228: "Transport / Logistics | Транспорт / Логистика | Transport / Logistika",
    229: "Unknown | Неизвестно | Noma'lum",
    230: "Pharmaceuticals | Фармацевтика | Farmatsevtika",
    231: "Metallurgy | Металлургия | Metallurgiya",
    232: "Healthcare / Medical | Здравоохранение / Медицина | Sog'liqni saqlash / Tibbiyot",
    233: "Education / Consulting | Образование / Консалтинг | Ta'lim / Konsalting",
    234: "Food Production | Производство продуктов питания | Oziq-ovqat ishlab chiqarish",
    235: "Meat Processing | Мясопереработка | Go'sht qayta ishlash",
    236: "Hospitality / Hotel | Гостиничный бизнес / Отель | Mehmonxona biznesi / Mehmonxona",
    237: "Unknown | Неизвестно | Noma'lum",
    238: "Ecotourism | Экотуризм | Ekoturizm",
    239: "Catering / Restaurant | Общепит / Ресторан | Umumiy ovqatlanish / Restoran",
    240: "Catering / Restaurant | Общепит / Ресторан | Umumiy ovqatlanish / Restoran",
    241: "Unknown | Неизвестно | Noma'lum",
    242: "Agriculture / Nursery | Сельское хозяйство / Питомник | Qishloq xo'jaligi / Piromnik",
    243: "Real Estate | Недвижимость | Ko'chmas mulk",
    244: "Electronics Manufacturing | Производство электроники | Elektronika ishlab chiqarish",
    245: "Finance / Leasing | Финансы / Лизинг | Moliya / Lizing",
    246: "Business Services / IT | Бизнес-услуги / IT | Biznes xizmatlar / IT",
    247: "Catering / Restaurant | Общепит / Ресторан | Umumiy ovqatlanish / Restoran",
    248: "Retail | Розничная торговля | Chakana savdo",
    249: "Logistics | Логистика | Logistika"
}

for idx, val in updates.items():
    if idx < len(df):
        df.loc[idx, 'industry'] = val

df.to_excel(path, index=False)
print("Updated 40 rows.")
