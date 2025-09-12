import asyncio
import os
import sys
import logging
from datetime import datetime

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Bot uchun path qo'shish
bot_root = os.path.dirname(os.path.abspath(__file__))
# Bot root papkada bo'lganligimiz uchun app papkasiga yo'l
app_path = os.path.join(bot_root, "app")
bot_app_path = os.path.join(bot_root, "app", "bot")
sys.path.insert(0, bot_root)  # Root directory
sys.path.insert(0, app_path)  # app directory
sys.path.insert(0, bot_app_path)  # app/bot directory

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

# Bot modullari
from app.bot.middlewares.db import DataBaseSession
from app.bot.middlewares.logging import LoggingMiddleware, DetailedLoggingMiddleware
from app.bot.common.bot_cmds_list import private, admin

# Database engine import qilish
try:
    from app.bot.database.engine import session_maker
    print("✅ Database engine import qilindi")
except ImportError as e:
    print(f"❌ Database engine import xatosi: {e}")
    session_maker = None

# Test connection funksiyasini alohida import qilish
async def test_db_connection():
    """Database connection test"""
    if not session_maker:
        print("❌ Session maker mavjud emas")
        return False
    
    try:
        from sqlalchemy import text
        async with session_maker() as session:
            await session.execute(text("SELECT 1"))
        print("✅ Database connection muvaffaqiyatli")
        return True
    except Exception as e:
        print(f"❌ Database connection xatosi: {e}")
        return False

# Handlers
from app.bot.handlers.user_private import user_private_router
from app.bot.handlers.admin_private import admin_router

# Импортируем планировщик отчетов
try:
    from app.bot.utils.scheduler import DailyReportScheduler
except ImportError:
    DailyReportScheduler = None
    print("⚠️ Планировщик отчетов недоступен")

ALLOWED_UPDATES = ['message', 'edited_message', 'callback_query']

# Bot tokenini tekshirish
bot_token = os.getenv('BOT_TOKEN', "7979956333:AAFUrZuOTgZ9L8-ygchRYBz0p2FKB9KUokk")
if not bot_token:
    print("❌ BOT_TOKEN .env faylida topilmadi!")
    print("📝 .env fayliga BOT_TOKEN=your_token_here qo'shing")
    exit(1)

# Yangi aiogram 3.7.0+ versiyasi uchun
bot = Bot(
    token=bot_token,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)
bot.my_admins_list = [1210278389]

dp = Dispatcher()

# Middlewares ni qo'shish (tartib muhim!)
dp.message.middleware(LoggingMiddleware())
dp.callback_query.middleware(LoggingMiddleware())
dp.update.middleware(DataBaseSession(session_pool=session_maker))

dp.include_router(user_private_router)
dp.include_router(admin_router)

async def on_startup(bot):
    logger.info("🚀 Бот запускается...")
    
    # Тестируем подключение к основной БД
    connection_ok = await test_db_connection()
    if not connection_ok:
        logger.error("❌ Не удалось подключиться к БД")
        print("❌ Не удалось подключиться к БД. Убедитесь, что:")
        print("1. Основное приложение workly_app было запущено хотя бы раз")
        print("2. DATABASE_URL в .env правильно настроен")
        print("3. База данных доступна")
        return
    
    logger.info("✅ Бот подключен к основной БД workly_app")
    logger.info("📋 Логирование всех действий активировано")
    print("✅ Бот подключен к основной БД workly_app")

async def on_shutdown(bot):
    logger.info("🛑 Бот останавливается...")
    print('бот лег')

async def main():
    try:
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)

        # Webhook o'chirish
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("✅ Webhook удален")
        except Exception as e:
            logger.warning(f"⚠️ Webhook: {e}")

        # Comandalar o'rnatish
        try:
            await bot.set_my_commands(commands=private, scope=types.BotCommandScopeAllPrivateChats())
            logger.info("📋 Команды установлены")
        except Exception as e:
            logger.warning(f"⚠️ Команды: {e}")

        # Admin comandalar
        try:
            for admin_id in bot.my_admins_list:
                await bot.set_my_commands(commands=admin, scope=types.BotCommandScopeChat(chat_id=admin_id))
            logger.info(f"👑 Админ команды установлены")
        except Exception as e:
            logger.warning(f"⚠️ Админ команды: {e}")

        # Polling boshlash
        logger.info("🚀 Polling запускается...")
        print("🚀 Бот ишга тушди!")
        
        await dp.start_polling(
            bot, 
            allowed_updates=ALLOWED_UPDATES,
            polling_timeout=10,
            drop_pending_updates=True
        )
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка бота: {e}", exc_info=True)
        print(f"❌ Бот ишга тушишда хатолик: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
        print("👋 Бот тўхтатилди")
