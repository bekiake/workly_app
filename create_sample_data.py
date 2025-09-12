import asyncio
import random
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import DATABASE_URL
from app.models.employee import Employee, PositionEnum
from app.models.attendance import Attendance, CheckTypeEnum
from app.utils.timezone import get_tashkent_time, TASHKENT_TZ, get_tashkent_time_naive
from app.core.database import Base

# Async engine yaratish
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# Sample ishchilar ma'lumotlari
SAMPLE_EMPLOYEES = [
    {
        "full_name": "Ahmedov Bobur Karimovich",
        "position": PositionEnum.MANAGER,
        "phone": "+998901234567",
        "base_salary": Decimal("8000000")
    },
    {
        "full_name": "Karimova Nilufar Rustamovna",
        "position": PositionEnum.DEVELOPER,
        "phone": "+998901234568",
        "base_salary": Decimal("6500000")
    },
    {
        "full_name": "Toshmatov Aziz Xurshidovich",
        "position": PositionEnum.DEVELOPER,
        "phone": "+998901234569",
        "base_salary": Decimal("7000000")
    },
    {
        "full_name": "Raxmonova Dilfuza Abrorovna",
        "position": PositionEnum.DESIGNER,
        "phone": "+998901234570",
        "base_salary": Decimal("5500000")
    },
    {
        "full_name": "Nazarov Sherzod Anvarovich",
        "position": PositionEnum.HR,
        "phone": "+998901234571",
        "base_salary": Decimal("5000000")
    },
    {
        "full_name": "Yusupova Gulnoza Davronovna",
        "position": PositionEnum.ACCOUNTANT,
        "phone": "+998901234572",
        "base_salary": Decimal("4500000")
    },
    {
        "full_name": "Mirzayev Jasur Toxirovich",
        "position": PositionEnum.SALES,
        "phone": "+998901234573",
        "base_salary": Decimal("4000000")
    },
    {
        "full_name": "Qodirova Shoira Botirovna",
        "position": PositionEnum.MARKETING,
        "phone": "+998901234574",
        "base_salary": Decimal("4200000")
    },
    {
        "full_name": "Abdullayev Sardor Ilhomovich",
        "position": PositionEnum.SUPPORT,
        "phone": "+998901234575",
        "base_salary": Decimal("3500000")
    },
    {
        "full_name": "Xolmatova Munisa Shavkatovna",
        "position": PositionEnum.INTERN,
        "phone": "+998901234576",
        "base_salary": Decimal("2000000")
    }
]

async def create_tables():
    """Ma'lumotlar bazasi jadvallarini yaratish"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Jadvallar muvaffaqiyatli yaratildi!")

async def create_sample_employees():
    """Sample ishchilar yaratish"""
    async with AsyncSessionLocal() as session:
        try:
            employees = []
            for emp_data in SAMPLE_EMPLOYEES:
                # Добавляем created_at для каждого сотрудника
                emp_data_with_time = emp_data.copy()
                emp_data_with_time['created_at'] = get_tashkent_time_naive()
                
                employee = Employee(**emp_data_with_time)
                employees.append(employee)
                session.add(employee)
            
            await session.commit()
            print(f"✅ {len(employees)} ta ishchi muvaffaqiyatli qo'shildi!")
            return employees
        except Exception as e:
            await session.rollback()
            print(f"❌ Ishchilarni qo'shishda xatolik: {e}")
            return []

async def create_sample_attendance(employees):
    """Sample davomat ma'lumotlarini yaratish (oxirgi 30 kun uchun)"""
    async with AsyncSessionLocal() as session:
        try:
            attendance_records = []
            
            # Oxirgi 30 kun uchun
            for day_offset in range(30):
                current_date = get_tashkent_time_naive() - timedelta(days=day_offset)
                
                # Faqat ish kunlari uchun (dushanba-juma)
                if current_date.weekday() < 5:  # 0-6, 0=Monday, 6=Sunday
                    
                    for employee in employees:
                        # Tasodifiy ravishda ishchi kelishi yoki kelmasligi (90% ehtimol)
                        if random.random() < 0.9:
                            
                            # Kelish vaqti (8:00-10:00 oralig'ida)
                            check_in_hour = random.randint(8, 9)
                            check_in_minute = random.randint(0, 59)
                            
                            # Agar 9:00 dan keyin kelsa, kechikkan hisoblanadi
                            is_late = check_in_hour >= 9
                            
                            check_in_time = current_date.replace(
                                hour=check_in_hour,
                                minute=check_in_minute,
                                second=0,
                                microsecond=0
                            )
                            
                            # Kelish
                            attendance_in = Attendance(
                                employee_id=employee.id,
                                check_type=CheckTypeEnum.IN,
                                check_time=check_in_time,
                                is_late=is_late
                            )
                            attendance_records.append(attendance_in)
                            session.add(attendance_in)
                            
                            # Ketish vaqti (17:00-19:00 oralig'ida)
                            # Ba'zida erta ketishi mumkin (20% ehtimol)
                            if random.random() < 0.8:
                                check_out_hour = random.randint(17, 18)
                                check_out_minute = random.randint(0, 59)
                                is_early = check_out_hour < 17 or (check_out_hour == 17 and check_out_minute < 30)
                            else:
                                # Erta ketish
                                check_out_hour = random.randint(15, 16)
                                check_out_minute = random.randint(0, 59)
                                is_early = True
                            
                            check_out_time = current_date.replace(
                                hour=check_out_hour,
                                minute=check_out_minute,
                                second=0,
                                microsecond=0
                            )
                            
                            # Ketish
                            attendance_out = Attendance(
                                employee_id=employee.id,
                                check_type=CheckTypeEnum.OUT,
                                check_time=check_out_time,
                                is_early_departure=is_early
                            )
                            attendance_records.append(attendance_out)
                            session.add(attendance_out)
            
            await session.commit()
            print(f"✅ {len(attendance_records)} ta davomat yozuvi muvaffaqiyatli qo'shildi!")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Davomat ma'lumotlarini qo'shishda xatolik: {e}")

async def main():
    """Asosiy funksiya"""
    print("🚀 Sample ma'lumotlar yaratish boshlandi...")
    
    # 1. Jadvallarni yaratish
    await create_tables()
    
    # 2. Ishchilarni yaratish
    employees = await create_sample_employees()
    
    if employees:
        # 3. Davomat ma'lumotlarini yaratish
        await create_sample_attendance(employees)
    
    print("🎉 Barcha sample ma'lumotlar muvaffaqiyatli yaratildi!")
    
    # Engine ni yopish
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
