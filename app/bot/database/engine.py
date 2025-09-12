import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Удаляем импорт моделей бота, используем модели основного приложения
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from app.core.database import Base

# Подключаемся к основной БД приложения
# Используем DATABASE_URL из .env основного приложения
DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('DB_URL') or "postgresql+asyncpg://username:password@localhost/workly_db"

engine = create_async_engine(DATABASE_URL, echo=False)

session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def test_connection():
    """Тестирование подключения к БД"""
    try:
        async with session_maker() as session:
            # Простой тест подключения
            await session.execute("SELECT 1")
            print("✅ Успешное подключение к основной БД workly_app")
            return True
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        return False


# Убираем create_db и drop_db функции, так как БД уже должна быть создана основным приложением
