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
        "👥 /employees - Управление сотрудниками\n"
        "➕ /add_employee - Добавить сотрудника\n"
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


# ========= XODIM BOSHQARUV =========

class EmployeeStates(StatesGroup):
    """Xodim qo'shish/tahrirlash uchun holatlar"""
    waiting_full_name = State()
    waiting_position = State()
    waiting_phone = State()
    waiting_salary = State()
    waiting_telegram_id = State()
    # Edit states
    edit_waiting_field = State()
    edit_waiting_value = State()
    # Delete confirmation
    delete_confirmation = State()

@admin_router.message(Command("employees"))
async def list_employees(message: types.Message, session: AsyncSession):
    """Xodimlar ro'yxati"""
    try:
        from database.orm_query import orm_get_all_employees
        employees = await orm_get_all_employees(session)
        
        if not employees:
            await message.answer("📝 Hozircha birorta xodim mavjud emas.")
            return
        
        text = "👥 <b>XODIMLAR RO'YXATI</b>\n\n"
        for i, emp in enumerate(employees, 1):
            status = "✅" if emp.is_active else "❌"
            position = emp.position or "Belgilanmagan"
            salary = f"{emp.base_salary:,.0f} so'm" if emp.base_salary else "Belgilanmagan"
            
            text += f"{i}. {status} <b>{emp.full_name}</b>\n"
            text += f"   📱 ID: {emp.id} | 💼 {position}\n"
            text += f"   💰 {salary} | 📞 {emp.phone or 'Yo\'q'}\n\n"
        
        text += "⚡️ Boshqarish:\n"
        text += "• /edit_employee [ID] - Tahrirlash\n"
        text += "• /delete_employee [ID] - O'chirish\n"
        text += "• /toggle_employee [ID] - Faollashtirish/O'chirish"
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"❌ Xato: {str(e)}")

@admin_router.message(Command("add_employee"))
async def start_add_employee(message: types.Message, state: FSMContext):
    """Yangi xodim qo'shishni boshlash"""
    await state.set_state(EmployeeStates.waiting_full_name)
    await message.answer(
        "➕ <b>YANGI XODIM QO'SHISH</b>\n\n"
        "Xodimning to'liq ismini kiriting:\n"
        "(Misol: Ahmadov Ahmad Ahmadovich)\n\n"
        "❌ Bekor qilish uchun /cancel",
        parse_mode="HTML"
    )

@admin_router.message(StateFilter(EmployeeStates.waiting_full_name))
async def process_full_name(message: types.Message, state: FSMContext):
    """To'liq ismni qabul qilish"""
    full_name = message.text.strip()
    
    if len(full_name) < 2:
        await message.answer("❌ Ism juda qisqa! Qaytadan kiriting:")
        return
    
    await state.update_data(full_name=full_name)
    await state.set_state(EmployeeStates.waiting_position)
    
    await message.answer(
        "💼 <b>LAVOZIM</b>\n\n"
        "Xodimning lavozimini kiriting:\n"
        "(Misol: Dasturchi, Menejer, Dizayner va h.k.)\n\n"
        "❌ /cancel - Bekor qilish",
        parse_mode="HTML"
    )

@admin_router.message(StateFilter(EmployeeStates.waiting_position))
async def process_position(message: types.Message, state: FSMContext):
    """Lavozimni qabul qilish"""
    position = message.text.strip()
    
    await state.update_data(position=position)
    await state.set_state(EmployeeStates.waiting_phone)
    
    await message.answer(
        "📞 <b>TELEFON RAQAM</b>\n\n"
        "Telefon raqamini kiriting:\n"
        "(Misol: +998901234567)\n\n"
        "⏭ O'tkazib yuborish uchun: /skip\n"
        "❌ Bekor qilish uchun: /cancel",
        parse_mode="HTML"
    )

