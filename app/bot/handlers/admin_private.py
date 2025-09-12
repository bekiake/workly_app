from aiogram import F, Router, types
from aiogram.filters import Command, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import date, datetime, timedelta
import os

from sqlalchemy.ext.asyncio import AsyncSession

from filters.chat_types import ChatTypeFilter, IsAdmin
from database.orm_query import orm_get_daily_attendance_report
import sys
import os

# Добавляем путь к utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
try:
    from utils.reports import format_daily_report, format_summary_stats
    from utils.scheduler import send_test_report
except ImportError:
    def format_daily_report(data):
        return "Отчет недоступен"
    def format_summary_stats(data):
        return "Статистика недоступна"
    async def send_test_report(bot, group_id):
        pass



admin_router = Router()
admin_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())




@admin_router.message(Command("admin"))
async def admin_features(message: types.Message):
    await message.answer(
        "👨‍💼 АДМИН ПАНЕЛЬ\n\n"
        "Доступные команды:\n"
        "📊 /report - Отчет за сегодня\n"
        "📅 /report_date YYYY-MM-DD - Отчет за конкретную дату\n"
        "📈 /week_stats - Статистика за неделю\n"
        "🧪 /test_report - Отправить тестовый отчет в группу\n"
        "⚙️ /settings - Настройки бота"
    )


@admin_router.message(Command("test_report"))
async def test_group_report(message: types.Message):
    """Отправляет тестовый отчет в группу"""
    group_chat_id = os.getenv('REPORTS_GROUP_ID')
    if not group_chat_id:
        await message.answer("❌ ID группы для отчетов не настроен. Проверьте REPORTS_GROUP_ID в .env")
        return
    
    try:
        bot = message.bot
        await send_test_report(bot, group_chat_id)
        await message.answer(f"✅ Тестовый отчет отправлен в группу {group_chat_id}")
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке тестового отчета: {str(e)}")


@admin_router.message(Command("report"))
async def daily_report_today(message: types.Message, session: AsyncSession):
    """Отчет за сегодня"""
    try:
        report_data = await orm_get_daily_attendance_report(session)
        report_text = format_daily_report(report_data)
        await message.answer(report_text)
    except Exception as e:
        await message.answer(f"❌ Ошибка при генерации отчета: {str(e)}")


@admin_router.message(Command("report_date"))
async def daily_report_date(message: types.Message, session: AsyncSession):
    """Отчет за конкретную дату"""
    try:
        # Извлекаем дату из команды
        command_parts = message.text.split()
        if len(command_parts) < 2:
            await message.answer(
                "❌ Неверный формат команды!\n"
                "Используйте: /report_date YYYY-MM-DD\n"
                "Например: /report_date 2025-09-11"
            )
            return
        
        date_str = command_parts[1]
        report_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        report_data = await orm_get_daily_attendance_report(session, report_date)
        report_text = format_daily_report(report_data)
        await message.answer(report_text)
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат даты!\n"
            "Используйте формат: YYYY-MM-DD\n"
            "Например: 2025-09-11"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка при генерации отчета: {str(e)}")


@admin_router.message(Command("week_stats"))
async def week_statistics(message: types.Message, session: AsyncSession):
    """Статистика за неделю"""
    try:
        today = date.today()
        week_stats = []
        
        for i in range(7):
            report_date = today - timedelta(days=i)
            # Пропускаем выходные (суббота=5, воскресенье=6)
            if report_date.weekday() < 5:  # Понедельник-Пятница
                report_data = await orm_get_daily_attendance_report(session, report_date)
                stats_line = format_summary_stats(report_data)
                week_stats.append(stats_line)
        
        message_text = "📈 СТАТИСТИКА ЗА НЕДЕЛЮ\n\n" + "\n".join(week_stats)
        await message.answer(message_text)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при генерации статистики: {str(e)}")

