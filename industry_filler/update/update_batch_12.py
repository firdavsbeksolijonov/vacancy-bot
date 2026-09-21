
import pandas as pd

path = __import__("pathlib").Path(__file__).resolve().parent.parent / "tashkent_hh_companies_clean.xlsx"
df = pd.read_excel(path)

updates = {
    380: "Engineering / Machinery | Машиностроение / Оборудование | Mashinasozlik / Uskunalar",
    381: "Industrial Compressors | Промышленные компрессоры | Sanoat kompressorlari",
    382: "Unknown | Неизвестно | Noma'lum",
    383: "Aviation MRO | Авиационное техобслуживание | Aviatsiya texnik xizmati",
    384: "Unknown | Неизвестно | Noma'lum",
    385: "Unknown | Неизвестно | Noma'lum",
    386: "Digital Marketing / SEO | Цифровой маркетинг / SEO | Raqamli marketing / SEO",
    387: "Unknown | Неизвестно | Noma'lum",
    388: "Lighting / Electrical | Освещение / Электрика | Yoritish / Elektr",
    398: "Printing / Art | Полиграфия / Искусство | Poligrafiya / San'at",
    399: "E-commerce / Retail | Электронная коммерция / Розничная торговля | Elektron tijorat / Chakana savdo",
    400: "Unknown | Неизвестно | Noma'lum",
    402: "Construction Materials | Строительные материалы | Qurilish materiallari",
    403: "E-commerce / Retail | Электронная коммерция / Розничная торговля | Elektron tijorat / Chakana savdo",
    405: "Energy / Greenhouses | Энергетика / Теплицы | Energetika / Issiqxonalar",
    406: "Health Supplements / Trade | БАДы / Торговля | Biologik qo'shimchalar / Savdo",
    407: "Chemicals / Fertilizers | Химия / Удобрения | Kimyo / O'g'itlar",
    408: "Unknown | Неизвестно | Noma'lum",
    409: "Biotech / Trade | Биотехнологии / Торговля | Biotexnologiyalar / Savdo",
    410: "Unknown | Неизвестно | Noma'lum",
    411: "Unknown | Неизвестно | Noma'lum",
    412: "Legal Tech / AI | Юридические технологии / ИИ | Huquqiy texnologiyalar / SI",
    413: "Unknown | Неизвестно | Noma'lum",
    414: "Cosmetics / Perfumery | Косметика / Парфюмерия | Kosmetika / Parfyumeriya",
    415: "Veterinary Pharma | Ветеринарная фармация | Veterinar farmatsevtika",
    416: "Luxury Goods / Watches | Предметы роскоши / Часы | Lyuks tovarlar / Soatlar",
    417: "Unknown | Неизвестно | Noma'lum",
    418: "FMCG Distribution / Metal | Дистрибуция FMCG / Металл | FMCG distributsiyasi / Metall",
    419: "Advertising / Production | Реклама / Производство | Reklama / Ishlab chiqarish",
    420: "Microfinance / Loans | Микрофинансирование / Кредиты | Mikro moliya / Kreditlar",
    421: "Unknown | Неизвестно | Noma'lum",
    422: "Unknown | Неизвестно | Noma'lum",
    423: "Unknown | Неизвестно | Noma'lum",
    424: "Chemicals / Fertilizers | Химия / Удобрения | Kimyo / O'g'itlar",
    425: "Unknown | Неизвестно | Noma'lum",
    426: "Restaurants / Food | Рестораны / Еда | Restoranlar / Oziq-ovqat",
    427: "Architecture / Design | Архитектура / Дизайн | Arxitektura / Dizayn",
    428: "Beauty Shop / Online | Магазин косметики / Онлайн | Kosmetika do'koni / Onlayn",
    429: "Trade / Maritime | Торговля / Морские перевозки | Savdo / Dengiz tashuvlari",
    430: "Unknown | Неизвестно | Noma'lum",
    431: "E-commerce / Retail | Электронная коммерция / Розничная торговля | Elektron tijorat / Chakana savdo",
    432: "IT Services / Telecom | IT услуги / Телеком | IT xizmatlar / Telekom",
    433: "Unknown | Неизвестно | Noma'lum",
    434: "Unknown | Неизвестно | Noma'lum",
    435: "Food Distribution | Дистрибуция продуктов | Oziq-ovqat distributsiyasi",
    436: "Air Cargo / Logistics | Авиаперевозки / Логистика | Aviatashuvlar / Logistika",
    437: "Unknown | Неизвестно | Noma'lum"
}

for idx, val in updates.items():
    if idx < len(df):
        df.loc[idx, 'industry'] = val

df.to_excel(path, index=False)
print("Updated rows.")
