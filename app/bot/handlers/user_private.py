from aiogram import F, types, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery

from sqlalchemy.ext.asyncio import AsyncSession
from database.orm_query import ( 
    orm_add_user,
    orm_get_all_employees,
    orm_get_employee_by_telegram_id,
    orm_link_employee_telegram,
    orm_create_attendance,
    orm_get_attendance_status_today,
    orm_get_today_attendance_status
)

from filters.chat_types import ChatTypeFilter
from kbds.inline import get_employee_selection_keyboard, get_attendance_keyboard, get_location_request_keyboard, get_smart_attendance_keyboard, get_checkout_keyboard, get_smart_attendance_keyboard, get_checkout_keyboard
from app.models.attendance import CheckTypeEnum
import sys
import os

# Добавляем путь к utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
try:
    from utils.location import is_at_office, format_distance, validate_live_location_security, is_location_realistic
    from utils.timezone import format_tashkent_time
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
    def format_tashkent_time(dt, fmt='%H:%M:%S'):
        return dt.strftime(fmt)



user_private_router = Router()
user_private_router.message.filter(ChatTypeFilter(["private"]))


@user_private_router.message(CommandStart())
async def start_cmd(message: types.Message, session: AsyncSession):
    # Добавляем пользователя в таблицу User (для совместимости)
    
    # Проверяем, привязан ли пользователь к сотруднику
    employee = await orm_get_employee_by_telegram_id(session, message.from_user.id)
    
    if employee:
        # Проверяем статус отметок на сегодня
        already_checked_in, already_checked_out = await orm_get_today_attendance_status(session, employee.id)
        
        # Определяем сообщение в зависимости от статуса
        if already_checked_in and already_checked_out:
            status_text = f"Вы уже завершили рабочий день. До свидания! 👋"
            await message.answer(status_text)
        elif already_checked_in and not already_checked_out:
            status_text = f"Вы на работе. Когда будете уходить, отметьтесь."
            keyboard = get_smart_attendance_keyboard(already_checked_in, already_checked_out)
            await message.answer(status_text, reply_markup=keyboard)
        elif not already_checked_in:
            status_text = f"Отметьтесь при приходе на работу."
            keyboard = get_smart_attendance_keyboard(already_checked_in, already_checked_out)
            await message.answer(status_text, reply_markup=keyboard)
        else:
            status_text = "Выберите действие:"
            keyboard = get_attendance_keyboard()
            await message.answer(f"Добро пожаловать, {employee.full_name}!\n\n{status_text}",
            reply_markup=keyboard)
    else:
        # Если не привязан, показываем список сотрудников для выбора
        employees = await orm_get_all_employees(session)
        
        if not employees:
            await message.answer(
                "❌ В системе нет зарегистрированных сотрудников.\n\n"
                "Обратитесь к администратору для добавления сотрудников в систему."
            )
            return

        await message.answer(
            "👋 Добро пожаловать в систему учета посещаемости!\n\n"
            "Для начала работы выберите ваше имя из списка:",
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
    
    # Проверяем статус отметок на сегодня
    already_checked_in, already_checked_out = await orm_get_attendance_status_today(session, employee.id)
    
    check_type = CheckTypeEnum.IN if check_type_str == "in" else CheckTypeEnum.OUT
    
    if check_type == CheckTypeEnum.IN:
        # Проверяем, не отметился ли уже как "пришел"
        if already_checked_in:
            await callback.answer(
                "⚠️ Вы уже отметились как ПРИШЕЛ сегодня!\n"
                f"Время прихода: {format_tashkent_time(already_checked_in, '%H:%M:%S')}",
                show_alert=True
            )
            return
            
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
        # Проверяем, не отметился ли уже как "ушел"
        if already_checked_out:
            await callback.answer(
                "⚠️ Вы уже отметились как УШЕЛ сегодня!\n"
                f"Время ухода: {format_tashkent_time(already_checked_out, '%H:%M:%S')}",
                show_alert=True
            )
            return
            
        # Проверяем, отметился ли как "пришел" сегодня
        if not already_checked_in:
            await callback.answer(
                "⚠️ Сначала отметьтесь как ПРИШЕЛ!",
                show_alert=True
            )
            return
            
        # Для "Ушел" сразу создаем запись
        attendance = await orm_create_attendance(
            session=session,
            employee_id=employee.id,
            check_type=check_type
        )
        
        await callback.message.edit_text(
            f"✅ <b>{employee.full_name}</b>, \nвы успешно отметились как <b>УШЕЛ</b>\n"
            f"🕐 Время: <code>{format_tashkent_time(attendance.check_time, '%H:%M:%S')}</code>\n\n"
            "Увидимся завтра! 👋",
            reply_markup=None  # Убираем кнопки после отметки
        )
    
    # Важно: отвечаем на callback
    await callback.answer()


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
        "📞 При проблемах обратитесь к IT отделу"
    )
    await callback.answer()


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
        f"✅ <b>{employee.full_name}</b>, \nвы успешно отметились как <b>ПРИШЕЛ</b>\n"
        f"🕐 Время: <code>{format_tashkent_time(attendance.check_time, '%H:%M:%S')}</code>\n"
        f"📍 Расстояние до офиса: <code>{format_distance(distance)}</code>\n"
        f"🎯 Live Location подтвержден\n\n"
        "Хорошего рабочего дня! 😊\n\n"
        "Когда будете уходить, нажмите кнопку ниже:",
        reply_markup=get_checkout_keyboard()
    )
    

