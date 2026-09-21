import requests

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Referer": "https://hh.uz/search/vacancy",
    "X-Requested-With": "XMLHttpRequest",
}

url = "https://hh.uz/shards/vacancy/search"
params = {
    "employer_id": "2552465",
    "area": "2759",
    "items_on_page": "5",
    "page": "0",
}

r = requests.get(url, headers=headers, params=params, timeout=10)
data = r.json()

vacancies = data.get("vacancySearchResult", {}).get("vacancies", [])
print(f"Vakansiyalar: {len(vacancies)} ta\n")

for v in vacancies:
    print("=" * 50)
    print("Nomi:     ", v.get("name", ""))
    print("Link:     ", v.get("links", {}).get("desktop", "") if isinstance(v.get("links"), dict) else "")

    # Maosh
    salary = v.get("compensation", {})
    if isinstance(salary, dict):
        print("Maosh:    ", salary.get("from"), "-", salary.get("to"), salary.get("currencyCode", ""))

    # Tajriba — string yoki dict bo'lishi mumkin
    exp = v.get("workExperience", "")
    if isinstance(exp, dict):
        print("Tajriba:  ", exp.get("id", ""))
    else:
        print("Tajriba:  ", exp)

    # Kompaniya
    emp = v.get("company", {})
    if isinstance(emp, dict):
        print("Kompaniya:", emp.get("name", ""))
        ratings = emp.get("ratings", {})
        if isinstance(ratings, dict):
            print("Reyting:  ", ratings.get("total", ""))

    print()