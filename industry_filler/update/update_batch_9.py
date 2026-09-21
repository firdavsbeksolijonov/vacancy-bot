
import pandas as pd

path = __import__("pathlib").Path(__file__).resolve().parent.parent / "tashkent_hh_companies_clean.xlsx"
df = pd.read_excel(path)

updates = {
    330: "Event Decor / Balloons | Декор мероприятий / Шары | Tadbir dekoratsiyasi / Sharlar",
    331: "Paper Trade | Торговля бумагой | Qog'oz savdosi",
    332: "FMCG Distribution | Дистрибуция FMCG | FMCG distributsiyasi",
    333: "Education | Образование | Ta'lim",
    334: "Medical Equipment | Медицинское оборудование | Tibbiy uskunalar",
    335: "Consulting / Business Services | Консалтинг / Бизнес-услуги | Konsalting / Biznes xizmatlar",
    336: "Unknown | Неизвестно | Noma'lum",
    337: "Energy | Энергетика | Energetika",
    338: "Unknown | Неизвестно | Noma'lum",
    339: "Unknown | Неизвестно | Noma'lum",
    340: "Management Consulting | Консалтинг по управлению | Menejment konsaltingi",
    341: "Unknown | Неизвестно | Noma'lum",
    342: "Waterproofing / Construction | Гидроизоляция / Строительство | Gidroizolyatsiya / Qurilish",
    343: "Trade | Торговля | Savdo",
    344: "Hospitality / Lounge | Гостиничный бизнес / Лаунж | Mehmonxona / Lounge",
    345: "Metal Trade | Торговля металлами | Metall savdosi",
    346: "Construction / Complex | Строительство / Комплекс | Qurilish / Kompleks",
    347: "Unknown | Неизвестно | Noma'lum",
    348: "Health / Wellness | Здоровье / Wellness | Sog'liq / Wellness",
    349: "Import / Trade | Импорт / Торговля | Import / Savdo",
    350: "Aviation / Transport | Авиация / Транспорт | Aviatsiya / Transport",
    351: "Unknown | Неизвестно | Noma'lum",
    352: "Agriculture | Сельское хозяйство | Qishloq xo'jaligi",
    353: "Medical Equipment | Медицинское оборудование | Tibbiy uskunalar",
    354: "Unknown | Неизвестно | Noma'lum",
    355: "Business Services | Бизнес-услуги | Biznes xizmatlar",
    356: "IT / Communications | IT / Связь | IT / Aloqa",
    357: "Audit / Consulting | Аудит / Консалтинг | Audit / Konsalting",
    358: "Cosmetics / Beauty | Косметика / Красота | Kosmetika / Go'zallik",
    359: "Cosmetics Distribution | Дистрибуция косметики | Kosmetika distributsiyasi",
    360: "Beauty Salon | Салон красоты | Go'zallik saloni",
    361: "Innovation / Technology | Инновации / Технологии | Innovatsiyalar / Texnologiyalar",
    362: "Fitness / Sports | Фитнес / Спорт | Fitnes / Sport",
    363: "Holding / Investment | Холдинг / Инвестиции | Holding / Investitsiyalar",
    364: "Unknown | Неизвестно | Noma'lum",
    365: "Unknown | Неизвестно | Noma'lum",
    366: "Hospitality / Resort | Гостиничный бизнес / Курорт | Mehmonxona / Kurort",
    367: "IT / Software | IT / Программное обеспечение | IT / Dasturiy ta'minot",
    368: "Tourism | Туризм | Turizm",
    369: "Baby Care / Products | Уход за детьми / Товары | Bolalar parvarishi / Mahsulotlar"
}

for idx, val in updates.items():
    if idx < len(df):
        df.loc[idx, 'industry'] = val

df.to_excel(path, index=False)
print("Updated 40 rows.")
