import logging
import os

from aiohttp import ClientSession
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.utils.markdown import hbold
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from tortoise import Tortoise
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

# DATABASE_URL = f"postgres://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

router = Router()

from models import SendMessageRequest


# async def init_db():
#     await Tortoise.init(
#         db_url=DATABASE_URL,
#         modules={'models': ['models']}
#     )
#
#     await Tortoise.generate_schemas()

@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Я ищу работу", callback_data="job_seeker")],
        [InlineKeyboardButton(text="Я работодатель", callback_data="employer")]
    ])
    print("ID", message.from_user.id)

    await message.answer(f"Hello, {hbold(message.from_user.full_name)}!\nКто вы?", reply_markup=keyboard)


@router.callback_query(lambda callback: callback.data in ["job_seeker", "employer"])
async def callback_handler(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    username = callback.from_user.username
    role = "candidate" if callback.data == "job_seeker" else "employer"

    payload = {
        "username": username or "unknown",  # Обработать случай, если username отсутствует
        "role": role,
        "id": str(user_id)
    }

    async with ClientSession() as session:
        try:
            async with session.post(
                    "https://674b214471933a4e88548354.mockapi.io/api/users/",
                    json=payload
            ) as response:
                if response.status == 201:  # HTTP 201 Created
                    await callback.message.answer(f"Ваши данные сохранены как: {role}.")
                else:
                    error_message = await response.text()
                    await callback.message.answer(f"Ошибка при сохранении данных: {error_message}")
        except Exception as e:
            await callback.message.answer(f"Не удалось отправить данные: {e}")

    await callback.answer()

@router.message()
async def echo_handler(message: Message) -> None:
    try:
        await message.send_copy(chat_id=message.chat.id)
    except TypeError:
        await message.answer("Nice try!")

dp.include_router(router)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # await init_db()
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

@app.post("/send_message")
async def send_message(request: SendMessageRequest):
    try:
        await bot.send_message(chat_id=request.chat_id, text=request.text)
        return {"status": "success", "message": "Message sent successfully"}
    except Exception as e:
        logging.error(f"Error sending message: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=WEBAPP_HOST, port=WEBAPP_PORT)
