import logging
import sys
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.utils.markdown import hbold
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

# Настройки вебхука
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")  # Ваш домен или IP-адрес с HTTPS
WEBHOOK_PATH = '/webhook'  # Путь для вебхука
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Настройки веб-сервера
WEBAPP_HOST = '0.0.0.0'  # Хост для веб-приложения
WEBAPP_PORT = 8000       # Порт для веб-приложения

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

async def on_startup(bot: Bot) -> None:
    # Устанавливаем вебхук при запуске
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(bot: Bot) -> None:
    # Удаляем вебхук при завершении работы
    await bot.delete_webhook()

def main() -> None:
    dp = Dispatcher()
    dp.include_router(router)

    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # Регистрируем функции запуска и завершения
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Создаем веб-приложение aiohttp
    app = web.Application()

    # Регистрируем обработчик вебхуков
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)

    # Настраиваем приложение
    setup_application(app, dp, bot=bot)

    # Запускаем веб-сервер
    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    main()
