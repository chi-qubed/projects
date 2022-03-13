import os
import re
import json
from configparser import ConfigParser
from pathlib import Path

import asyncio
import requests
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor, markdown as md


# получаем токен бота из ini-файла
path = Path(__file__)
ROOT_DIR = path.parent.absolute()
config_path = os.path.join(ROOT_DIR, "hh_jobs_bot.ini")
config = ConfigParser()
config.read(config_path)
TOKEN = config.get("main", "TOKEN")


# функция поиска вакансий
def search_vacancies(
    text: str,
    page: int = 0,
    area: int = 113,
    per_page: int = 100,
    order_by: str = "publication_time",
    period: int = 1,
) -> str:
    """
    Общая документация: https://github.com/hhru/api/blob/master/docs/vacancies.md#search
    Параметр 'text' (поиск по всем полям вакансии) => https://hh.ru/article/1175#simple-search
    Параметр 'area' (код страны/региона поиска) => https://github.com/hhru/api/blob/master/docs/areas.md
    Параметры пагинации: 'page' и 'per_page' => https://github.com/hhru/api/blob/master/docs/general.md#pagination
    Параметр сортировки: 'order_by" => https://api.hh.ru/dictionaries (ключ: "vacancy_search_order")
    ("publication_time", "salary_desc", "salary_asc", "relevance", "distance")
    Параметр 'period" <= кол-во дней, в пределах которого нужно найти вакансии
    """
    parameters = {
        "text": text,
        "area": area,  # дефолтится на 113 - вся Россия
        "page": page,  # номер страницы результатов поиска
        "per_page": per_page,  # количество вакансий на 1 странице
        "order_by": order_by,
        "period": period,
    }
    req = requests.get(
        "https://api.hh.ru/vacancies", parameters
    )  # Посылаем запрос к API
    data = req.content.decode()  # обеспечение корректного отображения кириллицы
    req.close()
    return data


def rm_tags(text: str) -> str:
    """Удаляем HTML-теги из строки"""
    clean = re.compile("<.*?>")
    return re.sub(clean, "", text)


# Загружаем вакансии в JSON-объект
jsObj = json.loads(
    search_vacancies(
        text="NAME:аналитик python NOT системный NOT сетевой NOT риск NOT инженер NOT безопасности",
        page=0,
        area=113,
        per_page=5,
        period=1,
    )
)

# Запускаем бота
bot = Bot(token=TOKEN, disable_web_page_preview=True)
dp = Dispatcher(bot)


@dp.message_handler(commands=["start"])
async def process_start_command(message: types.Message):
    await message.reply(
        "Привет\\! Я бот, пересылающий *5 самых свежих вакансий* по аналитике с HH\. Отправьте любое сообщение\.",
        parse_mode="MarkdownV2",
    )


@dp.message_handler(commands=["help"])
async def process_help_command(message: types.Message):
    await message.reply("В ответ на любое сообщение отправляю 5 свежайших вакансий")


@dp.message_handler()
async def send_vacancies(msg: types.Message):
    for item in jsObj["items"]:
        summary = ""
        org_nm = item["employer"]["name"]
        pos_nm = item["name"]
        pos_req = rm_tags(item["snippet"]["requirement"])
        pos_resp = rm_tags(item["snippet"]["responsibility"])
        sal = (
            None
            if item["salary"] is None
            else f'{item["salary"]["from"]} {item["salary"]["currency"]}'
        )
        area = item["area"]["name"]
        pub_time = item["published_at"].replace("T", " ")
        link = item["alternate_url"]
        summary += md.text(
            md.bold(org_nm),
            md.bold(pos_nm),
            md.escape_md(pos_req),
            md.escape_md(pos_resp),
            md.text("Зарплата от: ", md.escape_md(sal)),
            md.escape_md(area),
            md.escape_md(pub_time),
            md.link("Ссылка", link),
            sep="\n",
        )
        await bot.send_message(msg.from_user.id, summary, parse_mode="MarkdownV2")
        await asyncio.sleep(2)


if __name__ == "__main__":
    executor.start_polling(dp)
