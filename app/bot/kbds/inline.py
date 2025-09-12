from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import calendar


def get_employee_selection_keyboard(employees):
    """Создание клавиатуры для выбора сотрудника"""
    builder = InlineKeyboardBuilder()
    
    for employee in employees:
        builder.add(InlineKeyboardButton(
            text=employee.full_name,
            callback_data=f"select_employee_{employee.id}"
        ))
    
    # Добавляем кнопку "Меня нет в списке"
    builder.add(InlineKeyboardButton(
        text="👤 Меня нет в списке",
        callback_data="not_in_list"
    ))
    
    builder.adjust(1)  # По одной кнопке в ряду
    return builder.as_markup()


def get_attendance_keyboard():
    """Создание клавиатуры для отметки посещаемости"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="✅ Пришел",
        callback_data="attendance_in"
    ))
    
    builder.add(InlineKeyboardButton(
        text="❌ Ушел", 
        callback_data="attendance_out"
    ))
    
    builder.adjust(1)  # По одной кнопке в ряду для лучшего вида
    return builder.as_markup()


def get_checkout_keyboard():
    """Клавиатура только с кнопкой ухода (после того как уже пришел)"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="❌ Ушел", 
        callback_data="attendance_out"
    ))
    
    builder.adjust(1)
    return builder.as_markup()


def get_smart_attendance_keyboard(already_checked_in_today: bool = False, already_checked_out_today: bool = False):
    """Умная клавиатура, показывающая нужные кнопки в зависимости от статуса"""
    builder = InlineKeyboardBuilder()
    
    # Если сегодня еще не отметился как "пришел"
    if not already_checked_in_today:
        builder.add(InlineKeyboardButton(
            text="✅ Пришел",
            callback_data="attendance_in"
        ))
    
    # Если пришел, но еще не ушел
    if already_checked_in_today and not already_checked_out_today:
        builder.add(InlineKeyboardButton(
            text="❌ Ушел", 
            callback_data="attendance_out"
        ))
    
    # Если обе отметки уже есть, показываем обычное меню
    if already_checked_in_today and already_checked_out_today:
        builder.add(InlineKeyboardButton(
            text="✅ Пришел",
            callback_data="attendance_in"
        ))
        builder.add(InlineKeyboardButton(
            text="❌ Ушел", 
            callback_data="attendance_out"
        ))
    
    builder.adjust(1)
    return builder.as_markup()


def get_location_request_keyboard():
    """Клавиатура с пояснениями о Live Location"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="📍 Как отправить Live Location?",
        callback_data="how_to_location"
    ))
    
    builder.add(InlineKeyboardButton(
        text="🔄 Я отправил location",
        callback_data="location_sent"
    ))
    
    builder.adjust(1)
    return builder.as_markup()


def get_callback_btns(*, btns: dict[str, str], sizes: tuple[int] = (2,)):
    """Универсальная функция для создания inline клавиатур"""
    keyboard = InlineKeyboardBuilder()

    for text, data in btns.items():
        keyboard.add(InlineKeyboardButton(text=text, callback_data=data))

    return keyboard.adjust(*sizes).as_markup()


def get_admin_reports_keyboard():
    """Клавиатура админской панели для отчетов"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="📊 Отчеты посещаемости",
        callback_data="admin_reports"
    ))
    
    builder.add(InlineKeyboardButton(
        text="📈 Статистика",
        callback_data="admin_stats"
    ))
    
    builder.adjust(1)
    return builder.as_markup()


def get_month_selection_keyboard(year: int, month: int):
    """Клавиатура выбора месяца для отчетов"""
    
    builder = InlineKeyboardBuilder()
    
    month_name = calendar.month_name[month]
    
    # Кнопки для навигации по месяцам
    builder.add(InlineKeyboardButton(
        text="⬅️",
        callback_data=f"change_period_{year}_{month}_prev"
    ))
    
    builder.add(InlineKeyboardButton(
        text=f"{month_name} {year}",
        callback_data="current_period"
    ))
    
    builder.add(InlineKeyboardButton(
        text="➡️",
        callback_data=f"change_period_{year}_{month}_next"
    ))
    
    # Типы отчетов
    builder.add(InlineKeyboardButton(
        text="📋 Простой отчет",
        callback_data=f"report_simple_{year}_{month}"
    ))
    
    builder.add(InlineKeyboardButton(
        text="📊 Подробный отчет (с зарплатой)",
        callback_data=f"report_detailed_{year}_{month}"
    ))
    
    builder.adjust(3, 2)
    return builder.as_markup()

