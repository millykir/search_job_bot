import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import func
from database.db import SessionLocal
from database.models import Vacancy, UserRating

load_dotenv()
TOKEN = os.getenv("TOKEN")

bot = Bot(token=TOKEN)
router = Router()
dp = Dispatcher()
dp.include_router(router)

user_active_vacancies = {}
user_tasks = {}
users_no_vacancies = set()


async def get_unrated_vacancy(user_id: int):
    session: Session = SessionLocal()
    try:
        rated_vacancies = session.query(UserRating.vacancy_id).filter(
            UserRating.user_id == user_id
        ).all()
        rated_vacancy_ids = {vacancy_id for (vacancy_id,) in rated_vacancies}

        vacancy = session.query(Vacancy)\
            .filter(Vacancy.id.notin_(rated_vacancy_ids))\
            .order_by(func.random())\
            .first()
        return vacancy
    except Exception as e:
        logging.error(f"Ошибка при получении вакансии: {e}")
        return None
    finally:
        session.close()


async def send_vacancy(user_id: int):
    if user_id in user_active_vacancies:
        vacancy_id = user_active_vacancies[user_id]
        session: Session = SessionLocal()
        vacancy = session.query(Vacancy).filter(
            Vacancy.id == vacancy_id).first()
        session.close()
        if vacancy:
            description = vacancy.description.replace(
                "<highlighttext>", "<b>").replace(
                "</highlighttext>", "</b>")
            text = f"{vacancy.title}\n\n{description}\n\n{vacancy.link}"
            markup = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="👍", callback_data=f"like_{
                                vacancy.id}"), InlineKeyboardButton(
                            text="👎", callback_data=f"dislike_{
                                vacancy.id}"), InlineKeyboardButton(
                            text="➖", callback_data=f"neutral_{
                                vacancy.id}")]])
            await bot.send_message(user_id, text, reply_markup=markup, parse_mode="HTML")
        else:
            del user_active_vacancies[user_id]
        return

    try:
        vacancy = await get_unrated_vacancy(user_id)
        if not vacancy:
            if user_id not in users_no_vacancies:
                await bot.send_message(user_id, "Больше нет доступных вакансий. Ждите новых обновлений.")
                users_no_vacancies.add(user_id)
            return

        description = vacancy.description.replace(
            "<highlighttext>", "<b>").replace(
            "</highlighttext>", "</b>")
        text = f"{vacancy.title}\n\n{description}\n\n{vacancy.link}"
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="👍", callback_data=f"like_{
                            vacancy.id}"), InlineKeyboardButton(
                        text="👎", callback_data=f"dislike_{
                            vacancy.id}"), InlineKeyboardButton(
                                text="➖", callback_data=f"neutral_{
                                    vacancy.id}")]])

        await bot.send_message(user_id, text, reply_markup=markup, parse_mode="HTML")
        user_active_vacancies[user_id] = vacancy.id
    except Exception as e:
        logging.error(
            f"Ошибка при отправке вакансии пользователю {user_id}: {e}")


@router.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_tasks:
        await message.answer("Бот уже запущен и отправляет вакансии.")
        return

    await message.answer("Привет! Я буду отправлять тебе вакансии каждые 5 минут! Оценивай их, чтобы получать новые.")

    async def send_vacancies_periodically():
        while True:
            await send_vacancy(user_id)
            await asyncio.sleep(300)

    task = asyncio.create_task(send_vacancies_periodically())
    user_tasks[user_id] = task


@router.message(Command("stop"))
async def stop(message: types.Message):
    user_id = message.from_user.id
    task = user_tasks.get(user_id)
    if task:
        task.cancel()
        del user_tasks[user_id]
        if user_id in user_active_vacancies:
            del user_active_vacancies[user_id]
        await message.answer("Бот остановлен. Чтобы запустить его снова, отправьте /start.")
    else:
        await message.answer("Бот не запущен.")


@router.callback_query(
    lambda c: c.data is not None and c.data.startswith(
        ("like_", "dislike_", "neutral_")))
async def handle_rating(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    parts = callback_query.data.split("_")
    rating = parts[0]
    vacancy_id = int(parts[1])

    session: Session = SessionLocal()
    session.add(
        UserRating(
            user_id=user_id,
            vacancy_id=vacancy_id,
            rating=rating))
    session.commit()
    session.close()

    if user_active_vacancies.get(user_id) == vacancy_id:
        del user_active_vacancies[user_id]

    await callback_query.answer("Твой отзыв сохранен!")


async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
