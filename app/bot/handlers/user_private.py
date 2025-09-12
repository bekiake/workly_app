from aiogram import F, types, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from sqlalchemy.ext.asyncio import AsyncSession
from database.orm_query import ( 
    orm_add_user,
    orm_get_all_employees,
    orm_get_employee_by_telegram_id,
    orm_link_employee_telegram,
    orm_create_attendance
)

from filters.chat_types import ChatTypeFilter
from kbds.inline import get_employee_selection_keyboard, get_attendance_keyboard, get_location_request_keyboard
from kbds.reply import get_location_keyboard, get_main_menu
from app.models.attendance import CheckTypeEnum
import sys
import os

# Добавляем путь к utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
try:
    from utils.location import is_at_office, format_distance, validate_live_location_security, is_location_realistic
except ImportError:
    # Если модуль не найден, создадим заглушку
    def is_at_office(lat, lon):
        return True, 0
    def format_distance(dist):
        return f"{dist:.0f} м"
    def validate_live_location_security(location):
        return True, "OK"
    def is_location_realistic(lat, lon):
        return True



user_private_router = Router()
user_private_router.message.filter(ChatTypeFilter(["private"]))


@user_private_router.message(CommandStart())
async def start_cmd(message: types.Message, session: AsyncSession):
    # Добавляем пользователя в таблицу User (для совместимости)
    await orm_add_user(
        session=session,
        user_id=message.from_user.id,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        phone=None
    )
    
    # Проверяем, привязан ли пользователь к сотруднику
    employee = await orm_get_employee_by_telegram_id(session, message.from_user.id)
    
    if employee:
        # Если уже привязан, показываем клавиатуру посещаемости
        await message.answer(
            f"Добро пожаловать, {employee.full_name}!\n"
            "Выберите действие:",
            reply_markup=get_attendance_keyboard()
        )
    else:
        # Если не привязан, показываем список сотрудников для выбора
        employees = await orm_get_all_employees(session)
        
        if not employees:
            await message.answer(
                "❌ В системе пока нет сотрудников.\n"
                "Обратитесь к HR или IT отделу для регистрации."
            )
            return
            
        await message.answer(
            "👋 Добро пожаловать в систему учета рабочего времени!\n\n"
            "Пожалуйста, выберите себя из списка сотрудников:",
            reply_markup=get_employee_selection_keyboard(employees)
        )


@user_private_router.callback_query(F.data.startswith("select_employee_"))
async def select_employee_callback(callback: CallbackQuery, session: AsyncSession):
    employee_id = int(callback.data.split("_")[-1])
    telegram_id = callback.from_user.id
    
    # Проверяем, не привязан ли уже этот telegram_id
    existing_employee = await orm_get_employee_by_telegram_id(session, telegram_id)
    if existing_employee:
        await callback.answer("Вы уже зарегистрированы в системе!", show_alert=True)
        return
    
    # Привязываем telegram_id к сотруднику
    success, message_text = await orm_link_employee_telegram(session, employee_id, telegram_id)
    
    if success:
        # Получаем данные сотрудника
        employee = await orm_get_employee_by_telegram_id(session, telegram_id)
        
        await callback.message.edit_text(
            f"✅ Вы успешно зарегистрированы как {employee.full_name}!\n\n"
            "Теперь вы можете отмечать посещаемость:",
            reply_markup=get_attendance_keyboard()
        )
    else:
        await callback.answer(message_text, show_alert=True)


@user_private_router.callback_query(F.data == "not_in_list")
async def not_in_list_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        "❌ Если вас нет в списке сотрудников, пожалуйста:\n\n"
        "📞 Обратитесь к HR отделу для добавления в систему\n"
        "💻 Или свяжитесь с IT отделом\n\n"
        "После добавления в систему вы сможете пользоваться ботом."
    )


