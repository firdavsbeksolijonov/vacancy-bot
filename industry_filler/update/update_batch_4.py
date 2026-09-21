
import pandas as pd

path = __import__("pathlib").Path(__file__).resolve().parent.parent / "tashkent_hh_companies_clean.xlsx"
df = pd.read_excel(path)

updates = {
    130: "Fintech / B2B Services | Финтех / B2B услуги | Fintex / B2B xizmatlar",
    131: "Energy Automation | Автоматизация энергетики | Energetika avtomatizatsiyasi",
    132: "Medical Devices | Медицинские устройства | Tibbiy qurilmalar",
    133: "Unknown | Неизвестно | Noma'lum",
    134: "Construction Materials | Строительные материалы | Qurilish materiallari",
    135: "Engineering Services | Инженерные услуги | Injiniring xizmatlari",
    136: "Education | Образование | Ta'lim",
    137: "Aluminum Production | Производство алюминия | Alyuminiy ishlab chiqarish",
    138: "Building Materials | Строительные материалы | Qurilish materiallari",
    139: "Trade (Aluminum) | Торговля (Алюминий) | Savdo (Alyuminiy)",
    140: "Business Consulting | Бизнес-консалтинг | Biznes-konsalting",
    141: "Unknown | Неизвестно | Noma'lum",
    142: "Wood Products | Изделия из дерева | Yog'och mahsulotlari",
    143: "Automotive | Автомобильный сектор | Avtomobil sektori",
    144: "IT / Technology | IT / Технологии | IT / Texnologiyalar",
    145: "Unknown | Неизвестно | Noma'lum",
    146: "Media | Медиа | Media",
    147: "Recruitment / HR | Рекрутинг / HR | Rekruting / HR",
    148: "Education | Образование | Ta'lim",
    149: "Health Supplements | Биодобавки / Витамины | Biologik qo'shimchalar / Vitaminlar",
    150: "Higher Education | Высшее образование | Oliy ta'lim",
    151: "Cafe / Culture | Кафе / Культура | Kafe / Madaniyat",
    152: "Hospitality / Hotel | Гостиничный бизнес / Отель | Mehmonxona biznesi",
    153: "Trade | Торговля | Savdo",
    154: "Paints & Coatings | Краски и покрытия | Bo'yoqlar va qoplamalar",
    155: "Recruitment / HR | Рекрутинг / HR | Rekruting / HR",
    156: "Education | Образование | Ta'lim",
    157: "Business Consulting | Бизнес-консалтинг | Biznes-konsalting",
    158: "Retail | Розничная торговля | Chakana savdo",
    159: "Packaging | Упаковка | Qadoqlash",
    160: "Industrial Equipment | Промышленное оборудование | Sanoat uskunalari",
    161: "Education | Образование | Ta'lim",
    162: "Automotive | Автомобильный сектор | Avtomobil sektori",
    163: "Recruitment / HR | Рекрутинг / HR | Rekruting / HR",
    164: "Apparel Retail | Розничная торговля одеждой | Kiyim-kechak savdosi",
    165: "Unknown | Неизвестно | Noma'lum",
    166: "Tourism | Туризм | Turizm",
    167: "Construction Machinery | Строительная техника | Qurilish texnikasi",
    168: "IT Services | IT услуги | IT xizmatlar",
    169: "Industrial Materials | Промышленные материалы | Sanoat materiallari"
}

for idx, val in updates.items():
    if idx < len(df):
        df.loc[idx, 'industry'] = val

df.to_excel(path, index=False)
print("Updated 40 rows.")
