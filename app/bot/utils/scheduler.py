import asyncio
import os
from datetime import datetime, time
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from database.engine import session_maker
from database.orm_query import orm_get_daily_attendance_report
from utils.reports import format_daily_report


class DailyReportScheduler:
    def __init__(self, bot: Bot, group_chat_id: str):
        self.bot = bot
        self.group_chat_id = group_chat_id
        self.report_time = time(18, 0)  # 18:00 каждый день
        
    async def send_daily_report(self):
        """Отправляет ежедневный отчет в группу"""
        try:
            async with session_maker() as session:
                report_data = await orm_get_daily_attendance_report(session)
                report_text = format_daily_report(report_data)
                
                await self.bot.send_message(
                    chat_id=self.group_chat_id,
                    text=report_text
                )
                
                print(f"✅ Ежедневный отчет отправлен в группу {self.group_chat_id}")
                
        except Exception as e:
            print(f"❌ Ошибка при отправке ежедневного отчета: {str(e)}")
    
    async def schedule_daily_reports(self):
        """Планировщик ежедневных отчетов"""
        while True:
            now = datetime.now()
            current_time = now.time()
            
            # Проверяем, наступило ли время отправки отчета
            if (current_time.hour == self.report_time.hour and 
                current_time.minute == self.report_time.minute and
                now.weekday() < 5):  # Только в рабочие дни (Пн-Пт)
                
                await self.send_daily_report()
                
                # Ждем минуту, чтобы не отправлять дублирующие отчеты
                await asyncio.sleep(60)
            
            # Проверяем каждую минуту
            await asyncio.sleep(60)
    
    def start_scheduler(self):
        """Запускает планировщик в фоновом режиме"""
        asyncio.create_task(self.schedule_daily_reports())


# Функция для мгновенной отправки отчета (для тестирования)
async def send_test_report(bot: Bot, group_chat_id: str):
    """Отправляет тестовый отчет немедленно"""
    try:
        async with session_maker() as session:
            report_data = await orm_get_daily_attendance_report(session)
            report_text = format_daily_report(report_data)
            
            await bot.send_message(
                chat_id=group_chat_id,
                text=f"🧪 ТЕСТОВЫЙ ОТЧЕТ\n\n{report_text}"
            )
            
            print(f"✅ Тестовый отчет отправлен в группу {group_chat_id}")
            
    except Exception as e:
        print(f"❌ Ошибка при отправке тестового отчета: {str(e)}")