@user_private_router.callback_query(F.data.startswith("attendance_"))
async def attendance_callback(callback: CallbackQuery, session: AsyncSession):
    check_type_str = callback.data.split("_")[-1]  # "in" или "out"
    telegram_id = callback.from_user.id
    
    # Получаем сотрудника
    employee = await orm_get_employee_by_telegram_id(session, telegram_id)
    if not employee:
        await callback.answer("❌ Вы не зарегистрированы в системе!", show_alert=True)
        return
    
    check_type = CheckTypeEnum.IN if check_type_str == "in" else CheckTypeEnum.OUT
    
    if check_type == CheckTypeEnum.IN:
        # Для "Пришел" запрашиваем live location
        await callback.message.edit_text(
            "📍 Для отметки прихода необходимо подтвердить ваше местоположение\n\n"
            "⚠️ ВАЖНО: Используйте только LIVE LOCATION!\n\n"
            "📋 Как отправить Live Location:\n"
            "1️⃣ Нажмите кнопку 📎 (скрепка)\n"
            "2️⃣ Выберите 'Геопозиция'\n"
            "3️⃣ Нажмите 'Поделиться Live Location'\n"
            "4️⃣ Выберите время (минимум 15 минут)\n"
            "5️⃣ Отправьте\n\n"
            "❌ Обычная геолокация НЕ принимается!",
            reply_markup=get_location_request_keyboard()
        )
    else:
        # Для "Ушел" сразу создаем запись
        attendance = await orm_create_attendance(
            session=session,
            employee_id=employee.id,
            check_type=check_type
        )
        
        await callback.message.edit_text(
            f"✅ {employee.full_name}, вы успешно отметились как УШЕЛ\n"
            f"🕐 Время: {attendance.check_time.strftime('%H:%M:%S')}\n\n"
            "Увидимся завтра! 👋",
            reply_markup=get_attendance_keyboard()
        )


@user_private_router.callback_query(F.data == "how_to_location")
async def how_to_location_callback(callback: CallbackQuery):
    """Подробная инструкция по отправке Live Location"""
    await callback.message.edit_text(
        "📍 ПОДРОБНАЯ ИНСТРУКЦИЯ:\n\n"
        "🔴 Для Android:\n"
        "1️⃣ Откройте чат с ботом\n"
        "2️⃣ Нажмите кнопку 📎 (вложения)\n"
        "3️⃣ Выберите 'Геопозиция'\n"
        "4️⃣ Нажмите 'Поделиться Live Location'\n"
        "5️⃣ Выберите время: 15 минут или больше\n"
        "6️⃣ Нажмите 'Отправить'\n\n"
        "🔵 Для iPhone:\n"
        "1️⃣ Нажмите '+' рядом с полем ввода\n"
        "2️⃣ Выберите 'Геопозиция'\n"
        "3️⃣ Нажмите 'Поделиться Live Location'\n"
        "4️⃣ Выберите время: 15 минут или больше\n"
        "5️⃣ Нажмите 'Отправить'\n\n"
        "⚠️ ВАЖНО: \n"
        "❌ НЕ используйте 'Отправить мою геопозицию'\n"
        "✅ Используйте только 'Live Location'\n\n"
        "💡 Live Location показывает ваше местоположение в реальном времени",
        reply_markup=get_location_request_keyboard()
    )


@user_private_router.callback_query(F.data == "location_sent")
async def location_sent_callback(callback: CallbackQuery):
    """Подтверждение что location отправлен"""
    await callback.message.edit_text(
        "⏳ Ожидаю ваш Live Location...\n\n"
        "Если вы уже отправили Live Location, он должен появиться в чате.\n\n"
        "❓ Если ничего не происходит:\n"
        "1. Проверьте, что отправили именно Live Location\n"
        "2. Убедитесь, что разрешили доступ к геолокации\n"
        "3. Попробуйте еще раз\n\n"
        "📞 При проблемах обратитесь к IT отделу",
        reply_markup=get_attendance_keyboard()
    )