@admin_router.message(StateFilter(EmployeeStates.waiting_phone))
async def process_phone(message: types.Message, state: FSMContext):
    """Telefon raqamni qabul qilish"""
    if message.text == "/skip":
        phone = None
    else:
        phone = message.text.strip()
    
    await state.update_data(phone=phone)
    await state.set_state(EmployeeStates.waiting_salary)
    
    await message.answer(
        "💰 <b>OYLIK MAOSH</b>\n\n"
        "Oylik maoshni kiriting (faqat raqam):\n"
        "(Misol: 5000000)\n\n"
        "⏭ O'tkazib yuborish uchun: /skip\n"
        "❌ Bekor qilish uchun: /cancel",
        parse_mode="HTML"
    )

@admin_router.message(StateFilter(EmployeeStates.waiting_salary))
async def process_salary(message: types.Message, state: FSMContext):
    """Maoshni qabul qilish"""
    if message.text == "/skip":
        salary = None
    else:
        try:
            salary = float(message.text.strip())
            if salary < 0:
                await message.answer("❌ Maosh manfiy bo'lishi mumkin emas! Qaytadan kiriting:")
                return
        except ValueError:
            await message.answer("❌ Noto'g'ri format! Faqat raqam kiriting:")
            return
    
    await state.update_data(salary=salary)
    await state.set_state(EmployeeStates.waiting_telegram_id)
    
    await message.answer(
        "🤖 <b>TELEGRAM ID</b>\n\n"
        "Telegram ID raqamini kiriting:\n"
        "(Faqat raqam, masalan: 123456789)\n\n"
        "⏭ O'tkazib yuborish uchun: /skip\n"
        "❌ Bekor qilish uchun: /cancel",
        parse_mode="HTML"
    )

@admin_router.message(StateFilter(EmployeeStates.waiting_telegram_id))
async def process_telegram_id(message: types.Message, state: FSMContext, session: AsyncSession):
    """Telegram ID qabul qilish va xodimni saqlash"""
    if message.text == "/skip":
        telegram_id = None
    else:
        try:
            telegram_id = int(message.text.strip())
        except ValueError:
            await message.answer("❌ Noto'g'ri format! Faqat raqam kiriting:")
            return
    
    # Ma'lumotlarni olish
    data = await state.get_data()
    
    try:
        from database.orm_query import orm_add_employee
        
        # Xodim yaratish
        employee = await orm_add_employee(
            session=session,
            full_name=data['full_name'],
            position=data.get('position'),
            phone=data.get('phone'),
            base_salary=data.get('salary'),
            telegram_id=telegram_id
        )
        
        # Ma'lumotlarni ko'rsatish
        position = employee.position or "Belgilanmagan"
        phone = employee.phone or "Yo'q"
        salary = f"{employee.base_salary:,.0f} so'm" if employee.base_salary else "Belgilanmagan"
        tg_id = employee.telegram_id or "Yo'q"
        
        await message.answer(
            f"✅ <b>XODIM MUVAFFAQIYATLI QO'SHILDI!</b>\n\n"
            f"👤 <b>Ism:</b> {employee.full_name}\n"
            f"💼 <b>Lavozim:</b> {position}\n"
            f"📞 <b>Telefon:</b> {phone}\n"
            f"💰 <b>Maosh:</b> {salary}\n"
            f"🤖 <b>Telegram ID:</b> {tg_id}\n"
            f"🆔 <b>Xodim ID:</b> {employee.id}\n"
            f"📅 <b>Yaratilgan:</b> {employee.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"🔑 <b>QR kod UUID:</b> <code>{employee.uuid}</code>",
            parse_mode="HTML"
        )
        
    except Exception as e:
        await message.answer(f"❌ Xodim qo'shishda xato: {str(e)}")
    
    await state.clear()

# Cancel operatsiyasi uchun
@admin_router.message(Command("cancel"), StateFilter("*"))
async def cancel_operation(message: types.Message, state: FSMContext):
    """Har qanday operatsiyani bekor qilish"""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("🤷‍♂️ Bekor qilinadigan operatsiya yo'q.")
        return
    
    await state.clear()
    await message.answer(
        "❌ <b>OPERATSIYA BEKOR QILINDI</b>\n\n"
        "👨‍💼 Asosiy menu: /admin",
        parse_mode="HTML"
    )
