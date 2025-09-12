from aiogram import F, Router, types
from aiogram.filters import Command, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, FSInputFile
from datetime import date, datetime, timedelta
import os
import calendar

from sqlalchemy.ext.asyncio import AsyncSession

from filters.chat_types import ChatTypeFilter, IsAdmin
from database.orm_query import orm_get_daily_attendance_report
from kbds.inline import get_admin_reports_keyboard, get_month_selection_keyboard

import sys
import os

# Добавляем путь к utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
try:
    from utils.reports import format_daily_report, format_summary_stats
except ImportError:
    def format_daily_report(data):
        return "Отчет недоступен"
    def format_summary_stats(data):
        return "Статистика недоступна"

# Добавляем путь к app для импорта сервисов отчетов
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
try:
    from app.services.reports import generate_detailed_monthly_report, generate_monthly_report
except ImportError:
    async def generate_detailed_monthly_report(session, year, month):
        return None
    async def generate_monthly_report(session, year, month):
        return None

admin_router = Router()
admin_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())


@admin_router.message(Command("admin"))
async def admin_features(message: types.Message):
    """Главное меню админа"""
    await message.answer(
        "👨‍💼 <b>АДМИН ПАНЕЛЬ</b>\n\n"
        "Доступные команды:\n"
        "📊 /report - Отчет за сегодня\n"
        "📅 /report_date YYYY-MM-DD - Отчет за конкретную дату\n"
        "📈 /week_stats - Статистика за неделю\n"
        "📋 /reports - Excel отчеты\n"
        "⚙️ /settings - Настройки бота",
        parse_mode="HTML"
    )


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


# ============== EXCEL ОТЧЕТЫ ==============

@admin_router.message(Command("reports"))
async def admin_reports_panel(message: Message, session: AsyncSession):
    """Панель Excel отчетов для админа"""
    await message.answer(
        "📊 <b>ПАНЕЛЬ EXCEL ОТЧЕТОВ</b>\n\n"
        "Здесь вы можете скачать отчеты в формате Excel:\n\n"
        "• <b>Простой отчет</b> - только данные посещаемости\n"
        "• <b>Подробный отчет</b> - с расчетом зарплат и штрафов\n\n"
        "💰 <i>В подробном отчете штраф за опоздание составляет 1% от месячной зарплаты за каждый день опоздания</i>",
        reply_markup=get_admin_reports_keyboard(),
        parse_mode="HTML"
    )

@admin_router.callback_query(F.data == "admin_reports")
async def admin_reports_menu(callback: CallbackQuery):
    """Меню отчетов для админа"""
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    await callback.message.edit_text(
        "📊 <b>EXCEL ОТЧЕТЫ</b>\n\n"
        "Выберите тип отчета:\n\n"
        "• <b>Простой отчет</b> - только посещаемость\n"
        "• <b>Подробный отчет</b> - с зарплатами и штрафами\n\n"
        "💡 <i>Штраф: 1% от зарплаты за каждый день опоздания</i>",
        reply_markup=get_month_selection_keyboard(current_year, current_month),
        parse_mode="HTML"
    )

