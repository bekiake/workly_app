from aiogram.types import BotCommand


# Обычные пользователи
private = [
    BotCommand(command='start', description='📝 Отметить посещение'),
    BotCommand(command='help', description='ℹ️ Помощь')
]

# Администраторы
admin = [
    BotCommand(command='start', description='📝 Отметить посещение'),
    BotCommand(command='help', description='ℹ️ Помощь'),
    BotCommand(command='admin', description='👨‍💼 Админ панель'),
    BotCommand(command='report', description='📋 Отчет за сегодня'),
    BotCommand(command='week_stats', description='📈 Статистика за неделю'),
    BotCommand(command='reports', description='📊 Excel отчеты'),
    BotCommand(command='employees', description='👥 Управление сотрудниками'),
    BotCommand(command='add_employee', description='➕ Добавить сотрудника'),
    BotCommand(command='settings', description='⚙️ Настройки'),
]