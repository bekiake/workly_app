import asyncio
import os

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

from middlewares.db import DataBaseSession

from database.engine import test_connection, session_maker

from handlers.user_private import user_private_router
from handlers.user_group import user_group_router
from handlers.admin_private import admin_router

# Импортируем планировщик отчетов
import sys
sys.path.append(os.path.join(os.path.dirname(__file__)))
try:
    from utils.scheduler import DailyReportScheduler
except ImportError:
    DailyReportScheduler = None
    print("⚠️ Планировщик отчетов недоступен")

# from common.bot_cmds_list import private


# ALLOWED_UPDATES = ['message', 'edited_message', 'callback_query']

bot = Bot(token=os.getenv('TOKEN'), parse_mode=ParseMode.HTML)
bot.my_admins_list = []

dp = Dispatcher()

dp.include_router(user_private_router)
dp.include_router(user_group_router)
dp.include_router(admin_router)


async def on_startup(bot):
    # Тестируем подключение к основной БД
    connection_ok = await test_connection()
    if not connection_ok:
        print("❌ Не удалось подключиться к БД. Убедитесь, что:")
        print("1. Основное приложение workly_app было запущено хотя бы раз")
        print("2. DATABASE_URL в .env правильно настроен")
        print("3. База данных доступна")
        return
    
    print("✅ Бот подключен к основной БД workly_app")
    
    # Запускаем планировщик ежедневных отчетов
    group_chat_id = os.getenv('REPORTS_GROUP_ID')
    if group_chat_id and DailyReportScheduler:
        scheduler = DailyReportScheduler(bot, group_chat_id)
        scheduler.start_scheduler()
        print(f"✅ Планировщик отчетов запущен для группы {group_chat_id}")
    else:
        print("⚠️ Планировщик отчетов не запущен. Проверьте REPORTS_GROUP_ID в .env")


async def on_shutdown(bot):
    print('бот лег')


async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    dp.update.middleware(DataBaseSession(session_pool=session_maker))

    await bot.delete_webhook(drop_pending_updates=True)
    # await bot.delete_my_commands(scope=types.BotCommandScopeAllPrivateChats())
    # await bot.set_my_commands(commands=private, scope=types.BotCommandScopeAllPrivateChats())
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

asyncio.run(main())
