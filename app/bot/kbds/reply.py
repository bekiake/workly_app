from aiogram.types import KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_location_keyboard():
    """Клавиатура для запроса live location"""
    builder = ReplyKeyboardBuilder()
    
    # Кнопка для отправки live location
    builder.add(KeyboardButton(
        text="📍 Отправить Live Location",
        request_location=True
    ))
    
    # Кнопка отмены
    builder.add(KeyboardButton(text="❌ Отмена"))
    
    builder.adjust(1)  # По одной кнопке в ряд
    return builder.as_markup(
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_main_menu():
    """Основное меню после регистрации"""
    builder = ReplyKeyboardBuilder()
    
    builder.add(KeyboardButton(text="📊 Мой статус"))
    builder.add(KeyboardButton(text="ℹ️ Помощь"))
    
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


