"""
Bot uchun model importlari
Asosiy app modellariga murojaat qilish uchun
"""
import sys
import os

# Bot root papkasidan asosiy app papkasiga yo'l
bot_root = os.path.dirname(os.path.abspath(__file__))
app_root = os.path.join(bot_root, "..", "..")
sys.path.insert(0, app_root)

# Asosiy app modellarini import qilish
try:
    from app.models.employee import Employee
    from app.models.attendance import Attendance
    print("✅ Asosiy app modellari muvaffaqiyatli import qilindi")
except ImportError as e:
    print(f"❌ Modellarni import qilishda xato: {e}")
    # Fallback modellari
    Employee = None
    Attendance = None

__all__ = ['Employee', 'Attendance']
