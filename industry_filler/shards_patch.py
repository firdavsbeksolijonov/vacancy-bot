# Bu qatorlarni src/rss_client.py ga qo'shing
import requests
def fetch_vacancies_shards(employer_id: str) -> list[dict]:
    """HH.uz shards API orqali vakansiyalar oladi."""
    url = "https://hh.uz/shards/vacancy/search"
    params = {
        "employer_id": employer_id,
        "area": "2759",
        "items_on_page": "10",
        "page": "0",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Accept-Language": "ru-RU,ru;q=0.9",
        "Referer": "https://hh.uz/search/vacancy",
        "X-Requested-With": "XMLHttpRequest",
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []

    vacancies = data.get("vacancySearchResult", {}).get("vacancies", [])
    result = []

    for v in vacancies:
        # Experience — string yoki dict bo'lishi mumkin
        exp = v.get("workExperience", "")
        if isinstance(exp, dict):
            exp = exp.get("id", "")

        # Links — dict yoki string
        links = v.get("links", {})
        link = links.get("desktop", "") if isinstance(links, dict) else ""

        # Salary
        salary = v.get("compensation", {})
        sal_from = salary.get("from") if isinstance(salary, dict) else None
        sal_to   = salary.get("to")   if isinstance(salary, dict) else None

        # Company
        company = v.get("company", {})
        company_name = company.get("name", "") if isinstance(company, dict) else ""

        result.append({
            "id":           str(v.get("id", "")),
            "title":        v.get("name", ""),
            "link":         link or f"https://hh.uz/vacancy/{v.get('id','')}",
            "description":  v.get("snippet", {}).get("responsibility", "") if isinstance(v.get("snippet"), dict) else "",
            "published_at": None,
            "salary_from":  sal_from,
            "salary_to":    sal_to,
            "experience":   exp,
            "company":      company_name,
        })

    return result