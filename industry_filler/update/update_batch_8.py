
import pandas as pd

path = __import__("pathlib").Path(__file__).resolve().parent.parent / "tashkent_hh_companies_clean.xlsx"
df = pd.read_excel(path)

updates = {
    290: "Sports Equipment / Trade | Спортивные товары / Торговля | Sport anjomlari / Savdo",
    291: "IT / Computer Hardware | IT / Компьютерное оборудование | IT / Kompyuter uskunalari",
    292: "Unknown | Неизвестно | Noma'lum",
    293: "Unknown | Неизвестно | Noma'lum",
    294: "Unknown | Неизвестно | Noma'lum",
    295: "Unknown | Неизвестно | Noma'lum",
    296: "Unknown | Неизвестно | Noma'lum",
    297: "Textiles | Текстиль | To'qimachilik",
    298: "Cosmetics / Care | Косметика / Уход | Kosmetika / Parvarish",
    299: "Unknown | Неизвестно | Noma'lum",
    300: "Unknown | Неизвестно | Noma'lum",
    301: "Unknown | Неизвестно | Noma'lum",
    302: "Health & Care | Здоровье и уход | Sog'liq va parvarish",
    303: "Energy | Энергетика | Energetika",
    304: "Beauty / Nails | Красота / Ногти | Go'zallik / Tirnoqlar",
    305: "Unknown | Неизвестно | Noma'lum",
    306: "Trade | Торговля | Savdo",
    307: "Electrical Equipment | Электрооборудование | Elektr uskunalari",
    308: "Unknown | Неизвестно | Noma'lum",
    309: "Hospitality / Hotel | Гостиничный бизнес / Отель | Mehmonxona biznesi / Mehmonxona",
    310: "Tourism | Туризм | Turizm",
    311: "IT / Software | IT / Программное обеспечение | IT / Dasturiy ta'minot",
    312: "Unknown | Неизвестно | Noma'lum",
    313: "Art | Искусство | San'at",
    314: "Legal / Consulting | Юридические услуги / Консалтинг | Huquqiy xizmatlar / Konsalting",
    315: "Unknown | Неизвестно | Noma'lum",
    316: "Marketing Agency | Маркетинговое агентство | Marketing agentligi",
    317: "Unknown | Неизвестно | Noma'lum",
    318: "Unknown | Неизвестно | Noma'lum",
    319: "Retail (Baby Products) | Розничная торговля (Детские товары) | Chakana savdo (Bolalar mahsulotlari)",
    320: "Media | Медиа | Media",
    321: "Education (Kindergarten) | Образование (Детский сад) | Ta'lim (Bog'cha)",
    322: "Baby Care / Sun Care | Уход за детьми / Солнцезащита | Bolalar parvarishi / Quyoshdan himoya",
    323: "Unknown | Неизвестно | Noma'lum",
    324: "Holding / Investment | Холдинг / Инвестиции | Holding / Investitsiyalar",
    325: "Florist / Flowers | Цветочный магазин / Цветы | Gullar do'koni / Gullar",
    326: "Construction | Строительство | Qurilish",
    327: "Engineering Systems | Инженерные системы | Injiniring tizimlari",
    328: "Fintech / Payments | Финтех / Платежи | Fintex / To'lovlar",
    329: "IT / Software | IT / Программное обеспечение | IT / Dasturiy ta'minot"
}

for idx, val in updates.items():
    if idx < len(df):
        df.loc[idx, 'industry'] = val

df.to_excel(path, index=False)
print("Updated 40 rows.")