@admin_router.callback_query(F.data.startswith("report_"))
async def handle_report_generation(callback: CallbackQuery, session: AsyncSession):
    """Генерация Excel отчетов"""
    # Парсим данные: report_type_year_month
    data_parts = callback.data.split("_")
    report_type = data_parts[1]  # "detailed" или "simple"
    year = int(data_parts[2])
    month = int(data_parts[3])
    
    # Русские названия месяцев
    month_names = [
        "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    month_name_ru = month_names[month]
    
    # Показываем сообщение о генерации
    await callback.message.edit_text(
        f"⏳ <b>Генерируется отчет...</b>\n\n"
        f"📅 Период: {month_name_ru} {year}\n"
        f"📊 Тип: {'Подробный с зарплатами' if report_type == 'detailed' else 'Простой'}\n\n"
        f"⏰ Пожалуйста, подождите...",
        parse_mode="HTML"
    )
    
    try:
        # Генерируем отчет
        if report_type == "detailed":
            file_path = await generate_detailed_monthly_report(session, year, month)
            report_name = f"Подробный отчет за {month_name_ru} {year}"
            description = "с расчетом зарплат и штрафами за опоздания"
        else:
            file_path = await generate_monthly_report(session, year, month)
            report_name = f"Отчет посещаемости за {month_name_ru} {year}"
            description = "простой отчет посещаемости"
        
        # Проверяем файл
        if not file_path or not os.path.exists(file_path):
            await callback.message.edit_text(
                "❌ <b>Ошибка создания отчета</b>\n\n"
                "Возможные причины:\n"
                "• Нет данных за указанный период\n"
                "• Ошибка доступа к базе данных\n"
                "• Проблема с созданием файла\n\n"
                "Попробуйте выбрать другой период.",
                parse_mode="HTML"
            )
            return
        
        # Отправляем файл
        document = FSInputFile(file_path)
        await callback.message.answer_document(
            document,
            caption=f"📊 <b>{report_name}</b>\n\n"
                   f"📅 Период: {month_name_ru} {year}\n"
                   f"📋 Тип: {description}\n"
                   f"🕐 Создан: {datetime.now().strftime('%d.%m.%Y в %H:%M')}\n\n"
                   f"💰 {'Штраф за опоздание: 1% от зарплаты за каждый день' if report_type == 'detailed' else 'Данные только по посещаемости'}",
            parse_mode="HTML"
        )
        
        # Обновляем сообщение
        await callback.message.edit_text(
            f"✅ <b>Отчет успешно создан!</b>\n\n"
            f"📊 {report_name}\n"
            f"📋 {description.capitalize()}\n\n"
            f"📎 Файл отправлен выше ⬆️\n\n"
            f"🔄 Можете создать еще один отчет",
            parse_mode="HTML"
        )
        
        # Удаляем временный файл
        try:
            os.remove(file_path)
        except:
            pass
        
    except Exception as e:
        await callback.message.edit_text(
            f"❌ <b>Ошибка при создании отчета:</b>\n\n"
            f"<code>{str(e)}</code>\n\n"
            f"Обратитесь к разработчику для решения проблемы.",
            parse_mode="HTML"
        )

@admin_router.callback_query(F.data.startswith("change_period_"))
async def change_report_period(callback: CallbackQuery):
    """Изменение периода отчета"""
    # Парсим данные: change_period_year_month_direction
    data_parts = callback.data.split("_")
    year = int(data_parts[2])
    month = int(data_parts[3])
    direction = data_parts[4]  # "prev" или "next"
    
    # Изменяем период
    if direction == "prev":
        if month == 1:
            year -= 1
            month = 12
        else:
            month -= 1
    else:  # next
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
    
    # Обновляем сообщение
    await callback.message.edit_text(
        "📊 <b>EXCEL ОТЧЕТЫ</b>\n\n"
        "Выберите тип отчета:\n\n"
        "• <b>Простой отчет</b> - только посещаемость\n"
        "• <b>Подробный отчет</b> - с зарплатами и штрафами\n\n"
        "💡 <i>Штраф: 1% от зарплаты за каждый день опоздания</i>",
        reply_markup=get_month_selection_keyboard(year, month),
        parse_mode="HTML"
    )

@admin_router.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback: CallbackQuery, session: AsyncSession):
    """Общая статистика для админа"""
    await callback.message.edit_text(
        "📈 <b>ОБЩАЯ СТАТИСТИКА</b>\n\n"
        "Эта функция будет добавлена в следующих версиях.\n\n"
        "Пока что используйте:\n"
        "• /report - отчет за сегодня\n"
        "• /week_stats - статистика за неделю\n"
        "• /reports - Excel отчеты",
        parse_mode="HTML"
    )

@admin_router.message(Command("settings"))
async def admin_settings(message: types.Message):
    """Настройки бота"""
    await message.answer(
        "⚙️ <b>НАСТРОЙКИ БОТА</b>\n\n"
        "Функция в разработке...\n\n"
        "Планируемые настройки:\n"
        "• Время работы\n"
        "• Штрафы и бонусы\n"
        "• Уведомления\n"
        "• Резервное копирование",
        parse_mode="HTML"
    )
