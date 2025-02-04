import requests
import json
from database.db import SessionLocal
from database.models import Vacancy

HH_API_URL = "https://api.hh.ru/vacancies"
SEARCH_QUERY = "Python разработчик"
REGION_ID = 1


def fetch_vacancies():
    params = {
        "text": SEARCH_QUERY,
        "area": REGION_ID,
        "per_page": 10
    }

    response = requests.get(HH_API_URL, params=params)

    if response.status_code != 200:
        print("Ошибка при получении данных с HH.ru")
        return []

    data = response.json()
    vacancies = []

    for item in data["items"]:
        vacancy = {
            "title": item["name"],
            "description": item["snippet"]["responsibility"] or "Описание отсутствует",
            "link": item["alternate_url"]}
        vacancies.append(vacancy)

    return vacancies


def save_vacancies_to_db():
    session = SessionLocal()
    vacancies = fetch_vacancies()

    for v in vacancies:
        new_vacancy = Vacancy(
            title=v["title"], description=v["description"], link=v["link"])
        session.add(new_vacancy)

    session.commit()
    session.close()
    print("Вакансии успешно добавлены в базу!")


if __name__ == "__main__":
    save_vacancies_to_db()
