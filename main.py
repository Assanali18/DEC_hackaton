import logging
import os
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, Router, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.utils.markdown import hbold
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from tortoise import Tortoise
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State

from models import Employee

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")
WEBHOOK_PATH = '/webhook'
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

WEBAPP_HOST = '0.0.0.0'
WEBAPP_PORT = 8000

DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT", 5432)
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = f"postgres://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

storage = MemoryStorage()
dp = Dispatcher(storage=storage)

router = Router()


class EmployeeForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_surname = State()
    waiting_for_email = State()


@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Я ищу работу", callback_data="job_seeker")],
        [InlineKeyboardButton(text="Я работодатель", callback_data="employer")]
    ])
    print("ID", message.from_user.id)

    await message.answer(f"Hello, {hbold(message.from_user.full_name)}!\nКто вы?", reply_markup=keyboard)

@router.callback_query(lambda callback: callback.data == "job_seeker")
async def job_seeker_handler(callback: CallbackQuery, state: types.FSMContext):
    user_id = callback.from_user.id
    username = callback.from_user.username

    # Создаем или получаем запись о пользователе
    employee, created = await Employee.get_or_create(tg_id=user_id, defaults={'tg_username': username})

    await callback.message.answer("Пожалуйста, введите ваше имя:")
    await state.set_state(EmployeeForm.waiting_for_name)

    await callback.answer()

@router.message(EmployeeForm.waiting_for_name)
async def process_name(message: Message, state: types.FSMContext):
    name = message.text.strip()
    user_id = message.from_user.id

    # Обновляем запись в базе данных
    await Employee.filter(tg_id=user_id).update(name=name)

    await message.answer("Введите вашу фамилию:")
    await state.set_state(EmployeeForm.waiting_for_surname)

@router.message(EmployeeForm.waiting_for_surname)
async def process_surname(message: Message, state: types.FSMContext):
    surname = message.text.strip()
    user_id = message.from_user.id

    # Обновляем запись в базе данных
    await Employee.filter(tg_id=user_id).update(surname=surname)

    await message.answer("Введите ваш email:")
    await state.set_state(EmployeeForm.waiting_for_email)

@router.message(EmployeeForm.waiting_for_email)
async def process_email(message: Message, state: types.FSMContext):
    email = message.text.strip()
    user_id = message.from_user.id

    # Обновляем запись в базе данных
    await Employee.filter(tg_id=user_id).update(email=email)

    await message.answer("Спасибо! Ваши данные сохранены.")
    await state.clear()

@router.message()
async def echo_handler(message: Message) -> None:
    await message.answer("Пожалуйста, используйте /start для начала.")

dp.include_router(router)

async def init_db():
    await Tortoise.init(
        db_url=DATABASE_URL,
        modules={'models': ['__main__']}  # Указываем, где находятся наши модели
    )
    await Tortoise.generate_schemas()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logging.info("База данных подключена.")

    await bot.set_webhook(WEBHOOK_URL)
    logging.info("Webhook установлен.")

    yield

    await bot.delete_webhook()
    await bot.session.close()
    logging.info("Webhook удален.")

    await Tortoise.close_connections()
    logging.info("Подключение к базе данных закрыто.")

app = FastAPI(lifespan=lifespan)

@app.post(WEBHOOK_PATH)
async def telegram_webhook(update: dict):
    telegram_update = types.Update(**update)
    await dp.feed_update(bot, telegram_update)
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=WEBAPP_HOST, port=WEBAPP_PORT)