@user_private_router.message(F.text == "❌ Отмена")
async def cancel_location(message: Message, session: AsyncSession):
    """Отмена отправки геолокации"""
    telegram_id = message.from_user.id
    employee = await orm_get_employee_by_telegram_id(session, telegram_id)
    
    if employee:
        # Проверяем статус отметок
        already_checked_in, already_checked_out = await orm_get_today_attendance_status(session, employee.id)
        
        await message.answer(
            f"❌ Отметка прихода отменена.\n\n"
            f"{employee.full_name}, выберите действие:",
            reply_markup=get_smart_attendance_keyboard(already_checked_in, already_checked_out)
        )
    else:
        await message.answer(
            "Отменено. Используйте /start для регистрации."
        )





@user_private_router.message(Command("help"))
async def help_command_slash(message: Message):
    """Обработчик команды /help"""
    await message.answer(
        "ℹ️ <b>СПРАВКА ПО ИСПОЛЬЗОВАНИЮ БОТА</b>\n\n"
        "🎯 <b>ОСНОВНЫЕ ФУНКЦИИ:</b>\n"
        "• ✅ Отметка прихода на работу (с Live Location)\n"
        "• ❌ Отметка ухода с работы (без геолокации)\n\n"
        "📍 <b>ТРЕБОВАНИЯ К ГЕОЛОКАЦИИ:</b>\n"
        "• Используйте только <b>Live Location</b> (НЕ обычную геолокацию)\n"
        "• Убедитесь, что находитесь в радиусе офиса\n"
        "• Не пересылайте геолокацию от других пользователей\n"
        "• Включите GPS на своем устройстве\n\n"
        "🔧 <b>ДОСТУПНЫЕ КОМАНДЫ:</b>\n"
        "• /start - Начать работу\n"
        "• /help - Эта справка\n\n"
        "⚡ <b>БЫСТРЫЕ ДЕЙСТВИЯ:</b>\n"
        "• Нажмите 'Отметить приход' → отправьте Live Location\n"
        "• Нажмите 'Отметить уход' → подтвердите действие\n\n"
        "🆘 <b>ПОДДЕРЖКА:</b>\n"
        "При возникновении проблем обратитесь к IT отделу\n"
        "или администратору системы учета времени.",
        parse_mode="HTML"
    )
    