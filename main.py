import logging
import os
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, Router, types

from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.utils.markdown import hbold

from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")
WEBHOOK_PATH = '/webhook'
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

WEBAPP_HOST = '0.0.0.0'
WEBAPP_PORT = 8000

# Инициализируем бота и диспетчер
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Инициализируем роутер
router = Router()

@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Я ищу работу", callback_data="job_seeker")],
        [InlineKeyboardButton(text="Я работодатель", callback_data="employer")]
    ])
    await message.answer(f"Hello, {hbold(message.from_user.full_name)}!\nКто вы?", reply_markup=keyboard)

@router.callback_query(lambda callback: callback.data in ["job_seeker", "employer"])
async def callback_handler(callback: CallbackQuery) -> None:
    if callback.data == "job_seeker":
        await callback.message.answer("Вы выбрали: Я ищу работу.")
    elif callback.data == "employer":
        await callback.message.answer("Вы выбрали: Я работодатель.")

    await callback.answer()

@router.message()
async def echo_handler(message: Message) -> None:
    try:
        await message.send_copy(chat_id=message.chat.id)
    except TypeError:
        await message.answer("Nice try!")

# Включаем роутер в диспетчер
dp.include_router(router)

# Инициализируем FastAPI приложение
app = FastAPI()

# Обработчик вебхуков от Telegram
@app.post(WEBHOOK_PATH)
async def telegram_webhook(update: dict):
    telegram_update = types.Update(**update)
    await dp.feed_update(bot, telegram_update)
    return {"ok": True}

# Функция запуска
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)
    logging.info("Webhook установлен.")

# Функция остановки
async def on_shutdown():
    await bot.delete_webhook()
    await bot.session.close()
    logging.info("Webhook удален.")

# Добавляем события старта и остановки
app.on_event("startup")(on_startup)
app.on_event("shutdown")(on_shutdown)

# Добавляем POST-метод для приема внешних запросов
@app.post("/send_message")
async def send_message_endpoint(request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    text = data.get("text")

    if not user_id or not text:
        return {"status": "error", "message": "Параметры 'user_id' и 'text' обязательны."}

    try:
        await bot.send_message(chat_id=user_id, text=text)
        return {"status": "success", "message": "Сообщение отправлено."}
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения: {e}")
        return {"status": "error", "message": "Не удалось отправить сообщение."}

# Запускаем приложение
if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=WEBAPP_HOST, port=WEBAPP_PORT)
