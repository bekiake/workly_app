from datetime import date
from app.models.attendance import SourceEnum


def format_daily_report(report_data):
    """Форматирует ежедневный отчет для отправки в Telegram"""
    
    report_date = report_data['date']
    total = report_data['total_employees']
    attended = report_data['attended_count']
    absent_count = report_data['absent_count']
    late_count = report_data['late_count']
    on_time_count = report_data['on_time_count']
    
    # Заголовок отчета
    message = f"📊 ЕЖЕДНЕВНЫЙ ОТЧЕТ ПО ПОСЕЩАЕМОСТИ\n"
    message += f"📅 Дата: {report_date.strftime('%d.%m.%Y')}\n\n"
    
    # Общая статистика
    message += f"👥 Всего сотрудников: {total}\n"
    message += f"✅ Пришли на работу: {attended}\n"
    message += f"❌ Отсутствуют: {absent_count}\n"
    message += f"⏰ Опоздали: {late_count}\n"
    message += f"🎯 Пришли вовремя: {on_time_count}\n\n"
    
    # Процентная статистика
    if total > 0:
        attendance_rate = (attended / total) * 100
        message += f"📈 Процент посещаемости: {attendance_rate:.1f}%\n\n"
    
    # Список пришедших вовремя
    if report_data['on_time_employees']:
        message += "🎯 ПРИШЛИ ВОВРЕМЯ:\n"
        for emp_info in report_data['on_time_employees']:
            source_icon = "📱" if emp_info['source'] == SourceEnum.TELEGRAM else "💻"
            time_str = emp_info['check_time'].strftime('%H:%M')
            message += f"• {emp_info['employee'].full_name} - {time_str} {source_icon}\n"
        message += "\n"
    
    # Список опоздавших
    if report_data['late_employees']:
        message += "⏰ ОПОЗДАЛИ:\n"
        for emp_info in report_data['late_employees']:
            source_icon = "📱" if emp_info['source'] == SourceEnum.TELEGRAM else "💻"
            time_str = emp_info['check_time'].strftime('%H:%M')
            message += f"• {emp_info['employee'].full_name} - {time_str} {source_icon}\n"
        message += "\n"
    
    # Список отсутствующих
    if report_data['absent_employees']:
        message += "❌ ОТСУТСТВУЮТ:\n"
        for employee in report_data['absent_employees']:
            message += f"• {employee.full_name}\n"
        message += "\n"
    
    message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    message += "🤖 Отчет сгенерирован автоматически"
    
    return message


def format_summary_stats(report_data):
    """Краткая статистика для быстрого просмотра"""
    total = report_data['total_employees']
    attended = report_data['attended_count']
    attendance_rate = (attended / total * 100) if total > 0 else 0
    
    return (f"📊 {report_data['date'].strftime('%d.%m')} | "
            f"👥{attended}/{total} ({attendance_rate:.0f}%) | "
            f"⏰{report_data['late_count']} опозд.")