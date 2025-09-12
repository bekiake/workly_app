from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_employee_selection_keyboard(employees):
    """Создать клавиатуру для выбора сотрудника"""
    builder = InlineKeyboardBuilder()
    
    for employee in employees:
        builder.add(InlineKeyboardButton(
            text=employee.full_name,
            callback_data=f"select_employee_{employee.id}"
        ))
    
    # Добавляем кнопку "Я не в списке"
    builder.add(InlineKeyboardButton(
        text="👤 Меня нет в списке",
        callback_data="not_in_list"
    ))
    
    builder.adjust(1)  # По одной кнопке в ряд
    return builder.as_markup()


def get_attendance_keyboard():
    """Создать клавиатуру для отметки посещаемости"""
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="✅ Пришел на работу",
        callback_data="attendance_in"
    ))
    
    builder.add(InlineKeyboardButton(
        text="❌ Ушел с работы", 
        callback_data="attendance_out"
    ))
    
    builder.adjust(1)  # По одной кнопке в ряд для лучшей видимости
    return builder.as_markup()


def get_location_request_keyboard():
    """Клавиатура с объяснением про live location"""
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

