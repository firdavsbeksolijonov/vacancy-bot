
import pandas as pd

path = __import__("pathlib").Path(__file__).resolve().parent.parent / "tashkent_hh_companies_clean.xlsx"
df = pd.read_excel(path)

updates = {
    370: "Beauty / Cosmetics | Косметика | Go'zallik",
    371: "Restaurants / Food | Рестораны / Еда | Restoranlar / Oziq-ovqat",
    372: "Cosmetics / Skincare | Косметика / Уход за кожей | Kosmetika / Terini parvarishlash",
    373: "Industrial Belts / Engineering | Промышленные ленты / Инжиниринг | Sanoat lentalari / Injiniring",
    374: "Beverage Distribution | Дистрибуция напитков | Ichimliklar distributsiyasi",
    375: "Unknown | Неизвестно | Noma'lum",
    376: "Industrial Equipment | Промышленное оборудование | Sanoat uskunalari",
    377: "Unknown | Неизвестно | Noma'lum",
    378: "Investment / Management | Инвестиции / Менеджмент | Investitsiyalar / Menejment",
    379: "Metalworking | Металлообработка | Metallga ishlov berish",
    412: "Legal Tech / AI | Юридические технологии / ИИ | Huquqiy texnologiyalar / SI",
    413: "Unknown | Неизвестно | Noma'lum",
    414: "Cosmetics / Perfumery | Косметика / Парфюмерия | Kosmetika / Parfyumeriya",
    415: "Veterinary Pharma | Ветеринарная фармация | Veterinar farmatsevtika",
    416: "Luxury Goods / Watches | Предметы роскоши / Часы | Lyuks tovarlar / Soatlar",
    417: "Unknown | Неизвестно | Noma'lum",
    418: "FMCG Distribution / Metal | Дистрибуция FMCG / Металл | FMCG distributsiyasi / Metall",
    419: "Advertising / Production | Реклама / Производство | Reklama / Ishlab chiqarish",
    420: "Microfinance / Loans | Микрофинансирование / Кредиты | Mikro moliya / Kreditlar",
    421: "Unknown | Неизвестно | Noma'lum"
}

for idx, val in updates.items():
    if idx < len(df):
        df.loc[idx, 'industry'] = val

df.to_excel(path, index=False)
print("Updated rows.")
