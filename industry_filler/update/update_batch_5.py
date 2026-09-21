
import pandas as pd

path = __import__("pathlib").Path(__file__).resolve().parent.parent / "tashkent_hh_companies_clean.xlsx"
df = pd.read_excel(path)

updates = {
    170: "Banking | Банкинг | Bank",
    171: "Construction | Строительство | Qurilish",
    172: "Real Estate | Недвижимость | Ko'chmas mulk",
    173: "Glass Production | Производство стекла | Shisha ishlab chiqarish",
    174: "Unknown | Неизвестно | Noma'lum",
    175: "Textile Manufacturing | Производство текстиля | To'qimachilik ishlab chiqarish",
    176: "IT / Digital Solutions | IT / Цифровые решения | IT / Raqamli yechimlar",
    177: "Tourism | Туризм | Turizm",
    178: "Plastic Packaging | Пластиковая упаковка | Plastik qadoqlash",
    179: "Media / Digital Marketing | Медиа / Цифровой маркетинг | Media / Raqamli marketing",
    180: "Unknown | Неизвестно | Noma'lum",
    181: "Technical Services | Технические услуги | Texnik xizmatlar",
    182: "Water Solutions | Водные решения | Suv yechimlari",
    183: "Heating Systems | Системы отопления | Isitish tizimlari",
    184: "Water Purification | Очистка воды | Suvni tozalash",
    185: "Fragrances / Cosmetics | Парфюмерия / Косметика | Parfyumeriya / Kosmetika",
    186: "Architecture / Engineering | Архитектура / Инжиниринг | Arxitektura / Injiniring",
    187: "Architecture | Архитектура | Arxitektura",
    188: "Trade / Consulting | Торговля / Консалтинг | Savdo / Konsalting",
    189: "Sports | Спорт | Sport",
    190: "Unknown | Неизвестно | Noma'lum",
    191: "Holding / Investment | Холдинг / Инвестиции | Holding / Investitsiyalar",
    192: "Insurance | Страхование | Sug'urta",
    193: "Trade / Group | Торговля / Группа | Savdo / Guruh",
    194: "Finance / Investment | Финансы / Инвестиции | Moliya / Investitsiyalar",
    195: "Cosmetology | Косметология | Kosmetologiya",
    196: "Textiles | Текстиль | To'qimachilik",
    197: "Water Systems | Системы водоснабжения | Suv ta'minoti tizimlari",
    198: "Construction | Строительство | Qurilish",
    199: "Industrial Trade | Промышленная торговля | Sanoat savdosi",
    200: "Fragrances / Chemicals | Парфюмерия / Химия | Parfyumeriya / Kimyo",
    201: "Cosmetics / Fragrances | Косметика / Парфюмерия | Kosmetika / Parfyumeriya",
    202: "Education / Training | Образование / Тренинг | Ta'lim / Trening",
    203: "Logistics | Логистика | Logistika",
    204: "Confectionery | Кондитерские изделия | Konditerlik",
    205: "Design | Дизайн | Dizayn",
    206: "Unknown | Неизвестно | Noma'lum",
    207: "Home Appliances | Бытовая техника | Maishiy texnika",
    208: "Art / Design | Искусство / Дизайн | San'at / Dizayn",
    209: "Bakery | Пекарня | Novvoyxona"
}

for idx, val in updates.items():
    if idx < len(df):
        df.loc[idx, 'industry'] = val

df.to_excel(path, index=False)
print("Updated 40 rows.")