@user_private_router.message(F.location)
async def handle_location(message: Message, session: AsyncSession):
    """Обработчик геолокации для отметки прихода"""
    telegram_id = message.from_user.id
    
    # Проверяем, что сообщение не forwarded
    if message.forward_date:
        await message.answer(
            "❌ Нельзя использовать forwarded геолокацию!\n\n"
            "Пожалуйста, отправьте ваш Live Location:",
            reply_markup=get_location_request_keyboard()
        )
        return
    
    # Проверяем, что это live location
    if not message.location.live_period:
        await message.answer(
            "❌ Необходимо отправить Live Location!\n\n"
            "Вы отправили обычную геолокацию, которая может быть неточной.\n\n"
            "📍 Пожалуйста, отправьте Live Location согласно инструкции:",
            reply_markup=get_location_request_keyboard()
        )
        return
    
    # Получаем сотрудника
    employee = await orm_get_employee_by_telegram_id(session, telegram_id)
    if not employee:
        await message.answer(
            "❌ Вы не зарегистрированы в системе!\n\n"
            "Используйте команду /start для регистрации."
        )
        return
    
    # Получаем координаты
    latitude = message.location.latitude
    longitude = message.location.longitude
    
    # Дополнительные проверки безопасности
    if not is_location_realistic(latitude, longitude):
        await message.answer(
            "❌ Координаты находятся вне допустимого региона!\n\n"
            "Убедитесь, что GPS включен и работает корректно.",
            reply_markup=get_location_request_keyboard()
        )
        return
    
    # Проверка на подозрительные координаты
    is_secure, security_msg = validate_live_location_security(message.location)
    if not is_secure:
        await message.answer(
            f"❌ Обнаружена попытка использования поддельной геолокации!\n\n"
            f"Причина: {security_msg}\n\n"
            "Пожалуйста, используйте реальный Live Location с вашего устройства.",
            reply_markup=get_location_request_keyboard()
        )
        return
    
    # Проверяем расстояние до офиса
    is_in_office, distance = is_at_office(latitude, longitude)
    
    if not is_in_office:
        await message.answer(
            f"❌ Вы находитесь слишком далеко от офиса!\n\n"
            f"📍 Расстояние до офиса: {format_distance(distance)}\n"
            f"🏢 Вам нужно подойти ближе к офису для отметки.\n\n"
            "Попробуйте еще раз, когда будете ближе к офису.",
            reply_markup=get_attendance_keyboard()
        )
        return
    
    # Создаем запись посещаемости
    attendance = await orm_create_attendance(
        session=session,
        employee_id=employee.id,
        check_type=CheckTypeEnum.IN,
        location_lat=str(latitude),
        location_lon=str(longitude)
    )
    
    await message.answer(
        f"✅ {employee.full_name}, вы успешно отметились как ПРИШЕЛ\n"
        f"🕐 Время: {attendance.check_time.strftime('%H:%M:%S')}\n"
        f"📍 Расстояние до офиса: {format_distance(distance)}\n"
        f"🎯 Live Location подтвержден\n\n"
        "Хорошего рабочего дня! 😊",
        reply_markup=get_attendance_keyboard()
    )
    

@user_private_router.message(F.text == "❌ Отмена")
async def cancel_location(message: Message, session: AsyncSession):
    """Отмена отправки геолокации"""
    telegram_id = message.from_user.id
    employee = await orm_get_employee_by_telegram_id(session, telegram_id)
    
    if employee:
        await message.answer(
            f"❌ Отметка прихода отменена.\n\n"
            f"{employee.full_name}, выберите действие:",
            reply_markup=get_attendance_keyboard()
        )
    else:
        await message.answer(
            "Отменено. Используйте /start для регистрации."
        )


@user_private_router.message(F.text == "📊 Мой статус") 
async def my_status(message: Message, session: AsyncSession):
    """Показать статус сотрудника"""
    telegram_id = message.from_user.id
    employee = await orm_get_employee_by_telegram_id(session, telegram_id)
    
    if not employee:
        await message.answer("❌ Вы не зарегистрированы в системе!")
        return
        
    # Здесь можно добавить логику для показа последних отметок
    await message.answer(
        f"👤 {employee.full_name}\n"
        f"💼 {employee.position.value if employee.position else 'Не указано'}\n"
        f"📱 Telegram ID: {employee.telegram_id}\n\n"
        "Для отметки используйте кнопки ниже:",
        reply_markup=get_attendance_keyboard()
    )


@user_private_router.message(F.text == "ℹ️ Помощь")
async def help_command(message: Message):
    """Справка по использованию бота"""
    await message.answer(
        "ℹ️ СПРАВКА ПО ИСПОЛЬЗОВАНИЮ БОТА\n\n"
        "🎯 ОСНОВНЫЕ ФУНКЦИИ:\n"
        "• ✅ Отметка прихода (с Live Location)\n"
        "• ❌ Отметка ухода (без геолокации)\n"
        "• 📊 Просмотр своего статуса\n\n"
        "📍 ТРЕБОВАНИЯ К ГЕОЛОКАЦИИ:\n"
        "• Только Live Location (НЕ обычная геолокация)\n"
        "• Находиться в радиусе офиса\n"
        "• Не использовать forwarded сообщения\n\n"
        "🔧 КОМАНДЫ:\n"
        "/start - Регистрация/главное меню\n\n"
        "❓ При проблемах обратитесь к IT отделу"
    )
    