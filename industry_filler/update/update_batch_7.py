
import pandas as pd

path = __import__("pathlib").Path(__file__).resolve().parent.parent / "tashkent_hh_companies_clean.xlsx"
df = pd.read_excel(path)

updates = {
    250: "Fintech / Crypto | Финтех / Криптовалюта | Fintex / Kriptovalyuta",
    251: "Pharmaceuticals | Фармацевтика | Farmatsevtika",
    252: "Event Management | Организация мероприятий | Tadbirlarni tashkil qilish",
    253: "Healthcare | Здравоохранение | Sog'liqni saqlash",
    254: "Unknown | Неизвестно | Noma'lum",
    255: "Accounting / Consulting | Бухгалтерский учет / Консалтинг | Buxgalteriya / Konsalting",
    256: "Unknown | Неизвестно | Noma'lum",
    257: "Plastics Manufacturing | Производство пластика | Plastik ishlab chiqarish",
    258: "Shipping / Logistics | Судоходство / Логистика | Yuk tashish / Logistika",
    259: "Retail (Sports) | Розничная торговля (Спорт) | Chakana savdo (Sport)",
    260: "Logistics | Логистика | Logistika",
    261: "Unknown | Неизвестно | Noma'lum",
    262: "Unknown | Неизвестно | Noma'lum",
    263: "Unknown | Неизвестно | Noma'lum",
    264: "Conglomerate | Конгломерат | Konglomerat",
    265: "Technology / Global Services | Технологии / Глобальные услуги | Texnologiyalar / Global xizmatlar",
    266: "Unknown | Неизвестно | Noma'lum",
    267: "Cosmetics / Natural Care | Косметика / Натуральный уход | Kosmetika / Tabiiy parvarish",
    268: "Social Services / Health | Социальные услуги / Здоровье | Ijtimoiy xizmatlar / Sog'liq",
    269: "Automotive Services | Автомобильные услуги | Avtomobil xizmatlari",
    270: "Automotive Workshop | Автомастерская | Avtoservis",
    271: "Automotive Services | Автомобильные услуги | Avtomobil xizmatlari",
    272: "Automotive Consulting | Автомобильный консалтинг | Avtomobil konsaltingi",
    273: "Chemicals / Synthesis | Химия / Синтез | Kimyo / Sintez",
    274: "Tourism | Туризм | Turizm",
    275: "Unknown | Неизвестно | Noma'lum",
    276: "Education | Образование | Ta'lim",
    277: "Construction | Строительство | Qurilish",
    278: "Hospitality | Гостеприимство | Mehmonnawozlik",
    279: "Construction Materials | Строительные материалы | Qurilish materiallari",
    280: "Automotive (Tyres) | Автомобили (Шины) | Avtomobil (Shinalar)",
    281: "Textiles | Текстиль | To'qimachilik",
    282: "Education | Образование | Ta'lim",
    283: "Restaurant Group | Ресторанная группа | Restoranlar guruhi",
    284: "Unknown | Неизвестно | Noma'lum",
    285: "Unknown | Неизвестно | Noma'lum",
    286: "Automotive Finance | Автомобильный капитал / Финансы | Avtomobil moliya",
    287: "Trade | Торговля | Savdo",
    288: "Sports (Tennis) | Спорт (Теннис) | Sport (Tennis)",
    289: "Educational Innovation | Инновации в образовании | Ta'limdagi innovatsiyalar"
}

for idx, val in updates.items():
    if idx < len(df):
        df.loc[idx, 'industry'] = val

df.to_excel(path, index=False)
print("Updated 40 rows.")
