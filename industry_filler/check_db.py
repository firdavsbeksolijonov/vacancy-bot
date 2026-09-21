import sqlite3
import pandas as pd

conn = sqlite3.connect('industry_filler/company_vacancies.db')

# Statistika
cur = conn.cursor()
cur.execute('SELECT industry_uz, COUNT(*) FROM company_classifications GROUP BY industry_uz ORDER BY COUNT(*) DESC')
print('=== INDUSTRY STATISTIKA ===')
for row in cur.fetchall():
    print(f'{row[1]} ta → {row[0]}')

# Noma'lum larni Excel ga
df = pd.read_sql("SELECT * FROM company_classifications WHERE industry_uz='Noma''lum'", conn)
df.to_excel('industry_filler/unclassified_final.xlsx', index=False)
print(f"\nNoma'lum: {len(df)} ta → unclassified_final.xlsx ga saqlandi")

conn.close()